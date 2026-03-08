"""AWS NHI Scanner — discovers IAM roles used by non-human principals,
cross-references CloudTrail via Athena, and provides quarantine capability.

Security context: This module reads IAM policies and CloudTrail data to
identify over-privileged service roles. The quarantine function applies a
Deny-All permissions boundary — a reversible, non-destructive kill switch.
"""

import json
import logging
import re
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import AWS_DEFAULT_REGION, ATHENA_DATABASE, ATHENA_OUTPUT_BUCKET
from database import upsert_identity, mark_quarantined

logger = logging.getLogger("ghostprotocol.scanner")

# Non-human trust principals we care about
NHI_PRINCIPALS = {
    "ec2.amazonaws.com",
    "lambda.amazonaws.com",
}

QUARANTINE_POLICY_NAME = "GhostProtocol-Quarantine"
QUARANTINE_POLICY_DOC = json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "GhostProtocolDenyAll",
        "Effect": "Deny",
        "Action": "*",
        "Resource": "*",
    }],
})


# Regex that matches valid IAM role ARNs
_ROLE_ARN_RE = re.compile(
    r"^arn:aws:iam::\d{12}:role/[\w+=,.@/-]+$"
)


def _validate_role_arn(arn: str) -> bool:
    """Return True if *arn* is a well-formed IAM role ARN."""
    return bool(_ROLE_ARN_RE.match(arn))


def _get_iam_client():
    return boto3.client("iam", region_name=AWS_DEFAULT_REGION)


def _get_athena_client():
    return boto3.client("athena", region_name=AWS_DEFAULT_REGION)


# ---------------------------------------------------------------------------
# 1. Discover NHI roles
# ---------------------------------------------------------------------------

def _is_nhi_role(role: dict) -> bool:
    """Return True if the role's trust policy allows a known NHI principal."""
    trust = role.get("AssumeRolePolicyDocument", {})
    for stmt in trust.get("Statement", []):
        principal = stmt.get("Principal", {})
        services = principal.get("Service", [])
        if isinstance(services, str):
            services = [services]
        if NHI_PRINCIPALS.intersection(services):
            return True
    return False


def _list_nhi_roles() -> list[dict]:
    """Paginate through all IAM roles and return those with NHI trust."""
    iam = _get_iam_client()
    paginator = iam.get_paginator("list_roles")
    nhi_roles = []
    for page in paginator.paginate():
        for role in page["Roles"]:
            if _is_nhi_role(role):
                nhi_roles.append(role)
    logger.info("Discovered %d NHI roles", len(nhi_roles))
    return nhi_roles


# ---------------------------------------------------------------------------
# 2. Fetch policies for a role
# ---------------------------------------------------------------------------

def _get_allowed_actions(role_name: str) -> list[str]:
    """Collect all allowed actions from managed + inline policies on a role.

    Extracts Action lists from every policy statement. Handles pagination
    and gracefully skips policies the caller cannot read.
    """
    iam = _get_iam_client()
    actions: set[str] = set()

    # -- Managed policies --
    try:
        paginator = iam.get_paginator("list_attached_role_policies")
        for page in paginator.paginate(RoleName=role_name):
            for pol in page["AttachedPolicies"]:
                try:
                    version = iam.get_policy(PolicyArn=pol["PolicyArn"])["Policy"]["DefaultVersionId"]
                    doc = iam.get_policy_version(
                        PolicyArn=pol["PolicyArn"],
                        VersionId=version,
                    )["PolicyVersion"]["Document"]
                    for stmt in doc.get("Statement", []):
                        act = stmt.get("Action", [])
                        if isinstance(act, str):
                            act = [act]
                        actions.update(act)
                except ClientError as exc:
                    logger.warning("Cannot read policy %s: %s", pol["PolicyArn"], exc)
    except ClientError as exc:
        logger.warning("Cannot list managed policies for %s: %s", role_name, exc)

    # -- Inline policies --
    try:
        paginator = iam.get_paginator("list_role_policies")
        for page in paginator.paginate(RoleName=role_name):
            for policy_name in page["PolicyNames"]:
                try:
                    doc = iam.get_role_policy(
                        RoleName=role_name,
                        PolicyName=policy_name,
                    )["PolicyDocument"]
                    for stmt in doc.get("Statement", []):
                        act = stmt.get("Action", [])
                        if isinstance(act, str):
                            act = [act]
                        actions.update(act)
                except ClientError as exc:
                    logger.warning("Cannot read inline policy %s: %s", policy_name, exc)
    except ClientError as exc:
        logger.warning("Cannot list inline policies for %s: %s", role_name, exc)

    return sorted(actions)


# ---------------------------------------------------------------------------
# 3. Query CloudTrail via Athena for actually-used actions
# ---------------------------------------------------------------------------

def _query_used_actions(role_arn: str) -> list[str]:
    """Query Athena for API actions invoked by *role_arn* in the last 30 days.

    Returns a deduplicated, sorted list of 'service:Action' strings.
    Gracefully returns an empty list on query failure.
    """
    athena = _get_athena_client()

    # Validate ARN format before embedding in SQL
    if not _validate_role_arn(role_arn):
        logger.warning("Invalid role ARN format, skipping Athena query: %s", role_arn)
        return []

    query = (
        f"SELECT DISTINCT eventsource || ':' || eventname AS action "
        f"FROM {ATHENA_DATABASE}.cloudtrail_logs "
        f"WHERE useridentity.arn = '{role_arn}' "
        f"AND eventtime > date_add('day', -30, now()) "
        f"ORDER BY action"
    )

    try:
        execution = athena.start_query_execution(
            QueryString=query,
            ResultConfiguration={"OutputLocation": ATHENA_OUTPUT_BUCKET},
        )
        execution_id = execution["QueryExecutionId"]

        # Poll until complete (with back-off)
        for wait in (1, 2, 4, 8, 16, 30):
            status = athena.get_query_execution(QueryExecutionId=execution_id)
            state = status["QueryExecution"]["Status"]["State"]
            if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            time.sleep(wait)

        if state != "SUCCEEDED":
            logger.warning("Athena query for %s ended with state %s", role_arn, state)
            return []

        # Fetch results (paginated)
        actions: list[str] = []
        paginator = athena.get_paginator("get_query_results")
        first = True
        for page in paginator.paginate(QueryExecutionId=execution_id):
            for row in page["ResultSet"]["Rows"]:
                if first:          # skip header row
                    first = False
                    continue
                val = row["Data"][0].get("VarCharValue", "")
                if val:
                    actions.append(val)

        logger.info("Role %s used %d distinct actions in last 30 days", role_arn, len(actions))
        return actions

    except ClientError as exc:
        logger.warning("Athena query failed for %s: %s", role_arn, exc)
        return []


# ---------------------------------------------------------------------------
# Public: full scan
# ---------------------------------------------------------------------------

def get_nhi_profiles() -> list[dict[str, Any]]:
    """Scan AWS for NHI roles, enrich with policy & usage data, persist to DB.

    Returns a list of profile dicts with keys:
      arn, name, type, trust_principals, allowed_actions,
      used_actions, last_activity
    """
    roles = _list_nhi_roles()
    profiles: list[dict[str, Any]] = []

    for role in roles:
        arn = role["Arn"]
        name = role["RoleName"]
        trust = role.get("AssumeRolePolicyDocument", {})

        # Determine principal type label
        principals: list[str] = []
        for stmt in trust.get("Statement", []):
            svc = stmt.get("Principal", {}).get("Service", [])
            if isinstance(svc, str):
                svc = [svc]
            principals.extend(svc)

        role_type = "EC2" if "ec2.amazonaws.com" in principals else "Lambda"

        allowed = _get_allowed_actions(name)
        used = _query_used_actions(arn)

        profile = {
            "arn": arn,
            "name": name,
            "type": role_type,
            "trust_principals": principals,
            "allowed_actions": allowed,
            "used_actions": used,
            "last_activity": role.get("RoleLastUsed", {}).get("LastUsedDate", "").isoformat()
                if role.get("RoleLastUsed", {}).get("LastUsedDate") else None,
            "is_quarantined": False,
            "risk_score": 0,  # will be filled by analyzer
        }

        # Persist to Supabase
        try:
            upsert_identity(profile)
        except Exception:
            logger.exception("Failed to persist identity %s", arn)

        profiles.append(profile)

    logger.info("Scan complete — %d NHI profiles collected", len(profiles))
    return profiles


# ---------------------------------------------------------------------------
# 4. Quarantine — the "Kill Switch"
# ---------------------------------------------------------------------------

def _ensure_quarantine_policy() -> str:
    """Create the GhostProtocol-Quarantine managed policy if it doesn't exist.

    Returns the policy ARN.
    """
    iam = _get_iam_client()

    # Check if it already exists
    try:
        sts = boto3.client("sts", region_name=AWS_DEFAULT_REGION)
        account_id = sts.get_caller_identity()["Account"]
        policy_arn = f"arn:aws:iam::{account_id}:policy/{QUARANTINE_POLICY_NAME}"
        iam.get_policy(PolicyArn=policy_arn)
        logger.debug("Quarantine policy already exists: %s", policy_arn)
        return policy_arn
    except iam.exceptions.NoSuchEntityException:
        pass

    # Create it
    response = iam.create_policy(
        PolicyName=QUARANTINE_POLICY_NAME,
        PolicyDocument=QUARANTINE_POLICY_DOC,
        Description="GhostProtocol Deny-All quarantine boundary policy",
    )
    policy_arn = response["Policy"]["Arn"]
    logger.info("Created quarantine policy %s", policy_arn)
    return policy_arn


def quarantine_identity(arn: str) -> dict[str, Any]:
    """Quarantine an IAM role by attaching a Deny-All permissions boundary.

    This is a non-destructive kill switch: the role still exists but all
    API calls made under it will be denied. Reversible by removing the
    permissions boundary.

    Steps:
        1. Ensure the GhostProtocol-Quarantine policy exists.
        2. Attach it as a Permissions Boundary on the target role.
        3. Update the Supabase record.
    """
    iam = _get_iam_client()
    policy_arn = _ensure_quarantine_policy()

    # Validate and extract role name from ARN
    if not _validate_role_arn(arn):
        raise ValueError(f"Invalid IAM role ARN format: {arn}")
    role_name = arn.rsplit("/", 1)[-1]

    try:
        iam.put_role_permissions_boundary(
            RoleName=role_name,
            PermissionsBoundary=policy_arn,
        )
        logger.info("Permissions boundary applied to %s", role_name)
    except ClientError as exc:
        logger.error("Failed to set permissions boundary on %s: %s", role_name, exc)
        raise

    # Update database
    mark_quarantined(arn)

    return {
        "arn": arn,
        "quarantined": True,
        "boundary_policy": policy_arn,
    }

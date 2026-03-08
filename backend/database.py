"""Supabase database client for GhostProtocol.

Manages connection to Supabase and provides helper functions
for persisting NHI identity audit data.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger("ghostprotocol.database")

_client: Client | None = None


def get_client() -> Client:
    """Return a singleton Supabase client instance."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized")
    return _client


# ---------------------------------------------------------------------------
# Identity CRUD helpers
# ---------------------------------------------------------------------------

def upsert_identity(identity: dict[str, Any]) -> dict:
    """Insert or update an NHI identity record.

    The `identities` table is expected to have at least:
      arn (text, PK), name, type, trust_principals, allowed_actions,
      used_actions, risk_score, is_quarantined, last_activity, updated_at
    """
    identity["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = (
        get_client()
        .table("identities")
        .upsert(identity, on_conflict="arn")
        .execute()
    )
    logger.debug("Upserted identity %s", identity.get("arn"))
    return result.data


def get_all_identities() -> list[dict]:
    """Fetch every identity row ordered by risk_score descending."""
    result = (
        get_client()
        .table("identities")
        .select("*")
        .order("risk_score", desc=True)
        .execute()
    )
    return result.data


def get_identity(arn: str) -> dict | None:
    """Fetch a single identity by ARN."""
    result = (
        get_client()
        .table("identities")
        .select("*")
        .eq("arn", arn)
        .maybe_single()
        .execute()
    )
    return result.data


def mark_quarantined(arn: str) -> dict:
    """Set is_quarantined = true and log the timestamp."""
    result = (
        get_client()
        .table("identities")
        .update({
            "is_quarantined": True,
            "quarantined_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("arn", arn)
        .execute()
    )
    logger.info("Marked %s as quarantined in database", arn)
    return result.data

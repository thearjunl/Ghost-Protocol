"""Tests for the GhostProtocol backend.

Covers scanner helpers, analyzer JSON parsing, and API endpoint smoke tests.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# scanner.py unit tests
# ---------------------------------------------------------------------------

class TestIsNhiRole:
    """Tests for scanner._is_nhi_role()."""

    def test_ec2_trust_is_nhi(self):
        from scanner import _is_nhi_role

        role = {
            "AssumeRolePolicyDocument": {
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }]
            }
        }
        assert _is_nhi_role(role) is True

    def test_lambda_trust_is_nhi(self):
        from scanner import _is_nhi_role

        role = {
            "AssumeRolePolicyDocument": {
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }]
            }
        }
        assert _is_nhi_role(role) is True

    def test_user_trust_is_not_nhi(self):
        from scanner import _is_nhi_role

        role = {
            "AssumeRolePolicyDocument": {
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                    "Action": "sts:AssumeRole",
                }]
            }
        }
        assert _is_nhi_role(role) is False

    def test_multi_service_trust(self):
        from scanner import _is_nhi_role

        role = {
            "AssumeRolePolicyDocument": {
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {
                        "Service": [
                            "s3.amazonaws.com",
                            "ec2.amazonaws.com",
                        ]
                    },
                    "Action": "sts:AssumeRole",
                }]
            }
        }
        assert _is_nhi_role(role) is True

    def test_empty_trust(self):
        from scanner import _is_nhi_role
        assert _is_nhi_role({}) is False


class TestArnValidation:
    """Tests for scanner._validate_role_arn()."""

    def test_valid_arn(self):
        from scanner import _validate_role_arn

        assert _validate_role_arn("arn:aws:iam::123456789012:role/MyRole") is True

    def test_invalid_arn_no_role(self):
        from scanner import _validate_role_arn

        assert _validate_role_arn("arn:aws:s3:::my-bucket") is False

    def test_injection_attempt(self):
        from scanner import _validate_role_arn

        assert _validate_role_arn("'; DROP TABLE cloudtrail_logs; --") is False

    def test_empty_string(self):
        from scanner import _validate_role_arn

        assert _validate_role_arn("") is False


# ---------------------------------------------------------------------------
# analyzer.py unit tests
# ---------------------------------------------------------------------------

class TestExtractJson:
    """Tests for analyzer._extract_json()."""

    def test_clean_json(self):
        from analyzer import _extract_json

        raw = '{"risk_score": 75, "unused_actions": [], "recommended_policy": {}, "summary": "ok"}'
        result = _extract_json(raw)
        assert result["risk_score"] == 75

    def test_markdown_fenced_json(self):
        from analyzer import _extract_json

        raw = 'Here is the result:\n```json\n{"risk_score": 50, "unused_actions": [], "recommended_policy": {}, "summary": "ok"}\n```\n'
        result = _extract_json(raw)
        assert result["risk_score"] == 50

    def test_json_with_surrounding_text(self):
        from analyzer import _extract_json

        raw = 'Sure! Here is the policy:\n{"risk_score": 30, "unused_actions": ["s3:*"], "recommended_policy": {}, "summary": "reduced"}\nLet me know if you need more.'
        result = _extract_json(raw)
        assert result["risk_score"] == 30

    def test_no_json_raises(self):
        from analyzer import _extract_json

        with pytest.raises(ValueError, match="Could not parse"):
            _extract_json("This response has no JSON at all.")


# ---------------------------------------------------------------------------
# FastAPI endpoint smoke tests
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """Smoke test for the /health endpoint."""

    def test_health_returns_ok(self):
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestIdentitiesEndpoint:
    """Tests for /identities with mocked database."""

    @patch("main.get_all_identities")
    def test_list_identities(self, mock_get_all: MagicMock):
        from fastapi.testclient import TestClient
        from main import app

        mock_get_all.return_value = [
            {"arn": "arn:aws:iam::123:role/TestRole", "name": "TestRole",
             "risk_score": 85, "is_quarantined": False}
        ]
        client = TestClient(app)
        response = client.get("/identities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "TestRole"

    @patch("main.get_all_identities")
    def test_list_identities_db_error(self, mock_get_all: MagicMock):
        from fastapi.testclient import TestClient
        from main import app

        mock_get_all.side_effect = RuntimeError("DB down")
        client = TestClient(app)
        response = client.get("/identities")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# /identities/{arn} endpoint tests
# ---------------------------------------------------------------------------

class TestGetSingleIdentityEndpoint:
    """Tests for /identities/{arn} endpoint."""

    @patch("main.get_identity")
    def test_get_identity_found(self, mock_get: MagicMock):
        from fastapi.testclient import TestClient
        from main import app

        mock_get.return_value = {
            "arn": "arn:aws:iam::123456789012:role/MyRole",
            "name": "MyRole",
            "risk_score": 42,
            "is_quarantined": False,
        }
        client = TestClient(app)
        response = client.get("/identities/arn:aws:iam::123456789012:role/MyRole")
        assert response.status_code == 200
        assert response.json()["name"] == "MyRole"

    @patch("main.get_identity")
    def test_get_identity_not_found(self, mock_get: MagicMock):
        from fastapi.testclient import TestClient
        from main import app

        mock_get.return_value = None
        client = TestClient(app)
        response = client.get("/identities/arn:aws:iam::123456789012:role/Nope")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# /scan endpoint tests
# ---------------------------------------------------------------------------

class TestScanEndpoint:
    """Tests for POST /scan."""

    @patch("main.get_nhi_profiles")
    def test_scan_success(self, mock_scan: MagicMock):
        from fastapi.testclient import TestClient
        from main import app

        mock_scan.return_value = [
            {"arn": "arn:aws:iam::123456789012:role/SvcRole", "name": "SvcRole"},
        ]
        client = TestClient(app)
        response = client.post("/scan")
        assert response.status_code == 200
        data = response.json()
        assert data["scanned"] == 1
        assert len(data["profiles"]) == 1

    @patch("main.get_nhi_profiles")
    def test_scan_failure(self, mock_scan: MagicMock):
        from fastapi.testclient import TestClient
        from main import app

        mock_scan.side_effect = RuntimeError("AWS unavailable")
        client = TestClient(app)
        response = client.post("/scan")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# /analyze endpoint tests
# ---------------------------------------------------------------------------

class TestAnalyzeEndpoint:
    """Tests for POST /analyze."""

    @patch("main.generate_least_privilege_policy")
    @patch("main.get_identity")
    def test_analyze_success(self, mock_get: MagicMock, mock_analyze: MagicMock):
        from fastapi.testclient import TestClient
        from main import app

        mock_get.return_value = {
            "arn": "arn:aws:iam::123456789012:role/TestRole",
            "allowed_actions": ["s3:GetObject", "s3:PutObject", "s3:DeleteBucket"],
            "used_actions": ["s3:GetObject"],
        }
        mock_analyze.return_value = {
            "risk_score": 67,
            "unused_actions": ["s3:PutObject", "s3:DeleteBucket"],
            "recommended_policy": {"Version": "2012-10-17", "Statement": []},
            "summary": "Over-privileged role.",
        }
        client = TestClient(app)
        response = client.post("/analyze", json={"arn": "arn:aws:iam::123456789012:role/TestRole"})
        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] == 67
        assert len(data["unused_actions"]) == 2

    @patch("main.get_identity")
    def test_analyze_identity_not_found(self, mock_get: MagicMock):
        from fastapi.testclient import TestClient
        from main import app

        mock_get.return_value = None
        client = TestClient(app)
        response = client.post("/analyze", json={"arn": "arn:aws:iam::123456789012:role/Missing"})
        assert response.status_code == 404

    @patch("main.generate_least_privilege_policy")
    @patch("main.get_identity")
    def test_analyze_llm_failure(self, mock_get: MagicMock, mock_analyze: MagicMock):
        from fastapi.testclient import TestClient
        from main import app

        mock_get.return_value = {
            "arn": "arn:aws:iam::123456789012:role/TestRole",
            "allowed_actions": ["s3:*"],
            "used_actions": [],
        }
        mock_analyze.side_effect = ValueError("Could not parse LLM response as JSON")
        client = TestClient(app)
        response = client.post("/analyze", json={"arn": "arn:aws:iam::123456789012:role/TestRole"})
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# /quarantine endpoint tests
# ---------------------------------------------------------------------------

class TestQuarantineEndpoint:
    """Tests for POST /quarantine."""

    @patch("main.quarantine_identity")
    def test_quarantine_success(self, mock_q: MagicMock):
        from fastapi.testclient import TestClient
        from main import app

        mock_q.return_value = {
            "arn": "arn:aws:iam::123456789012:role/BadRole",
            "quarantined": True,
            "boundary_policy": "arn:aws:iam::123456789012:policy/GhostProtocol-Quarantine",
        }
        client = TestClient(app)
        response = client.post("/quarantine", json={"arn": "arn:aws:iam::123456789012:role/BadRole"})
        assert response.status_code == 200
        assert response.json()["quarantined"] is True

    @patch("main.quarantine_identity")
    def test_quarantine_failure(self, mock_q: MagicMock):
        from fastapi.testclient import TestClient
        from main import app

        mock_q.side_effect = RuntimeError("IAM access denied")
        client = TestClient(app)
        response = client.post("/quarantine", json={"arn": "arn:aws:iam::123456789012:role/BadRole"})
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# scanner._query_used_actions tests
# ---------------------------------------------------------------------------

class TestQueryUsedActions:
    """Tests for scanner._query_used_actions() with mocked Athena."""

    @patch("scanner._get_athena_client")
    def test_successful_query(self, mock_athena_factory: MagicMock):
        from scanner import _query_used_actions

        mock_athena = MagicMock()
        mock_athena_factory.return_value = mock_athena

        mock_athena.start_query_execution.return_value = {"QueryExecutionId": "qid-123"}
        mock_athena.get_query_execution.return_value = {
            "QueryExecution": {"Status": {"State": "SUCCEEDED"}}
        }

        mock_paginator = MagicMock()
        mock_athena.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "ResultSet": {
                    "Rows": [
                        {"Data": [{"VarCharValue": "action"}]},                # header
                        {"Data": [{"VarCharValue": "s3.amazonaws.com:GetObject"}]},
                        {"Data": [{"VarCharValue": "sts.amazonaws.com:AssumeRole"}]},
                    ]
                }
            }
        ]

        result = _query_used_actions("arn:aws:iam::123456789012:role/TestRole")
        assert result == ["s3.amazonaws.com:GetObject", "sts.amazonaws.com:AssumeRole"]

    @patch("scanner._get_athena_client")
    def test_failed_query_returns_empty(self, mock_athena_factory: MagicMock):
        from scanner import _query_used_actions

        mock_athena = MagicMock()
        mock_athena_factory.return_value = mock_athena

        mock_athena.start_query_execution.return_value = {"QueryExecutionId": "qid-456"}
        mock_athena.get_query_execution.return_value = {
            "QueryExecution": {"Status": {"State": "FAILED"}}
        }

        result = _query_used_actions("arn:aws:iam::123456789012:role/TestRole")
        assert result == []

    def test_invalid_arn_skips_query(self):
        from scanner import _query_used_actions

        result = _query_used_actions("not-an-arn")
        assert result == []

    @patch("scanner._get_athena_client")
    def test_athena_client_error(self, mock_athena_factory: MagicMock):
        from scanner import _query_used_actions

        mock_athena = MagicMock()
        mock_athena_factory.return_value = mock_athena
        mock_athena.start_query_execution.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "denied"}}, "StartQuery"
        )

        result = _query_used_actions("arn:aws:iam::123456789012:role/TestRole")
        assert result == []


# ---------------------------------------------------------------------------
# scanner.quarantine_identity tests
# ---------------------------------------------------------------------------

class TestQuarantineIdentity:
    """Tests for scanner.quarantine_identity() with mocked IAM."""

    @patch("scanner.mark_quarantined")
    @patch("scanner._ensure_quarantine_policy")
    @patch("scanner._get_iam_client")
    def test_quarantine_applies_boundary(self, mock_iam_factory, mock_ensure, mock_mark):
        from scanner import quarantine_identity

        mock_iam = MagicMock()
        mock_iam_factory.return_value = mock_iam
        mock_ensure.return_value = "arn:aws:iam::123456789012:policy/GhostProtocol-Quarantine"

        result = quarantine_identity("arn:aws:iam::123456789012:role/BadRole")

        mock_iam.put_role_permissions_boundary.assert_called_once_with(
            RoleName="BadRole",
            PermissionsBoundary="arn:aws:iam::123456789012:policy/GhostProtocol-Quarantine",
        )
        mock_mark.assert_called_once_with("arn:aws:iam::123456789012:role/BadRole")
        assert result["quarantined"] is True

    def test_quarantine_rejects_invalid_arn(self):
        from scanner import quarantine_identity

        with pytest.raises(ValueError, match="Invalid IAM role ARN"):
            quarantine_identity("not-a-valid-arn")

    @patch("scanner._ensure_quarantine_policy")
    @patch("scanner._get_iam_client")
    def test_quarantine_iam_error_propagates(self, mock_iam_factory, mock_ensure):
        from scanner import quarantine_identity

        mock_iam = MagicMock()
        mock_iam_factory.return_value = mock_iam
        mock_ensure.return_value = "arn:aws:iam::123456789012:policy/GhostProtocol-Quarantine"
        mock_iam.put_role_permissions_boundary.side_effect = ClientError(
            {"Error": {"Code": "NoSuchEntity", "Message": "role not found"}}, "PutBoundary"
        )

        with pytest.raises(ClientError):
            quarantine_identity("arn:aws:iam::123456789012:role/GhostRole")


# ---------------------------------------------------------------------------
# analyzer.generate_least_privilege_policy tests
# ---------------------------------------------------------------------------

class TestGenerateLeastPrivilegePolicy:
    """Tests for analyzer.generate_least_privilege_policy() with mocked LLM."""

    @patch("analyzer.Ollama")
    def test_successful_analysis(self, mock_ollama_cls: MagicMock):
        from analyzer import generate_least_privilege_policy

        mock_llm = MagicMock()
        mock_ollama_cls.return_value = mock_llm

        # The chain is prompt | llm, so we need to mock __or__ on the prompt
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = json.dumps({
            "risk_score": 80,
            "unused_actions": ["s3:DeleteBucket"],
            "recommended_policy": {
                "Version": "2012-10-17",
                "Statement": [{"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": "*"}],
            },
            "summary": "Role is over-privileged.",
        })

        with patch("analyzer.ChatPromptTemplate") as mock_prompt_cls:
            mock_prompt = MagicMock()
            mock_prompt_cls.from_messages.return_value = mock_prompt
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)

            result = generate_least_privilege_policy(
                current_policy=["s3:GetObject", "s3:DeleteBucket"],
                used_actions=["s3:GetObject"],
            )

        assert result["risk_score"] == 80
        assert "s3:DeleteBucket" in result["unused_actions"]

    @patch("analyzer.Ollama")
    def test_risk_score_clamped_to_100(self, mock_ollama_cls: MagicMock):
        from analyzer import generate_least_privilege_policy

        mock_llm = MagicMock()
        mock_ollama_cls.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = json.dumps({
            "risk_score": 150,
            "unused_actions": [],
            "recommended_policy": {},
            "summary": "Extreme.",
        })

        with patch("analyzer.ChatPromptTemplate") as mock_prompt_cls:
            mock_prompt = MagicMock()
            mock_prompt_cls.from_messages.return_value = mock_prompt
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)

            result = generate_least_privilege_policy(
                current_policy=["s3:*"],
                used_actions=[],
            )

        assert result["risk_score"] == 100

    @patch("analyzer.Ollama")
    def test_risk_score_clamped_to_1(self, mock_ollama_cls: MagicMock):
        from analyzer import generate_least_privilege_policy

        mock_llm = MagicMock()
        mock_ollama_cls.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = json.dumps({
            "risk_score": -5,
            "unused_actions": [],
            "recommended_policy": {},
            "summary": "Perfect.",
        })

        with patch("analyzer.ChatPromptTemplate") as mock_prompt_cls:
            mock_prompt = MagicMock()
            mock_prompt_cls.from_messages.return_value = mock_prompt
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)

            result = generate_least_privilege_policy(
                current_policy=["s3:GetObject"],
                used_actions=["s3:GetObject"],
            )

        assert result["risk_score"] == 1

    @patch("analyzer.Ollama")
    def test_policy_dict_input_extracts_actions(self, mock_ollama_cls: MagicMock):
        from analyzer import generate_least_privilege_policy

        mock_llm = MagicMock()
        mock_ollama_cls.return_value = mock_llm

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = json.dumps({
            "risk_score": 30,
            "unused_actions": [],
            "recommended_policy": {},
            "summary": "OK.",
        })

        with patch("analyzer.ChatPromptTemplate") as mock_prompt_cls:
            mock_prompt = MagicMock()
            mock_prompt_cls.from_messages.return_value = mock_prompt
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)

            policy_doc = {
                "Statement": [
                    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"], "Resource": "*"},
                    {"Effect": "Allow", "Action": "ec2:DescribeInstances", "Resource": "*"},
                ]
            }

            result = generate_least_privilege_policy(
                current_policy=policy_doc,
                used_actions=["s3:GetObject"],
            )

        assert result["risk_score"] == 30

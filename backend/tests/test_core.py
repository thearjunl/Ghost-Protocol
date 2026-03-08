"""Tests for the GhostProtocol backend.

Covers scanner helpers, analyzer JSON parsing, and API endpoint smoke tests.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

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

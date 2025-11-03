"""
Unit tests for FastAPI bucket endpoints.
Tests business logic of create/get/delete buckets via backend router.
Uses shared fixtures from tests/conftest.py (no hardcoded credentials).
"""

import os
from unittest.mock import AsyncMock, patch
import pytest


@pytest.fixture
def ensure_env(dev_environment):
    """Ensure environment variables from .env.dev are set for each test case."""
    old = os.environ.copy()
    os.environ.update(dev_environment)
    # critical for auth middleware — no fallbacks, fail fast if missing
    os.environ['API_KEY'] = dev_environment['API_KEY']
    os.environ['JWT_SECRET_KEY'] = dev_environment['JWT_SECRET_KEY']
    yield
    os.environ.clear()
    os.environ.update(old)


class TestBucketEndpoints:
    @patch("endpoints.buckets._sync_bucket_to_db", new_callable=AsyncMock)
    @patch("endpoints.buckets._get_system_user_id", new_callable=AsyncMock)
    @patch("endpoints.buckets.storage_client")
    def test_create_bucket_success(self, mock_client, mock_get_user_id, mock_sync_bucket, ensure_env, api_client, test_api_key):
        mock_client.make_request = AsyncMock(return_value={
            "success": True,
            "bucket": {"name": "unit-bucket", "internal_bucket_name": "unit-bucket", "public": False},
        })
        mock_get_user_id.return_value = "test-user-id"
        mock_sync_bucket.return_value = None

        client = api_client

        resp = client.post(
            "/api/v1/buckets",
            json={"name": "unit-bucket", "owner_id": "test-user-id", "public": False},
            headers={"x-api-key": test_api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["bucket"]["name"] == "unit-bucket"

    @patch("endpoints.buckets._db_manager")
    def test_get_bucket_not_found(self, mock_db_manager, ensure_env, api_client, test_api_key):
        # Mock database to return None (bucket not found)
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_db_manager.acquire.return_value.__aenter__.return_value = mock_conn

        client = api_client

        resp = client.get(
            "/api/v1/buckets/missing-bucket",
            headers={"x-api-key": test_api_key},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("endpoints.buckets._delete_bucket_from_db", new_callable=AsyncMock)
    @patch("endpoints.buckets.storage_client")
    def test_delete_bucket_success(self, mock_client, mock_delete_bucket, ensure_env, api_client, test_api_key):
        mock_client.make_request = AsyncMock(return_value={"success": True})
        mock_delete_bucket.return_value = None

        client = api_client

        resp = client.delete(
            "/api/v1/buckets/empty-bucket",
            headers={"x-api-key": test_api_key},
        )
        assert resp.status_code == 200
        assert resp.json().get("success", True) is True

    @patch("endpoints.buckets.storage_client")
    def test_delete_bucket_not_found(self, mock_client, ensure_env, api_client, test_api_key):
        mock_client.make_request = AsyncMock(return_value={"detail": "Bucket not found"})

        client = api_client

        resp = client.delete(
            "/api/v1/buckets/does-not-exist",
            headers={"x-api-key": test_api_key},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_create_bucket_unauthorized(self, api_client):
        client = api_client

        resp = client.post(
            "/api/v1/buckets",
            json={"name": "unauth-bucket"},
            headers={},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "INVALID_API_KEY"

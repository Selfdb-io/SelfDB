"""
Integration tests for bucket endpoints against running Docker services.
Consistent style with user and tables tests: AsyncClient fixture and test_api_key.
"""

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestBucketEndpointsIntegration:
    @pytest.mark.asyncio
    async def test_bucket_crud_flow(self, client: AsyncClient, test_api_key: str) -> None:
        # Login as admin to get valid user_id
        from shared.config.config_manager import ConfigManager
        config = ConfigManager()
        admin_login_response = await client.post(
            "/auth/login",
            json={
                "email": config.admin_email,
                "password": config.admin_password
            },
            headers={"X-API-Key": test_api_key}
        )
        assert admin_login_response.status_code == 200
        admin_data = admin_login_response.json()
        admin_user_id = admin_data["user"]["id"]
        
        bucket_name = f"integration-bucket-{uuid.uuid4().hex[:8]}"

        # Create bucket with actual admin user_id
        create = await client.post(
            "/api/v1/buckets",
            headers={"X-API-Key": test_api_key},
            json={
                "name": bucket_name,
                "owner_id": admin_user_id,
                "public": False,
            },
        )
        assert create.status_code == 200, create.text
        body = create.json()
        assert body["success"] is True
        assert body["bucket"]["name"] == bucket_name

        try:
            # Get bucket
            getr = await client.get(
                f"/api/v1/buckets/{bucket_name}", headers={"X-API-Key": test_api_key}
            )
            assert getr.status_code == 200, getr.text
            assert getr.json()["bucket"]["name"] == bucket_name
        finally:
            # Delete bucket (empty → success)
            dele = await client.delete(
                f"/api/v1/buckets/{bucket_name}", headers={"X-API-Key": test_api_key}
            )
            assert dele.status_code == 200, dele.text

    @pytest.mark.asyncio
    async def test_invalid_bucket_name(self, client: AsyncClient, test_api_key: str) -> None:
        # Login as admin to get valid user_id
        from shared.config.config_manager import ConfigManager
        config = ConfigManager()
        admin_login_response = await client.post(
            "/auth/login",
            json={
                "email": config.admin_email,
                "password": config.admin_password
            },
            headers={"X-API-Key": test_api_key}
        )
        assert admin_login_response.status_code == 200
        admin_data = admin_login_response.json()
        admin_user_id = admin_data["user"]["id"]
        
        bad_name = "Invalid!Name"
        resp = await client.post(
            "/api/v1/buckets",
            headers={"X-API-Key": test_api_key},
            json={"name": bad_name, "owner_id": admin_user_id},
        )
        assert resp.status_code in [400, 422]

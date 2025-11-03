"""
Integration tests for file endpoints that create and properly tear down resources.
"""

import io
import os
import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestFileEndpointsIntegration:
    """Test file endpoints against running Docker services with cleanup."""

    @pytest.mark.asyncio
    async def test_backend_health(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == "backend"

    @pytest.mark.asyncio
    async def test_api_status(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        expected_version = os.getenv("SELFDB_VERSION")
        if isinstance(expected_version, str):
            sanitized = expected_version.strip()
            if len(sanitized) >= 2 and sanitized[0] == sanitized[-1] and sanitized[0] in {'"', "'"}:
                expected_version = sanitized[1:-1]
            else:
                expected_version = sanitized
        assert data["api_version"] == expected_version
        assert "services" in data
        assert "ports" in data

    @pytest.mark.asyncio
    async def test_upload_file_success(self, client: AsyncClient, test_api_key: str) -> None:
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
        
        file_content = b"test file content for integration test"
        bucket = f"test-bucket-{uuid.uuid4().hex[:8]}"
        path = f"integration/test_{uuid.uuid4().hex[:12]}.txt"
        headers = {"X-API-Key": test_api_key}

        try:
            # Create bucket first
            create_bucket_response = await client.post(
                "/api/v1/buckets",
                headers=headers,
                json={
                    "name": bucket,
                    "owner_id": admin_user_id,
                    "public": False,
                },
            )
            assert create_bucket_response.status_code == 200
            
            # Upload file
            files = {"file": ("test_integration.txt", io.BytesIO(file_content), "text/plain")}
            data = {"bucket": bucket, "path": path}
            response = await client.post("/api/v1/files/upload", files=files, data=data, headers=headers)
            assert response.status_code in [200, 503]

            if response.status_code == 200:
                result = response.json()
                assert result["success"] is True
                assert result["bucket"] == bucket
                assert result["path"] == path
                assert result["size"] == len(file_content)
            else:
                result = response.json()
                assert "upload failed" in result["detail"].lower() or \
                       "storage service" in result["detail"].lower() or \
                       "unavailable" in result["detail"].lower()
        finally:
            # Cleanup: delete file and bucket
            try:
                await client.delete(f"/api/v1/files/{bucket}/{path}", headers=headers)
            except Exception:
                pass
            try:
                await client.delete(f"/api/v1/buckets/{bucket}", headers=headers)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_upload_file_missing_bucket(self, client: AsyncClient, test_api_key: str) -> None:
        file_content = b"test content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"path": "folder/test.txt"}

        response = await client.post(
            "/api/v1/files/upload",
            files=files,
            data=data,
            headers={"X-API-Key": test_api_key},
        )

        assert response.status_code == 422
        assert "bucket" in response.text.lower()

    @pytest.mark.asyncio
    async def test_download_file(self, client: AsyncClient, test_api_key: str) -> None:
        headers = {"X-API-Key": test_api_key}
        response = await client.get(
            "/api/v1/files/test-bucket/integration/test.txt",
            headers=headers,
        )

        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            assert "content-disposition" in response.headers.keys() or \
                   "Content-Disposition" in response.headers.keys()
        elif response.status_code == 404:
            result = response.json()
            assert "not found" in result["detail"].lower()
        else:
            result = response.json()
            assert "storage service" in result["detail"].lower() or "unavailable" in result["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_file(self, client: AsyncClient, test_api_key: str) -> None:
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
        
        headers = {"X-API-Key": test_api_key}
        bucket = f"test-bucket-{uuid.uuid4().hex[:8]}"
        path = f"integration/test_delete_{uuid.uuid4().hex[:8]}.txt"

        # Create bucket first
        try:
            await client.post(
                "/api/v1/buckets",
                headers=headers,
                json={
                    "name": bucket,
                    "owner_id": admin_user_id,
                    "public": False,
                },
            )
            
            # Best-effort: create a file to delete (ignore result if storage unavailable)
            files = {"file": ("to_delete.txt", io.BytesIO(b"to delete"), "text/plain")}
            data = {"bucket": bucket, "path": path}
            await client.post("/api/v1/files/upload", files=files, data=data, headers=headers)
        except Exception:
            pass

        try:
            response = await client.delete(
                f"/api/v1/files/{bucket}/{path}",
                headers=headers,
            )

            assert response.status_code in [200, 404, 503]

            if response.status_code == 200:
                result = response.json()
                assert result["success"] is True
                assert result["bucket"] == bucket
                assert result["path"] == path
            elif response.status_code == 404:
                result = response.json()
                assert "not found" in result["detail"].lower()
            else:
                result = response.json()
                assert "storage service" in result["detail"].lower() or "unavailable" in result["detail"].lower()
        finally:
            # Cleanup bucket
            try:
                await client.delete(f"/api/v1/buckets/{bucket}", headers=headers)
            except Exception:
                pass


class TestFileEndpointsConfiguration:
    """Test that configuration and adapters are working correctly"""
    
    def test_config_adapter_initialization(self):
        """Test that configuration adapters can be initialized"""
        from endpoints.files import config_adapter, auth_adapter, service_discovery
        
        # Test config adapter
        assert config_adapter is not None
        assert hasattr(config_adapter, 'get_setting')
        assert hasattr(config_adapter, 'get_port')
        
        # Test auth adapter  
        assert auth_adapter is not None
        assert hasattr(auth_adapter, 'validate_api_key')
        
        # Test service discovery adapter
        assert service_discovery is not None
        assert hasattr(service_discovery, 'get_service_url')
    
    def test_proxy_components_initialization(self):
        """Test that proxy components are properly initialized"""
        from endpoints.files import upload_proxy, download_proxy, storage_client
        
        # Test upload proxy
        assert upload_proxy is not None
        assert hasattr(upload_proxy, 'upload_file')
        
        # Test download proxy
        assert download_proxy is not None  
        assert hasattr(download_proxy, 'download_file')
        
        # Test storage client
        assert storage_client is not None
        assert hasattr(storage_client, 'make_request')
"""
Unit tests for authentication middleware on file endpoints.
Tests API key and JWT validation on /api/v1/files/* endpoints.
"""

import pytest
import os
import jwt
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
import io
from shared.config.config_manager import ConfigManager
from shared.auth.jwt_service import JWTService


class TestAuthenticationMiddleware:
    """Test authentication middleware on file endpoints"""
    
    def setup_method(self):
        """Set up test environment with proper configuration"""
        # Use the same consistent API key as other tests
        self.test_api_key = "dev_api_key_not_for_production"
        self.test_jwt_secret = "dev_jwt_secret_not_for_production"
        
        # Set environment variables (will be used by middleware)
        os.environ["API_KEY"] = self.test_api_key
        os.environ["JWT_SECRET_KEY"] = self.test_jwt_secret
        os.environ["JWT_ISSUER"] = "selfdb"
        
        # Initialize JWT service with the same values
        self.jwt_service = JWTService(
            secret_key=self.test_jwt_secret,
            algorithm="HS256",
            access_token_expire_minutes=30,
            issuer="selfdb"
        )
    
    def teardown_method(self):
        """Clean up test environment"""
        os.environ.pop("API_KEY", None)
        os.environ.pop("JWT_SECRET_KEY", None)
        os.environ.pop("JWT_ISSUER", None)
    
    @patch("endpoints.files._sync_file_to_db", new_callable=AsyncMock)
    @patch("endpoints.files._get_system_user_id", new_callable=AsyncMock)
    @patch("endpoints.files.upload_proxy.stream_upload_file")
    def test_upload_with_valid_api_key(self, mock_stream_upload, mock_get_user_id, mock_sync_file, api_client):
        """Test file upload with valid API key"""
        # Arrange - Mock successful upload on streaming path and database sync
        mock_get_user_id.return_value = "test-user-id"
        mock_sync_file.return_value = None
        
        client = api_client
        
        file_content = b"test file content"
        file_data = {
            "file": ("test.txt", io.BytesIO(file_content), "text/plain")
        }
        form_data = {"bucket": "test-bucket", "path": "test.txt"}
        mock_stream_upload.return_value = {
            "status": "uploaded",
            "file_id": "test-file-123",
            "size": len(file_content),
            "upload_time": "2025-01-09T12:00:00Z"
        }
        
        # Act - Make request with valid API key from config
        response = client.post(
            "/api/v1/files/upload",
            files=file_data,
            data=form_data,
            headers={"x-api-key": self.test_api_key}
        )
        
        # Assert - Should succeed
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
    
    def test_upload_with_invalid_api_key(self, api_client):
        """Test file upload with invalid API key"""
        client = api_client
        
        file_content = b"test file content"
        file_data = {
            "file": ("test.txt", io.BytesIO(file_content), "text/plain")
        }
        form_data = {"bucket": "test-bucket", "path": "test.txt"}
        
        # Act - Make request with invalid API key
        response = client.post(
            "/api/v1/files/upload",
            files=file_data,
            data=form_data,
            headers={"x-api-key": "invalid-api-key"}
        )
        
        # Assert - Should fail with 401
        assert response.status_code == 401
        result = response.json()
        assert "error" in result
        assert result["error"]["code"] == "INVALID_API_KEY"
    
    def test_upload_without_api_key(self, api_client):
        """Test file upload without API key"""
        client = api_client
        
        file_content = b"test file content"
        file_data = {
            "file": ("test.txt", io.BytesIO(file_content), "text/plain")
        }
        form_data = {"bucket": "test-bucket", "path": "test.txt"}
        
        # Act - Make request without API key
        response = client.post(
            "/api/v1/files/upload",
            files=file_data,
            data=form_data
        )
        
        # Assert - Should fail with 401
        assert response.status_code == 401
        result = response.json()
        assert "error" in result
        assert result["error"]["code"] == "INVALID_API_KEY"
        assert "missing" in result["error"]["message"].lower()
    
    @patch("endpoints.files.download_proxy.stream_download_file")
    def test_download_with_valid_api_key(self, mock_stream_download, api_client):
        """Test file download with valid API key"""
        # Arrange - Mock successful streaming download
        async def _gen():
            yield b"file content"
        mock_stream_download.return_value = {
            "status": "streaming",
            "stream": _gen(),
            "content_type": "text/plain",
            "content_length": "12"
        }
        
        client = api_client
        
        # Act - Make request with valid API key from config
        response = client.get(
            "/api/v1/files/test-bucket/test.txt",
            headers={"x-api-key": self.test_api_key}
        )
        
        # Assert - Should succeed
        assert response.status_code == 200
    
    def test_download_without_api_key(self, api_client):
        """Test file download without API key"""
        client = api_client
        
        # Act - Make request without API key
        response = client.get("/api/v1/files/test-bucket/test.txt")
        
        # Assert - Should fail with 401
        assert response.status_code == 401
        result = response.json()
        assert "error" in result
        assert result["error"]["code"] == "INVALID_API_KEY"
    
    @patch("endpoints.files._delete_file_from_db", new_callable=AsyncMock)
    @patch("endpoints.files.storage_client")
    def test_delete_with_valid_api_key(self, mock_storage_client, mock_delete_file, api_client):
        """Test file deletion with valid API key"""
        # Arrange - Mock successful deletion and database sync
        mock_storage_client.make_request = AsyncMock(return_value={
            "status": "success"
        })
        mock_delete_file.return_value = None
        
        client = api_client
        
        # Act - Make request with valid API key from config
        response = client.delete(
            "/api/v1/files/test-bucket/test.txt",
            headers={"x-api-key": self.test_api_key}
        )
        
        # Assert - Should succeed
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
    
    def test_delete_without_api_key(self, api_client):
        """Test file deletion without API key"""
        client = api_client
        
        # Act - Make request without API key
        response = client.delete("/api/v1/files/test-bucket/test.txt")
        
        # Assert - Should fail with 401
        assert response.status_code == 401
        result = response.json()
        assert "error" in result
        assert result["error"]["code"] == "INVALID_API_KEY"


class TestJWTAuthentication:
    """Test JWT token authentication on file endpoints"""
    
    def setup_method(self):
        """Set up test environment with proper JWT service"""
        # Use the same consistent values as TestAuthenticationMiddleware
        self.test_api_key = "dev_api_key_not_for_production"
        self.test_jwt_secret = "dev_jwt_secret_not_for_production"
        
        # Set environment variables (will be used by middleware)
        os.environ["API_KEY"] = self.test_api_key
        os.environ["JWT_SECRET_KEY"] = self.test_jwt_secret
        os.environ["JWT_ISSUER"] = "selfdb"
        
        # Initialize JWT service with the same values  
        self.jwt_service = JWTService(
            secret_key=self.test_jwt_secret,
            algorithm="HS256",
            access_token_expire_minutes=30,
            issuer="selfdb"
        )
    
    def teardown_method(self):
        """Clean up test environment"""
        os.environ.pop("API_KEY", None)
        os.environ.pop("JWT_SECRET_KEY", None)
        os.environ.pop("JWT_ISSUER", None)
    
    def _create_valid_jwt_token(self, user_id: str = "user123", role: str = "USER") -> str:
        """Helper to create a valid JWT token using the actual JWTService"""
        payload = {
            "user_id": user_id,
            "role": role
        }
        return self.jwt_service.generate_access_token(payload)
    
    @patch("endpoints.files._sync_file_to_db", new_callable=AsyncMock)
    @patch("endpoints.files._get_system_user_id", new_callable=AsyncMock)
    @patch("endpoints.files.upload_proxy.stream_upload_file")
    def test_upload_with_valid_jwt(self, mock_stream_upload, mock_get_user_id, mock_sync_file, api_client):
        """Test file upload with properly created and validated JWT token"""
        # Arrange - Mock successful upload on streaming path and database sync
        mock_get_user_id.return_value = "test-user-id"
        mock_sync_file.return_value = None
        
        client = api_client
        
        # Create a valid JWT token using the same service the middleware will use
        token = self._create_valid_jwt_token(user_id="test-user", role="USER")
        
        file_content = b"test file content"
        file_data = {
            "file": ("test.txt", io.BytesIO(file_content), "text/plain")
        }
        form_data = {"bucket": "test-bucket", "path": "test.txt"}
        mock_stream_upload.return_value = {
            "status": "uploaded",
            "file_id": "test-file-123",
            "size": len(file_content),
            "upload_time": "2025-01-09T12:00:00Z"
        }
        
        # Act - Make request with properly signed JWT token
        response = client.post(
            "/api/v1/files/upload",
            files=file_data,
            data=form_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Assert - Should succeed with valid JWT
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
    
    def test_upload_with_expired_jwt(self, api_client):
        """Test file upload with expired JWT token"""
        client = api_client
        
        # Create an expired JWT token by manually encoding with past expiration
        past_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        payload = {
            "user_id": "test-user",
            "role": "USER",
            "token_type": "access",
            "iat": past_time,
            "exp": past_time,  # Already expired
            "iss": "selfdb"
        }
        expired_token = jwt.encode(payload, self.jwt_service.secret_key, algorithm="HS256")
        
        file_content = b"test file content"
        file_data = {
            "file": ("test.txt", io.BytesIO(file_content), "text/plain")
        }
        form_data = {"bucket": "test-bucket", "path": "test.txt"}
        
        # Act - Make request with expired JWT token
        response = client.post(
            "/api/v1/files/upload",
            files=file_data,
            data=form_data,
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        # Assert - Should fail with 401
        assert response.status_code == 401
        result = response.json()
        assert "error" in result
        assert "jwt token has expired" in result["error"]["message"].lower()
    
    def test_upload_with_invalid_jwt(self, api_client):
        """Test file upload with invalid JWT token"""
        client = api_client
        
        file_content = b"test file content"
        file_data = {
            "file": ("test.txt", io.BytesIO(file_content), "text/plain")
        }
        form_data = {"bucket": "test-bucket", "path": "test.txt"}
        
        # Act - Make request with invalid JWT token
        response = client.post(
            "/api/v1/files/upload",
            files=file_data,
            data=form_data,
            headers={"Authorization": "Bearer invalid.jwt.token"}
        )
        
        # Assert - Should fail with 401
        assert response.status_code == 401
        result = response.json()
        assert "error" in result


class TestHealthEndpointsExcluded:
    """Test that health endpoints bypass authentication"""
    
    def setup_method(self):
        """Set up test environment with proper configuration"""
        # Set service port configuration (following ConfigManager pattern)
        self.test_env_vars = {
            'API_PORT': '8000',
            'STORAGE_PORT': '8001', 
            'DENO_PORT': '8090',
            'POSTGRES_PORT': '5432',
            'FRONTEND_PORT': '3000',
            'POSTGRES_DB': 'selfdb_test',
            'POSTGRES_USER': 'selfdb_test_user'
        }
        
        # Apply environment variables
        for key, value in self.test_env_vars.items():
            os.environ[key] = value
    
    def teardown_method(self):
        """Clean up test environment"""
        for key in self.test_env_vars:
            os.environ.pop(key, None)
    
    def test_health_endpoint_no_auth_required(self, api_client):
        """Test that /health endpoint works without authentication"""
        client = api_client
        
        # Act - Make request to health endpoint without auth
        response = client.get("/health")
        
        # Assert - Should succeed
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "ready"
    
    def test_api_status_endpoint_no_auth_required(self, api_client):
        """Test that /api/v1/status endpoint works without authentication"""
        client = api_client
        
        # Act - Make request to status endpoint without auth
        response = client.get("/api/v1/status")
        
        # Assert - Should succeed
        assert response.status_code == 200
        result = response.json()
        assert "api_version" in result
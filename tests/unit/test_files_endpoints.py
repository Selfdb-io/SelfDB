"""
Unit tests for FastAPI file endpoints.
Tests the integration of file upload/download/delete endpoints with existing proxy components.
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from fastapi import UploadFile
import io
import json


class TestFileUploadEndpoint:
    """Test POST /api/v1/files/upload endpoint"""
    
    @pytest.fixture(autouse=True)
    def _set_client(self, api_client):
        self.client = api_client

    def setup_method(self):
        """Set up test environment with proper authentication configuration"""
        self.test_api_key = "test-api-key-12345"
        self.test_jwt_secret = "test-jwt-secret-key"
        
        # Set required authentication environment variables
        os.environ["API_KEY"] = self.test_api_key
        os.environ["JWT_SECRET_KEY"] = self.test_jwt_secret
        os.environ["JWT_ISSUER"] = "selfdb"
        
        # Set other required environment variables
        os.environ["API_PORT"] = "8000"
        os.environ["STORAGE_PORT"] = "8001"
        os.environ["DENO_PORT"] = "8090"
        os.environ["POSTGRES_PORT"] = "5432"
        os.environ["FRONTEND_PORT"] = "3000"
        os.environ["POSTGRES_DB"] = "selfdb_test"
        os.environ["POSTGRES_USER"] = "selfdb_test_user"
    
    def teardown_method(self):
        """Clean up test environment"""
        env_vars = ["API_KEY", "JWT_SECRET_KEY", "JWT_ISSUER", "API_PORT", 
                   "STORAGE_PORT", "DENO_PORT", "POSTGRES_PORT", "FRONTEND_PORT", 
                   "POSTGRES_DB", "POSTGRES_USER"]
        for var in env_vars:
            os.environ.pop(var, None)
    
    @patch("endpoints.files._sync_file_to_db", new_callable=AsyncMock)
    @patch("endpoints.files._get_system_user_id", new_callable=AsyncMock)
    @patch("endpoints.files.upload_proxy.stream_upload_file")
    def test_upload_file_success(self, mock_stream_upload, mock_get_user_id, mock_sync_file):
        """Test successful file upload through the endpoint"""
        # Arrange - Mock the streaming upload response and database sync
        mock_get_user_id.return_value = "test-user-id"
        mock_sync_file.return_value = None
        
        client = self.client
        
        # Create a test file
        file_content = b"test file content"
        file = io.BytesIO(file_content)
        
        # Prepare stream mock after we know file size
        mock_stream_upload.return_value = {
            "status": "uploaded",
            "file_id": "test-file-123",
            "upload_time": "2025-01-09T12:00:00Z",
            "size": len(file_content)
        }

        # Act - Make request with valid API key
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("test.txt", file, "text/plain")},
            data={"bucket": "test-bucket", "path": "folder/test.txt"},
            headers={"x-api-key": self.test_api_key}
        )
            
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["bucket"] == "test-bucket"
        assert result["path"] == "folder/test.txt"
        assert "size" in result
        assert result["size"] == len(file_content)
        assert result["file_id"] == "test-file-123"
        assert result["upload_time"] == "2025-01-09T12:00:00Z"
    
    def test_upload_file_missing_bucket(self):
        """Test upload fails when bucket is not provided"""
        client = self.client
        
        file = io.BytesIO(b"test content")
        
        # Act - Make request with valid API key but missing bucket
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("test.txt", file, "text/plain")},
            data={"path": "folder/test.txt"},  # Missing bucket
            headers={"x-api-key": self.test_api_key}
        )
        
        # Assert
        assert response.status_code == 422
        assert "bucket" in response.text.lower()

    @patch("endpoints.files.upload_proxy.stream_upload_file")  
    def test_upload_file_storage_error(self, mock_stream_upload):
        """Test upload handles storage service errors gracefully"""
        # Arrange - Mock storage service error on streaming path
        mock_stream_upload.side_effect = Exception("Storage service unavailable")
        
        client = self.client
        
        file = io.BytesIO(b"test content")
        
        # Act - Make request with valid API key
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("test.txt", file, "text/plain")},
            data={"bucket": "test-bucket", "path": "test.txt"},
            headers={"x-api-key": self.test_api_key}
        )
        
        # Assert
        assert response.status_code == 503
        result = response.json()
        assert result["detail"] == "Storage service unavailable"


class TestFileDownloadEndpoint:
    """Test GET /api/v1/files/{bucket}/{path} endpoint"""

    @pytest.fixture(autouse=True)
    def _set_client(self, api_client):
        self.client = api_client
    
    def setup_method(self):
        """Set up test environment with proper authentication configuration"""
        self.test_api_key = "test-api-key-12345"
        self.test_jwt_secret = "test-jwt-secret-key"
        
        # Set required authentication environment variables
        os.environ["API_KEY"] = self.test_api_key
        os.environ["JWT_SECRET_KEY"] = self.test_jwt_secret
        os.environ["JWT_ISSUER"] = "selfdb"
        
        # Set other required environment variables
        os.environ["API_PORT"] = "8000"
        os.environ["STORAGE_PORT"] = "8001"
        os.environ["DENO_PORT"] = "8090"
        os.environ["POSTGRES_PORT"] = "5432"
        os.environ["FRONTEND_PORT"] = "3000"
        os.environ["POSTGRES_DB"] = "selfdb_test"
        os.environ["POSTGRES_USER"] = "selfdb_test_user"
    
    def teardown_method(self):
        """Clean up test environment"""
        env_vars = ["API_KEY", "JWT_SECRET_KEY", "JWT_ISSUER", "API_PORT", 
                   "STORAGE_PORT", "DENO_PORT", "POSTGRES_PORT", "FRONTEND_PORT", 
                   "POSTGRES_DB", "POSTGRES_USER"]
        for var in env_vars:
            os.environ.pop(var, None)
    
    @patch("endpoints.files.download_proxy.stream_download_file")
    def test_download_file_success(self, mock_stream_download):
        """Test successful file download through the endpoint"""
        # Arrange - Mock the streaming download response
        async def _gen():
            yield b"PDF content here"
        mock_stream_download.return_value = {
            "status": "streaming",
            "stream": _gen(),
            "content_type": "application/pdf",
            "content_length": str(len(b"PDF content here"))
        }
        
        client = self.client
        
        # Act - Make request with valid API key
        response = client.get(
            "/api/v1/files/test-bucket/folder/document.pdf",
            headers={"x-api-key": self.test_api_key}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "content-disposition" in response.headers

    @patch("endpoints.files.download_proxy.stream_download_file")
    def test_download_file_not_found(self, mock_stream_download):
        """Test download returns 404 for non-existent files"""
        # Arrange - Mock file not found via streaming path error result
        mock_stream_download.return_value = {
            "status": "error",
            "error_code": 404,
            "error_message": "File not found"
        }
        
        client = self.client
        
        # Act - Make request with valid API key
        response = client.get(
            "/api/v1/files/test-bucket/nonexistent.txt",
            headers={"x-api-key": self.test_api_key}
        )
        
        # Assert
        assert response.status_code == 404
        result = response.json()
        assert "not found" in result["detail"].lower()


class TestFileDeleteEndpoint:
    """Test DELETE /api/v1/files/{bucket}/{path} endpoint"""

    @pytest.fixture(autouse=True)
    def _set_client(self, api_client):
        self.client = api_client
    
    def setup_method(self):
        """Set up test environment with proper authentication configuration"""
        self.test_api_key = "test-api-key-12345"
        self.test_jwt_secret = "test-jwt-secret-key"
        
        # Set required authentication environment variables
        os.environ["API_KEY"] = self.test_api_key
        os.environ["JWT_SECRET_KEY"] = self.test_jwt_secret
        os.environ["JWT_ISSUER"] = "selfdb"
        
        # Set other required environment variables
        os.environ["API_PORT"] = "8000"
        os.environ["STORAGE_PORT"] = "8001"
        os.environ["DENO_PORT"] = "8090"
        os.environ["POSTGRES_PORT"] = "5432"
        os.environ["FRONTEND_PORT"] = "3000"
        os.environ["POSTGRES_DB"] = "selfdb_test"
        os.environ["POSTGRES_USER"] = "selfdb_test_user"
    
    def teardown_method(self):
        """Clean up test environment"""
        env_vars = ["API_KEY", "JWT_SECRET_KEY", "JWT_ISSUER", "API_PORT", 
                   "STORAGE_PORT", "DENO_PORT", "POSTGRES_PORT", "FRONTEND_PORT", 
                   "POSTGRES_DB", "POSTGRES_USER"]
        for var in env_vars:
            os.environ.pop(var, None)
    
    @patch("endpoints.files._delete_file_from_db", new_callable=AsyncMock)
    @patch("endpoints.files.storage_client")
    def test_delete_file_success(self, mock_storage_client, mock_delete_file):
        """Test successful file deletion through the endpoint"""
        # Arrange - Mock the storage client response and database sync
        mock_storage_client.make_request = AsyncMock(return_value={
            "status": "success"
        })
        mock_delete_file.return_value = None
        
        client = self.client
        
        # Act - Make request with valid API key
        response = client.delete(
            "/api/v1/files/test-bucket/folder/old-file.txt",
            headers={"x-api-key": self.test_api_key}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["bucket"] == "test-bucket"
        assert result["path"] == "folder/old-file.txt"
        assert result["message"] == "File deleted successfully"

    @patch("endpoints.files.storage_client")
    def test_delete_file_not_found(self, mock_storage_client):
        """Test delete returns 404 for non-existent files"""
        # Arrange - Mock file not found
        mock_storage_client.make_request = AsyncMock(side_effect=FileNotFoundError("File not found"))
        
        client = self.client
        
        # Act - Make request with valid API key
        response = client.delete(
            "/api/v1/files/test-bucket/nonexistent.txt",
            headers={"x-api-key": self.test_api_key}
        )
        
        # Assert
        assert response.status_code == 404
        result = response.json()
        assert "not found" in result["detail"].lower()

    def test_delete_file_unauthorized(self):
        """Test delete fails without proper authentication"""
        client = self.client
        
        # Act - attempt delete without API key
        response = client.delete(
            "/api/v1/files/private-bucket/secret.txt",
            headers={}  # No authorization header
        )
        
        # Assert
        assert response.status_code == 401
        result = response.json()
        assert "error" in result
        assert result["error"]["code"] == "INVALID_API_KEY"
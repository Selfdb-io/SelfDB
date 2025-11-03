"""
Unit tests for file upload proxy functionality.

Tests streaming file upload through the backend proxy to storage service.
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
import io
from typing import Dict, Any


class TestFileUploadProxy:
    """Test suite for file upload proxy functionality."""
    
    @pytest.fixture
    def config_manager(self):
        """Mock configuration manager."""
        config = Mock()
        config.get_setting.side_effect = lambda key: {
            "storage_port": 8003,
            "backend_port": 8000,
            "storage_host": "localhost",
            "max_file_size": 1024 * 1024 * 1024  # 1GB
        }.get(key, "localhost")
        return config
    
    @pytest.fixture
    def auth_middleware(self):
        """Mock authentication middleware."""
        auth = AsyncMock()
        auth.validate_api_key.return_value = {
            "user_id": "test-user-123",
            "permissions": ["write"]
        }
        return auth
    
    @pytest.fixture
    def file_upload_proxy(self, config_manager, auth_middleware):
        """FileUploadProxy instance for testing."""
        from file_handlers import FileUploadProxy
        
        return FileUploadProxy(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
    
    @pytest.mark.asyncio
    async def test_file_upload_proxy_single_part(self, file_upload_proxy):
        """Test single-part file upload through proxy."""
        # Mock file data
        file_content = b"This is a test file content for upload"
        file_metadata = {
            "filename": "test.txt",
            "content_type": "text/plain",
            "bucket": "test-bucket",
            "path": "documents/test.txt"
        }
        
        # Mock storage service response
        mock_storage_response = {
            "file_id": "file-123",
            "status": "uploaded",
            "size": len(file_content),
            "url": "/api/v1/files/test-bucket/documents/test.txt"
        }
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = mock_storage_response
        
        with patch.object(file_upload_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await file_upload_proxy.upload_file(
                file_data=file_content,
                metadata=file_metadata,
                auth_headers={"Authorization": "Bearer test-token"}
            )
            
            # Verify successful upload
            assert result["status"] == "uploaded"
            assert result["file_id"] == "file-123"
            assert result["size"] == len(file_content)
            
            # Verify request was made correctly
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "POST"
            assert "test-bucket" in call_args[1]["url"]
            assert "documents/test.txt" in call_args[1]["url"]
    
    @pytest.mark.asyncio
    async def test_file_upload_proxy_multipart(self, file_upload_proxy):
        """Test multipart file upload for large files."""
        # Create a large file (10MB)
        large_file_content = b"x" * (10 * 1024 * 1024)
        file_metadata = {
            "filename": "large-file.bin",
            "content_type": "application/octet-stream",
            "bucket": "test-bucket",
            "path": "uploads/large-file.bin"
        }
        
        # Mock multipart upload initiation
        init_response = {
            "upload_id": "multipart-123",
            "status": "initiated",
            "chunk_size": 5 * 1024 * 1024  # 5MB chunks
        }
        
        # Mock chunk upload responses
        chunk_responses = [
            {"part_number": 1, "etag": "etag1", "status": "uploaded"},
            {"part_number": 2, "etag": "etag2", "status": "uploaded"}
        ]
        
        # Mock completion response
        completion_response = {
            "file_id": "file-456",
            "status": "completed",
            "size": len(large_file_content),
            "parts": 2
        }
        
        with patch.object(file_upload_proxy, '_initiate_multipart_upload', new_callable=AsyncMock) as mock_init:
            with patch.object(file_upload_proxy, '_upload_part', new_callable=AsyncMock) as mock_upload_part:
                with patch.object(file_upload_proxy, '_complete_multipart_upload', new_callable=AsyncMock) as mock_complete:
                    
                    mock_init.return_value = init_response
                    mock_upload_part.side_effect = chunk_responses
                    mock_complete.return_value = completion_response
                    
                    result = await file_upload_proxy.upload_large_file(
                        file_data=large_file_content,
                        metadata=file_metadata,
                        auth_headers={"Authorization": "Bearer test-token"}
                    )
                    
                    # Verify multipart upload process
                    assert result["status"] == "completed"
                    assert result["file_id"] == "file-456"
                    assert result["size"] == len(large_file_content)
                    assert result["parts"] == 2
                    
                    # Verify all multipart methods were called
                    mock_init.assert_called_once()
                    assert mock_upload_part.call_count == 2  # Two 5MB chunks
                    mock_complete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_file_upload_proxy_streaming(self, file_upload_proxy):
        """Test streaming file upload without memory buffering."""
        # Create a streaming file-like object
        class AsyncFileStream:
            def __init__(self, data):
                self.data = data
                self.position = 0
                self.chunk_size = 8192
            
            async def read(self, size=-1):
                if self.position >= len(self.data):
                    return b""
                
                if size == -1:
                    chunk = self.data[self.position:]
                    self.position = len(self.data)
                else:
                    end_pos = min(self.position + size, len(self.data))
                    chunk = self.data[self.position:end_pos]
                    self.position = end_pos
                
                return chunk
            
            async def __aiter__(self):
                while True:
                    chunk = await self.read(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk
        
        file_content = b"Streaming file content " * 1000  # ~23KB
        file_stream = AsyncFileStream(file_content)
        
        file_metadata = {
            "filename": "stream-test.txt",
            "content_type": "text/plain",
            "bucket": "test-bucket",
            "path": "streams/test.txt"
        }
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "file_id": "stream-file-789",
            "status": "uploaded",
            "size": len(file_content)
        }
        
        with patch.object(file_upload_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await file_upload_proxy.stream_upload_file(
                file_stream=file_stream,
                metadata=file_metadata,
                auth_headers={"Authorization": "Bearer test-token"}
            )
            
            # Verify streaming upload
            assert result["status"] == "uploaded"
            assert result["file_id"] == "stream-file-789"
            
            # Verify request was made with streaming data
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            # Should use streaming content (async generator)
            assert hasattr(call_args[1]["content"], "__aiter__")  # Should be async iterable
    
    @pytest.mark.asyncio
    async def test_file_upload_proxy_progress_tracking(self, file_upload_proxy):
        """Test upload progress tracking."""
        file_content = b"Progress tracking test content " * 100
        file_metadata = {
            "filename": "progress-test.txt",
            "content_type": "text/plain",
            "bucket": "test-bucket",
            "path": "progress/test.txt"
        }
        
        progress_updates = []
        
        def progress_callback(bytes_uploaded: int, total_bytes: int):
            progress_updates.append({
                "uploaded": bytes_uploaded,
                "total": total_bytes,
                "percentage": (bytes_uploaded / total_bytes) * 100
            })
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "file_id": "progress-file-456",
            "status": "uploaded",
            "size": len(file_content)
        }
        
        with patch.object(file_upload_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await file_upload_proxy.upload_file_with_progress(
                file_data=file_content,
                metadata=file_metadata,
                auth_headers={"Authorization": "Bearer test-token"},
                progress_callback=progress_callback
            )
            
            # Verify upload completed
            assert result["status"] == "uploaded"
            
            # Verify progress tracking
            assert len(progress_updates) > 0
            assert progress_updates[-1]["percentage"] == 100.0  # Should reach 100%
            assert progress_updates[-1]["uploaded"] == len(file_content)
    
    @pytest.mark.asyncio
    async def test_file_upload_proxy_cancellation(self, file_upload_proxy):
        """Test upload cancellation handling."""
        file_content = b"Cancellation test content " * 1000
        file_metadata = {
            "filename": "cancel-test.txt",
            "content_type": "text/plain",
            "bucket": "test-bucket",
            "path": "cancel/test.txt"
        }
        
        # Create a cancellation token
        cancellation_token = asyncio.Event()
        
        async def mock_slow_request(*args, **kwargs):
            # Simulate slow upload that gets cancelled
            await asyncio.sleep(0.1)
            if cancellation_token.is_set():
                raise asyncio.CancelledError("Upload cancelled")
            return Mock(status_code=201)
        
        with patch.object(file_upload_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_slow_request
            
            # Start upload and cancel it
            upload_task = asyncio.create_task(
                file_upload_proxy.upload_file_with_cancellation(
                    file_data=file_content,
                    metadata=file_metadata,
                    auth_headers={"Authorization": "Bearer test-token"},
                    cancellation_token=cancellation_token
                )
            )
            
            # Cancel after a short delay
            await asyncio.sleep(0.05)
            cancellation_token.set()
            
            # Verify cancellation
            with pytest.raises(asyncio.CancelledError):
                await upload_task
    
    @pytest.mark.asyncio
    async def test_file_upload_proxy_error_handling(self, file_upload_proxy):
        """Test various error conditions during upload."""
        file_content = b"Error handling test"
        file_metadata = {
            "filename": "error-test.txt",
            "content_type": "text/plain",
            "bucket": "test-bucket",
            "path": "errors/test.txt"
        }
        
        # Test different error scenarios
        error_scenarios = [
            (413, "File too large"),
            (400, "Invalid file format"),
            (403, "Permission denied"),
            (500, "Internal server error"),
            (503, "Service unavailable")
        ]
        
        for status_code, error_message in error_scenarios:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.json.return_value = {
                "error": error_message,
                "code": f"ERROR_{status_code}"
            }
            
            with patch.object(file_upload_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                
                result = await file_upload_proxy.upload_file(
                    file_data=file_content,
                    metadata=file_metadata,
                    auth_headers={"Authorization": "Bearer test-token"}
                )
                
                # Verify error handling
                assert result["status"] == "error"
                assert result["error_code"] == status_code
                assert error_message in result["error_message"]
    
    @pytest.mark.asyncio
    async def test_file_upload_proxy_authentication_forwarding(self, file_upload_proxy):
        """Test that authentication headers are properly forwarded."""
        file_content = b"Auth test content"
        file_metadata = {
            "filename": "auth-test.txt",
            "content_type": "text/plain",
            "bucket": "test-bucket",
            "path": "auth/test.txt"
        }
        
        auth_headers = {
            "Authorization": "Bearer jwt-token-123",
            "X-API-Key": "api-key-456",
            "X-User-ID": "user-789"
        }
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "file_id": "auth-file-123",
            "status": "uploaded"
        }
        
        with patch.object(file_upload_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            await file_upload_proxy.upload_file(
                file_data=file_content,
                metadata=file_metadata,
                auth_headers=auth_headers
            )
            
            # Verify authentication headers were forwarded
            call_args = mock_request.call_args
            forwarded_headers = call_args[1]["headers"]
            
            assert "Authorization" in forwarded_headers
            assert "X-API-Key" in forwarded_headers
            assert "X-User-ID" in forwarded_headers
            assert forwarded_headers["Authorization"] == "Bearer jwt-token-123"
            assert forwarded_headers["X-API-Key"] == "api-key-456"
            assert forwarded_headers["X-User-ID"] == "user-789"
    
    def test_file_upload_proxy_configuration(self, file_upload_proxy):
        """Test file upload proxy configuration and limits."""
        config = file_upload_proxy.get_configuration()
        
        # Verify configuration settings
        assert config["max_file_size"] > 0
        assert config["chunk_size"] > 0
        assert config["multipart_threshold"] > 0
        assert config["supported_content_types"] is not None
        assert config["max_concurrent_uploads"] > 0
        
        # Test file size validation
        assert file_upload_proxy.is_file_size_valid(1024 * 1024) is True  # 1MB
        assert file_upload_proxy.is_file_size_valid(2 * 1024 * 1024 * 1024) is False  # 2GB (over limit)
        
        # Test content type validation
        assert file_upload_proxy.is_content_type_supported("text/plain") is True
        assert file_upload_proxy.is_content_type_supported("image/jpeg") is True
        assert file_upload_proxy.is_content_type_supported("application/x-malware") is False
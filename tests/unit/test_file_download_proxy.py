"""
Unit tests for file download proxy functionality.

Tests streaming file download through the backend proxy from storage service.
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from typing import Dict, Any


class TestFileDownloadProxy:
    """Test suite for file download proxy functionality."""
    
    @pytest.fixture
    def config_manager(self):
        """Mock configuration manager."""
        config = Mock()
        config.get_setting.side_effect = lambda key: {
            "storage_port": 8003,
            "backend_port": 8000,
            "storage_host": "localhost",
            "download_timeout": 300
        }.get(key, "localhost")
        return config
    
    @pytest.fixture
    def auth_middleware(self):
        """Mock authentication middleware."""
        auth = AsyncMock()
        auth.validate_api_key.return_value = {
            "user_id": "test-user-123",
            "permissions": ["read"]
        }
        return auth
    
    @pytest.fixture
    def file_download_proxy(self, config_manager, auth_middleware):
        """FileDownloadProxy instance for testing."""
        from file_handlers import FileDownloadProxy
        
        return FileDownloadProxy(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
    
    @pytest.mark.asyncio
    async def test_file_download_proxy_basic(self, file_download_proxy):
        """Test basic file download through proxy."""
        # Mock file metadata and content
        file_content = b"This is downloaded file content"
        file_metadata = {
            "bucket": "test-bucket",
            "path": "documents/test.txt",
            "content_type": "text/plain",
            "size": len(file_content)
        }
        
        # Mock storage service response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "text/plain",
            "Content-Length": str(len(file_content)),
            "X-File-Name": "test.txt"
        }
        mock_response.content = file_content
        
        with patch.object(file_download_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await file_download_proxy.download_file(
                bucket=file_metadata["bucket"],
                path=file_metadata["path"],
                auth_headers={"Authorization": "Bearer test-token"}
            )
            
            # Verify successful download
            assert result["status"] == "success"
            assert result["content"] == file_content
            assert result["content_type"] == "text/plain"
            assert result["size"] == len(file_content)
            
            # Verify request was made correctly
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "GET"
            assert "test-bucket" in call_args[1]["url"]
            assert "documents/test.txt" in call_args[1]["url"]
    
    @pytest.mark.asyncio
    async def test_file_download_proxy_streaming(self, file_download_proxy):
        """Test streaming file download without buffering."""
        # Create a mock streaming response
        class AsyncIteratorMock:
            def __init__(self, items):
                self.items = items
                self.index = 0
            
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item
        
        file_chunks = [b"chunk1", b"chunk2", b"chunk3", b"chunk4"]
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": "24"
        }
        def mock_aiter_bytes(chunk_size=8192):
            return AsyncIteratorMock(file_chunks)
        mock_response.aiter_bytes = mock_aiter_bytes
        
        # Create async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_context_manager.__aexit__.return_value = None
        
        with patch.object(file_download_proxy._http_client, 'stream', return_value=mock_context_manager):
            result = await file_download_proxy.stream_download_file(
                bucket="test-bucket",
                path="large-file.bin",
                auth_headers={"Authorization": "Bearer test-token"}
            )
            
            # Should return a streaming response
            assert result["status"] == "streaming"
            assert hasattr(result["stream"], "__aiter__")
            
            # Collect streamed chunks
            chunks = []
            async for chunk in result["stream"]:
                chunks.append(chunk)
            
            assert chunks == file_chunks
    
    @pytest.mark.asyncio
    async def test_file_download_proxy_range_request(self, file_download_proxy):
        """Test partial file download with range requests."""
        # Mock partial content
        partial_content = b"partial file content"
        
        mock_response = Mock()
        mock_response.status_code = 206  # Partial Content
        mock_response.headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(partial_content)),
            "Content-Range": "bytes 100-119/1000",
            "Accept-Ranges": "bytes"
        }
        mock_response.content = partial_content
        
        with patch.object(file_download_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await file_download_proxy.download_file_range(
                bucket="test-bucket",
                path="large-file.bin",
                start_byte=100,
                end_byte=119,
                auth_headers={"Authorization": "Bearer test-token"}
            )
            
            # Verify partial download
            assert result["status"] == "partial"
            assert result["content"] == partial_content
            assert result["range"] == "100-119"
            assert result["total_size"] == 1000
            
            # Verify Range header was sent
            call_args = mock_request.call_args
            assert "Range" in call_args[1]["headers"]
            assert call_args[1]["headers"]["Range"] == "bytes=100-119"
    
    @pytest.mark.asyncio
    async def test_file_download_proxy_head_request(self, file_download_proxy):
        """Test file metadata retrieval using HEAD request."""
        # Mock HEAD response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Type": "image/jpeg",
            "Content-Length": "1024000",
            "Last-Modified": "Wed, 09 Jan 2025 12:00:00 GMT",
            "ETag": "\"abc123def456\"",
            "X-File-Name": "photo.jpg"
        }
        mock_response.content = b""  # HEAD responses have no body
        
        with patch.object(file_download_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await file_download_proxy.get_file_metadata(
                bucket="test-bucket",
                path="images/photo.jpg",
                auth_headers={"Authorization": "Bearer test-token"}
            )
            
            # Verify metadata retrieval
            assert result["status"] == "found"
            assert result["content_type"] == "image/jpeg"
            assert result["size"] == 1024000
            assert result["last_modified"] == "Wed, 09 Jan 2025 12:00:00 GMT"
            assert result["etag"] == "\"abc123def456\""
            assert result["filename"] == "photo.jpg"
            
            # Verify HEAD request was made
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "HEAD"
    
    @pytest.mark.asyncio
    async def test_file_download_proxy_progress_tracking(self, file_download_proxy):
        """Test download progress tracking."""
        # Mock file content in chunks
        file_chunks = [b"x" * 1024 for _ in range(10)]  # 10KB in 1KB chunks
        total_size = sum(len(chunk) for chunk in file_chunks)
        
        progress_updates = []
        
        def progress_callback(bytes_downloaded: int, total_bytes: int):
            progress_updates.append({
                "downloaded": bytes_downloaded,
                "total": total_bytes,
                "percentage": (bytes_downloaded / total_bytes) * 100
            })
        
        class AsyncIteratorMock:
            def __init__(self, items):
                self.items = items
                self.index = 0
            
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Length": str(total_size)}
        def mock_aiter_bytes(chunk_size=8192):
            return AsyncIteratorMock(file_chunks)
        mock_response.aiter_bytes = mock_aiter_bytes
        
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_context_manager.__aexit__.return_value = None
        
        with patch.object(file_download_proxy._http_client, 'stream', return_value=mock_context_manager):
            result = await file_download_proxy.download_file_with_progress(
                bucket="test-bucket",
                path="progress-test.bin",
                auth_headers={"Authorization": "Bearer test-token"},
                progress_callback=progress_callback
            )
            
            # Verify download completed
            assert result["status"] == "success"
            assert result["size"] == total_size
            
            # Verify progress tracking
            assert len(progress_updates) > 0
            assert progress_updates[-1]["percentage"] == 100.0
            assert progress_updates[-1]["downloaded"] == total_size
    
    @pytest.mark.asyncio
    async def test_file_download_proxy_error_handling(self, file_download_proxy):
        """Test various error conditions during download."""
        error_scenarios = [
            (404, "File not found"),
            (403, "Access denied"),
            (410, "File expired"),
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
            
            with patch.object(file_download_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                
                result = await file_download_proxy.download_file(
                    bucket="test-bucket",
                    path="missing-file.txt",
                    auth_headers={"Authorization": "Bearer test-token"}
                )
                
                # Verify error handling
                assert result["status"] == "error"
                assert result["error_code"] == status_code
                assert error_message in result["error_message"]
    
    @pytest.mark.asyncio
    async def test_file_download_proxy_timeout_handling(self, file_download_proxy):
        """Test timeout handling during download."""
        import httpx
        
        with patch.object(file_download_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Download timed out")
            
            result = await file_download_proxy.download_file(
                bucket="test-bucket",
                path="slow-file.bin",
                auth_headers={"Authorization": "Bearer test-token"}
            )
            
            # Verify timeout handling
            assert result["status"] == "timeout"
            assert "timeout" in result["error_message"].lower()
    
    @pytest.mark.asyncio
    async def test_file_download_proxy_authentication_forwarding(self, file_download_proxy):
        """Test that authentication headers are properly forwarded."""
        auth_headers = {
            "Authorization": "Bearer jwt-token-123",
            "X-API-Key": "api-key-456",
            "X-User-ID": "user-789"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"authenticated file content"
        mock_response.headers = {"Content-Type": "text/plain"}
        
        with patch.object(file_download_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            await file_download_proxy.download_file(
                bucket="test-bucket",
                path="secure-file.txt",
                auth_headers=auth_headers
            )
            
            # Verify authentication headers were forwarded
            call_args = mock_request.call_args
            forwarded_headers = call_args[1]["headers"]
            
            assert "Authorization" in forwarded_headers
            assert "X-API-Key" in forwarded_headers
            assert "X-User-ID" in forwarded_headers
            assert forwarded_headers["Authorization"] == "Bearer jwt-token-123"
    
    @pytest.mark.asyncio
    async def test_file_download_proxy_caching_headers(self, file_download_proxy):
        """Test handling of caching and conditional request headers."""
        # Test If-None-Match header (ETag)
        mock_response = Mock()
        mock_response.status_code = 304  # Not Modified
        mock_response.headers = {"ETag": "\"abc123\""}
        mock_response.content = b""
        
        with patch.object(file_download_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await file_download_proxy.download_file_conditional(
                bucket="test-bucket",
                path="cached-file.txt",
                auth_headers={"Authorization": "Bearer test-token"},
                if_none_match="\"abc123\""
            )
            
            # Verify conditional download
            assert result["status"] == "not_modified"
            assert result["etag"] == "\"abc123\""
            
            # Verify If-None-Match header was sent
            call_args = mock_request.call_args
            assert "If-None-Match" in call_args[1]["headers"]
            assert call_args[1]["headers"]["If-None-Match"] == "\"abc123\""
    
    def test_file_download_proxy_configuration(self, file_download_proxy):
        """Test file download proxy configuration."""
        config = file_download_proxy.get_configuration()
        
        # Verify configuration settings
        assert config["download_timeout"] > 0
        assert config["max_concurrent_downloads"] > 0
        assert config["buffer_size"] > 0
        assert config["supports_range_requests"] is True
        assert config["supports_conditional_requests"] is True
        
        # Test URL building
        url = file_download_proxy.build_download_url("test-bucket", "path/to/file.txt")
        assert "test-bucket" in url
        assert "path/to/file.txt" in url
        assert url.startswith("http://localhost:8003")
    
    def test_file_download_proxy_url_validation(self, file_download_proxy):
        """Test URL validation and sanitization."""
        # Test valid paths
        valid_paths = [
            "documents/file.txt",
            "images/photo.jpg",
            "data/2025/report.pdf"
        ]
        
        for path in valid_paths:
            assert file_download_proxy.is_path_valid(path) is True
        
        # Test invalid paths
        invalid_paths = [
            "../../../etc/passwd",  # Path traversal
            "file with spaces.txt",  # Unencoded spaces
            "file\x00.txt",         # Null byte
            "CON.txt",              # Windows reserved name
        ]
        
        for path in invalid_paths:
            assert file_download_proxy.is_path_valid(path) is False
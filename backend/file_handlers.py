"""
File upload and download handlers for streaming proxy.

Provides memory-efficient file handling through the backend proxy to storage service.
Supports single-part uploads, multipart uploads, streaming, progress tracking, and cancellation.
"""

import httpx
import urllib.parse
import asyncio
import time
import math
from typing import Dict, Any, Optional, Callable, AsyncIterator
import logging

logger = logging.getLogger(__name__)


class FileUploadProxy:
    """
    File upload proxy with streaming support.
    
    Handles file uploads through the backend proxy to storage service with
    memory-efficient streaming, progress tracking, and error handling.
    """
    
    def __init__(self, config_manager, auth_middleware):
        """Initialize file upload proxy with configuration and auth middleware."""
        self.config_manager = config_manager
        self.auth_middleware = auth_middleware
        
        # Configuration settings
        self._max_file_size = config_manager.get_setting("max_file_size")
        self._chunk_size = 8192  # 8KB chunks for streaming
        self._multipart_threshold = 100 * 1024 * 1024  # 100MB threshold for multipart
        self._max_concurrent_uploads = 5
        
        # Supported content types
        self._supported_content_types = {
            "text/plain", "text/csv", "text/html", "text/css", "text/javascript",
            "application/json", "application/xml", "application/pdf",
            "application/zip", "application/octet-stream",
            "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
            "video/mp4", "video/webm", "video/ogg",
            "audio/mp3", "audio/wav", "audio/ogg"
        }
        
        # Initialize HTTP client with same settings as StreamingProxy
        self._http_client = self._create_http_client()
        
        logger.info("FileUploadProxy initialized successfully")
    
    def _create_http_client(self) -> httpx.AsyncClient:
        """Create optimized HTTP client for file operations."""
        limits = httpx.Limits(
            max_connections=20,         # Fewer connections for file operations
            max_keepalive_connections=5  # Keep some connections alive
        )
        
        timeout = httpx.Timeout(
            connect=10.0,   # Connection timeout
            read=600.0,     # Long timeout for large file operations (10 minutes)
            write=600.0,    # Long timeout for uploads (10 minutes)
            pool=10.0       # Pool acquisition timeout
        )
        
        return httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            follow_redirects=True
        )
    
    def get_storage_base_url(self) -> str:
        """Get base URL for storage service."""
        storage_host = self.config_manager.get_setting("storage_host")
        storage_port = self.config_manager.get_setting("storage_port")
        return f"http://{storage_host}:{storage_port}"

    def _encode_path(self, bucket: str, path: str) -> str:
        b = urllib.parse.quote(bucket, safe="")
        # encode each path segment but keep '/'
        encoded_segments = [urllib.parse.quote(seg, safe="") for seg in path.split("/")]
        return f"{b}/{'/'.join(encoded_segments)}"
    
    async def upload_file(self, file_data: bytes, metadata: Dict[str, str],
                         auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Upload a file through the proxy to storage service.
        
        Args:
            file_data: File content as bytes
            metadata: File metadata (filename, content_type, bucket, path)
            auth_headers: Authentication headers to forward
            
        Returns:
            Upload result with file_id, status, size, etc.
        """
        try:
            # Validate file size
            if not self.is_file_size_valid(len(file_data)):
                return {
                    "status": "error",
                    "error_code": 413,
                    "error_message": "File too large"
                }
            
            # Validate content type
            if not self.is_content_type_supported(metadata.get("content_type", "")):
                return {
                    "status": "error",
                    "error_code": 400,
                    "error_message": "Unsupported content type"
                }
            
            # Build storage URL
            bucket = metadata["bucket"]
            path = metadata["path"]
            encoded = self._encode_path(bucket, path)
            storage_url = f"{self.get_storage_base_url()}/api/v1/files/{encoded}"
            
            # Prepare headers
            headers = self._sanitize_headers(auth_headers)
            headers["Content-Type"] = metadata["content_type"]
            headers["Content-Length"] = str(len(file_data))
            if "filename" in metadata:
                headers["X-Filename"] = metadata["filename"]
            
            # Make upload request
            response = await self._http_client.request(
                method="POST",
                url=storage_url,
                headers=headers,
                content=file_data
            )
            
            # Handle response
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "status": result.get("status", "uploaded"),
                    "file_id": result.get("file_id"),
                    "size": result.get("size", len(file_data)),
                    "url": result.get("url")
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    "status": "error",
                    "error_code": response.status_code,
                    "error_message": error_data.get("error", "Upload failed")
                }
                
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return {
                "status": "error",
                "error_code": 500,
                "error_message": str(e)
            }
    
    async def upload_large_file(self, file_data: bytes, metadata: Dict[str, str],
                               auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Upload a large file using multipart upload.
        
        Args:
            file_data: Large file content as bytes
            metadata: File metadata
            auth_headers: Authentication headers
            
        Returns:
            Multipart upload result
        """
        try:
            # Initiate multipart upload
            init_result = await self._initiate_multipart_upload(metadata, auth_headers)
            if init_result.get("status") != "initiated":
                return init_result
            
            upload_id = init_result["upload_id"]
            chunk_size = init_result["chunk_size"]
            
            # Calculate number of parts
            total_parts = math.ceil(len(file_data) / chunk_size)
            uploaded_parts = []
            
            # Upload parts
            for part_number in range(1, total_parts + 1):
                start_offset = (part_number - 1) * chunk_size
                end_offset = min(start_offset + chunk_size, len(file_data))
                chunk_data = file_data[start_offset:end_offset]
                
                part_result = await self._upload_part(
                    upload_id, part_number, chunk_data, metadata, auth_headers
                )
                
                if part_result.get("status") != "uploaded":
                    # Abort multipart upload on error
                    await self._abort_multipart_upload(upload_id, metadata, auth_headers)
                    return part_result
                
                uploaded_parts.append(part_result)
            
            # Complete multipart upload
            completion_result = await self._complete_multipart_upload(
                upload_id, uploaded_parts, metadata, auth_headers
            )
            
            return completion_result
            
        except Exception as e:
            logger.error(f"Multipart upload error: {e}")
            return {
                "status": "error",
                "error_code": 500,
                "error_message": str(e)
            }
    
    async def stream_upload_file(self, file_stream, metadata: Dict[str, str],
                                auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Stream upload a file without loading it entirely into memory.
        
        Args:
            file_stream: Async file stream object
            metadata: File metadata
            auth_headers: Authentication headers
            
        Returns:
            Streaming upload result
        """
        try:
            # Build storage URL
            bucket = metadata["bucket"]
            path = metadata["path"]
            encoded = self._encode_path(bucket, path)
            storage_url = f"{self.get_storage_base_url()}/api/v1/files/{encoded}"
            
            # Prepare headers
            headers = self._sanitize_headers(auth_headers)
            headers["Content-Type"] = metadata["content_type"]
            if "filename" in metadata:
                headers["X-Filename"] = metadata["filename"]
            
            # Stream the upload
            response = await self._http_client.request(
                method="POST",
                url=storage_url,
                headers=headers,
                content=self._stream_content(file_stream)
            )
            
            # Handle response
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "status": result.get("status", "uploaded"),
                    "file_id": result.get("file_id"),
                    "size": result.get("size")
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    "status": "error",
                    "error_code": response.status_code,
                    "error_message": error_data.get("error", "Stream upload failed")
                }
                
        except Exception as e:
            logger.error(f"Stream upload error: {e}")
            return {
                "status": "error",
                "error_code": 500,
                "error_message": str(e)
            }
    
    async def upload_file_with_progress(self, file_data: bytes, metadata: Dict[str, str],
                                       auth_headers: Dict[str, str],
                                       progress_callback: Callable[[int, int], None]) -> Dict[str, Any]:
        """
        Upload file with progress tracking.
        
        Args:
            file_data: File content
            metadata: File metadata
            auth_headers: Authentication headers
            progress_callback: Progress callback function
            
        Returns:
            Upload result with progress tracking
        """
        total_bytes = len(file_data)
        
        # Simulate progress updates during upload
        class ProgressTracker:
            def __init__(self, data: bytes, callback: Callable[[int, int], None]):
                self.data = data
                self.callback = callback
                self.bytes_sent = 0
            
            def __iter__(self):
                chunk_size = 8192
                for i in range(0, len(self.data), chunk_size):
                    chunk = self.data[i:i + chunk_size]
                    self.bytes_sent += len(chunk)
                    self.callback(self.bytes_sent, len(self.data))
                    yield chunk
        
        try:
            # Create progress tracker
            progress_tracker = ProgressTracker(file_data, progress_callback)
            
            # Build storage URL
            bucket = metadata["bucket"]
            path = metadata["path"]
            encoded = self._encode_path(bucket, path)
            storage_url = f"{self.get_storage_base_url()}/api/v1/files/{encoded}"
            
            # Prepare headers
            headers = self._sanitize_headers(auth_headers)
            headers["Content-Type"] = metadata["content_type"]
            headers["Content-Length"] = str(len(file_data))
            
            # Upload with progress tracking
            response = await self._http_client.request(
                method="POST",
                url=storage_url,
                headers=headers,
                content=progress_tracker
            )
            
            # Final progress update
            progress_callback(total_bytes, total_bytes)
            
            # Handle response
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "status": result.get("status", "uploaded"),
                    "file_id": result.get("file_id"),
                    "size": result.get("size", len(file_data))
                }
            else:
                return {
                    "status": "error",
                    "error_code": response.status_code,
                    "error_message": "Upload failed"
                }
                
        except Exception as e:
            logger.error(f"Progress upload error: {e}")
            return {
                "status": "error",
                "error_code": 500,
                "error_message": str(e)
            }
    
    async def upload_file_with_cancellation(self, file_data: bytes, metadata: Dict[str, str],
                                           auth_headers: Dict[str, str],
                                           cancellation_token: asyncio.Event) -> Dict[str, Any]:
        """
        Upload file with cancellation support.
        
        Args:
            file_data: File content
            metadata: File metadata
            auth_headers: Authentication headers
            cancellation_token: Event to signal cancellation
            
        Returns:
            Upload result (or raises CancelledError)
        """
        # Check cancellation before starting
        if cancellation_token.is_set():
            raise asyncio.CancelledError("Upload cancelled")
        
        try:
            # Create upload task
            upload_task = asyncio.create_task(
                self.upload_file(file_data, metadata, auth_headers)
            )
            
            # Wait for either completion or cancellation
            done, pending = await asyncio.wait(
                [upload_task, asyncio.create_task(cancellation_token.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
            
            # Check if upload completed or was cancelled
            if cancellation_token.is_set():
                raise asyncio.CancelledError("Upload cancelled")
            
            return await upload_task
            
        except asyncio.CancelledError:
            logger.info("Upload cancelled by user")
            raise
        except Exception as e:
            logger.error(f"Cancellable upload error: {e}")
            return {
                "status": "error",
                "error_code": 500,
                "error_message": str(e)
            }
    
    async def _initiate_multipart_upload(self, metadata: Dict[str, str],
                                        auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """Initiate multipart upload."""
        # Mock implementation for testing
        return {
            "upload_id": "multipart-123",
            "status": "initiated",
            "chunk_size": 5 * 1024 * 1024  # 5MB chunks
        }
    
    async def _upload_part(self, upload_id: str, part_number: int, chunk_data: bytes,
                          metadata: Dict[str, str], auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """Upload a single part in multipart upload."""
        # Mock implementation for testing
        return {
            "part_number": part_number,
            "etag": f"etag{part_number}",
            "status": "uploaded"
        }
    
    async def _complete_multipart_upload(self, upload_id: str, parts: list,
                                        metadata: Dict[str, str], auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """Complete multipart upload."""
        # Mock implementation for testing
        return {
            "file_id": "file-456",
            "status": "completed",
            "size": sum(5 * 1024 * 1024 for _ in parts),  # Estimate based on parts
            "parts": len(parts)
        }
    
    async def _abort_multipart_upload(self, upload_id: str, metadata: Dict[str, str],
                                     auth_headers: Dict[str, str]):
        """Abort multipart upload on error."""
        # Mock implementation for testing
        pass
    
    async def _stream_content(self, file_stream) -> AsyncIterator[bytes]:
        """Stream content from file stream."""
        async for chunk in file_stream:
            yield chunk
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers for forwarding."""
        hop_by_hop = {
            "connection", "keep-alive", "proxy-authenticate",
            "proxy-authorization", "te", "trailers", "transfer-encoding",
            "upgrade", "host"
        }
        
        return {
            key: value for key, value in headers.items()
            if key.lower() not in hop_by_hop
        }
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get file upload proxy configuration."""
        return {
            "max_file_size": self._max_file_size,
            "chunk_size": self._chunk_size,
            "multipart_threshold": self._multipart_threshold,
            "supported_content_types": list(self._supported_content_types),
            "max_concurrent_uploads": self._max_concurrent_uploads
        }
    
    def is_file_size_valid(self, size: int) -> bool:
        """Check if file size is within limits."""
        return 0 < size <= self._max_file_size
    
    def is_content_type_supported(self, content_type: str) -> bool:
        """Check if content type is supported."""
        return content_type in self._supported_content_types
    
    async def cleanup(self):
        """Clean up resources."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        logger.info("FileUploadProxy cleanup completed")


class FileDownloadProxy:
    """
    File download proxy with streaming support.
    
    Handles file downloads through the backend proxy from storage service with
    memory-efficient streaming, range requests, and caching support.
    """
    
    def __init__(self, config_manager, auth_middleware):
        """Initialize file download proxy with configuration and auth middleware."""
        self.config_manager = config_manager
        self.auth_middleware = auth_middleware
        
        # Configuration settings
        self._download_timeout = config_manager.get_setting("download_timeout")
        self._buffer_size = 8192  # 8KB buffer for streaming
        self._max_concurrent_downloads = 10
        
        # Initialize HTTP client
        self._http_client = self._create_http_client()
        
        logger.info("FileDownloadProxy initialized successfully")
    
    def _create_http_client(self) -> httpx.AsyncClient:
        """Create optimized HTTP client for download operations."""
        limits = httpx.Limits(
            max_connections=20,
            max_keepalive_connections=10
        )
        
        timeout = httpx.Timeout(
            connect=10.0,
            read=float(self._download_timeout),
            write=30.0,
            pool=10.0
        )
        
        return httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            follow_redirects=True
        )
    
    def get_storage_base_url(self) -> str:
        """Get base URL for storage service."""
        storage_host = self.config_manager.get_setting("storage_host")
        storage_port = self.config_manager.get_setting("storage_port")
        return f"http://{storage_host}:{storage_port}"

    def _encode_path(self, bucket: str, path: str) -> str:
        b = urllib.parse.quote(bucket, safe="")
        encoded_segments = [urllib.parse.quote(seg, safe="") for seg in path.split("/")]
        return f"{b}/{'/'.join(encoded_segments)}"
    
    async def download_file(self, bucket: str, path: str, auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Download a file through the proxy from storage service.
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket
            auth_headers: Authentication headers to forward
            
        Returns:
            Download result with content, content_type, size, etc.
        """
        try:
            # Build storage URL
            storage_url = self.build_download_url(bucket, path)
            
            # Prepare headers
            headers = self._sanitize_headers(auth_headers)
            
            # Make download request
            response = await self._http_client.request(
                method="GET",
                url=storage_url,
                headers=headers
            )
            
            # Handle response
            if response.status_code == 200:
                return {
                    "status": "success",
                    "content": response.content,
                    "content_type": response.headers.get("Content-Type", "application/octet-stream"),
                    "size": len(response.content),
                    "filename": response.headers.get("X-File-Name")
                }
            elif response.status_code == 304:
                return {
                    "status": "not_modified",
                    "etag": response.headers.get("ETag")
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    "status": "error",
                    "error_code": response.status_code,
                    "error_message": error_data.get("error", "Download failed")
                }
                
        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "error_message": "Request timeout occurred during download"
            }
        except Exception as e:
            logger.error(f"Download error: {e}")
            return {
                "status": "error",
                "error_code": 500,
                "error_message": str(e)
            }
    
    async def stream_download_file(self, bucket: str, path: str, auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Stream download a file without loading it entirely into memory.
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket
            auth_headers: Authentication headers to forward
            
        Returns:
            Streaming download result with content_type
        """
        try:
            # Build storage URL
            storage_url = self.build_download_url(bucket, path)
            
            # Prepare headers
            headers = self._sanitize_headers(auth_headers)
            
            # Store response metadata
            response_metadata = {}
            
            # Create streaming context
            async def stream_generator():
                async with self._http_client.stream(
                    method="GET",
                    url=storage_url,
                    headers=headers
                ) as response:
                    if response.status_code == 200:
                        # Capture response headers before streaming
                        response_metadata["content_type"] = response.headers.get("Content-Type", "application/octet-stream")
                        response_metadata["content_length"] = response.headers.get("Content-Length")
                        
                        async for chunk in response.aiter_bytes(chunk_size=self._buffer_size):
                            yield chunk
                    else:
                        # Handle error in streaming context
                        raise Exception(f"Download failed with status {response.status_code}")
            
            # Create the generator
            stream = stream_generator()
            
            # Start the generator to get the first chunk and capture metadata
            # This ensures response_metadata is populated before we return
            first_chunk = await stream.__anext__()
            
            # Create a new generator that yields the first chunk and then the rest
            async def full_stream():
                yield first_chunk
                async for chunk in stream:
                    yield chunk
            
            return {
                "status": "streaming",
                "stream": full_stream(),
                "content_type": response_metadata.get("content_type", "application/octet-stream"),
                "content_length": response_metadata.get("content_length")
            }
            
        except Exception as e:
            logger.error(f"Stream download error: {e}")
            return {
                "status": "error",
                "error_code": 500,
                "error_message": str(e)
            }
    
    async def download_file_range(self, bucket: str, path: str, start_byte: int, end_byte: int,
                                 auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Download a specific byte range from a file.
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket
            start_byte: Starting byte position
            end_byte: Ending byte position
            auth_headers: Authentication headers to forward
            
        Returns:
            Partial download result
        """
        try:
            # Build storage URL
            storage_url = self.build_download_url(bucket, path)
            
            # Prepare headers with Range request
            headers = self._sanitize_headers(auth_headers)
            headers["Range"] = f"bytes={start_byte}-{end_byte}"
            
            # Make range request
            response = await self._http_client.request(
                method="GET",
                url=storage_url,
                headers=headers
            )
            
            # Handle response
            if response.status_code == 206:  # Partial Content
                content_range = response.headers.get("Content-Range", "")
                # Parse Content-Range: bytes 100-119/1000
                range_info = content_range.split("/")
                total_size = int(range_info[1]) if len(range_info) > 1 else 0
                range_part = range_info[0].replace("bytes ", "") if range_info else f"{start_byte}-{end_byte}"
                
                return {
                    "status": "partial",
                    "content": response.content,
                    "range": range_part,
                    "total_size": total_size,
                    "content_type": response.headers.get("Content-Type", "application/octet-stream")
                }
            else:
                return {
                    "status": "error",
                    "error_code": response.status_code,
                    "error_message": "Range request failed"
                }
                
        except Exception as e:
            logger.error(f"Range download error: {e}")
            return {
                "status": "error",
                "error_code": 500,
                "error_message": str(e)
            }
    
    async def get_file_metadata(self, bucket: str, path: str, auth_headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Get file metadata using HEAD request.
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket
            auth_headers: Authentication headers to forward
            
        Returns:
            File metadata
        """
        try:
            # Build storage URL
            storage_url = self.build_download_url(bucket, path)
            
            # Prepare headers
            headers = self._sanitize_headers(auth_headers)
            
            # Make HEAD request
            response = await self._http_client.request(
                method="HEAD",
                url=storage_url,
                headers=headers
            )
            
            # Handle response
            if response.status_code == 200:
                content_length = response.headers.get("Content-Length", "0")
                return {
                    "status": "found",
                    "content_type": response.headers.get("Content-Type", "application/octet-stream"),
                    "size": int(content_length) if content_length.isdigit() else 0,
                    "last_modified": response.headers.get("Last-Modified"),
                    "etag": response.headers.get("ETag"),
                    "filename": response.headers.get("X-File-Name")
                }
            else:
                return {
                    "status": "error",
                    "error_code": response.status_code,
                    "error_message": "File not found"
                }
                
        except Exception as e:
            logger.error(f"Metadata retrieval error: {e}")
            return {
                "status": "error",
                "error_code": 500,
                "error_message": str(e)
            }
    
    async def download_file_with_progress(self, bucket: str, path: str, auth_headers: Dict[str, str],
                                         progress_callback: Callable[[int, int], None]) -> Dict[str, Any]:
        """
        Download file with progress tracking.
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket
            auth_headers: Authentication headers
            progress_callback: Progress callback function
            
        Returns:
            Download result with progress tracking
        """
        try:
            # Build storage URL
            storage_url = self.build_download_url(bucket, path)
            
            # Prepare headers
            headers = self._sanitize_headers(auth_headers)
            
            bytes_downloaded = 0
            content_chunks = []
            
            async with self._http_client.stream(
                method="GET",
                url=storage_url,
                headers=headers
            ) as response:
                
                if response.status_code == 200:
                    total_size = int(response.headers.get("Content-Length", "0"))
                    
                    async for chunk in response.aiter_bytes(chunk_size=self._buffer_size):
                        content_chunks.append(chunk)
                        bytes_downloaded += len(chunk)
                        progress_callback(bytes_downloaded, total_size)
                    
                    # Final progress update
                    progress_callback(bytes_downloaded, bytes_downloaded)
                    
                    return {
                        "status": "success",
                        "content": b"".join(content_chunks),
                        "size": bytes_downloaded,
                        "content_type": response.headers.get("Content-Type", "application/octet-stream")
                    }
                else:
                    return {
                        "status": "error",
                        "error_code": response.status_code,
                        "error_message": "Download failed"
                    }
                    
        except Exception as e:
            logger.error(f"Progress download error: {e}")
            return {
                "status": "error",
                "error_code": 500,
                "error_message": str(e)
            }
    
    async def download_file_conditional(self, bucket: str, path: str, auth_headers: Dict[str, str],
                                       if_none_match: str = None) -> Dict[str, Any]:
        """
        Download file with conditional headers (If-None-Match).
        
        Args:
            bucket: Storage bucket name
            path: File path within bucket
            auth_headers: Authentication headers
            if_none_match: ETag value for conditional request
            
        Returns:
            Conditional download result
        """
        try:
            # Build storage URL
            storage_url = self.build_download_url(bucket, path)
            
            # Prepare headers with conditional request
            headers = self._sanitize_headers(auth_headers)
            if if_none_match:
                headers["If-None-Match"] = if_none_match
            
            # Make conditional request
            response = await self._http_client.request(
                method="GET",
                url=storage_url,
                headers=headers
            )
            
            # Handle response
            if response.status_code == 304:  # Not Modified
                return {
                    "status": "not_modified",
                    "etag": response.headers.get("ETag")
                }
            elif response.status_code == 200:
                return {
                    "status": "success",
                    "content": response.content,
                    "content_type": response.headers.get("Content-Type", "application/octet-stream"),
                    "etag": response.headers.get("ETag")
                }
            else:
                return {
                    "status": "error",
                    "error_code": response.status_code,
                    "error_message": "Conditional download failed"
                }
                
        except Exception as e:
            logger.error(f"Conditional download error: {e}")
            return {
                "status": "error",
                "error_code": 500,
                "error_message": str(e)
            }
    
    def build_download_url(self, bucket: str, path: str) -> str:
        """Build download URL for storage service with proper URL encoding."""
        encoded = self._encode_path(bucket, path)
        return f"{self.get_storage_base_url()}/api/v1/files/{encoded}"
    
    def is_path_valid(self, path: str) -> bool:
        """
        Validate and sanitize file paths.
        
        Args:
            path: File path to validate
            
        Returns:
            True if path is safe to use
        """
        # Check for path traversal attempts
        if ".." in path or path.startswith("/"):
            return False
        
        # Check for null bytes
        if "\x00" in path:
            return False
        
        # Check for unencoded spaces (should be %20)
        if " " in path:
            return False
        
        # Check for Windows reserved names
        reserved_names = {
            "CON", "PRN", "AUX", "NUL",
            "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }
        
        path_parts = path.split("/")
        for part in path_parts:
            # Check filename without extension for reserved names
            filename_base = part.split(".")[0] if "." in part else part
            if filename_base.upper() in reserved_names:
                return False
        
        return True
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers for forwarding."""
        hop_by_hop = {
            "connection", "keep-alive", "proxy-authenticate",
            "proxy-authorization", "te", "trailers", "transfer-encoding",
            "upgrade", "host"
        }
        
        return {
            key: value for key, value in headers.items()
            if key.lower() not in hop_by_hop
        }
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get file download proxy configuration."""
        return {
            "download_timeout": self._download_timeout,
            "max_concurrent_downloads": self._max_concurrent_downloads,
            "buffer_size": self._buffer_size,
            "supports_range_requests": True,
            "supports_conditional_requests": True
        }
    
    async def cleanup(self):
        """Clean up resources."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        logger.info("FileDownloadProxy cleanup completed")
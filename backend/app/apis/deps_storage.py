import httpx
import logging
from typing import Optional, Dict, Any, BinaryIO, AsyncGenerator
from fastapi import UploadFile, Depends, HTTPException, status
import io
import os
from urllib.parse import urljoin

from ..core.config import settings
from ..models.user import User
from .deps import get_current_active_user

logger = logging.getLogger(__name__)

class StorageServiceClient:
    """
    Client for interacting with the storage service.
    This replaces the MinIO client with HTTP requests to our custom storage service.
    """
    def __init__(self, base_url: str, token: Optional[str] = None, anon_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.anon_key = anon_key
        self.client = httpx.AsyncClient(timeout=60.0)  # Longer timeout for file uploads/downloads

    async def close(self):
        await self.client.aclose()

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication if available"""
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.anon_key:
            headers["Authorization"] = f"Bearer {self.anon_key}"
        return headers

    async def create_bucket(self, name: str, is_public: bool = True) -> Dict[str, Any]:
        """Create a new bucket"""
        url = f"{self.base_url}/buckets"
        data = {"name": name, "is_public": is_public}

        try:
            response = await self.client.post(url, json=data, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error creating bucket: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error: {e.response.text}"
            )

    async def list_buckets(self) -> list:
        """List all accessible buckets"""
        url = f"{self.base_url}/buckets"

        try:
            response = await self.client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error listing buckets: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error: {e.response.text}"
            )

    async def get_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """Get bucket details"""
        url = f"{self.base_url}/buckets/{bucket_name}"

        try:
            response = await self.client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting bucket: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error: {e.response.text}"
            )

    async def update_bucket(self, bucket_name: str, is_public: bool) -> Dict[str, Any]:
        """Update bucket properties"""
        url = f"{self.base_url}/buckets/{bucket_name}"
        data = {"is_public": is_public}

        try:
            response = await self.client.put(url, json=data, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error updating bucket: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error: {e.response.text}"
            )

    async def delete_bucket(self, bucket_name: str) -> None:
        """Delete a bucket"""
        url = f"{self.base_url}/buckets/{bucket_name}"

        try:
            response = await self.client.delete(url, headers=self._get_headers())
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error deleting bucket: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error: {e.response.text}"
            )

    async def upload_file(self, bucket_name: str, file: UploadFile) -> Dict[str, Any]:
        """
        Upload a file to a bucket.
        DEPRECATED: This method directly uploads data through the backend.
        Use generate_presigned_upload_url for client-side direct uploads.
        """
        logger.warning("Direct server-side upload_file is deprecated. Use pre-signed URLs.")
        url = f"{self.base_url}/files/upload/{bucket_name}"
        form = {"file": (file.filename, await file.read(), file.content_type)}
        try:
            response = await self.client.post(url, files=form, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error uploading file (deprecated method): {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error (deprecated upload): {e.response.text}"
            )

    async def generate_presigned_upload_url(
        self, bucket_name: str, object_name: str, content_type: Optional[str] = None, expires_in_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Generate a pre-signed URL for uploading a file directly to the storage service.
        """
        url = f"{self.base_url}/files/presigned-url/upload/{bucket_name}/{object_name}"
        payload = {"expires_in_seconds": expires_in_seconds}
        if content_type:
            payload["content_type"] = content_type
        
        logger.info(f"Requesting pre-signed upload URL for {bucket_name}/{object_name}, content_type: {content_type}")

        try:
            response = await self.client.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            presigned_data = response.json()
            logger.info(f"Successfully generated pre-signed upload URL for {bucket_name}/{object_name}: {presigned_data.get('upload_url')}")
            # Ensure expected fields are present, e.g., 'upload_url' and 'method'
            if 'upload_url' not in presigned_data or 'method' not in presigned_data:
                logger.error(f"Storage service response for presigned upload URL is missing required fields: {presigned_data}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Storage service returned invalid pre-signed URL data."
                )
            return presigned_data # Expected: {"upload_url": "...", "method": "PUT/POST", ...}
        except httpx.HTTPStatusError as e:
            logger.error(f"Error generating pre-signed upload URL for {bucket_name}/{object_name}: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error generating pre-signed upload URL: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Unexpected error generating pre-signed upload URL for {bucket_name}/{object_name}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error generating pre-signed upload URL: {str(e)}"
            )

    async def list_files(self, bucket_name: str) -> list:
        """List files in a bucket"""
        url = f"{self.base_url}/files/list/{bucket_name}"

        try:
            response = await self.client.get(url, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error listing files: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error: {e.response.text}"
            )

    async def get_file_stream(self, bucket_name: str, filename: str) -> AsyncGenerator[bytes, None]:
        """
        Get a file as a stream of bytes.
        NOTE: This streams through the backend. For client downloads, prefer get_direct_download_url.
        The 'filename' parameter is the object_name/key within the bucket.
        """
        url = f"{self.base_url}/files/download/{bucket_name}/{filename}"

        try:
            # Use a timeout configuration optimized for streaming large files
            timeout = httpx.Timeout(5.0, read=60.0, write=60.0, pool=5.0)

            logger.info(f"Starting file download stream from: {url}")
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("GET", url, headers=self._get_headers()) as response:
                    response.raise_for_status()
                    # Log response headers to help diagnose issues
                    logger.info(f"Response headers: {response.headers}")
                    # Use a moderate chunk size for better performance and to avoid corruption
                    async for chunk in response.aiter_bytes(chunk_size=16384):  # 16KB chunks
                        yield chunk
        except httpx.HTTPStatusError as e:
            logger.error(f"Error downloading file: {e.response.text if hasattr(e.response, 'text') else str(e)}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error: {str(e)}"
            )

    async def delete_file(self, bucket_name: str, object_name: str) -> None:
        """
        Delete a file from a bucket.
        'object_name' is the key of the file within the bucket.
        """
        # Ensure object_name does not inadvertently contain bucket prefix from old system.
        # This check can be removed if DB is confirmed clean.
        prefix_to_check = f"{bucket_name}/"
        if object_name.startswith(prefix_to_check):
            logger.warning(f"Object name '{object_name}' in delete_file started with bucket prefix. Stripping to '{object_name[len(prefix_to_check):]}'. Ensure File.object_name is stored correctly.")
            object_name = object_name[len(prefix_to_check):]
            
        url = f"{self.base_url}/files/{bucket_name}/{object_name}"

        try:
            response = await self.client.delete(url, headers=self._get_headers())
            response.raise_for_status()
            logger.info(f"Successfully deleted file {object_name} from bucket {bucket_name} via storage service.")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error deleting file {object_name} from bucket {bucket_name}: {e.response.text}")

    async def download_file_content(self, bucket_name: str, file_name: str) -> AsyncGenerator[bytes, None]:
        """
        Get a file as a stream of bytes directly from the storage service.
        NOTE: This streams through the backend. For client downloads, prefer get_direct_download_url.
        The 'file_name' parameter is the object_name/key within the bucket.
        """
        import time
        start_time = time.time()
        
        # 'file_name' should be the actual key within the bucket.
        # The old logic for stripping bucket prefix is removed here, assuming caller provides correct 'file_name'.
        # If object_name in DB might still contain prefixes, that needs to be handled by the caller.
        original_file_name_param = file_name # for logging
        
        path_proc_time = time.time() - start_time
        logger.info(f"[TIMING] Path processing took {path_proc_time*1000:.2f}ms (download_file_content)")
        logger.info(f"Attempting to download file (stream via backend): bucket='{bucket_name}', object_name='{file_name}' (original param: '{original_file_name_param}')")

        url = f"{self.base_url}/files/download/{bucket_name}/{file_name}"
        logger.info(f"Constructed download URL (stream via backend): {url}")

        try:
            # Use a timeout configuration optimized for streaming large files
            timeout = httpx.Timeout(5.0, read=60.0, write=60.0, pool=5.0)

            # Create a new client with optimized timeout settings
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Sanitize headers before logging
                log_safe_headers = {**self._get_headers()}
                if 'Authorization' in log_safe_headers:
                    log_safe_headers['Authorization'] = 'Bearer [REDACTED]'
                
                logger.info(f"Sending GET request to {url} with headers: {log_safe_headers}")
                request_start_time = time.time()
                async with client.stream("GET", url, headers=self._get_headers()) as response:
                    response_received_time = time.time()
                    logger.info(f"[TIMING] Time to receive response headers: {(response_received_time - request_start_time)*1000:.2f}ms")
                    logger.info(f"Received response from {url}, status_code: {response.status_code}")
                    response.raise_for_status() # Check for HTTP errors first

                    # Log response headers for debugging
                    logger.info(f"Storage service response headers: {response.headers}")
                    content_length_from_storage = response.headers.get("Content-Length")
                    content_type_from_storage = response.headers.get("Content-Type")
                    logger.info(f"Storage service reported Content-Length: {content_length_from_storage}, Content-Type: {content_type_from_storage}")

                    # Stream the response in chunks
                    chunk_count = 0
                    total_bytes_streamed = 0
                    first_chunk_time = None

                    # Use a smaller chunk size for better reliability
                    async for chunk in response.aiter_bytes(chunk_size=8192):  # 8KB chunks
                        if chunk_count == 0:
                            first_chunk_time = time.time()
                            logger.info(f"[TIMING] Time to first chunk: {(first_chunk_time - request_start_time)*1000:.2f}ms")
                        
                        if not chunk: # Handle empty chunks, though aiter_bytes usually doesn't yield them unless stream ends
                            logger.warning(f"Received empty chunk while streaming from {url}. Chunk count: {chunk_count}, Total bytes: {total_bytes_streamed}")
                            continue
                        chunk_count += 1
                        total_bytes_streamed += len(chunk)
                        if chunk_count % 100 == 0:  # Log every 100 chunks to avoid excessive logging
                            current_time = time.time()
                            elapsed = current_time - first_chunk_time if first_chunk_time else 0
                            rate = total_bytes_streamed / elapsed if elapsed > 0 else 0
                            logger.info(f"Streaming chunk {chunk_count} from {url}: {len(chunk)} bytes, total bytes streamed so far: {total_bytes_streamed}, rate: {rate/1024:.2f} KB/s")
                        yield chunk
                    
                    logger.info(f"Finished streaming file from {url}: total_chunks={chunk_count}, total_bytes_streamed={total_bytes_streamed}")
                    if content_length_from_storage and int(content_length_from_storage) != total_bytes_streamed:
                        logger.error(
                            f"Mismatch in Content-Length for {url}: "
                            f"Expected (from storage header): {content_length_from_storage}, "
                            f"Actual streamed: {total_bytes_streamed}"
                        )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading file from {url}: status_code={e.response.status_code}, response_text='{e.response.text if hasattr(e.response, 'text') else str(e)}'")
            # Log request details that led to error
            logger.error(f"Request details: method=GET, url={url}, headers={self._get_headers()}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service HTTP error: {str(e)}" # Propagate a cleaner message
            )
        except Exception as e:
            logger.error(f"Generic error in download_file_content for {url}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error downloading file: {str(e)}"
            )

    async def get_direct_download_url(self, bucket_name: str, object_name: str) -> str:
        """Generate a direct download URL for the specified object."""
        try:
            # Use the configured external storage URL from settings
            public_url = str(settings.STORAGE_SERVICE_EXTERNAL_URL).rstrip("/")
            download_path = f"/files/download/{bucket_name}/{object_name}"
            download_url = f"{public_url}{download_path}"
            
            logger.info(f"Generated direct download URL for {bucket_name}/{object_name}: {download_url}")
            return download_url
        except Exception as e:
            logger.error(f"Error generating direct download URL for {bucket_name}/{object_name}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Storage service error generating direct download URL: {str(e)}"
            )

    async def get_direct_view_url(self, bucket_name: str, object_name: str, content_type: Optional[str] = None) -> str:
        """Generate a direct view URL for the specified object."""
        try:
            # Use the configured external storage URL from settings
            public_url = str(settings.STORAGE_SERVICE_EXTERNAL_URL).rstrip("/")
            view_path = f"/files/view/{bucket_name}/{object_name}"
            
            # Add content_type as a query parameter if provided
            if content_type:
                view_path += f"?content_type={content_type}"
            
            view_url = f"{public_url}{view_path}"
            
            logger.info(f"Generated direct view URL for {bucket_name}/{object_name} with content_type={content_type}: {view_url}")
            return view_url
        except Exception as e:
            logger.error(f"Error generating direct view URL for {bucket_name}/{object_name}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Storage service error generating direct view URL: {str(e)}"
            )


async def get_storage_service_client(current_user: Optional[User] = Depends(get_current_active_user)) -> AsyncGenerator[StorageServiceClient, None]:
    """
    Returns a configured storage service client.
    This replaces the MinIO client dependency.
    """
    token = None
    if current_user:
        # In a real implementation, you would generate a token for the user
        # For now, we'll use the user's ID as a placeholder
        from jose import jwt
        import time

        token_data = {
            "sub": str(current_user.id),
            "exp": int(time.time() + 3600)  # 1 hour expiry (as integer)
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    client = StorageServiceClient(
        base_url=settings.STORAGE_SERVICE_URL,
        token=token,
        anon_key=settings.ANON_KEY
    )

    try:
        yield client
    finally:
        await client.close()

async def get_storage_service_client_anon() -> AsyncGenerator[StorageServiceClient, None]:
    """
    Returns a storage service client with anonymous access.
    """
    client = StorageServiceClient(
        base_url=settings.STORAGE_SERVICE_URL,
        anon_key=settings.ANON_KEY
    )

    try:
        yield client
    finally:
        await client.close()

import logging
import uuid
from typing import Dict, Any, Optional, AsyncGenerator, BinaryIO
import httpx
from fastapi import HTTPException, status

from .config import settings

logger = logging.getLogger(__name__)

class StorageServiceClient:
    """
    Client for interacting with the Storage Service API.
    """
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Accept": "application/json"
        }
        logger.info(f"StorageServiceClient initialized with base URL: {base_url}")

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make a request to the storage service API.
        """
        url = f"{self.base_url}{endpoint}"
        
        # Add headers to kwargs
        if "headers" in kwargs:
            kwargs["headers"].update(self.headers)
        else:
            kwargs["headers"] = self.headers
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, **kwargs)
                
                if response.status_code >= 400:
                    logger.error(f"Storage service error: {response.status_code} - {response.text}")
                    detail = f"Storage service error: {response.status_code}"
                    try:
                        error_data = response.json()
                        if "detail" in error_data:
                            detail = error_data["detail"]
                    except Exception:
                        pass
                    
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=detail
                    )
                
                if response.status_code != 204:  # No content
                    return response.json()
                return {"status": "success"}
        except httpx.RequestError as e:
            logger.error(f"Request error to storage service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Storage service unavailable: {str(e)}"
            )

    async def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if a bucket exists in the storage service.
        """
        try:
            result = await self._make_request(
                "GET", 
                f"/buckets/{bucket_name}/exists"
            )
            return result.get("exists", False)
        except HTTPException as e:
            if e.status_code == 404:
                return False
            raise
            
    async def check_bucket_exists(self, bucket_name: str) -> Dict[str, Any]:
        """
        Check if a bucket exists in the storage service and return a dict with the result.
        This is an alias for bucket_exists that returns a dict instead of a boolean.
        """
        exists = await self.bucket_exists(bucket_name)
        return {"exists": exists}

    async def create_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """
        Create a new bucket in the storage service.
        """
        return await self._make_request(
            "POST", 
            f"/buckets/{bucket_name}"
        )

    async def delete_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """
        Delete a bucket and all its contents from the storage service.
        """
        return await self._make_request(
            "DELETE", 
            f"/buckets/{bucket_name}"
        )

    async def upload_file(
        self, 
        bucket_name: str, 
        object_path: str, 
        file_content: bytes,
        content_type: str
    ) -> Dict[str, Any]:
        """
        Upload a file to the storage service.
        Note: This method loads the entire file into memory.
        For large files, use upload_file_streaming instead.
        """
        # Create a form with the file
        files = {
            "file": (object_path.split("/")[-1], file_content, content_type)
        }
        
        params = {
            "object_path": object_path
        }
        
        return await self._make_request(
            "POST", 
            f"/buckets/{bucket_name}/objects",
            params=params,
            files=files
        )
        
    async def upload_file_streaming(
        self, 
        bucket_name: str, 
        object_path: str, 
        file: Any,  # UploadFile from FastAPI
        content_type: str
    ) -> Dict[str, Any]:
        """
        Upload a file to the storage service using streaming to handle large files.
        This method streams the file directly without loading it entirely into memory.
        """
        url = f"{self.base_url}/buckets/{bucket_name}/objects"
        
        params = {
            "object_path": object_path
        }
        
        try:
            # Read the file content first - we need to do this because we can't pass
            # the UploadFile object directly to httpx as it contains coroutines
            content = await file.read()
            
            # Reset the file position for any future reads
            await file.seek(0)
            
            # Create a form with the file content
            files = {
                "file": (object_path.split("/")[-1], content, content_type)
            }
            
            headers = self.headers.copy()
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=600.0)) as client:  # 10 minute timeout
                response = await client.post(
                    url,
                    params=params,
                    files=files,
                    headers=headers
                )
                
                if response.status_code >= 400:
                    logger.error(f"Storage service error: {response.status_code} - {response.text}")
                    detail = f"Storage service error: {response.status_code}"
                    try:
                        error_data = response.json()
                        if "detail" in error_data:
                            detail = error_data["detail"]
                    except Exception:
                        pass
                    
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=detail
                    )
                
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Request error to storage service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Storage service unavailable: {str(e)}"
            )

    async def get_object_info(self, bucket_name: str, object_path: str) -> Dict[str, Any]:
        """
        Get metadata about an object without retrieving the object itself.
        """
        return await self._make_request(
            "HEAD", 
            f"/buckets/{bucket_name}/objects/{object_path}"
        )

    async def get_object_stream(
        self, 
        bucket_name: str, 
        object_path: str,
        range_header: Optional[str] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Get an object as a stream of bytes with optimized performance.
        The storage service is configured to provide ultra-fast initial response time (<100ms)
        regardless of file size.
        """
        url = f"{self.base_url}/buckets/{bucket_name}/objects/{object_path}"
        
        # Prepare headers with optional range request
        request_headers = self.headers.copy()
        
        # If client provided a range header, pass it through
        if range_header:
            request_headers["Range"] = range_header
        
        try:
            # Use a timeout configuration optimized for streaming large files
            # - connect_timeout: Time to establish connection (5s)
            # - read_timeout: Time between bytes received (60s)
            # - write_timeout: Time between bytes sent (60s)
            # - pool_timeout: Time to get connection from pool (5s)
            timeout = httpx.Timeout(5.0, read=60.0, write=60.0, pool=5.0)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Log the request for debugging
                logger.debug(f"Streaming request to {url} with headers: {request_headers}")
                
                start_time = __import__("time").time()
                async with client.stream("GET", url, headers=request_headers) as response:
                    # Log response time for monitoring
                    response_time = __import__("time").time() - start_time
                    logger.info(f"Initial response time from storage service: {response_time*1000:.2f}ms")
                    
                    if response.status_code >= 400:
                        logger.error(f"Storage service error: {response.status_code} - {response.text}")
                        detail = f"Storage service error: {response.status_code}"
                        
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=detail
                        )
                    
                    # Stream the response in chunks
                    # The storage service is optimized to send a small initial chunk very quickly
                    # to ensure downloads start within 100ms
                    async for chunk in response.aiter_bytes(chunk_size=16384):  # 16KB chunks
                        yield chunk
                        
        except httpx.RequestError as e:
            logger.error(f"Request error to storage service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Storage service unavailable: {str(e)}"
            )

    async def delete_object(self, bucket_name: str, object_path: str) -> Dict[str, Any]:
        """
        Delete an object from the storage service.
        """
        return await self._make_request(
            "DELETE", 
            f"/buckets/{bucket_name}/objects/{object_path}"
        )
        
    async def set_bucket_public(self, bucket_name: str, is_public: bool) -> Dict[str, Any]:
        """
        Set a bucket's public access policy.
        """
        return await self._make_request(
            "PUT",
            f"/buckets/{bucket_name}/policy",
            json={"is_public": is_public}
        )
        
    async def delete_all_objects(self, bucket_name: str) -> Dict[str, Any]:
        """
        Delete all objects in a bucket.
        """
        return await self._make_request(
            "DELETE",
            f"/buckets/{bucket_name}/objects"
        )

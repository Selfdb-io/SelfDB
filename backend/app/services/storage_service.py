"""
Storage Service Client

This module provides a client for interacting with the FastAPI-based storage service
that replaces MinIO in the SelfDB architecture.
"""

import httpx
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import UploadFile, HTTPException, status
import io
import os
from urllib.parse import urljoin

from ..core.config import settings

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
        """Upload a file to a bucket"""
        url = f"{self.base_url}/files/upload/{bucket_name}"
        
        # Prepare file for upload
        content = await file.read()
        files = {"file": (file.filename, content, file.content_type)}
        
        try:
            response = await self.client.post(
                url, 
                files=files,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error uploading file: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error: {e.response.text}"
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
        """Get a file as a stream of bytes"""
        url = f"{self.base_url}/files/download/{bucket_name}/{filename}"
        
        try:
            async with self.client.stream("GET", url, headers=self._get_headers()) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    yield chunk
        except httpx.HTTPStatusError as e:
            logger.error(f"Error downloading file: {e.response.text if hasattr(e.response, 'text') else str(e)}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error: {str(e)}"
            )
    
    async def download_file_content(self, bucket_name: str, file_name: str) -> AsyncGenerator[bytes, None]:
        """Get a file as a stream of bytes - alias for get_file_stream with parameter name matching"""
        # Handle object names that include the bucket prefix (e.g., 'bucket_name/file.txt')
        # Extract the actual filename without the bucket prefix
        if '/' in file_name and file_name.startswith(f"{bucket_name}/"):
            # Remove the bucket prefix from the object_name
            file_name = file_name[len(bucket_name)+1:]
            
        logger.info(f"Downloading file: bucket={bucket_name}, file={file_name}")
        async for chunk in self.get_file_stream(bucket_name, file_name):
            yield chunk
    
    async def delete_file(self, bucket_name: str, file_name: str) -> None:
        """Delete a file from a bucket"""
        url = f"{self.base_url}/files/{bucket_name}/{file_name}"
        
        try:
            response = await self.client.delete(url, headers=self._get_headers())
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error deleting file: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Storage service error: {e.response.text}"
            )
    
    async def get_file_url(self, bucket_name: str, file_name: str, expires_in_minutes: int = 60) -> str:
        """Generate a URL for accessing a file with optional expiration"""
        url = f"{self.base_url}/files/url/{bucket_name}/{file_name}?expires={expires_in_minutes}"
        
        try:
            response = await self.client.get(url, headers=self._get_headers())
            response.raise_for_status()
            result = response.json()
            return result.get('url', f"{settings.STORAGE_SERVICE_EXTERNAL_URL}/files/download/{bucket_name}/{file_name}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error getting file URL: {e.response.text}")
            # Fall back to direct URL if the storage service doesn't support presigned URLs
            return f"{settings.STORAGE_SERVICE_EXTERNAL_URL}/files/download/{bucket_name}/{file_name}"

import os
import shutil
import logging
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional
import aiofiles
from fastapi import HTTPException, status

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

class FileStorage:
    """
    File storage utility for managing files and buckets on the filesystem.
    """
    def __init__(self, base_path: str = settings.STORAGE_BASE_PATH):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Storage initialized at {self.base_path}")

    def _get_bucket_path(self, bucket_name: str) -> Path:
        """Get the filesystem path for a bucket"""
        return self.base_path / bucket_name

    def _get_object_path(self, bucket_name: str, object_path: str) -> Path:
        """
        Get the filesystem path for an object within a bucket.
        Includes security checks to prevent path traversal attacks.
        """
        # Normalize object_path to prevent directory traversal
        if object_path.startswith('/'):
            object_path = object_path[1:]
            
        bucket_path = self._get_bucket_path(bucket_name)
        full_object_path = (bucket_path / object_path).resolve()

        # Security check: ensure the resolved path is within the bucket_path
        if not str(full_object_path).startswith(str(bucket_path.resolve())):
            logger.error(f"Potential directory traversal attempt: bucket='{bucket_name}', object='{object_path}'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid object path"
            )
            
        return full_object_path

    async def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists"""
        bucket_path = self._get_bucket_path(bucket_name)
        return bucket_path.is_dir()

    async def create_bucket(self, bucket_name: str) -> bool:
        """Create a new bucket (directory)"""
        bucket_path = self._get_bucket_path(bucket_name)
        try:
            bucket_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Bucket '{bucket_name}' created at {bucket_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create bucket '{bucket_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create bucket: {str(e)}"
            )

    async def delete_bucket(self, bucket_name: str) -> bool:
        """Delete a bucket and all its contents"""
        bucket_path = self._get_bucket_path(bucket_name)
        if not bucket_path.is_dir():
            logger.warning(f"Attempted to delete non-existent bucket: {bucket_name}")
            return False
        
        try:
            shutil.rmtree(bucket_path)
            logger.info(f"Bucket '{bucket_name}' deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete bucket '{bucket_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete bucket: {str(e)}"
            )

    async def save_object(
        self, 
        bucket_name: str, 
        object_path: str, 
        content: bytes,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save an object to the specified bucket and path"""
        # Ensure bucket exists
        if not await self.bucket_exists(bucket_name):
            await self.create_bucket(bucket_name)
        
        object_fs_path = self._get_object_path(bucket_name, object_path)
        
        # Create parent directories if needed
        object_fs_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Write file
            async with aiofiles.open(object_fs_path, "wb") as f:
                await f.write(content)
            
            # Get file stats
            stat_info = object_fs_path.stat()
            
            logger.info(f"Object '{object_path}' saved to bucket '{bucket_name}' ({stat_info.st_size} bytes)")
            
            return {
                "bucket_name": bucket_name,
                "object_path": object_path,
                "size": stat_info.st_size,
                "last_modified": stat_info.st_mtime,
                "content_type": content_type or "application/octet-stream"
            }
        except Exception as e:
            logger.error(f"Failed to save object '{object_path}' to bucket '{bucket_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save object: {str(e)}"
            )
            
    async def save_object_streaming(
        self, 
        bucket_name: str, 
        object_path: str, 
        file: Any,  # UploadFile from FastAPI
        content_type: Optional[str] = None,
        chunk_size: int = 1024 * 1024  # 1MB chunks
    ) -> Dict[str, Any]:
        """Save an object to the specified bucket and path using streaming
        to handle large files efficiently without loading entire file into memory"""
        # Ensure bucket exists
        if not await self.bucket_exists(bucket_name):
            await self.create_bucket(bucket_name)
        
        object_fs_path = self._get_object_path(bucket_name, object_path)
        
        # Create parent directories if needed
        object_fs_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Write file in chunks
            total_size = 0
            async with aiofiles.open(object_fs_path, "wb") as f:
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    await f.write(chunk)
                    total_size += len(chunk)
            
            # Get file stats
            stat_info = object_fs_path.stat()
            
            logger.info(f"Object '{object_path}' saved to bucket '{bucket_name}' ({stat_info.st_size} bytes) using streaming upload")
            
            return {
                "bucket_name": bucket_name,
                "object_path": object_path,
                "size": stat_info.st_size,
                "last_modified": stat_info.st_mtime,
                "content_type": content_type or "application/octet-stream"
            }
        except Exception as e:
            # Clean up partial file if there was an error
            if object_fs_path.exists():
                try:
                    object_fs_path.unlink()
                    logger.info(f"Cleaned up partial file after error: {object_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up partial file: {cleanup_error}")
                    
            logger.error(f"Failed to save object '{object_path}' to bucket '{bucket_name}' using streaming: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save object: {str(e)}"
            )

    async def get_object_info(self, bucket_name: str, object_path: str) -> Dict[str, Any]:
        """Get metadata about an object"""
        object_fs_path = self._get_object_path(bucket_name, object_path)
        
        if not object_fs_path.is_file():
            logger.warning(f"Object '{object_path}' not found in bucket '{bucket_name}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Object not found"
            )
        
        stat_info = object_fs_path.stat()
        
        return {
            "bucket_name": bucket_name,
            "object_path": object_path,
            "size": stat_info.st_size,
            "last_modified": stat_info.st_mtime,
            # We don't store content type, so we use a generic one
            "content_type": "application/octet-stream"
        }

    async def get_object_stream(self, bucket_name: str, object_path: str, chunk_size: int = 8192) -> AsyncGenerator[bytes, None]:
        """
        Get an object as a stream of bytes.
        Returns an async generator that yields chunks of the file.
        """
        object_fs_path = self._get_object_path(bucket_name, object_path)
        
        if not object_fs_path.is_file():
            logger.warning(f"Object '{object_path}' not found in bucket '{bucket_name}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Object not found"
            )
        
        try:
            async with aiofiles.open(object_fs_path, 'rb') as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
                    
            logger.info(f"Streamed object '{object_path}' from bucket '{bucket_name}'")
        except Exception as e:
            logger.error(f"Failed to stream object '{object_path}' from bucket '{bucket_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read object: {str(e)}"
            )

    async def delete_object(self, bucket_name: str, object_path: str) -> bool:
        """Delete an object from a bucket"""
        object_fs_path = self._get_object_path(bucket_name, object_path)
        
        if not object_fs_path.is_file():
            logger.warning(f"Object '{object_path}' not found in bucket '{bucket_name}' for deletion")
            return False
        
        try:
            object_fs_path.unlink()
            logger.info(f"Object '{object_path}' deleted from bucket '{bucket_name}'")
            
            # Clean up empty directories
            current_dir = object_fs_path.parent
            bucket_path = self._get_bucket_path(bucket_name)
            
            # Remove empty parent directories up to but not including the bucket directory
            while current_dir != bucket_path:
                if not any(current_dir.iterdir()):
                    current_dir.rmdir()
                    logger.info(f"Removed empty directory: {current_dir}")
                    current_dir = current_dir.parent
                else:
                    break
                    
            return True
        except Exception as e:
            logger.error(f"Failed to delete object '{object_path}' from bucket '{bucket_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete object: {str(e)}"
            )

# Create a singleton instance
storage = FileStorage()

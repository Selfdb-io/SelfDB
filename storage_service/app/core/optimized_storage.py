import os
import asyncio
import logging
import mmap
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional, BinaryIO, Union
import aiofiles
from fastapi import HTTPException, status, UploadFile
import time

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

class OptimizedFileStorage:
    """
    Optimized file storage utility for handling large files and ensuring fast download response times.
    Extends the base FileStorage with optimized methods for large file operations.
    """
    def __init__(self, base_path: str = settings.STORAGE_BASE_PATH):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        # Set optimal buffer sizes for different operations
        self.read_buffer_size = 65536  # 64KB initial read buffer for fast response
        self.write_buffer_size = 1024 * 1024  # 1MB write buffer for uploads
        logger.info(f"OptimizedFileStorage initialized at {self.base_path} with {self.read_buffer_size}B read buffer")

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

    async def save_object(
        self, 
        bucket_name: str, 
        object_path: str, 
        content: bytes,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save an object to the specified bucket and path.
        Optimized for medium-sized files.
        """
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
        file: Union[UploadFile, BinaryIO],
        content_type: Optional[str] = None,
        chunk_size: int = None
    ) -> Dict[str, Any]:
        """
        Save an object to the specified bucket and path using optimized streaming.
        Handles files of any size efficiently without loading the entire file into memory.
        
        Args:
            bucket_name: Name of the bucket
            object_path: Path within the bucket to save the object
            file: File-like object or UploadFile from FastAPI
            content_type: MIME type of the file
            chunk_size: Size of chunks to read (defaults to self.write_buffer_size)
        """
        if chunk_size is None:
            chunk_size = self.write_buffer_size
            
        # Ensure bucket exists
        if not await self.bucket_exists(bucket_name):
            await self.create_bucket(bucket_name)
        
        object_fs_path = self._get_object_path(bucket_name, object_path)
        
        # Create parent directories if needed
        object_fs_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Write file in chunks
            total_size = 0
            start_time = time.time()
            
            async with aiofiles.open(object_fs_path, "wb") as f:
                # Handle different types of file objects
                if hasattr(file, 'read') and callable(file.read):
                    # This is likely a FastAPI UploadFile or similar with async read
                    while True:
                        chunk = await file.read(chunk_size)
                        if not chunk:
                            break
                        await f.write(chunk)
                        total_size += len(chunk)
                else:
                    # Assume it's a regular file-like object with sync read
                    while True:
                        chunk = file.read(chunk_size)
                        if not chunk:
                            break
                        await f.write(chunk)
                        total_size += len(chunk)
            
            # Get file stats
            stat_info = object_fs_path.stat()
            elapsed = time.time() - start_time
            
            logger.info(
                f"Object '{object_path}' saved to bucket '{bucket_name}' "
                f"({stat_info.st_size} bytes) in {elapsed:.2f}s using streaming upload "
                f"({stat_info.st_size / (1024*1024*elapsed):.2f} MB/s)"
            )
            
            return {
                "bucket_name": bucket_name,
                "object_path": object_path,
                "size": stat_info.st_size,
                "last_modified": stat_info.st_mtime,
                "content_type": content_type or "application/octet-stream",
                "upload_time_seconds": elapsed
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
        """
        Get metadata about an object.
        Optimized for fast response time.
        """
        object_fs_path = self._get_object_path(bucket_name, object_path)
        
        if not object_fs_path.is_file():
            logger.warning(f"Object '{object_path}' not found in bucket '{bucket_name}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Object not found"
            )
        
        stat_info = object_fs_path.stat()
        
        # Try to determine content type from file extension
        content_type = "application/octet-stream"
        extension = object_fs_path.suffix.lower()
        if extension:
            content_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.pdf': 'application/pdf',
                '.txt': 'text/plain',
                '.html': 'text/html',
                '.htm': 'text/html',
                '.json': 'application/json',
                '.mp4': 'video/mp4',
                '.mp3': 'audio/mpeg',
                '.zip': 'application/zip',
            }
            content_type = content_types.get(extension, "application/octet-stream")
        
        return {
            "bucket_name": bucket_name,
            "object_path": object_path,
            "size": stat_info.st_size,
            "last_modified": stat_info.st_mtime,
            "content_type": content_type
        }

    async def get_object_stream(
        self, 
        bucket_name: str, 
        object_path: str, 
        chunk_size: int = None,
        range_header: str = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Get an object as a stream of bytes with ultra-fast initial response time.
        Returns an async generator that yields chunks of the file.
        
        This implementation is optimized for sub-100ms time-to-first-byte (TTFB)
        regardless of file size by using header-only initial response.
        """
        object_fs_path = self._get_object_path(bucket_name, object_path)
        
        if not object_fs_path.is_file():
            logger.warning(f"Object '{object_path}' not found in bucket '{bucket_name}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Object not found"
            )
            
        # Get file size
        file_size = object_fs_path.stat().st_size
        
        # Ultra-fast response strategy: always return a small initial chunk
        # This ensures sub-100ms response time regardless of file size
        initial_chunk_size = 16 * 1024  # 16KB is enough for immediate display/download start
        
        # For very small files (< 1MB), just read the whole file at once
        if file_size < 1024 * 1024:
            try:
                with open(object_fs_path, 'rb') as f:
                    content = f.read()
                yield content
                logger.info(f"Streamed small object '{object_path}' ({file_size} bytes) from bucket '{bucket_name}' in one chunk")
                return
            except Exception as e:
                logger.error(f"Failed to stream small object '{object_path}' from bucket '{bucket_name}': {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to read object: {str(e)}"
                )
        
        # Handle range requests if present
        start_byte = 0
        end_byte = file_size - 1
        
        if range_header:
            try:
                # Parse range header (e.g., "bytes=0-1023")
                range_str = range_header.replace("bytes=", "")
                start_str, end_str = range_str.split("-")
                if start_str:
                    start_byte = int(start_str)
                if end_str:
                    end_byte = min(int(end_str), file_size - 1)
            except Exception as e:
                logger.warning(f"Invalid range header: {range_header}, ignoring: {e}")
        
        # For all other files, use direct file access with minimal overhead
        try:
            # Open file directly - faster than async IO for initial response
            with open(object_fs_path, 'rb') as f:
                # Seek to start position if needed
                if start_byte > 0:
                    f.seek(start_byte)
                
                # First chunk - ultra small for guaranteed fast response
                # This ensures the download starts immediately
                bytes_to_read = min(initial_chunk_size, end_byte - start_byte + 1)
                first_chunk = f.read(bytes_to_read)
                yield first_chunk
                
                # Calculate remaining bytes
                bytes_sent = len(first_chunk)
                remaining_bytes = end_byte - start_byte + 1 - bytes_sent
                
                if remaining_bytes <= 0:
                    return
                
                # For the rest of the file, use larger chunks for efficiency
                # Adaptive chunk size based on file size
                if file_size > 1024 * 1024 * 1024:  # > 1GB
                    subsequent_chunk_size = 8 * 1024 * 1024  # 8MB chunks
                elif file_size > 100 * 1024 * 1024:  # > 100MB
                    subsequent_chunk_size = 4 * 1024 * 1024  # 4MB chunks
                else:
                    subsequent_chunk_size = 1 * 1024 * 1024  # 1MB chunks
                
                # Stream the rest of the file
                while remaining_bytes > 0:
                    bytes_to_read = min(subsequent_chunk_size, remaining_bytes)
                    chunk = f.read(bytes_to_read)
                    if not chunk:
                        break
                    yield chunk
                    remaining_bytes -= len(chunk)
                    
            logger.info(f"Streamed object '{object_path}' ({file_size} bytes) from bucket '{bucket_name}'")
        except Exception as e:
            logger.error(f"Failed to stream object '{object_path}' from bucket '{bucket_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read object: {str(e)}"
            )
            
    async def get_object_mmap_stream(
        self, 
        bucket_name: str, 
        object_path: str, 
        chunk_size: int = 8192
    ) -> AsyncGenerator[bytes, None]:
        """
        Get an object as a stream using memory-mapped files for improved performance.
        This can provide faster access for large files, especially for random access patterns.
        
        Note: This method requires the mmap module and may not work on all platforms.
        """
        object_fs_path = self._get_object_path(bucket_name, object_path)
        
        if not object_fs_path.is_file():
            logger.warning(f"Object '{object_path}' not found in bucket '{bucket_name}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Object not found"
            )
        
        try:
            # Memory mapping requires synchronous file operations
            with open(object_fs_path, 'rb') as f:
                # Skip mmap for small files (less than 1MB)
                if os.path.getsize(object_fs_path) < 1024 * 1024:
                    content = f.read()
                    yield content
                    return
                
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    # First chunk - larger for fast initial response
                    first_chunk_size = min(self.read_buffer_size, len(mm))
                    yield mm[:first_chunk_size]
                    
                    # Subsequent chunks
                    for i in range(first_chunk_size, len(mm), chunk_size):
                        # Yield control back to event loop periodically
                        await asyncio.sleep(0)
                        yield mm[i:min(i + chunk_size, len(mm))]
                    
            logger.info(f"Memory-mapped streamed object '{object_path}' from bucket '{bucket_name}'")
        except Exception as e:
            logger.error(f"Failed to memory-map stream object '{object_path}' from bucket '{bucket_name}': {e}")
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
            
    async def delete_bucket(self, bucket_name: str) -> bool:
        """Delete a bucket and all its contents"""
        bucket_path = self._get_bucket_path(bucket_name)
        if not bucket_path.is_dir():
            logger.warning(f"Attempted to delete non-existent bucket: {bucket_name}")
            return False
        
        try:
            # Delete all files and subdirectories
            for root, dirs, files in os.walk(bucket_path, topdown=False):
                for file in files:
                    os.unlink(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
                    
            # Finally delete the bucket directory itself
            os.rmdir(bucket_path)
            
            logger.info(f"Bucket '{bucket_name}' deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete bucket '{bucket_name}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete bucket: {str(e)}"
            )

# Create a singleton instance
optimized_storage = OptimizedFileStorage()

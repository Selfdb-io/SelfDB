import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional

# Import both storage implementations
from ..core.storage import storage
from ..core.optimized_storage import optimized_storage

# Use the optimized storage implementation
storage = optimized_storage

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.post("/{bucket_name}/objects", status_code=status.HTTP_201_CREATED)
async def upload_object(
    bucket_name: str,
    object_path: str,
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """
    Upload a file to the specified bucket and path.
    Uses streaming to handle large files efficiently.
    """
    try:
        # Read file content
        content = await file.read()
        
        # Save the object
        result = await storage.save_object(
            bucket_name=bucket_name,
            object_path=object_path,
            content=content,
            content_type=file.content_type
        )
        
        return {
            "status": "success",
            "message": f"Object '{object_path}' uploaded successfully to bucket '{bucket_name}'",
            "bucket_name": bucket_name,
            "object_path": object_path,
            "size": result["size"],
            "content_type": result["content_type"]
        }
    except Exception as e:
        logger.error(f"Error uploading object '{object_path}' to bucket '{bucket_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload object: {str(e)}"
        )

@router.head("/{bucket_name}/objects/{object_path:path}")
async def head_object(bucket_name: str, object_path: str) -> Dict[str, Any]:
    """
    Get metadata about an object without retrieving the object itself.
    """
    try:
        info = await storage.get_object_info(bucket_name, object_path)
        return info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting info for object '{object_path}' in bucket '{bucket_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get object info: {str(e)}"
        )

@router.get("/{bucket_name}/objects/{object_path:path}")
async def get_object(bucket_name: str, object_path: str, request: Request = None) -> StreamingResponse:
    """
    Get an object from the specified bucket and path.
    Returns the object as a streaming response with ultra-fast initial response time.
    Supports range requests for efficient large file handling.
    """
    try:
        start_time = time.time()
        
        # Get the filesystem path directly for faster response
        object_fs_path = storage._get_object_path(bucket_name, object_path)
        
        # Check if file exists and get basic info
        if not object_fs_path.exists():
            logger.warning(f"Object '{object_path}' not found in bucket '{bucket_name}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Object not found"
            )
            
        # Get file stats directly
        stat_info = object_fs_path.stat()
        file_size = stat_info.st_size
        
        # Determine content type from file extension
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
        
        # Get range header if present
        range_header = None
        headers = {}
        
        if request and "range" in request.headers:
            range_header = request.headers["range"]
            
            # Parse range header
            try:
                range_str = range_header.replace("bytes=", "")
                start_str, end_str = range_str.split("-")
                
                start_byte = int(start_str) if start_str else 0
                end_byte = int(end_str) if end_str else file_size - 1
                end_byte = min(end_byte, file_size - 1)
                content_length = end_byte - start_byte + 1
                
                # Set response headers for range request
                headers["Content-Range"] = f"bytes {start_byte}-{end_byte}/{file_size}"
                headers["Content-Length"] = str(content_length)
                status_code = status.HTTP_206_PARTIAL_CONTENT
            except Exception as e:
                logger.warning(f"Invalid range header: {range_header}, ignoring: {e}")
                range_header = None
                status_code = status.HTTP_200_OK
                headers["Content-Length"] = str(file_size)
        else:
            status_code = status.HTTP_200_OK
            headers["Content-Length"] = str(file_size)
        
        # Add common headers
        headers.update({
            "Content-Disposition": f'attachment; filename="{object_path.split("/")[-1]}"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400"  # Cache for 24 hours
        })
        
        # Create a streaming response with ultra-fast initial response
        response = StreamingResponse(
            storage.get_object_stream(bucket_name, object_path, range_header=range_header),
            media_type=content_type,
            headers=headers,
            status_code=status_code
        )
        
        # Log the response preparation time
        prep_time = time.time() - start_time
        logger.info(f"Response preparation time for '{object_path}': {prep_time*1000:.2f}ms")
            
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming object '{object_path}' from bucket '{bucket_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stream object: {str(e)}"
        )

@router.delete("/{bucket_name}/objects/{object_path:path}")
async def delete_object(bucket_name: str, object_path: str) -> Dict[str, Any]:
    """
    Delete an object from the specified bucket and path.
    """
    try:
        result = await storage.delete_object(bucket_name, object_path)
        if result:
            return {
                "status": "success",
                "message": f"Object '{object_path}' deleted successfully from bucket '{bucket_name}'",
                "bucket_name": bucket_name,
                "object_path": object_path
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object '{object_path}' not found in bucket '{bucket_name}'"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting object '{object_path}' from bucket '{bucket_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete object: {str(e)}"
        )

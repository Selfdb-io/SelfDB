from fastapi import APIRouter, Depends, HTTPException, status, Path, UploadFile, File, Query, Body, Request
from fastapi.responses import StreamingResponse, FileResponse
from typing import List, Optional, Union, Literal
import os
import logging
import mimetypes
import aiofiles
import json
from datetime import datetime
from pathlib import Path as FilePath
import shutil
import uuid

from ...core.config import settings
from ...schemas.file import FileUploadResponse, FileInfo
from ..deps import get_current_user, get_current_user_or_anon, TokenData, ANON_USER_ROLE
from pydantic import BaseModel, Field

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

STORAGE_BASE_PATH = settings.STORAGE_PATH

# --- Pydantic Models (Consider moving to a schemas.py) ---
class PresignedUrlRequest(BaseModel):
    expires_in_seconds: Optional[int] = Field(3600, description="Requested expiry for the URL in seconds")
    content_type: Optional[str] = Field(None, description="Expected content type of the file")

class PresignedUrlResponse(BaseModel):
    upload_url: str
    method: str = "PUT" # Usually PUT for S3-style uploads
    # headers: Optional[Dict[str, str]] = None # If specific headers are needed for the client's PUT request
# --- End Pydantic Models ---

def get_bucket_path(bucket_name: str) -> str:
    """Get the full path to a bucket directory"""
    return os.path.join(STORAGE_BASE_PATH, bucket_name)

def get_bucket_metadata_path(bucket_name: str) -> str:
    """Get the path to a bucket's metadata file"""
    return os.path.join(get_bucket_path(bucket_name), ".metadata.json")

def bucket_exists(bucket_name: str) -> bool:
    """Check if a bucket exists"""
    bucket_path = get_bucket_path(bucket_name)
    return os.path.isdir(bucket_path)

def get_bucket_metadata(bucket_name: str) -> Optional[dict]:
    """Get bucket metadata from the metadata file"""
    metadata_path = get_bucket_metadata_path(bucket_name)
    if not os.path.exists(metadata_path):
        return None
    
    try:
        with open(metadata_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading bucket metadata: {e}")
        return None

def get_file_path(bucket_name: str, filename: str) -> str:
    """Get the full path to a file within a bucket"""
    # Ensure filename is sanitized to prevent directory traversal
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename.")
    return os.path.join(get_bucket_path(bucket_name), filename)

def file_exists(bucket_name: str, filename: str) -> bool:
    """Check if a file exists in a bucket"""
    file_path = get_file_path(bucket_name, filename)
    return os.path.isfile(file_path) and not os.path.basename(file_path).startswith('.')

def get_file_url(bucket_name: str, filename: str) -> str:
    """Generate a URL for accessing a file"""
    return f"{settings.BASE_URL}/storage/{bucket_name}/{filename}"

@router.post("/upload/{bucket_name}", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    bucket_name: str,
    file: UploadFile = File(...),
    requester: Union[TokenData, Literal["anon"], None] = Depends(get_current_user_or_anon)
):
    """
    Upload a file to a bucket.
    - Authenticated users can upload to their buckets
    - Anonymous users can upload to public buckets if ANON_KEY is provided
    """
    # Check if bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket_name}' not found"
        )
    
    # Get bucket metadata
    metadata = get_bucket_metadata(bucket_name)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bucket metadata"
        )
    
    # Check permissions
    is_public = metadata.get("is_public", False)
    owner_id = metadata.get("owner_id")
    
    if requester == ANON_USER_ROLE:
        # Anonymous users can only upload to public buckets
        if not is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anonymous uploads are only allowed to public buckets"
            )
    elif isinstance(requester, TokenData):
        # Authenticated users can only upload to their own buckets
        if owner_id != requester.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to upload to this bucket"
            )
    else:
        # No valid authentication
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Ensure filename is safe
    filename = os.path.basename(file.filename)
    if not filename or filename.startswith('.'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )
    
    # Check if file already exists
    file_path = get_file_path(bucket_name, filename)
    if os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File '{filename}' already exists in bucket '{bucket_name}'"
        )
    
    # Save file
    try:
        async with aiofiles.open(file_path, "wb") as f:
            # Read and write in chunks to handle large files
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        # Clean up partial file if it exists
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file"
        )
    
    # Get file size
    file_size = os.path.getsize(file_path)
    
    # Generate file URL
    file_url = get_file_url(bucket_name, filename)
    
    return FileUploadResponse(
        filename=filename,
        content_type=file.content_type,
        size=file_size,
        url=file_url,
        bucket=bucket_name,
        created_at=datetime.utcnow()
    )

@router.get("/list/{bucket_name}", response_model=List[FileInfo])
async def list_files(
    bucket_name: str,
    requester: Union[TokenData, Literal["anon"], None] = Depends(get_current_user_or_anon)
):
    """
    List files in a bucket.
    - Authenticated users can list files in their buckets and public buckets
    - Anonymous users can only list files in public buckets
    """
    # Check if bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket_name}' not found"
        )
    
    # Get bucket metadata
    metadata = get_bucket_metadata(bucket_name)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bucket metadata"
        )
    
    # Check permissions
    is_public = metadata.get("is_public", False)
    owner_id = metadata.get("owner_id")
    
    if requester == ANON_USER_ROLE or requester is None:
        if not is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to private bucket"
            )
    elif isinstance(requester, TokenData):
        if not is_public and owner_id != requester.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to private bucket"
            )
    
    # List files in bucket
    bucket_path = get_bucket_path(bucket_name)
    files = []
    
    try:
        for item in os.listdir(bucket_path):
            item_path = os.path.join(bucket_path, item)
            
            # Skip directories and hidden files (like .metadata.json)
            if os.path.isdir(item_path) or item.startswith('.'):
                continue
            
            # Get file info
            stat = os.stat(item_path)
            content_type, _ = mimetypes.guess_type(item_path)
            
            files.append(FileInfo(
                filename=item,
                content_type=content_type or "application/octet-stream",
                size=stat.st_size,
                bucket=bucket_name,
                url=get_file_url(bucket_name, item),
                created_at=datetime.fromtimestamp(stat.st_ctime)
            ))
    except OSError as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files"
        )
    
    return files

@router.get("/download/{bucket_name}/{filename}")
async def download_file(
    bucket_name: str,
    filename: str,
    requester: Union[TokenData, Literal["anon"], None] = Depends(get_current_user_or_anon)
):
    """
    Download a file from a bucket.
    - Authenticated users can download from their buckets and public buckets
    - Anonymous users can only download from public buckets
    """
    logger.info(f"Storage Service: Download request for bucket='{bucket_name}', filename='{filename}'. Requester type: {type(requester)}")

    # Ensure filename is safe and not trying to access parent directories or hidden files
    if ".." in filename or filename.startswith('.'):
        logger.warning(f"Storage Service: Attempt to access potentially unsafe filename: '{filename}' in bucket '{bucket_name}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )

    # Check if bucket exists
    if not bucket_exists(bucket_name):
        logger.warning(f"Storage Service: Bucket '{bucket_name}' not found for download attempt of '{filename}'.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket_name}' not found"
        )
    
    # Get bucket metadata for permission checking
    metadata = get_bucket_metadata(bucket_name)
    if not metadata:
        logger.error(f"Storage Service: Failed to get metadata for bucket '{bucket_name}' during download of '{filename}'.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bucket metadata"
        )
    
    is_public_bucket = metadata.get("is_public", False)
    bucket_owner_id = metadata.get("owner_id")
    logger.info(f"Storage Service: Bucket '{bucket_name}' metadata - is_public: {is_public_bucket}, owner_id: {bucket_owner_id}")

    # Permission check
    if requester == ANON_USER_ROLE or requester is None:
        if not is_public_bucket:
            logger.warning(f"Storage Service: Anonymous access denied to private bucket '{bucket_name}' for file '{filename}'.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. This is a private bucket."
            )
        logger.info(f"Storage Service: Anonymous access granted to public bucket '{bucket_name}' for file '{filename}'.")
    elif isinstance(requester, TokenData):
        # Allow any authenticated user to access any bucket
        logger.info(f"Storage Service: Authenticated access granted for user '{requester.sub}' to bucket '{bucket_name}' for file '{filename}'.")
    else:
        # Should not happen if deps are set up correctly, but as a safeguard:
        logger.error(f"Storage Service: Invalid requester type '{type(requester)}' encountered for bucket '{bucket_name}', file '{filename}'. Denying access.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication state."
        )

    # Check if file exists
    file_path = get_file_path(bucket_name, filename)
    logger.info(f"Storage Service: Resolved file path for download: {file_path}")

    if not file_exists(bucket_name, filename): # Uses the function that also checks for hidden files
        logger.warning(f"Storage Service: File '{filename}' not found or is a hidden file in bucket '{bucket_name}' at path '{file_path}'.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found in bucket '{bucket_name}'"
        )
    
    try:
        # Get file size for Content-Length header
        file_size = os.path.getsize(file_path)
        logger.info(f"Storage Service: File size for '{file_path}' is {file_size} bytes.")

        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        media_type = content_type if content_type else "application/octet-stream"
        logger.info(f"Storage Service: Determined media type for '{file_path}' as '{media_type}'.")

        # Prepare headers
        # FileResponse sets Content-Length and Content-Type automatically based on the file.
        # It also handles ETag, Last-Modified for caching.
        # We can add Content-Disposition if we want to suggest a filename to the browser.
        # Handle quotes in filename - safe way to handle special characters
        safe_filename = os.path.basename(filename)
        disposition_header = f'attachment; filename="{safe_filename}"'
        
        response_headers = {
            "Content-Disposition": disposition_header
        }
        logger.info(f"Storage Service: Preparing FileResponse for '{file_path}' with media_type='{media_type}' and additional headers: {response_headers}")
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=os.path.basename(filename), # Suggests filename for download
            headers=response_headers
        )
    except Exception as e:
        logger.error(f"Storage Service: Error preparing or streaming file '{file_path}': {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving file: {str(e)}"
        )

@router.get("/view/{bucket_name}/{filename}")
async def view_file(
    bucket_name: str,
    filename: str,
    content_type: Optional[str] = Query(None, description="Override content type"),
    requester: Union[TokenData, Literal["anon"], None] = Depends(get_current_user_or_anon)
):
    """
    View a file from a bucket directly in the browser.
    - Authenticated users can view files from their buckets and public buckets
    - Anonymous users can only view files from public buckets
    - Same as download but with inline content disposition
    """
    logger.info(f"Storage Service: View request for bucket='{bucket_name}', filename='{filename}'. Requester type: {type(requester)}")
    logger.info(f"Storage Service: Content-Type override provided: {content_type}")

    # Ensure filename is safe and not trying to access parent directories or hidden files
    if ".." in filename or filename.startswith('.'):
        logger.warning(f"Storage Service: Attempt to access potentially unsafe filename: '{filename}' in bucket '{bucket_name}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )

    # Check if bucket exists
    if not bucket_exists(bucket_name):
        logger.warning(f"Storage Service: Bucket '{bucket_name}' not found for view attempt of '{filename}'.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket_name}' not found"
        )
    
    # Get bucket metadata for permission checking
    metadata = get_bucket_metadata(bucket_name)
    if not metadata:
        logger.error(f"Storage Service: Failed to get metadata for bucket '{bucket_name}' during view of '{filename}'.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bucket metadata"
        )
    
    is_public_bucket = metadata.get("is_public", False)
    bucket_owner_id = metadata.get("owner_id")
    logger.info(f"Storage Service: Bucket '{bucket_name}' metadata - is_public: {is_public_bucket}, owner_id: {bucket_owner_id}")

    # Permission check
    if requester == ANON_USER_ROLE or requester is None:
        if not is_public_bucket:
            logger.warning(f"Storage Service: Anonymous access denied to private bucket '{bucket_name}' for file '{filename}'.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. This is a private bucket."
            )
        logger.info(f"Storage Service: Anonymous access granted to public bucket '{bucket_name}' for file '{filename}'.")
    elif isinstance(requester, TokenData):
        # Allow any authenticated user to access any bucket
        logger.info(f"Storage Service: Authenticated access granted for user '{requester.sub}' to bucket '{bucket_name}' for file '{filename}'.")
    else:
        # Should not happen if deps are set up correctly, but as a safeguard:
        logger.error(f"Storage Service: Invalid requester type '{type(requester)}' encountered for bucket '{bucket_name}', file '{filename}'. Denying access.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication state."
        )

    # Check if file exists
    file_path = get_file_path(bucket_name, filename)
    logger.info(f"Storage Service: Resolved file path for view: {file_path}")

    if not file_exists(bucket_name, filename): # Uses the function that also checks for hidden files
        logger.warning(f"Storage Service: File '{filename}' not found or is a hidden file in bucket '{bucket_name}' at path '{file_path}'.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found in bucket '{bucket_name}'"
        )
    
    try:
        # Get file size for Content-Length header
        file_size = os.path.getsize(file_path)
        logger.info(f"Storage Service: File size for '{file_path}' is {file_size} bytes.")

        # Determine content type
        if content_type:
            # Use the provided content type if available (from query parameter)
            media_type = content_type
            logger.info(f"Storage Service: Using provided content type: '{media_type}'")
        else:
            # Guess content type from file extension
            guessed_type, _ = mimetypes.guess_type(file_path)
            
            # Try harder for common image formats based on file extension
            if not guessed_type and filename.lower().endswith(('.png')):
                guessed_type = 'image/png'
            elif not guessed_type and filename.lower().endswith(('.jpg', '.jpeg')):
                guessed_type = 'image/jpeg'
            elif not guessed_type and filename.lower().endswith(('.gif')):
                guessed_type = 'image/gif'
            elif not guessed_type and filename.lower().endswith(('.webp')):
                guessed_type = 'image/webp'
            elif not guessed_type and filename.lower().endswith(('.pdf')):
                guessed_type = 'application/pdf'
            
            media_type = guessed_type if guessed_type else "application/octet-stream"
            logger.info(f"Storage Service: Determined media type for '{file_path}' as '{media_type}'.")
        
        # Prepare headers - Use 'inline' instead of 'attachment' to view in browser
        disposition_header = f'inline; filename="{os.path.basename(filename)}"'
        
        response_headers = {
            "Content-Disposition": disposition_header,
            "Cache-Control": "max-age=3600",  # Allow caching for one hour
            "Access-Control-Allow-Origin": "*"  # Allow CORS
        }
        logger.info(f"Storage Service: Preparing FileResponse for viewing '{file_path}' with media_type='{media_type}' and headers: {response_headers}")
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            headers=response_headers
        )
    except Exception as e:
        logger.error(f"Storage Service: Error preparing or streaming file '{file_path}' for viewing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving file: {str(e)}"
        )

@router.delete("/{bucket_name}/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    bucket_name: str,
    filename: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Delete a file from a bucket.
    Only bucket owners can delete files.
    """
    # Check if bucket exists
    if not bucket_exists(bucket_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket_name}' not found"
        )
    
    # Get bucket metadata
    metadata = get_bucket_metadata(bucket_name)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bucket metadata"
        )
    
    # Check ownership
    if metadata.get("owner_id") != current_user.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete files from this bucket"
        )
    
    # Check if file exists
    file_path = get_file_path(bucket_name, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found in bucket '{bucket_name}'"
        )
    
    # Delete file
    try:
        os.remove(file_path)
    except OSError as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )
    
    return None

@router.post("/presigned-url/upload/{bucket_name}/{object_name}", response_model=PresignedUrlResponse)
async def generate_presigned_upload_url(
    bucket_name: str,
    object_name: str,
    request_data: PresignedUrlRequest = Body(...),
    # token: str = Depends(get_current_user_token) # Add if storage service validates backend token
):
    """
    Generates a URL for the client to directly upload a file.
    For this custom service, it's a direct path to an upload endpoint on this service.
    The "presigned" nature is simplified here; true cryptographic signing is not implemented.
    """
    bucket_path = get_bucket_path(bucket_name)
    if not os.path.exists(bucket_path) or not os.path.isdir(bucket_path):
        logger.warning(f"Presigned URL request for non-existent bucket: {bucket_name}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bucket not found")

    # The client will PUT to an endpoint like /files/upload-direct/{bucket_name}/{object_name}
    # The storage service URL itself needs to be known. Assuming it runs on localhost:8001 for this example
    # In a real setup, this base URL should come from settings.
    # For now, let's construct it relative to how the client accesses this service.
    # This is tricky as the service itself doesn't know its external URL easily.
    # The calling backend (main app) knows STORAGE_SERVICE_URL.
    # A common pattern is for the calling service to *tell* the storage service its public base URL
    # or for the storage service to have a configured `PUBLIC_BASE_URL`.
    # For now, we will return a relative path or a path based on a configured setting.

    # Let's assume settings.STORAGE_SERVICE_PUBLIC_URL is configured, e.g., "http://localhost:8001"
    # If not, the main backend might need to construct the full URL after getting parts from here.
    # The `StorageServiceClient` in the main backend expects a full URL.

    # This endpoint will be used by the client for the actual PUT
    # Ensure object_name is safe
    if ".." in object_name or object_name.startswith("/"):
        logger.error(f"Invalid object_name for presigned URL: {object_name}")
        raise HTTPException(status_code=400, detail="Invalid object_name.")

    # The URL the client will use to PUT the file
    # THIS IS THE CRITICAL PART: How does the storage service know its own public-facing URL?
    # Option A: Hardcode for local dev (bad for flexibility)
    # Option B: Configure settings.STORAGE_SERVICE_PUBLIC_URL
    # Option C: Return relative path and let main backend construct full URL (changes StorageServiceClient)

    # Assuming Option B: settings.STORAGE_SERVICE_EXTERNAL_URL = "http://localhost:8001" (or your external IP/domain)
    if not settings.STORAGE_SERVICE_EXTERNAL_URL:
        logger.error("settings.STORAGE_SERVICE_EXTERNAL_URL is not configured in storage_service. Cannot generate absolute presigned URL.")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Storage service URL not configured.")
    
    upload_target_url = f"{str(settings.STORAGE_SERVICE_EXTERNAL_URL).rstrip('/')}/files/upload-direct/{bucket_name}/{object_name}"
    
    logger.info(f"Generated presigned upload URL for {bucket_name}/{object_name} to {upload_target_url} (expires in {request_data.expires_in_seconds}s, content_type: {request_data.content_type})")
    
    # Here, 'expires_in_seconds' and 'content_type' are noted but not strictly enforced
    # by this simplified "presigned" URL mechanism. A more robust solution would use tokens with expiry.
    
    return PresignedUrlResponse(upload_url=upload_target_url)

@router.put("/upload-direct/{bucket_name}/{object_name}", status_code=status.HTTP_201_CREATED)
async def direct_upload_file(
    bucket_name: str,
    object_name: str,
    request: Request,
):
    """
    Endpoint for clients to directly PUT their file after obtaining a 'presigned' URL.
    This endpoint accepts raw file content or multipart form data.
    """
    bucket_path = get_bucket_path(bucket_name)
    if not os.path.exists(bucket_path) or not os.path.isdir(bucket_path):
        logger.warning(f"Direct upload attempt to non-existent bucket: {bucket_name}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bucket not found")

    # Basic security: Ensure object_name is not trying to escape the bucket
    if ".." in object_name or object_name.startswith("/"):
        logger.error(f"Invalid object_name for direct upload: {object_name}")
        raise HTTPException(status_code=400, detail="Invalid object_name.")

    file_location = get_file_path(bucket_name, object_name)
    
    # Ensure the immediate parent directory for the object_name exists if it contains slashes (folders)
    try:
        parent_dir = os.path.dirname(file_location)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            logger.info(f"Created directory structure for direct upload: {parent_dir}")
    except Exception as e:
        logger.error(f"Error creating directory structure '{parent_dir}' for direct upload: {e}")
        raise HTTPException(status_code=500, detail=f"Could not create directory structure for file: {str(e)}")

    # Get content type from request headers
    content_type = request.headers.get("content-type", "application/octet-stream")
    logger.info(f"Upload request content-type: {content_type}")

    written_bytes = 0
    try:
        # Handle different content types appropriately
        if content_type.startswith('multipart/form-data'):
            # For multipart form data, extract only the file content
            logger.info("Handling multipart/form-data upload")
            form = await request.form()
            uploaded_file = form.get("file")
            
            if not uploaded_file:
                logger.error("No file part found in multipart form data")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="No file found in form data. Expected field name 'file'"
                )
                
            # Read the file content
            file_content = await uploaded_file.read()
            written_bytes = len(file_content)
            
            # Write just the file content, not the form boundaries
            async with aiofiles.open(file_location, 'wb') as out_file:
                await out_file.write(file_content)
        else:
            # For raw binary uploads (PUT with Content-Type matching the file)
            logger.info("Handling raw body upload")
            body = await request.body()
            written_bytes = len(body)
            
            # Write the file
            async with aiofiles.open(file_location, 'wb') as out_file:
                await out_file.write(body)
        
        # Optionally validate file content based on extension
        if written_bytes > 0:
            # Read a small chunk to validate file signatures for common formats
            async with aiofiles.open(file_location, 'rb') as f:
                header = await f.read(32)  # Read first 32 bytes for signatures
                
                # Basic file signature checks
                if object_name.lower().endswith('.png') and not header.startswith(b'\x89PNG\r\n\x1a\n'):
                    logger.warning(f"File has PNG extension but invalid signature: {header[:8].hex()}")
                elif object_name.lower().endswith('.jpg') or object_name.lower().endswith('.jpeg'):
                    if not (header.startswith(b'\xff\xd8\xff') or header.startswith(b'\xff\xd8\xff\xe0') or header.startswith(b'\xff\xd8\xff\xe1')):
                        logger.warning(f"File has JPG extension but invalid signature: {header[:8].hex()}")
                
        logger.info(f"Successfully received direct upload for {bucket_name}/{object_name}, size: {written_bytes} bytes. Stored at {file_location}")
    except Exception as e:
        logger.error(f"Error during direct file upload to {file_location}: {e}")
        # Clean up partially written file if error occurs
        if os.path.exists(file_location):
            try:
                os.remove(file_location)
            except Exception as e_remove:
                logger.error(f"Error cleaning up partial file {file_location}: {e_remove}")
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    
    # Return file metadata (size, name, etc.)
    return {
        "filename": object_name,
        "bucket_name": bucket_name,
        "size": written_bytes,
        "content_type": content_type,
        "object_name": object_name
    }

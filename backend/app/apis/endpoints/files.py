from typing import Any, List, Optional, Union, Literal
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl, Field as PydanticField

from ...db.notify import emit_table_notification
from ...core.config import settings

from ...schemas.file import File, FileCreate
from ...models.user import User
from ...crud.file import get_file, get_files_by_owner, get_files_by_bucket, create_file, delete_file
from ...crud.bucket import get_bucket
from ..deps import get_db, get_current_active_user, get_current_user_or_anon, ANON_USER_ROLE
from ..deps_storage import get_storage_service_client, get_storage_service_client_anon, StorageServiceClient

# --- Pydantic model definitions (Ideally move to schemas/file.py and import) ---
class FileUploadInitiateRequest(BaseModel):
    filename: str = PydanticField(..., example="mydocument.pdf")
    content_type: Optional[str] = PydanticField(None, example="application/pdf")
    size: Optional[int] = PydanticField(None, example=1024768) # Size in bytes, client should provide
    bucket_id: uuid.UUID

class PresignedUploadInfo(BaseModel):
    upload_url: HttpUrl
    upload_method: str = PydanticField(..., example="PUT")
    # upload_headers: Optional[Dict[str, str]] = None # If storage service provides specific headers for client to use

class FileUploadInitiateResponse(BaseModel):
    file_metadata: File 
    presigned_upload_info: PresignedUploadInfo

class FileDownloadInfoResponse(BaseModel):
    file_metadata: File
    download_url: HttpUrl

class FileViewInfoResponse(BaseModel):
    file_metadata: File
    view_url: HttpUrl

class PresignedUrlRequest(BaseModel):
    expires_in_seconds: Optional[int] = PydanticField(3600, description="Requested expiry for the URL in seconds")
    content_type: Optional[str] = PydanticField(None, description="Expected content type of the file")
# --- End Pydantic model definitions ---

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

async def get_conditional_storage_client(
    requester: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon)
) -> StorageServiceClient:
    """
    Returns the appropriate storage service client based on the requester type.
    For authenticated users, returns a client with user token.
    For anonymous users, returns a client with anon key.
    """
    is_anon_request = requester == ANON_USER_ROLE
    is_authenticated_user = isinstance(requester, User)
    
    if is_authenticated_user:
        # Generate a JWT token for the authenticated user
        from jose import jwt
        import time
        token_data = {
            "sub": str(requester.id),
            "exp": int(time.time() + 3600)  # 1 hour expiry
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        client = StorageServiceClient(
            base_url=settings.STORAGE_SERVICE_URL,
            token=token,
            anon_key=settings.ANON_KEY
        )
    else:
        # For anonymous users or no authentication
        client = StorageServiceClient(
            base_url=settings.STORAGE_SERVICE_URL,
            anon_key=settings.ANON_KEY
        )
    
    return client

@router.get("", response_model=List[File])
async def list_files(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    bucket_id: Optional[uuid.UUID] = Query(None, description="Filter files by bucket ID"),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve files for the current user, optionally filtered by bucket.
    """
    if bucket_id:
        # Check if the bucket exists and belongs to the user
        bucket = await get_bucket(db, bucket_id=bucket_id)
        if not bucket or (bucket.owner_id != current_user.id and not current_user.is_superuser):
            raise HTTPException(status_code=404, detail="Bucket not found")

        # Get files from the specified bucket
        files = await get_files_by_bucket(db, bucket_id=bucket_id, skip=skip, limit=limit)
    else:
        # Get all files for the user
        files = await get_files_by_owner(db, owner_id=current_user.id, skip=skip, limit=limit)

    return files

@router.post("/initiate-upload", response_model=FileUploadInitiateResponse, status_code=status.HTTP_201_CREATED)
async def initiate_file_upload(
    *,
    db: AsyncSession = Depends(get_db),
    upload_request: FileUploadInitiateRequest, # New request body
    requester: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
    storage_client: StorageServiceClient = Depends(get_conditional_storage_client),
) -> Any:
    """
    Initiate a file upload.
    Creates a file record in the database and returns a pre-signed URL
    for the client to upload the file directly to the storage service.
    """
    try:
        is_anon_request = requester == ANON_USER_ROLE
        is_authenticated_user = isinstance(requester, User)

        if not is_authenticated_user and not is_anon_request:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )

        bucket_id = upload_request.bucket_id
        db_bucket = await get_bucket(db, bucket_id=bucket_id)
        if not db_bucket:
            logger.warning(f"Upload initiation for invalid bucket_id {bucket_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bucket not found"
            )

        # Permission check for bucket (simplified, adjust as per your app's logic)
        if is_anon_request:
            # For open-discussion-board sample app, allow anonymous users to upload to any bucket
            logger.info(f"Anonymous user initiating upload to bucket {db_bucket.name}")
        elif is_authenticated_user:
            if db_bucket.owner_id != requester.id and not requester.is_superuser:
                 # More fine-grained: check if bucket is public if allowing uploads to public buckets by any auth user
                if not db_bucket.is_public: # Example: only owner or superuser can upload to private bucket
                    raise HTTPException(status_code=403, detail="Permission denied for this bucket")
            logger.info(f"User {requester.id} initiating upload to bucket {db_bucket.name}")
        
        # Generate a unique object name for storage. Using UUID to avoid collisions.
        # You might want a more structured naming convention, e.g., user_id/bucket_id/uuid/filename
        file_extension = ""
        if '.' in upload_request.filename:
            file_extension = "." + upload_request.filename.rsplit('.', 1)[1]
        object_name_in_storage = f"{uuid.uuid4()}{file_extension}" # Example: "random-uuid.jpg"

        owner_id = requester.id if is_authenticated_user else db_bucket.owner_id

        file_in_db = FileCreate(
            filename=upload_request.filename,
            object_name=object_name_in_storage, # This is the key within the bucket
            bucket_name=db_bucket.name,
            content_type=upload_request.content_type,
            size=upload_request.size or 0, # Use provided size, default to 0
            owner_id=owner_id,
            bucket_id=bucket_id,
        )
        db_file = await create_file(db, file_in=file_in_db)
        logger.info(f"Created file record (ID: {db_file.id}) for {object_name_in_storage} in bucket {db_bucket.name}")

        # Get pre-signed URL from storage service
        try:
            presigned_data = await storage_client.generate_presigned_upload_url(
                bucket_name=db_bucket.name,
                object_name=object_name_in_storage,
                content_type=upload_request.content_type
                # expires_in_seconds can be customized if needed
            )
        except HTTPException as e: # Catch HTTPExceptions from storage client
            logger.error(f"Storage service error generating presigned URL: {e.detail}")
            # Attempt to clean up the created DB record if presigned URL generation fails
            await delete_file(db, file_id=db_file.id) # This might need adjustment if delete_file expects storage deletion too
            logger.warning(f"Rolled back file record {db_file.id} due to presigned URL generation failure.")
            raise # Re-raise the HTTPException
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {object_name_in_storage}: {str(e)}")
            await delete_file(db, file_id=db_file.id)
            logger.warning(f"Rolled back file record {db_file.id} due to presigned URL generation failure.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not generate upload URL: {str(e)}"
            )
        
        # Note: After client uploads, you might need a separate "finalize" or "confirm" endpoint
        # that the client calls. This endpoint could verify the upload with the storage service
        # and update the file's status/size in the DB if needed.
        # For simplicity, we assume the client upload will succeed.
        # The `emit_table_notification` for bucket stats would ideally be after successful upload confirmation.
        # For now, we emit it here, or it can be moved to a confirmation step.
        await emit_table_notification(
            db=db,
            table_name="buckets",
            operation="UPDATE",
            data={"id": str(bucket_id), "total_size_updated": True} # This might be premature if size is not confirmed
        )

        return FileUploadInitiateResponse(
            file_metadata=File.from_orm(db_file), # Ensure File schema can be created from ORM object
            presigned_upload_info=PresignedUploadInfo(
                upload_url=presigned_data["upload_url"],
                upload_method=presigned_data["method"]
                # upload_headers=presigned_data.get("headers") # if storage provides this
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error initiating file upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initiating file upload: {str(e)}",
        )

@router.get("/{file_id}/download-info", response_model=FileDownloadInfoResponse)
async def get_file_download_info(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    requester: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
    storage_client: StorageServiceClient = Depends(get_conditional_storage_client),
) -> Any:
    """
    Get file metadata and a direct download URL.
    Client uses this URL to download directly from storage.
    Authentication/authorization for the URL itself is handled by the storage service
    (e.g., via Bearer token in request to storage, or if URL is inherently public).
    """
    is_anon_request = requester == ANON_USER_ROLE
    is_authenticated_user = isinstance(requester, User)

    if not is_authenticated_user and not is_anon_request:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")

    db_file = await get_file(db, file_id=file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    db_bucket = await get_bucket(db, bucket_id=db_file.bucket_id)
    if not db_bucket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated bucket not found")

    # Permission check
    can_access = False
    if is_authenticated_user:
        if db_file.owner_id == requester.id or db_bucket.is_public or requester.is_superuser:
            can_access = True
    elif is_anon_request:
        if db_bucket.is_public: # Anonymous can only access public bucket files
            can_access = True
        # Special case for open-discussion-board (if still needed here)
        # elif "open-discussion-board" in some_context: can_access = True

    if not can_access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this file")
    
    # Ensure db_file.object_name is the actual key in storage (no bucket prefix)
    # The create_file logic should ensure this. If legacy data exists, sanitize here or in CRUD.
    object_name_in_storage = db_file.object_name 
    # Example sanitization (if File.object_name might still have bucket_name/ prefix):
    # prefix_to_check = f"{db_file.bucket_name}/"
    # if db_file.object_name.startswith(prefix_to_check):
    #    object_name_in_storage = db_file.object_name[len(prefix_to_check):]


    try:
        download_url = await storage_client.get_direct_download_url(
            bucket_name=db_file.bucket_name,
            object_name=object_name_in_storage,
        )
        return FileDownloadInfoResponse(
            file_metadata=File.from_orm(db_file),
            download_url=download_url
        )
    except Exception as e:
        logger.error(f"Error generating file download URL for {file_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )

@router.get("/{file_id}/view-info", response_model=FileViewInfoResponse)
async def get_file_view_info(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    requester: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
    storage_client: StorageServiceClient = Depends(get_conditional_storage_client),
) -> Any:
    """
    Get file metadata and a direct view URL.
    Client uses this URL to view the file directly from storage.
    Authentication/authorization for the URL itself is handled by the storage service.
    """
    is_anon_request = requester == ANON_USER_ROLE
    is_authenticated_user = isinstance(requester, User)

    if not is_authenticated_user and not is_anon_request:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")

    db_file = await get_file(db, file_id=file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    db_bucket = await get_bucket(db, bucket_id=db_file.bucket_id)
    if not db_bucket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated bucket not found")

    # Permission check
    can_access = False
    if is_authenticated_user:
        if db_file.owner_id == requester.id or db_bucket.is_public or requester.is_superuser:
            can_access = True
    elif is_anon_request:
        if db_bucket.is_public: # Anonymous can only access public bucket files
            can_access = True

    if not can_access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this file")
    
    object_name_in_storage = db_file.object_name 

    try:
        # Determine content type
        content_type = db_file.content_type
        
        # If no content type is stored or it's application/octet-stream, try to guess from extension
        if not content_type or content_type == "application/octet-stream":
            filename = db_file.filename
            if filename.lower().endswith('.png'):
                content_type = 'image/png'
            elif filename.lower().endswith(('.jpg', '.jpeg')):
                content_type = 'image/jpeg'
            elif filename.lower().endswith('.gif'):
                content_type = 'image/gif'
            elif filename.lower().endswith('.pdf'):
                content_type = 'application/pdf'
            elif filename.lower().endswith('.mp4'):
                content_type = 'video/mp4'
            elif filename.lower().endswith('.mp3'):
                content_type = 'audio/mpeg'

        logger.info(f"Generating view URL for file {file_id} with content_type: {content_type}")
        
        view_url = await storage_client.get_direct_view_url(
            bucket_name=db_file.bucket_name,
            object_name=object_name_in_storage,
            content_type=content_type
        )
        return FileViewInfoResponse(
            file_metadata=File.from_orm(db_file),
            view_url=view_url
        )
    except Exception as e:
        logger.error(f"Error generating file view URL for {file_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate view URL"
        )

@router.get("/public/{file_id}/download-info", response_model=FileDownloadInfoResponse)
async def public_get_file_download_info(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage_client: StorageServiceClient = Depends(get_storage_service_client_anon), # Use anon client
) -> Any:
    """
    Public endpoint to get file metadata and a direct download URL for files in public buckets.
    """
    db_file = await get_file(db, file_id=file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if not db_file.bucket_id:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="File is not in a bucket, cannot be public.")

    db_bucket = await get_bucket(db, bucket_id=db_file.bucket_id)
    if not db_bucket or not db_bucket.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="File is not in a public bucket.")

    logger.info(f"Public access request for file {file_id} in public bucket {db_bucket.name}")

    object_name_in_storage = db_file.object_name # Assuming this is the correct key

    try:
        download_url = await storage_client.get_direct_download_url(
            bucket_name=db_file.bucket_name,
            object_name=object_name_in_storage,
        )
        return FileDownloadInfoResponse(
            file_metadata=File.from_orm(db_file),
            download_url=download_url
        )
    except Exception as e:
        logger.error(f"Error generating public download URL for {file_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate public download URL"
        )

@router.get("/public/{file_id}/view-info", response_model=FileViewInfoResponse)
async def public_get_file_view_info(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage_client: StorageServiceClient = Depends(get_storage_service_client_anon), # Use anon client
) -> Any:
    """
    Public endpoint to get file metadata and a direct view URL for files in public buckets.
    """
    db_file = await get_file(db, file_id=file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if not db_file.bucket_id:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="File is not in a bucket, cannot be public.")

    db_bucket = await get_bucket(db, bucket_id=db_file.bucket_id)
    if not db_bucket or not db_bucket.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="File is not in a public bucket.")

    logger.info(f"Public access request for file {file_id} in public bucket {db_bucket.name}")

    object_name_in_storage = db_file.object_name # Assuming this is the correct key

    try:
        # Determine content type
        content_type = db_file.content_type
        
        # If no content type is stored or it's application/octet-stream, try to guess from extension
        if not content_type or content_type == "application/octet-stream":
            filename = db_file.filename
            if filename.lower().endswith('.png'):
                content_type = 'image/png'
            elif filename.lower().endswith(('.jpg', '.jpeg')):
                content_type = 'image/jpeg'
            elif filename.lower().endswith('.gif'):
                content_type = 'image/gif'
            elif filename.lower().endswith('.pdf'):
                content_type = 'application/pdf'
            elif filename.lower().endswith('.mp4'):
                content_type = 'video/mp4'
            elif filename.lower().endswith('.mp3'):
                content_type = 'audio/mpeg'

        logger.info(f"Generating public view URL for file {file_id} with content_type: {content_type}")
        
        view_url = await storage_client.get_direct_view_url(
            bucket_name=db_file.bucket_name,
            object_name=object_name_in_storage,
            content_type=content_type
        )
        return FileViewInfoResponse(
            file_metadata=File.from_orm(db_file),
            view_url=view_url
        )
    except Exception as e:
        logger.error(f"Error generating public view URL for {file_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate public view URL"
        )

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT) # Return 204 on successful delete
async def delete_file_endpoint(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    storage_client: StorageServiceClient = Depends(get_storage_service_client),
) -> None: # Return None for 204
    """
    Delete a file from storage service and the database.
    """
    db_file = await get_file(db, file_id=file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if db_file.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    try:
        # Ensure db_file.object_name is the correct key for the storage service
        object_name_in_storage = db_file.object_name 
        # Example sanitization if File.object_name might still have bucket_name/ prefix:
        # prefix_to_check = f"{db_file.bucket_name}/"
        # if db_file.object_name.startswith(prefix_to_check):
        #    object_name_in_storage = db_file.object_name[len(prefix_to_check):]

        await storage_client.delete_file(
            bucket_name=db_file.bucket_name,
            object_name=object_name_in_storage, # Changed from 'filename' to 'object_name'
        )
        logger.info(f"Successfully deleted file {object_name_in_storage} from storage service bucket {db_file.bucket_name}")

        await delete_file(db, file_id=file_id) # This is the DB delete
        logger.info(f"Successfully deleted file record {file_id} from database.")


        await emit_table_notification(
            db=db,
            table_name="buckets",
            operation="UPDATE",
            data={"id": str(db_file.bucket_id), "total_size_updated": True}
        )
        logger.info(f"Emitted notification to buckets_changes for bucket ID {db_file.bucket_id} after file deletion.")

        # No explicit return for 204
    except HTTPException as e: # Re-raise HTTPExceptions from storage_client or auth
        logger.error(f"HTTPException during file deletion {file_id}: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}",
        )

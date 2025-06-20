from typing import Any, List, Union, Literal
import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
# Remove MinIO imports
from fastapi.encoders import jsonable_encoder

from ...schemas.bucket import Bucket, BucketCreate, BucketUpdate, BucketWithStats
from ...schemas.file import File
from ...models.user import User
from ...crud.bucket import (
    get_bucket,
    get_buckets_by_owner,
    get_public_buckets,
    get_all_buckets,
    create_bucket,
    update_bucket,
    delete_bucket,
    get_bucket_stats
)
from ...crud.file import get_files_by_bucket
from ..deps import get_db, get_current_active_user, get_current_user_or_anon, ANON_USER_ROLE
from ..deps_storage import get_storage_service_client, StorageServiceClient
from ...core.config import settings
from ...db.notify import emit_table_notification

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("", response_model=List[BucketWithStats])
async def get_buckets(
    db: AsyncSession = Depends(get_db),
    requester: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get buckets based on authentication status.
    Authenticated users can see all buckets (both public and private).
    Anonymous users (with ANON_KEY) can see all buckets (for compatibility with open-discussion-board).
    """
    # Check permissions
    is_anon_request = requester == ANON_USER_ROLE
    is_authenticated_user = isinstance(requester, User)

    if not is_authenticated_user and not is_anon_request:
        # No authentication provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Get buckets based on authentication status
    if is_authenticated_user:
        logger.info(f"Getting all buckets for authenticated user {requester.id}")
        buckets = await get_all_buckets(db, skip=skip, limit=limit)
    else:
        # For anonymous users, get all buckets (for compatibility with open-discussion-board)
        logger.info("Getting all buckets for anonymous user")
        buckets = await get_all_buckets(db, skip=skip, limit=limit)

    # Add stats to each bucket
    result = []
    for bucket in buckets:
        stats = await get_bucket_stats(db, bucket.id)
        bucket_dict = Bucket.model_validate(bucket).model_dump()
        bucket_dict.update(stats)
        result.append(bucket_dict)

    logger.info(f"Found {len(result)} buckets for {'anonymous' if is_anon_request else 'authenticated'} user")
    return result

@router.get("/public", response_model=List[BucketWithStats])
async def get_public_buckets_endpoint(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get all public buckets for unauthenticated users.
    Unauthenticated users can only see public buckets.
    """
    # Get public buckets
    logger.info("Getting public buckets for unauthenticated user")
    buckets = await get_public_buckets(db, skip=skip, limit=limit)

    # Add stats to each bucket
    result = []
    for bucket in buckets:
        stats = await get_bucket_stats(db, bucket.id)
        bucket_dict = Bucket.model_validate(bucket).model_dump()
        bucket_dict.update(stats)
        result.append(bucket_dict)

    logger.info(f"Found {len(result)} public buckets")
    return result

@router.post("", response_model=Bucket, status_code=status.HTTP_201_CREATED)
async def create_bucket_endpoint(
    *,
    db: AsyncSession = Depends(get_db),
    bucket_in: BucketCreate,
    current_user: User = Depends(get_current_active_user),
    storage_client: StorageServiceClient = Depends(get_storage_service_client),
) -> Any:
    """
    Create a new bucket.
    """
    try:
        # Create bucket in database
        db_bucket = await create_bucket(
            db=db,
            bucket_in=bucket_in,
            owner_id=current_user.id
        )

        # Create the actual storage service bucket
        try:
            # Create the bucket in storage service
            logger.info(f"Creating storage service bucket: {db_bucket.name}")
            await storage_client.create_bucket(name=db_bucket.name, is_public=db_bucket.is_public)
            logger.info(f"Successfully created storage service bucket: {db_bucket.name}")
            
            # Update bucket visibility if needed
            if db_bucket.is_public != db_bucket.is_public:  # This is always false, but we'll keep the structure for future updates
                logger.info(f"Updating bucket visibility for: {db_bucket.name} to public={db_bucket.is_public}")
                await storage_client.update_bucket(bucket_name=db_bucket.name, is_public=db_bucket.is_public)
            
            await emit_table_notification(
                db, 
                "buckets", 
                "INSERT", 
                jsonable_encoder(db_bucket)
            )
            
            return db_bucket
            
        except Exception as e:
            # If we can't create the bucket in storage service, delete the database record
            logger.error(f"Error creating storage service bucket {db_bucket.name}: {str(e)}")
            await delete_bucket(db, db_bucket.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Storage service error: {str(e)}",
            )

    except ValueError as e:
        # Handle validation errors from the create_bucket function
        logger.warning(f"Validation error creating bucket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error creating bucket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating bucket: {str(e)}",
        )

@router.get("/{bucket_id}", response_model=BucketWithStats)
async def get_bucket_endpoint(
    bucket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    requester: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
) -> Any:
    """
    Get a specific bucket by ID.
    Authenticated users can access any bucket.
    Anonymous users (with ANON_KEY) can only access public buckets.
    """
    bucket = await get_bucket(db, bucket_id=bucket_id)
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")

    # Check permissions
    is_anon_request = requester == ANON_USER_ROLE
    is_authenticated_user = isinstance(requester, User)

    if not is_authenticated_user and not is_anon_request:
        # No authentication provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Anonymous users can only access public buckets
    if is_anon_request and not bucket.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This bucket is not public"
        )

    # Get bucket stats
    stats = await get_bucket_stats(db, bucket.id)
    bucket_dict = Bucket.model_validate(bucket).model_dump()
    bucket_dict.update(stats)

    return bucket_dict

@router.put("/{bucket_id}", response_model=Bucket)
async def update_bucket_endpoint(
    bucket_id: uuid.UUID,
    bucket_in: BucketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update a bucket.
    """
    bucket = await get_bucket(db, bucket_id=bucket_id)
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")

    # Check if the user is the owner
    if bucket.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    updated_bucket = await update_bucket(db, bucket_id=bucket_id, bucket_in=bucket_in)
    
    await emit_table_notification(
        db, 
        "buckets", 
        "UPDATE", 
        jsonable_encoder(updated_bucket)
    )
    
    return updated_bucket

@router.delete("/{bucket_id}", response_model=bool)
async def delete_bucket_endpoint(
    bucket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    storage_client: StorageServiceClient = Depends(get_storage_service_client),
) -> Any:
    """
    Delete a bucket and all its contents.
    """
    bucket = await get_bucket(db, bucket_id=bucket_id)
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")

    # Check if the user is the owner
    if bucket.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        # First, try to check if the storage service bucket exists
        try:
            await storage_client.get_bucket(bucket.name)
        except Exception as e:
            # If the storage service bucket doesn't exist, just delete the database record
            logger.warning(f"Storage service bucket {bucket.name} not found, deleting database record only")
            
            await emit_table_notification(
                db, 
                "buckets", 
                "DELETE", 
                None, 
                jsonable_encoder(bucket)
            )
            
            result = await delete_bucket(db, bucket_id=bucket_id)
            return result

        # Delete the bucket from storage service (this will delete all files in the bucket)
        logger.info(f"Deleting bucket {bucket.name} from storage service")
        await storage_client.delete_bucket(bucket.name)
        logger.info(f"Successfully deleted bucket {bucket.name} from storage service")

        # Delete the bucket from the database
        # This will cascade delete all file records associated with this bucket
        logger.info(f"Deleting bucket {bucket.name} from database")
        
        await emit_table_notification(
            db, 
            "buckets", 
            "DELETE", 
            None, 
            jsonable_encoder(bucket)
        )
        
        result = await delete_bucket(db, bucket_id=bucket_id)
        return result
    except Exception as e:
        logger.error(f"Storage service error deleting bucket {bucket.name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage service error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting bucket {bucket.name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting bucket: {str(e)}",
        )

@router.get("/{bucket_id}/files", response_model=List[File])
async def get_bucket_files(
    bucket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    requester: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get all files in a specific bucket.
    Authenticated users can access files in any bucket.
    Anonymous users (with ANON_KEY) can only access files in public buckets.
    """
    bucket = await get_bucket(db, bucket_id=bucket_id)
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")

    # Check permissions
    is_anon_request = requester == ANON_USER_ROLE
    is_authenticated_user = isinstance(requester, User)

    if not is_authenticated_user and not is_anon_request:
        # No authentication provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Anonymous users can only access public buckets
    if is_anon_request and not bucket.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This bucket is not public"
        )

    files = await get_files_by_bucket(db, bucket_id=bucket_id, skip=skip, limit=limit)
    return files

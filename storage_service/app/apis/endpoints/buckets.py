from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List, Optional, Union, Literal
import os
import json
import logging
from pathlib import Path as FilePath

from ...core.config import settings
from ...schemas.bucket import Bucket, BucketCreate, BucketUpdate
from ..deps import get_current_user, get_current_user_or_anon, TokenData, ANON_USER_ROLE

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter()

def get_bucket_path(bucket_name: str) -> str:
    """Get the full path to a bucket directory"""
    return os.path.join(settings.STORAGE_PATH, bucket_name)

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

def save_bucket_metadata(bucket_name: str, metadata: dict) -> bool:
    """Save bucket metadata to the metadata file"""
    metadata_path = get_bucket_metadata_path(bucket_name)
    try:
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
        return True
    except IOError as e:
        logger.error(f"Error saving bucket metadata: {e}")
        return False

@router.post("", response_model=Bucket, status_code=status.HTTP_201_CREATED)
async def create_bucket(
    bucket_in: BucketCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Create a new bucket.
    """
    bucket_name = bucket_in.name
    
    # Check if bucket already exists
    if bucket_exists(bucket_name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bucket '{bucket_name}' already exists"
        )
    
    # Create bucket directory
    bucket_path = get_bucket_path(bucket_name)
    try:
        os.makedirs(bucket_path, exist_ok=True)
    except OSError as e:
        logger.error(f"Error creating bucket directory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bucket"
        )
    
    # Save bucket metadata
    metadata = {
        "name": bucket_name,
        "is_public": bucket_in.is_public,
        "owner_id": current_user.sub,
        "created_at": FilePath(bucket_path).stat().st_ctime
    }
    
    if not save_bucket_metadata(bucket_name, metadata):
        # Clean up if metadata save fails
        try:
            os.rmdir(bucket_path)
        except OSError:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save bucket metadata"
        )
    
    return Bucket(
        name=bucket_name,
        is_public=bucket_in.is_public,
        owner_id=current_user.sub
    )

@router.get("", response_model=List[Bucket])
async def list_buckets(
    requester: Union[TokenData, Literal["anon"], None] = Depends(get_current_user_or_anon)
):
    """
    List buckets. 
    - Authenticated users see all their buckets plus public buckets
    - Anonymous users only see public buckets
    """
    buckets = []
    
    # Scan the storage directory for bucket directories
    try:
        for item in os.listdir(settings.STORAGE_PATH):
            item_path = os.path.join(settings.STORAGE_PATH, item)
            
            # Skip non-directories and hidden directories
            if not os.path.isdir(item_path) or item.startswith('.'):
                continue
            
            # Get bucket metadata
            metadata = get_bucket_metadata(item)
            if not metadata:
                logger.warning(f"Skipping bucket {item} with missing or invalid metadata")
                continue
            
            # For anonymous users, only include public buckets
            if requester == ANON_USER_ROLE or requester is None:
                if metadata.get("is_public", False):
                    buckets.append(Bucket(
                        name=metadata["name"],
                        is_public=metadata["is_public"],
                        owner_id=metadata["owner_id"]
                    ))
            # For authenticated users, include their buckets and public buckets
            elif isinstance(requester, TokenData):
                if metadata.get("owner_id") == requester.sub or metadata.get("is_public", False):
                    buckets.append(Bucket(
                        name=metadata["name"],
                        is_public=metadata["is_public"],
                        owner_id=metadata["owner_id"]
                    ))
    except OSError as e:
        logger.error(f"Error listing buckets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list buckets"
        )
    
    return buckets

@router.get("/{bucket_name}", response_model=Bucket)
async def get_bucket(
    bucket_name: str = Path(..., description="Bucket name"),
    requester: Union[TokenData, Literal["anon"], None] = Depends(get_current_user_or_anon)
):
    """
    Get bucket details.
    - Authenticated users can access their buckets and public buckets
    - Anonymous users can only access public buckets
    """
    if not bucket_exists(bucket_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket_name}' not found"
        )
    
    metadata = get_bucket_metadata(bucket_name)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bucket metadata"
        )
    
    # Check access permissions
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
    
    return Bucket(
        name=metadata["name"],
        is_public=metadata["is_public"],
        owner_id=metadata["owner_id"]
    )

@router.put("/{bucket_name}", response_model=Bucket)
async def update_bucket(
    bucket_update: BucketUpdate,
    bucket_name: str = Path(..., description="Bucket name"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Update bucket details. Currently only supports changing is_public flag.
    """
    if not bucket_exists(bucket_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket_name}' not found"
        )
    
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
            detail="You don't have permission to update this bucket"
        )
    
    # Update metadata
    update_data = bucket_update.model_dump(exclude_unset=True)
    metadata.update(update_data)
    
    if not save_bucket_metadata(bucket_name, metadata):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save bucket metadata"
        )
    
    return Bucket(
        name=metadata["name"],
        is_public=metadata["is_public"],
        owner_id=metadata["owner_id"]
    )

@router.delete("/{bucket_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bucket(
    bucket_name: str = Path(..., description="Bucket name"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Delete a bucket. The bucket must be empty.
    """
    if not bucket_exists(bucket_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket_name}' not found"
        )
    
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
            detail="You don't have permission to delete this bucket"
        )
    
    bucket_path = get_bucket_path(bucket_name)
    
    # Check if bucket is empty (except for metadata file)
    bucket_contents = os.listdir(bucket_path)
    if len(bucket_contents) > 1 or (len(bucket_contents) == 1 and ".metadata.json" not in bucket_contents):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete non-empty bucket"
        )
    
    # Delete metadata file and bucket directory
    try:
        metadata_path = get_bucket_metadata_path(bucket_name)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
        os.rmdir(bucket_path)
    except OSError as e:
        logger.error(f"Error deleting bucket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete bucket"
        )
    
    return None

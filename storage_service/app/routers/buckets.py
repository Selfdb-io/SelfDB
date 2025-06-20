import logging
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any

from ..core.storage import storage

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.post("/{bucket_name}", status_code=status.HTTP_201_CREATED)
async def create_bucket(bucket_name: str) -> Dict[str, Any]:
    """
    Create a new bucket.
    """
    try:
        await storage.create_bucket(bucket_name)
        return {
            "status": "success",
            "message": f"Bucket '{bucket_name}' created successfully",
            "bucket_name": bucket_name
        }
    except Exception as e:
        logger.error(f"Error creating bucket '{bucket_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bucket: {str(e)}"
        )

@router.get("/{bucket_name}/exists")
async def check_bucket_exists(bucket_name: str) -> Dict[str, Any]:
    """
    Check if a bucket exists.
    """
    exists = await storage.bucket_exists(bucket_name)
    return {
        "exists": exists,
        "bucket_name": bucket_name
    }

@router.delete("/{bucket_name}")
async def delete_bucket(bucket_name: str) -> Dict[str, Any]:
    """
    Delete a bucket and all its contents.
    """
    try:
        result = await storage.delete_bucket(bucket_name)
        if result:
            return {
                "status": "success",
                "message": f"Bucket '{bucket_name}' deleted successfully",
                "bucket_name": bucket_name
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{bucket_name}' not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bucket '{bucket_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete bucket: {str(e)}"
        )

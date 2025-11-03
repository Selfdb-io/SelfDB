"""
FastAPI endpoints for bucket CRUD operations proxied to storage service.
"""

import os
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from shared.config.config_manager import ConfigManager
from shared.network.service_resolver import ServiceResolver
from shared.database.connection_manager import DatabaseConnectionManager
from storage_client import StorageClient


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/buckets", tags=["buckets"])


class ConfigAdapter:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._settings = {
            "connection_pool_size": 20,
            "health_check_interval": 60,
            "storage_host": "storage",
            "storage_port": config_manager.get_port("storage"),
        }

    def get_setting(self, key: str):
        return self._settings.get(key)

    def get_port(self, service: str) -> int:
        return self.config_manager.get_port(service)


class ServiceResolverAdapter:
    def __init__(self, service_resolver: ServiceResolver, config_manager: ConfigManager):
        self.service_resolver = service_resolver
        self.config_manager = config_manager

    def get_service_url(self, service_name: str) -> str:
        if service_name == "storage":
            return f"http://storage:{self.config_manager.get_port('storage')}"
        elif service_name == "backend":
            return f"http://backend:{self.config_manager.get_port('backend')}"
        else:
            return f"http://{service_name}:8000"

    def __getattr__(self, name):
        return getattr(self.service_resolver, name)


# Initialize dependencies
config_manager = ConfigManager()
config_adapter = ConfigAdapter(config_manager)
service_resolver = ServiceResolver(config_manager)
service_discovery = ServiceResolverAdapter(service_resolver, config_manager)
storage_client = StorageClient(config_adapter, service_discovery)

# Database manager for metadata sync
_db_manager = DatabaseConnectionManager(config_manager)

# Get default system user for storage operations
async def _get_system_user_id() -> str:
    """Get an admin user to use as default owner for storage operations."""
    try:
        async with _db_manager.acquire() as conn:
            # Try to get an admin user
            user_id = await conn.fetchval(
                "SELECT id FROM users WHERE role = 'ADMIN' LIMIT 1"
            )
            if user_id:
                return str(user_id)
            # Fallback to any user
            user_id = await conn.fetchval("SELECT id FROM users LIMIT 1")
            if user_id:
                return str(user_id)
        logger.warning("No users found in database for default owner")
        return "00000000-0000-0000-0000-000000000000"  # Fallback
    except Exception as e:
        logger.error(f"Failed to get system user: {e}")
        return "00000000-0000-0000-0000-000000000000"  # Fallback


class BucketCreate(BaseModel):
    name: str
    owner_id: Optional[str] = None
    public: Optional[bool] = False


class BucketUpdate(BaseModel):
    public: Optional[bool] = None


# Database sync helper functions
async def _sync_bucket_to_db(bucket_name: str, owner_id: str, public: bool = False) -> None:
    """Insert or update bucket metadata in database to trigger pg_notify."""
    try:
        bucket_id = str(uuid.uuid4())
        async with _db_manager.acquire() as conn:
            # Check if bucket already exists
            existing_id = await conn.fetchval(
                "SELECT id FROM buckets WHERE name = $1", 
                bucket_name
            )
            
            if existing_id:
                # Update existing bucket
                await conn.execute("""
                    UPDATE buckets 
                    SET public = $1, updated_at = NOW()
                    WHERE name = $2
                """, public, bucket_name)
            else:
                # Insert new bucket
                await conn.execute("""
                    INSERT INTO buckets (id, name, owner_id, public, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, NOW(), NOW())
                """, bucket_id, bucket_name, owner_id, public)
        
        logger.info(f"Synced bucket '{bucket_name}' to database")
    except Exception as e:
        logger.error(f"Failed to sync bucket '{bucket_name}' to database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync bucket metadata: {str(e)}"
        )


async def _delete_bucket_from_db(bucket_name: str) -> None:
    """Delete bucket metadata from database to trigger pg_notify."""
    try:
        async with _db_manager.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM buckets WHERE name = $1", 
                bucket_name
            )
        logger.info(f"Deleted bucket '{bucket_name}' from database")
    except Exception as e:
        logger.error(f"Failed to delete bucket '{bucket_name}' from database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete bucket metadata: {str(e)}"
        )


@router.get("")
async def list_buckets():
    """List all buckets from database for real-time updates."""
    try:
        async with _db_manager.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    b.id,
                    b.name,
                    b.owner_id,
                    b.public,
                    b.description,
                    b.metadata,
                    b.created_at,
                    b.updated_at,
                    COUNT(f.id) as file_count,
                    COALESCE(SUM(f.size), 0) as total_size
                FROM buckets b
                LEFT JOIN files f ON f.bucket_id = b.id
                GROUP BY b.id, b.name, b.owner_id, b.public, b.description, b.metadata, b.created_at, b.updated_at
                ORDER BY b.created_at DESC
            """)
            
            buckets = []
            for row in rows:
                buckets.append({
                    "id": row["id"],
                    "name": row["name"],
                    "internal_bucket_name": row["name"],
                    "owner_id": row["owner_id"],
                    "public": row["public"],
                    "description": row["description"],
                    "file_count": row["file_count"],
                    "total_size": row["total_size"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                })
            
            return {"success": True, "buckets": buckets, "total": len(buckets)}
    except Exception as e:
        logger.error(f"List buckets from database failed: {e}")
        raise HTTPException(status_code=503, detail="Database service unavailable")


@router.post("")
async def create_bucket(payload: BucketCreate):
    try:
        headers = {"x-api-key": os.getenv("API_KEY", "")}
        result = await storage_client.make_request(
            method="POST",
            endpoint="/api/v1/buckets",
            data=payload.model_dump(),
            headers=headers,
        )

        # Normalize and propagate error semantics without fallbacks
        if isinstance(result, dict):
            if result.get("success") is True or "bucket" in result:
                # Storage creation successful - sync to database
                owner_id = payload.owner_id or await _get_system_user_id()
                await _sync_bucket_to_db(
                    bucket_name=payload.name,
                    owner_id=owner_id,
                    public=payload.public or False
                )
                
                if result.get("success") is True:
                    return result
                if "bucket" in result and "success" not in result:
                    return {"success": True, **result}
            
            if "detail" in result:
                detail = str(result.get("detail", "")).lower()
                if "invalid" in detail:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["detail"]) 
                if "not empty" in detail:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["detail"]) 
                if "not found" in detail:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["detail"]) 
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)

        # If non-dict or unknown shape, treat as service error
        raise HTTPException(status_code=503, detail="Storage service unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create bucket failed: {e}")
        raise HTTPException(status_code=503, detail="Storage service unavailable")


@router.get("/{bucket}")
async def get_bucket(bucket: str):
    """Get bucket details from database for real-time updates."""
    try:
        async with _db_manager.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    b.id,
                    b.name,
                    b.owner_id,
                    b.public,
                    b.description,
                    b.metadata,
                    b.created_at,
                    b.updated_at,
                    COUNT(f.id) as file_count,
                    COALESCE(SUM(f.size), 0) as total_size
                FROM buckets b
                LEFT JOIN files f ON f.bucket_id = b.id
                WHERE b.name = $1
                GROUP BY b.id, b.name, b.owner_id, b.public, b.description, b.metadata, b.created_at, b.updated_at
            """, bucket)
            
            if not row:
                raise HTTPException(status_code=404, detail="Bucket not found")
            
            return {
                "success": True,
                "bucket": {
                    "id": row["id"],
                    "name": row["name"],
                    "internal_bucket_name": row["name"],
                    "owner_id": row["owner_id"],
                    "public": row["public"],
                    "description": row["description"],
                    "file_count": row["file_count"],
                    "total_size": row["total_size"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get bucket from database failed: {e}")
        raise HTTPException(status_code=503, detail="Database service unavailable")


@router.delete("/{bucket}")
async def delete_bucket(bucket: str):
    try:
        headers = {"x-api-key": os.getenv("API_KEY", "")}
        result = await storage_client.make_request(
            method="DELETE",
            endpoint=f"/api/v1/buckets/{bucket}",
            headers=headers,
        )

        if isinstance(result, dict) and result.get("detail") == "Bucket not found":
            raise HTTPException(status_code=404, detail="Bucket not found")

        # Storage deletion successful - sync to database
        await _delete_bucket_from_db(bucket)
        
        return result if isinstance(result, dict) else {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete bucket failed: {e}")
        raise HTTPException(status_code=503, detail="Storage service unavailable")


@router.put("/{bucket}")
async def update_bucket(bucket: str, payload: BucketUpdate):
    try:
        headers = {"x-api-key": os.getenv("API_KEY", "")}
        result = await storage_client.make_request(
            method="PUT",
            endpoint=f"/api/v1/buckets/{bucket}",
            data=payload.model_dump(),
            headers=headers,
        )
        if isinstance(result, dict) and result.get("detail") == "Bucket not found":
            raise HTTPException(status_code=404, detail="Bucket not found")
        
        # Storage update successful - sync to database
        if payload.public is not None:
            await _sync_bucket_to_db(
                bucket_name=bucket,
                owner_id=await _get_system_user_id(),
                public=payload.public
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update bucket failed: {e}")
        raise HTTPException(status_code=503, detail="Storage service unavailable")


@router.get("/{bucket}/files")
async def list_bucket_files(bucket: str):
    """List files in a bucket from database for real-time updates."""
    try:
        async with _db_manager.acquire() as conn:
            # Get bucket ID first
            bucket_id = await conn.fetchval(
                "SELECT id FROM buckets WHERE name = $1", 
                bucket
            )
            
            if not bucket_id:
                raise HTTPException(status_code=404, detail="Bucket not found")
            
            # Get files for this bucket
            rows = await conn.fetch("""
                SELECT 
                    id,
                    name as filename,
                    size,
                    mime_type as content_type,
                    created_at,
                    updated_at,
                    owner_id
                FROM files
                WHERE bucket_id = $1
                ORDER BY created_at DESC
            """, bucket_id)
            
            files = []
            for row in rows:
                files.append({
                    "id": row["filename"],  # Use filename as ID for compatibility
                    "filename": row["filename"].split("/")[-1],  # Extract just the filename
                    "size": row["size"],
                    "content_type": row["content_type"],
                    "created_at": int(row["created_at"].timestamp()) if row["created_at"] else 0,
                    "updated_at": int(row["updated_at"].timestamp()) if row["updated_at"] else 0,
                    "bucket": bucket,
                })
            
            return {"success": True, "files": files}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List bucket files from database failed: {e}")
        raise HTTPException(status_code=503, detail="Database service unavailable")

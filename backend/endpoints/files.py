"""
FastAPI endpoints for unified file operations.
Uses existing proxy components to handle file upload/download/delete operations.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
import logging
import os
import uuid
from datetime import datetime

# Import existing components  
from shared.config.config_manager import ConfigManager
from shared.network.service_resolver import ServiceResolver
from shared.database.connection_manager import DatabaseConnectionManager
from file_handlers import FileUploadProxy, FileDownloadProxy
from storage_client import StorageClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["files"])


class ConfigAdapter:
    """Adapter to make ConfigManager compatible with proxy components."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._settings = {
            # File upload settings
            # Effectively unlimited (10TB) — actual enforcement handled by infrastructure
            "max_file_size": 10 * 1024 * 1024 * 1024 * 1024,
            
            # Connection and networking
            "connection_pool_size": 20,
            "health_check_interval": 60,
            
            # Storage service configuration
            "storage_host": "storage",
            "storage_port": config_manager.get_port("storage"),
            
            # Download configuration
            "download_timeout": 600.0,  # 10 minutes for large files
            
            # Upload configuration  
            "upload_timeout": 600.0,    # 10 minutes for large files
            
            # Retry configuration
            "retry_attempts": 3,
            "retry_backoff": 1.0,
        }
    
    def get_setting(self, key: str):
        """Get setting value by key."""
        return self._settings.get(key)
    
    def get_port(self, service: str) -> int:
        return self.config_manager.get_port(service)


class AuthMiddlewareAdapter:
    """Simple auth middleware adapter for proxy components."""
    
    def __init__(self):
        self.api_key = os.getenv("API_KEY")
    
    def validate_api_key(self, key: str) -> bool:
        return key == self.api_key


class ServiceResolverAdapter:
    """Adapter to add missing methods to ServiceResolver."""
    
    def __init__(self, service_resolver: ServiceResolver, config_manager: ConfigManager):
        self.service_resolver = service_resolver
        self.config_manager = config_manager
        
    def get_service_url(self, service_name: str) -> str:
        """Get service URL for the given service name."""
        if service_name == "storage":
            return f"http://storage:{self.config_manager.get_port('storage')}"
        elif service_name == "backend":
            return f"http://backend:{self.config_manager.get_port('backend')}" 
        elif service_name == "frontend":
            return f"http://frontend:{self.config_manager.get_port('frontend')}"
        else:
            return f"http://{service_name}:8000"
    
    def __getattr__(self, name):
        """Delegate all other attributes to the original service resolver."""
        return getattr(self.service_resolver, name)


# Initialize dependencies with adapters
config_manager = ConfigManager()
config_adapter = ConfigAdapter(config_manager)
service_resolver = ServiceResolver(config_manager)
service_discovery = ServiceResolverAdapter(service_resolver, config_manager)
auth_adapter = AuthMiddlewareAdapter()

# Initialize actual proxy components
upload_proxy = FileUploadProxy(config_adapter, auth_adapter)
download_proxy = FileDownloadProxy(config_adapter, auth_adapter)
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


# Database sync helper functions
async def _sync_file_to_db(bucket_name: str, file_path: str, file_size: int, content_type: str, owner_id: str) -> None:
    """Insert file metadata to database to trigger pg_notify."""
    try:
        async with _db_manager.acquire() as conn:
            # Get bucket_id from bucket name
            bucket_id = await conn.fetchval("SELECT id FROM buckets WHERE name = $1", bucket_name)
            if not bucket_id:
                logger.warning(f"Bucket '{bucket_name}' not found in database, cannot sync file metadata")
                raise ValueError(f"Bucket {bucket_name} not found in database")
            
            # Check if file already exists (for updates)
            existing_file = await conn.fetchrow(
                "SELECT id FROM files WHERE bucket_id = $1 AND name = $2",
                bucket_id, file_path
            )
            
            if existing_file:
                # Update existing file
                await conn.execute("""
                    UPDATE files 
                    SET size = $1, mime_type = $2, updated_at = NOW()
                    WHERE bucket_id = $3 AND name = $4
                """, file_size, content_type, bucket_id, file_path)
            else:
                # Insert new file
                file_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO files (id, bucket_id, name, owner_id, size, mime_type, version, is_latest, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, 1, TRUE, NOW(), NOW())
                """, file_id, bucket_id, file_path, owner_id, file_size, content_type)
        
        logger.info(f"Synced file '{file_path}' in bucket '{bucket_name}' to database")
    except Exception as e:
        logger.error(f"Failed to sync file '{file_path}' to database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync file metadata: {str(e)}"
        )


async def _delete_file_from_db(bucket_name: str, file_path: str) -> None:
    """Delete file metadata from database to trigger pg_notify."""
    try:
        async with _db_manager.acquire() as conn:
            bucket_id = await conn.fetchval("SELECT id FROM buckets WHERE name = $1", bucket_name)
            if bucket_id:
                result = await conn.execute(
                    "DELETE FROM files WHERE bucket_id = $1 AND name = $2", 
                    bucket_id, file_path
                )
                logger.info(f"Deleted file '{file_path}' from bucket '{bucket_name}' in database")
            else:
                logger.warning(f"Bucket '{bucket_name}' not found, skipping file deletion from database")
    except Exception as e:
        logger.error(f"Failed to delete file '{file_path}' from database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file metadata: {str(e)}"
        )


@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    bucket: str = Form(...),
    path: Optional[str] = Form(None)
):
    """Upload a file to the specified bucket using streaming to avoid memory spikes."""
    try:
        # Prepare metadata for the proxy
        target_path = path or file.filename
        metadata = {
            "filename": file.filename,
            "content_type": file.content_type or "application/octet-stream",
            "bucket": bucket,
            "path": target_path,
        }

        # Prepare auth headers
        auth_headers = {"x-api-key": os.getenv("API_KEY", "")}

        # Async chunked reader to stream upload without loading full file in memory
        async def iter_file_chunks(upload: UploadFile, chunk_size: int = 1024 * 1024):
            while True:
                chunk = await upload.read(chunk_size)
                if not chunk:
                    break
                yield chunk

        result = await upload_proxy.stream_upload_file(
            file_stream=iter_file_chunks(file),
            metadata=metadata,
            auth_headers=auth_headers,
        )
        
        # Handle proxy response
        if result.get("status") == "error":
            code = result.get("error_code", 503)
            if code == 413:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result.get("error_message", "Storage service unavailable"))
        
        # Storage upload successful - sync to database
        file_size = result.get("size", 0)
        await _sync_file_to_db(
            bucket_name=bucket,
            file_path=target_path,
            file_size=file_size,
            content_type=metadata["content_type"],
            owner_id=await _get_system_user_id()
        )
        
        return {
            "success": True,
            "message": "File uploaded successfully",
            "bucket": bucket,
            "path": target_path,
            "size": result.get("size"),
            "file_id": result.get("file_id"),
            "upload_time": result.get("upload_time")
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service unavailable"
        )


@router.get("/files/{bucket}/{path:path}")
async def download_file(bucket: str, path: str):
    """Stream a file from storage to the client with immediate TTFB."""
    try:
        auth_headers = {"x-api-key": os.getenv("API_KEY", "")}

        # Stream directly from storage → client
        stream_result = await download_proxy.stream_download_file(
            bucket=bucket,
            path=path,
            auth_headers=auth_headers,
        )

        if stream_result.get("status") == "streaming":
            filename = path.split("/")[-1]
            # Use the actual content type from storage service
            content_type = stream_result.get("content_type", "application/octet-stream")
            
            headers = {"Content-Disposition": f"attachment; filename=\"{filename}\""}
            
            # Add content length if available
            if stream_result.get("content_length"):
                headers["Content-Length"] = stream_result["content_length"]
            
            return StreamingResponse(
                stream_result["stream"],
                media_type=content_type,
                headers=headers,
            )

        # Map errors
        if stream_result.get("status") == "error" and stream_result.get("error_code") == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Storage service unavailable")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Storage service unavailable")


@router.delete("/files/{bucket}/{path:path}")
async def delete_file(bucket: str, path: str):
    """Delete a file from the specified bucket using StorageClient."""
    try:
        # Prepare request data
        delete_endpoint = f"/{bucket}/{path}"
        auth_headers = {
            "x-api-key": os.getenv("API_KEY", ""),
        }
        
        # Use actual StorageClient to make DELETE request to storage service
        result = await storage_client.make_request(
            method="DELETE",
            endpoint=delete_endpoint,
            headers=auth_headers
        )
        
        # Handle storage client response
        status_code = result.get("status_code")
        if status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        elif status_code in [401, 403]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized to delete file"
            )
        elif status_code and status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service error"
            )
        elif result.get("status") == "error":
            # Handle connection errors and other errors without status_code
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result.get("error_message", "Storage service unavailable")
            )
        
        # Storage deletion successful - sync to database
        await _delete_file_from_db(bucket, path)
        
        return {
            "success": True,
            "message": "File deleted successfully",
            "bucket": bucket,
            "path": path
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized to delete file"
        )
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service unavailable"
        )
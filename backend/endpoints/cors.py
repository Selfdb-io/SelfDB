"""
FastAPI endpoints for CORS origin management.
Admin-only endpoints for managing allowed CORS origins.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request, Response
from pydantic import BaseModel, Field, ConfigDict

from shared.config.config_manager import ConfigManager
from shared.database.connection_manager import DatabaseConnectionManager
from shared.services.cors_origin_crud_manager import (
    CorsOriginCRUDManager,
    CorsOriginNotFoundError,
    CorsOriginAlreadyExistsError,
    CorsOriginValidationError,
)
from shared.models.cors_origin import CorsOrigin
from shared.auth.admin_access import AdminAccessControl
from shared.auth.jwt_service import JWTService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["cors"])

# Dependencies (injected from FastAPI dependency system)
def get_auth_endpoints():
    """Get AuthEndpoints instance with dependencies."""
    try:
        from backend.dependencies import get_auth_endpoints as get_auth_deps
        return get_auth_deps()
    except ImportError:
        # Fallback for testing
        from shared.auth.auth_endpoints import AuthEndpoints
        from shared.auth.jwt_service import JWTService
        from shared.config.config_manager import ConfigManager
        from shared.auth.database_user_store import DatabaseUserStore
        from shared.database.connection_manager import DatabaseConnectionManager

        config = ConfigManager()
        jwt_service = JWTService(
            secret_key=config.get_jwt_secret(),
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_hours=24
        )
        
        db_manager = DatabaseConnectionManager(config)
        user_store = DatabaseUserStore(db_manager)
        
        return AuthEndpoints(
            api_key=config.get_api_key(),
            jwt_service=jwt_service,
            user_store=user_store
        )

try:
    _config_manager = ConfigManager()
    _db_manager = DatabaseConnectionManager(_config_manager)
    cors_crud_manager = CorsOriginCRUDManager(_db_manager)
    
    # Initialize JWT service for admin access control
    jwt_service = JWTService(
        secret_key=_config_manager.get_jwt_secret(),
        algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_hours=24
    )
    
    admin_access = AdminAccessControl(
        api_key=_config_manager.get_api_key(),
        jwt_service=jwt_service,
        enable_logging=True
    )
except Exception as exc:
    logger.warning("Failed to initialize CORS CRUD managers: %s", exc)
    cors_crud_manager = None
    admin_access = None


# Pydantic request/response models
class CorsOriginResponse(BaseModel):
    """Response model for CORS origin data."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    origin: str
    description: Optional[str] = None
    is_active: bool
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by: str
    created_at: str
    updated_at: str


class CorsOriginListResponse(BaseModel):
    """Response model for CORS origins list."""
    origins: List[CorsOriginResponse]
    total_count: int


class CreateCorsOriginRequest(BaseModel):
    """Request model for creating a CORS origin."""
    origin: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    extra_metadata: Optional[Dict[str, Any]] = None


class UpdateCorsOriginRequest(BaseModel):
    """Request model for updating a CORS origin."""
    origin: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    extra_metadata: Optional[Dict[str, Any]] = None


class CorsOriginValidationResponse(BaseModel):
    """Response model for CORS origin validation."""
    origin: str
    is_valid: bool
    error_message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str


async def get_current_admin_user(request: Request) -> Dict[str, Any]:
    """Get current admin user and validate admin access."""
    try:
        # Get API key from request headers
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="API key is required"
            )

        # Get Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Bearer token is required"
            )

        access_token = auth_header.split(" ")[1]

        # Use AuthEndpoints business logic
        auth_endpoints = get_auth_endpoints()
        if not auth_endpoints:
            raise HTTPException(
                status_code=500,
                detail="AuthEndpoints dependency not available"
            )

        result = await auth_endpoints.get_current_user(
            api_key=api_key,
            access_token=access_token
        )

        if not result["success"]:
            # Handle business logic errors
            error = result["error"]
            status_code = 401
            if error["code"] == "INVALID_API_KEY":
                status_code = 401
            elif error["code"] == "INVALID_TOKEN":
                status_code = 401
            elif error["code"] == "TOKEN_EXPIRED":
                status_code = 401
            elif error["code"] == "TOKEN_BLACKLISTED":
                status_code = 401
            elif error["code"] == "USER_NOT_FOUND":
                status_code = 404

            raise HTTPException(
                status_code=status_code,
                detail=error["message"]
            )

        user = result["user"]
        # Ensure user is active and has ADMIN role
        if not user.get("is_active") or user.get("role") != "ADMIN":
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )

        return {
            "user_id": user["id"],
            "api_key": api_key,
            "access_token": access_token,
            "user": user
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting current admin user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error getting current admin user"
        )


async def check_admin_operation(operation: str, api_key: str, access_token: str) -> None:
    """Helper to check admin operation permissions."""
    if not admin_access or not await admin_access.check_admin_operation(
        operation=operation,
        api_key=api_key,
        jwt_token=access_token
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Admin operation '{operation}' not allowed"
        )


@router.get("/cors/origins/", response_model=CorsOriginListResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def list_cors_origins(
    request: Request,
    active_only: bool = Query(True, description="Only return active origins"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """List CORS origins (admin only)."""
    await check_admin_operation("list_cors_origins", _admin["api_key"], _admin["access_token"])

    try:
        if not cors_crud_manager:
            raise HTTPException(status_code=500, detail="CORS service not available")

        origins = await cors_crud_manager.list_cors_origins(
            active_only=active_only,
            limit=limit,
            offset=offset
        )

        return CorsOriginListResponse(
            origins=[CorsOriginResponse(**origin.to_dict()) for origin in origins],
            total_count=len(origins)  # For now, return actual count; could be optimized later
        )
    except Exception as e:
        logger.error(f"Failed to list CORS origins: {e}")
        raise HTTPException(status_code=500, detail="Failed to list CORS origins")


@router.post("/cors/origins/", response_model=CorsOriginResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def create_cors_origin(
    request: Request,
    origin_data: CreateCorsOriginRequest,
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Create a new CORS origin (admin only)."""
    await check_admin_operation("add_cors_origin", _admin["api_key"], _admin["access_token"])

    try:
        if not cors_crud_manager:
            raise HTTPException(status_code=500, detail="CORS service not available")

        cors_origin = await cors_crud_manager.create_cors_origin(
            origin=origin_data.origin,
            created_by=uuid.UUID(_admin["user_id"]),
            description=origin_data.description,
            is_active=True,
            extra_metadata=origin_data.extra_metadata
        )

        return CorsOriginResponse(**cors_origin.to_dict())
    except CorsOriginAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except CorsOriginValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create CORS origin: {e}")
        raise HTTPException(status_code=500, detail="Failed to create CORS origin")


@router.get("/cors/origins/{origin_id}", response_model=CorsOriginResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_cors_origin(
    request: Request,
    origin_id: str,
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get a specific CORS origin by ID (admin only)."""
    await check_admin_operation("list_cors_origins", _admin["api_key"], _admin["access_token"])

    try:
        if not cors_crud_manager:
            raise HTTPException(status_code=500, detail="CORS service not available")

        origin_uuid = uuid.UUID(origin_id)
        cors_origin = await cors_crud_manager.get_cors_origin_by_id(origin_uuid)

        return CorsOriginResponse(**cors_origin.to_dict())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid origin ID format")
    except CorsOriginNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get CORS origin: {e}")
        raise HTTPException(status_code=500, detail="Failed to get CORS origin")


@router.put("/cors/origins/{origin_id}", response_model=CorsOriginResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def update_cors_origin(
    request: Request,
    origin_id: str,
    origin_data: UpdateCorsOriginRequest,
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update a CORS origin (admin only)."""
    await check_admin_operation("add_cors_origin", _admin["api_key"], _admin["access_token"])

    try:
        if not cors_crud_manager:
            raise HTTPException(status_code=500, detail="CORS service not available")

        origin_uuid = uuid.UUID(origin_id)
        cors_origin = await cors_crud_manager.update_cors_origin(
            origin_id=origin_uuid,
            origin=origin_data.origin,
            description=origin_data.description,
            is_active=origin_data.is_active,
            extra_metadata=origin_data.extra_metadata
        )

        return CorsOriginResponse(**cors_origin.to_dict())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid origin ID format")
    except CorsOriginNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CorsOriginAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update CORS origin: {e}")
        raise HTTPException(status_code=500, detail="Failed to update CORS origin")


@router.delete("/cors/origins/{origin_id}", responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def delete_cors_origin(
    request: Request,
    origin_id: str,
    hard_delete: bool = Query(True, description="Permanently delete instead of soft delete (default: True)"),
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete a CORS origin (admin only)."""
    await check_admin_operation("remove_cors_origin", _admin["api_key"], _admin["access_token"])

    try:
        if not cors_crud_manager:
            raise HTTPException(status_code=500, detail="CORS service not available")

        origin_uuid = uuid.UUID(origin_id)
        await cors_crud_manager.delete_cors_origin(origin_uuid, hard_delete)

        return Response(status_code=204)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid origin ID format")
    except CorsOriginNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete CORS origin: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete CORS origin")


@router.post("/cors/origins/validate", response_model=CorsOriginValidationResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def validate_cors_origin(
    request: Request,
    origin: str = Query(..., description="Origin URL to validate"),
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Validate a CORS origin URL format (admin only)."""
    await check_admin_operation("list_cors_origins", _admin["api_key"], _admin["access_token"])

    try:
        if not cors_crud_manager:
            raise HTTPException(status_code=500, detail="CORS service not available")

        validation_result = await cors_crud_manager.validate_origin_url(origin)

        return CorsOriginValidationResponse(
            origin=origin,
            is_valid=validation_result["is_valid"],
            error_message=validation_result.get("error_message")
        )
    except Exception as e:
        logger.error(f"Failed to validate CORS origin: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate CORS origin")


@router.post("/cors/origins/refresh-cache", responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def refresh_cors_cache(
    request: Request,
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Refresh CORS origins cache (admin only)."""
    await check_admin_operation("list_cors_origins", _admin["api_key"], _admin["access_token"])

    try:
        if not cors_crud_manager:
            raise HTTPException(status_code=500, detail="CORS service not available")

        result = await cors_crud_manager.refresh_cors_cache()

        return result
    except Exception as e:
        logger.error(f"Failed to refresh CORS cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh CORS cache")
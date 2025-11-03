"""
Admin user management endpoints for SelfDB.

This module provides HTTP endpoints for admin user management operations:
- List users with pagination
- Get user details
- Update user information
- Delete users

Following TDD methodology - minimal implementation to make tests pass.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from shared.models.user import User, UserRole
from .users import UserResponse, ErrorResponse  # Import UserResponse and ErrorResponse from users.py
from shared.auth.auth_endpoints import AuthEndpoints
import logging

# Pydantic models
class UserListResponse(BaseModel):
    users: List[UserResponse]
    pagination: dict

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class UserUpdateRequest(BaseModel):
    """Full admin update model. All fields are optional and only provided fields will be applied.

    Note: password is accepted here for convenience but will be handled via the admin set-password
    flow (hashed and stored separately) to keep password handling explicit and auditable.
    """
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    # Optional admin-provided password; handled separately (not sent to update_user)
    password: Optional[str] = None


class AdminSetPasswordRequest(BaseModel):
    new_password: str


# Configure logging
logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/v1/users", tags=["user-management"])

# Dependencies
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

async def get_current_admin_user(request: Request) -> Dict[str, Any]:
    """Dependency to get current admin user from JWT token."""
    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Bearer token is required"
        )

    access_token = auth_header.split(" ")[1]

    # Get API key from request headers
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="API key is required"
        )

    # Validate token and get user
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
        error = result["error"]
        status_code = 401
        if error["code"] in ["INVALID_TOKEN", "TOKEN_EXPIRED", "TOKEN_BLACKLISTED"]:
            status_code = 401
        elif error["code"] == "USER_NOT_FOUND":
            status_code = 404

        raise HTTPException(
            status_code=status_code,
            detail=error["message"]
        )

    # Check if user is admin
    user = result["user"]
    if user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return user

@router.post("/", response_model=UserResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def create_user(
    request: Request,
    user_data: UserCreateRequest,
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Create a new user (admin only)."""
    try:
        logger.info(f"Admin user {_admin['email']} creating new user {user_data.email}")

        # Get API key from request headers
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="API key is required"
            )

        # Use AuthEndpoints business logic for user creation
        auth_endpoints = get_auth_endpoints()
        if not auth_endpoints:
            raise HTTPException(
                status_code=500,
                detail="AuthEndpoints dependency not available"
            )

        result = await auth_endpoints.register(
            api_key=api_key,
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )

        if not result["success"]:
            # Handle business logic errors
            error = result["error"]
            status_code = 500
            if error["code"] == "INVALID_API_KEY":
                status_code = 401
            elif error["code"] == "USER_ALREADY_EXISTS":
                status_code = 409
            elif error["code"] == "INVALID_DATA":
                status_code = 400

            raise HTTPException(
                status_code=status_code,
                detail=error["message"]
            )

        # Return the created user data
        return result["user"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating user {user_data.email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error creating user"
        )

@router.get("/", response_model=UserListResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def list_users(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    sort: str = "created_at:desc",
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """List users with pagination (admin only)."""
    try:
        logger.info(f"Admin user {_admin['email']} listing users")

        # Get API key from request headers
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="API key is required"
            )

        # Use AuthEndpoints business logic
        auth_endpoints = get_auth_endpoints()
        if not auth_endpoints:
            raise HTTPException(
                status_code=500,
                detail="AuthEndpoints dependency not available"
            )

        result = await auth_endpoints.list_users(
            api_key=api_key,
            limit=limit,
            offset=offset,
            sort=sort,
            filter_role=role,
            filter_active=is_active
        )

        if not result["success"]:
            # Handle business logic errors
            error = result["error"]
            status_code = 500
            if error["code"] == "INVALID_API_KEY":
                status_code = 401

            raise HTTPException(
                status_code=status_code,
                detail=error["message"]
            )

        # Return successful response
        return {
            "users": result["users"],
            "pagination": result["pagination"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing users: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error listing users"
        )

@router.get("/{user_id}", response_model=UserResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_user(
    request: Request,
    user_id: str,
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get user details (admin only)."""
    try:
        logger.info(f"Admin user {_admin['email']} getting user {user_id}")

        # Get API key from request headers
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="API key is required"
            )

        # Use AuthEndpoints business logic
        auth_endpoints = get_auth_endpoints()
        if not auth_endpoints:
            raise HTTPException(
                status_code=500,
                detail="AuthEndpoints dependency not available"
            )

        result = await auth_endpoints.get_user_by_id(
            api_key=api_key,
            user_id=user_id
        )

        if not result["success"]:
            # Handle business logic errors
            error = result["error"]
            status_code = 500
            if error["code"] == "INVALID_API_KEY":
                status_code = 401
            elif error["code"] == "USER_NOT_FOUND":
                status_code = 404

            raise HTTPException(
                status_code=status_code,
                detail=error["message"]
            )

        # Return user data
        return result["user"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error getting user"
        )

@router.put("/{user_id}", response_model=UserResponse, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def update_user(
    request: Request,
    user_id: str,
    update_data: UserUpdateRequest,
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Update user (admin only)."""
    try:
        logger.info(f"Admin user {_admin['email']} updating user {user_id}")

        # Get API key from request headers
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="API key is required"
            )

        # Use the Pydantic model to collect only provided fields. This avoids manual per-field checks
        # and is less error-prone. We handle `password` separately (if provided) by calling the
        # admin password flow; the remaining fields are forwarded to AuthEndpoints.update_user.
        data = update_data.dict(exclude_unset=True)

        # Handle password separately
        password_to_set = None
        if 'password' in data:
            password_to_set = data.pop('password')

        # Convert role enum to its value if present
        if 'role' in data and data['role'] is not None:
            # Pydantic may give an enum; normalize to string
            role_val = data['role'].value if hasattr(data['role'], 'value') else data['role']
            data['role'] = role_val

        updates = data

        if not updates and not password_to_set:
            raise HTTPException(
                status_code=400,
                detail="No fields to update"
            )

        # Use AuthEndpoints business logic
        auth_endpoints = get_auth_endpoints()
        if not auth_endpoints:
            raise HTTPException(
                status_code=500,
                detail="AuthEndpoints dependency not available"
            )

        # First update non-password fields (if any)
        result = None
        if updates:
            result = await auth_endpoints.update_user(
                api_key=api_key,
                user_id=user_id,
                updates=updates
            )

            if not result or not result.get("success"):
                # Handle business logic errors
                error = result["error"] if result else {"code": "UPDATE_FAILED", "message": "Failed to update user"}
                status_code = 500
                if error["code"] == "INVALID_API_KEY":
                    status_code = 401
                elif error["code"] == "USER_NOT_FOUND":
                    status_code = 404
                elif error["code"] == "INVALID_UPDATE":
                    status_code = 400

                raise HTTPException(
                    status_code=status_code,
                    detail=error["message"]
                )

        # If a password was provided, call the admin password setter
        if password_to_set:
            pwd_result = await auth_endpoints.admin_set_user_password(
                api_key=api_key,
                admin_user_id=_admin['id'],
                target_user_id=user_id,
                new_password=password_to_set
            )

            if not pwd_result.get("success"):
                err = pwd_result.get("error", {})
                code = err.get("code")
                if code == "USER_NOT_FOUND":
                    raise HTTPException(status_code=404, detail=err.get("message"))
                if code == "INSUFFICIENT_PRIVILEGES":
                    raise HTTPException(status_code=403, detail=err.get("message"))
                if code == "WEAK_PASSWORD":
                    raise HTTPException(status_code=400, detail=err.get("message"))
                raise HTTPException(status_code=500, detail=err.get("message", "Failed to set password"))

        # Return updated user data
        return result["user"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error updating user"
        )

@router.delete("/{user_id}", response_model=dict, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def delete_user(
    request: Request,
    user_id: str,
    soft_delete: bool = False,  # Changed to False for hard delete
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete user (admin only)."""
    try:
        logger.info(f"Admin user {_admin['email']} deleting user {user_id} (soft={soft_delete})")

        # Get API key from request headers
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="API key is required"
            )

        # Use AuthEndpoints business logic
        auth_endpoints = get_auth_endpoints()
        if not auth_endpoints:
            raise HTTPException(
                status_code=500,
                detail="AuthEndpoints dependency not available"
            )

        result = await auth_endpoints.delete_user(
            api_key=api_key,
            user_id=user_id,
            soft_delete=soft_delete
        )

        if not result["success"]:
            # Handle business logic errors
            error = result["error"]
            status_code = 500
            if error["code"] == "INVALID_API_KEY":
                status_code = 401
            elif error["code"] == "USER_NOT_FOUND":
                status_code = 404

            raise HTTPException(
                status_code=status_code,
                detail=error["message"]
            )

        # Return success response
        return {
            "message": result["message"],
            "user_id": user_id,
            "soft_deleted": result.get("soft_deleted", soft_delete)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error deleting user"
        )


@router.post("/{user_id}/password", response_model=dict, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def set_user_password(
    request: Request,
    user_id: str,
    body: AdminSetPasswordRequest,
    _admin: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Admin-only endpoint to set/reset a user's password."""
    try:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(status_code=400, detail="API key is required")

        auth_endpoints = get_auth_endpoints()
        if not auth_endpoints:
            raise HTTPException(status_code=500, detail="AuthEndpoints dependency not available")

        admin_user = _admin

        result = await auth_endpoints.admin_set_user_password(
            api_key=api_key,
            admin_user_id=admin_user["id"],
            target_user_id=user_id,
            new_password=body.new_password
        )

        if not result.get("success"):
            err = result.get("error", {})
            code = err.get("code")
            if code == "USER_NOT_FOUND":
                raise HTTPException(status_code=404, detail=err.get("message"))
            if code == "INSUFFICIENT_PRIVILEGES":
                raise HTTPException(status_code=403, detail=err.get("message"))
            if code == "WEAK_PASSWORD":
                raise HTTPException(status_code=400, detail=err.get("message"))

            raise HTTPException(status_code=500, detail=err.get("message", "Failed to set password"))

        return {"message": result.get("message", "Password updated")}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error setting password for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error setting password")



"""
User authentication endpoints for SelfDB.

This module provides HTTP endpoints for user authentication operations:
- User registration
- User login
- Token refresh
- User logout
- Get current user

Following TDD methodology - minimal implementation to make tests pass.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Dict, Any
from shared.auth.auth_endpoints import AuthEndpoints
from shared.auth.jwt_service import JWTService
from shared.models.user import User, UserRole
import logging
import re

# Pydantic models for request/response
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength requirements."""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    @field_validator('first_name')
    @classmethod
    def validate_first_name(cls, v):
        """Validate first name contains only letters and spaces."""
        if not re.match(r'^[a-zA-Z\s]+$', v):
            raise ValueError('First name must contain only letters and spaces')
        return v.strip()

    @field_validator('last_name')
    @classmethod
    def validate_last_name(cls, v):
        """Validate last name contains only letters and spaces."""
        if not re.match(r'^[a-zA-Z\s]+$', v):
            raise ValueError('Last name must contain only letters and spaces')
        return v.strip()

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        # Reuse the same strength requirements as registration
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    created_at: str
    updated_at: str
    last_login_at: Optional[str]

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

# Configure logging
logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/auth", tags=["authentication"])

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

@router.post("/register", response_model=TokenResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def register(request_data: UserRegisterRequest, req: Request):
    """Register new user endpoint."""
    try:
        logger.info(f"User registration attempt for email: {request_data.email}")

        # Get API key from request headers
        api_key = req.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="API key is required"
            )

        # Use AuthEndpoints business logic
        auth_endpoints = get_auth_endpoints()
        print(f"Auth endpoints: {auth_endpoints}")
        if not auth_endpoints:
            print("Auth endpoints is None or falsy")
            raise HTTPException(
                status_code=500,
                detail="AuthEndpoints dependency not available"
            )

        result = await auth_endpoints.register(
            api_key=api_key,
            email=request_data.email,
            password=request_data.password,
            first_name=request_data.first_name,
            last_name=request_data.last_name
        )

        if not result["success"]:
            # Handle business logic errors
            error = result["error"]
            status_code = 400
            if error["code"] == "INVALID_API_KEY":
                status_code = 401
            elif error["code"] == "USER_ALREADY_EXISTS":
                status_code = 409
            elif error["code"] == "RATE_LIMIT_EXCEEDED":
                status_code = 429

            raise HTTPException(
                status_code=status_code,
                detail=error["message"]
            )

        # Return successful registration response
        return {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
            "user": result["user"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during registration"
        )

@router.post("/login", response_model=TokenResponse, responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def login(request_data: UserLoginRequest, req: Request):
    """Login user endpoint."""
    try:
        logger.info(f"User login attempt for email: {request_data.email}")

        # Get API key from request headers
        api_key = req.headers.get("X-API-Key")
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

        result = await auth_endpoints.login(
            api_key=api_key,
            email=request_data.email,
            password=request_data.password
        )

        if not result["success"]:
            # Handle business logic errors
            error = result["error"]
            status_code = 401
            if error["code"] == "INVALID_API_KEY":
                status_code = 401
            elif error["code"] == "INVALID_CREDENTIALS":
                status_code = 401
            elif error["code"] == "USER_NOT_FOUND":
                status_code = 401
            elif error["code"] == "USER_INACTIVE":
                status_code = 403
            elif error["code"] == "RATE_LIMIT_EXCEEDED":
                status_code = 429

            raise HTTPException(
                status_code=status_code,
                detail=error["message"]
            )

        # Return successful login response
        return {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
            "user": result["user"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during login"
        )

@router.post("/refresh", response_model=TokenResponse, responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def refresh_token(refresh_request: dict, req: Request):
    """Refresh JWT token endpoint."""
    try:
        logger.info("Token refresh attempt")

        # Get API key from request headers
        api_key = req.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="API key is required"
            )

        refresh_token = refresh_request.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=400,
                detail="Refresh token is required"
            )

        # Use AuthEndpoints business logic
        auth_endpoints = get_auth_endpoints()
        if not auth_endpoints:
            raise HTTPException(
                status_code=500,
                detail="AuthEndpoints dependency not available"
            )

        result = await auth_endpoints.refresh_token(
            api_key=api_key,
            refresh_token=refresh_token
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
            elif error["code"] == "RATE_LIMIT_EXCEEDED":
                status_code = 429

            raise HTTPException(
                status_code=status_code,
                detail=error["message"]
            )

        # Return successful token refresh response
        return {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
            "user": result["user"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during token refresh"
        )

@router.post("/logout", response_model=dict, responses={500: {"model": ErrorResponse}})
async def logout(
    request: Request,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None
):
    """Logout user endpoint."""
    try:
        logger.info("User logout attempt")

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

        result = await auth_endpoints.logout(
            api_key=api_key,
            access_token=access_token,
            refresh_token=refresh_token
        )

        if not result["success"]:
            # Handle business logic errors
            error = result["error"]
            status_code = 500
            if error["code"] == "INVALID_API_KEY":
                status_code = 401
            elif error["code"] == "INVALID_TOKEN":
                status_code = 401
            elif error["code"] == "TOKEN_EXPIRED":
                status_code = 401

            raise HTTPException(
                status_code=status_code,
                detail=error["message"]
            )

        # Return successful logout response
        return {
            "message": "Successfully logged out",
            "access_token_blacklisted": result.get("access_token_blacklisted", False),
            "refresh_token_blacklisted": result.get("refresh_token_blacklisted", False)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during logout: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during logout"
        )


@router.post("/change-password", response_model=dict, responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def change_password(request_data: ChangePasswordRequest, request: Request):
    """Authenticated endpoint for users to change their own password."""
    try:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(status_code=400, detail="API key is required")

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Bearer token is required")

        access_token = auth_header.split(" ")[1]

        auth_endpoints = get_auth_endpoints()
        if not auth_endpoints:
            raise HTTPException(status_code=500, detail="AuthEndpoints dependency not available")

        # Validate token and get current user
        result = await auth_endpoints.get_current_user(api_key=api_key, access_token=access_token)
        if not result["success"]:
            error = result["error"]
            status_code = 401
            if error.get("code") == "USER_NOT_FOUND":
                status_code = 404
            raise HTTPException(status_code=status_code, detail=error.get("message"))

        user = result["user"]

        # Call business logic
        res = await auth_endpoints.change_password(
            api_key=api_key,
            user_id=user["id"],
            current_password=request_data.current_password,
            new_password=request_data.new_password
        )

        if not res.get("success"):
            err = res.get("error", {})
            code = err.get("code")
            if code == "INVALID_CURRENT_PASSWORD":
                raise HTTPException(status_code=401, detail=err.get("message"))
            if code == "WEAK_PASSWORD":
                raise HTTPException(status_code=400, detail=err.get("message"))
            if code == "USER_NOT_FOUND":
                raise HTTPException(status_code=404, detail=err.get("message"))

            raise HTTPException(status_code=500, detail=err.get("message", "Failed to change password"))

        return {"message": res.get("message", "Password changed")}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during password change: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during password change")

@router.get("/me", response_model=UserResponse, responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_current_user(request: Request):
    """Get current user endpoint."""
    try:
        logger.info("Get current user attempt")

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

        # Return user data
        return result["user"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting current user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error getting current user"
        )


@router.get('/me/api-key', response_model=dict, responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_api_key_for_admin(request: Request):
    """Return the configured API key to authenticated admin users.

    This endpoint requires a valid Bearer token and X-API-Key header, and will
    verify that the authenticated user is active and has role 'ADMIN'. It returns
    JSON: {"api_key": <string|null>}.
    """
    try:
        # Validate that the request contains the required headers
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            raise HTTPException(status_code=400, detail='API key is required')

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(status_code=401, detail='Bearer token is required')

        access_token = auth_header.split(' ')[1]

        auth_endpoints = get_auth_endpoints()
        if not auth_endpoints:
            raise HTTPException(status_code=500, detail='AuthEndpoints dependency not available')

        # Reuse get_current_user logic to validate token and get the user
        result = await auth_endpoints.get_current_user(api_key=api_key, access_token=access_token)
        if not result['success']:
            error = result['error']
            status_code = 401
            if error.get('code') == 'USER_NOT_FOUND':
                status_code = 404
            raise HTTPException(status_code=status_code, detail=error.get('message'))

        user = result['user']
        # Ensure user is active and has ADMIN role
        if not user.get('is_active') or user.get('role') != 'ADMIN':
            raise HTTPException(status_code=403, detail='Admin access required')

        # Read configured API key from AuthEndpoints instance (it stores api_key on init)
        api_key_value = getattr(auth_endpoints, 'api_key', None)

        return {'api_key': api_key_value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Unexpected error getting api key: {str(e)}')
        raise HTTPException(status_code=500, detail='Internal server error getting api key')
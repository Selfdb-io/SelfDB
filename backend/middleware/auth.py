"""
Combined authentication middleware for FastAPI endpoints.
Supports both API key and JWT token authentication.
"""

import os
import jwt
import logging
import uuid
from typing import Optional, List, Callable
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

# Import existing auth components
try:
    # Docker environment (relative import)
    from shared.auth.api_key_middleware import APIKeyMiddleware
    from shared.auth.jwt_service import JWTService
except ImportError:
    # Local environment (absolute import)
    from shared.auth.api_key_middleware import APIKeyMiddleware
    from shared.auth.jwt_service import JWTService

logger = logging.getLogger(__name__)


class CombinedAuthMiddleware(BaseHTTPMiddleware):
    """
    Combined authentication middleware that supports both API keys and JWT tokens.
    
    Authentication methods (in order of preference):
    1. JWT token in Authorization header (Bearer token)
    2. API key in x-api-key header
    """
    
    def __init__(
        self,
        app,
        exclude_paths: Optional[List[str]] = None,
        api_key: Optional[str] = None,
        jwt_secret_key: Optional[str] = None
    ):
        """
        Initialize combined authentication middleware.
        
        Args:
            app: FastAPI application
            exclude_paths: Paths that bypass authentication (e.g., /health)
            api_key: Valid API key (if None, loads from API_KEY env var)
            jwt_secret_key: JWT secret key (if None, loads from JWT_SECRET_KEY env var)
        """
        super().__init__(app)
        
        # Set up excluded paths (health endpoints don't need auth)
        self.exclude_paths = exclude_paths or ["/health", "/", "/docs", "/redoc", "/openapi.json", "/api/v1/status"]
        
        # Initialize API key validation
        self.api_key = api_key or os.environ.get("API_KEY")
        if not self.api_key:
            logger.warning("API_KEY not configured - API key authentication disabled")
        
        # Initialize JWT service
        jwt_secret = jwt_secret_key or os.environ.get("JWT_SECRET_KEY")
        if jwt_secret:
            # Use JWTService.from_environment() to get all settings from env vars
            self.jwt_service = JWTService.from_environment()
        else:
            self.jwt_service = None
            logger.warning("JWT_SECRET_KEY not configured - JWT authentication disabled")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and validate authentication."""
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Skip authentication for WebSocket connections
        # WebSocket authentication is handled in the WebSocket endpoint itself
        if request.url.path.startswith("/api/v1/realtime/ws"):
            logger.debug(f"Request {request_id} to {request.url.path} - WebSocket connection, skipping auth middleware")
            return await call_next(request)
        
        # Check if path is excluded from authentication
        # Only exclude webhook reception endpoints (ingest), not webhook CRUD endpoints
        is_webhook_ingest = (
            request.url.path.startswith("/api/v1/webhooks/ingest/")
        )
        
        if request.url.path in self.exclude_paths or is_webhook_ingest:
            logger.debug(f"Request {request_id} to {request.url.path} - excluded from auth")
            return await call_next(request)
        
        # Check for JWT token first (preferred method)
        auth_result = await self._check_jwt_token(request, request_id)
        if auth_result:
            if auth_result["valid"]:
                # JWT token is valid, set user context and proceed
                request.state.user_id = auth_result.get("user_id")
                request.state.user_role = auth_result.get("role")
                request.state.auth_method = "jwt"
                logger.info(f"Request {request_id} authenticated via JWT for user {auth_result.get('user_id')}")
                return await call_next(request)
            else:
                # JWT token is present but invalid
                return self._create_error_response(
                    code="INVALID_JWT_TOKEN",
                    message=auth_result["error"],
                    request_id=request_id
                )
        
        # If no JWT token, check for API key
        auth_result = self._check_api_key(request, request_id)
        if auth_result:
            if auth_result["valid"]:
                # API key is valid, proceed
                request.state.auth_method = "api_key"
                logger.info(f"Request {request_id} authenticated via API key")
                return await call_next(request)
            else:
                # API key is present but invalid
                return self._create_error_response(
                    code="INVALID_API_KEY", 
                    message=auth_result["error"],
                    request_id=request_id
                )
        
        # No valid authentication found
        logger.warning(f"Request {request_id} to {request.url.path} - no valid authentication")
        return self._create_error_response(
            code="INVALID_API_KEY",
            message="API key is missing",
            request_id=request_id
        )
    
    async def _check_jwt_token(self, request: Request, request_id: str) -> Optional[dict]:
        """
        Check for JWT token in Authorization header.
        
        Returns:
            dict with validation result or None if no token present
        """
        if not self.jwt_service:
            return None
        
        # Look for Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None
        
        # Extract Bearer token
        if not auth_header.startswith("Bearer "):
            return {"valid": False, "error": "Invalid Authorization header format"}
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            # Validate JWT token using direct JWT decode to catch specific exceptions
            payload = jwt.decode(
                token,
                self.jwt_service.secret_key,
                algorithms=[self.jwt_service.algorithm],
                issuer=self.jwt_service.issuer
            )
            
            # Check token type
            if payload.get("token_type") != "access":
                return {"valid": False, "error": "Invalid JWT token type"}
            
            return {
                "valid": True,
                "user_id": payload.get("user_id"),
                "role": payload.get("role", "USER")
            }
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "JWT token has expired"}
        except jwt.InvalidTokenError:
            return {"valid": False, "error": "Invalid JWT token"}
        except Exception as e:
            logger.error(f"JWT validation error for request {request_id}: {e}")
            return {"valid": False, "error": "JWT token validation failed"}
    
    def _check_api_key(self, request: Request, request_id: str) -> Optional[dict]:
        """
        Check for API key in x-api-key header.
        
        Returns:
            dict with validation result or None if no key present
        """
        if not self.api_key:
            return None
        
        # Extract API key from header (case-insensitive)
        api_key = None
        for header_name, header_value in request.headers.items():
            if header_name.lower() == "x-api-key":
                api_key = header_value
                break
        
        if not api_key:
            return None
        
        # Validate API key
        if api_key == self.api_key:
            return {"valid": True}
        else:
            return {"valid": False, "error": "Provided API key is invalid"}
    
    def _create_error_response(
        self,
        code: str,
        message: str,
        request_id: str,
        status_code: int = 401
    ) -> JSONResponse:
        """
        Create a standardized error response.
        
        Args:
            code: Error code
            message: Error message
            request_id: Request ID for tracking
            status_code: HTTP status code
            
        Returns:
            JSONResponse with error details
        """
        error_body = {
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id
            }
        }
        
        response = JSONResponse(
            content=error_body,
            status_code=status_code,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "x-api-key, Authorization, Content-Type",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS"
            }
        )
        
        return response
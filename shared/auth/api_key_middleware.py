"""
API Key validation middleware for SelfDB.

This middleware validates API keys in the x-api-key header for all requests.
"""

import os
import json
import logging
import uuid
from typing import Optional, List, Union, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse


logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API keys in requests."""
    
    def __init__(
        self,
        app: Optional[Callable] = None,
        api_key: Optional[Union[str, List[str]]] = None,
        exclude_paths: Optional[List[str]] = None,
        allow_query_param: bool = False,
        enable_rate_limit_tracking: bool = False
    ):
        """
        Initialize API Key middleware.
        
        Args:
            app: The ASGI application (for middleware)
            api_key: Valid API key(s). If None, loads from API_KEY env var
            exclude_paths: Paths that bypass API key validation
            allow_query_param: Allow API key in query params as fallback
            enable_rate_limit_tracking: Track API key usage for rate limiting
        """
        if app:
            super().__init__(app)
        
        # Load API key from environment if not provided
        if api_key is None:
            api_key = os.environ.get("API_KEY")
            if not api_key:
                raise ValueError("API_KEY must be configured")
        
        # Support multiple API keys
        self.api_keys = api_key if isinstance(api_key, list) else [api_key]
        self.exclude_paths = exclude_paths or []
        self.allow_query_param = allow_query_param
        self.enable_rate_limit_tracking = enable_rate_limit_tracking
        self.usage_count = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and validate API key."""
        return await self(request, call_next)
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        Validate API key in the request.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint
            
        Returns:
            Response object
        """
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Check if path is excluded from validation
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Extract API key from header (case-insensitive)
        api_key = None
        for header_name, header_value in request.headers.items():
            if header_name.lower() == "x-api-key":
                api_key = header_value
                break
        
        # Fallback to query parameter if allowed
        if not api_key and self.allow_query_param:
            query_params = getattr(request, 'query_params', {})
            api_key = query_params.get('api_key')
        
        # Validate API key
        if not api_key:
            logger.warning(f"Missing API key for request {request_id} to {request.url.path}")
            return self._create_error_response(
                code="INVALID_API_KEY",
                message="API key is missing",
                request_id=request_id
            )
        
        if api_key not in self.api_keys:
            logger.warning(f"Invalid API key attempt for request {request_id} to {request.url.path}")
            return self._create_error_response(
                code="INVALID_API_KEY",
                message="Provided API key is invalid",
                request_id=request_id
            )
        
        # Track usage if enabled
        if self.enable_rate_limit_tracking:
            if api_key not in self.usage_count:
                self.usage_count[api_key] = 0
            self.usage_count[api_key] += 1
            request.state.api_key_usage_count = self.usage_count[api_key]
        
        # API key is valid, proceed to next middleware/endpoint
        logger.info(f"Valid API key for request {request_id} to {request.url.path}")
        return await call_next(request)
    
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
                "Access-Control-Allow-Headers": "x-api-key, Content-Type",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS"
            }
        )
        
        return response
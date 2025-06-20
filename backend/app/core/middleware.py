from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class AnonKeyEnforcerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log CORS headers for debugging
        origin = request.headers.get("origin")
        logger.debug(f"CORS Origin: {origin}")

        # Allow preflight OPTIONS requests to pass through
        if request.method == "OPTIONS":
            response = await call_next(request)
            return response

        # Allow public access to docs and openapi routes
        public_paths = [
            "/docs", "/redoc", "/openapi.json", "/docs/", "/redoc/", "/openapi.json/",
            "/api/v1/openapi.json", "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json/", "/api/v1/docs/", "/api/v1/redoc/"
        ]
        if request.url.path in public_paths or request.url.path.startswith("/static/"):
            return await call_next(request)

        # Check for anon-key in headers (case-insensitive)
        anon_key = request.headers.get("apikey") or request.headers.get("anon-key")
        # Also allow anon-key as a query param for flexibility
        if not anon_key:
            anon_key = request.query_params.get("apikey") or request.query_params.get("anon-key")

        # If anon-key is required, enforce it
        if settings.ANON_KEY:
            if not anon_key or anon_key != settings.ANON_KEY:
                logger.warning(f"Missing or invalid anon-key: {anon_key}")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Missing or invalid anon-key. Every request must include a valid anon-key in the header or query params."}
                )
        # If anon-key is not set in config, allow all requests (for dev)
        response = await call_next(request)
        return response 
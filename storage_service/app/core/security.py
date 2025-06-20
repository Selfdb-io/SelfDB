import logging
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(request: Request, api_key: str = Depends(api_key_header)):
    """
    Verify the API key for internal authentication between services.
    This ensures only the main backend can access the storage service.
    """
    if api_key is None:
        logger.warning(f"API key missing in request from {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
        )
    
    if api_key != settings.STORAGE_SERVICE_API_KEY:
        logger.warning(f"Invalid API key in request from {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return True

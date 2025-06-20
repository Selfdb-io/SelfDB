from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from ..deps import get_db # Import the DB dependency

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Set basic logging level

# Create an API router instance
router = APIRouter()

@router.get("/health", summary="Check API Health", status_code=200)
async def health_check():
    """
    Simple health check endpoint to confirm the API service is running.
    """
    logger.info("Health check endpoint called")
    return {"status": "ok", "message": "API is running"}

@router.get("/health/db", summary="Check Database Connectivity", status_code=200)
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """
    Checks if the API can successfully connect to the database
    by executing a simple query.
    """
    logger.info("Database health check endpoint called")
    try:
        # Execute a simple query to test the connection
        result = await db.execute(text("SELECT 1"))
        if result.scalar_one() == 1:
            logger.info("Database connection successful")
            return {"status": "ok", "message": "Database connection successful"}
        else:
            # This case should ideally not happen if execute succeeds
            logger.error("Database connection test failed: Unexpected result from 'SELECT 1'")
            raise HTTPException(status_code=503, detail="Database connection test failed: Unexpected result")
    except Exception as e:
        logger.error(f"Database connection error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Database connection error: {e}")

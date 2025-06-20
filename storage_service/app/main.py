from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import sys

from .core.config import settings
from .apis.endpoints import buckets, files as files_router_module # Rename to avoid conflict

# --- Root Logger Configuration ---
# Clear any existing handlers on the root logger
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Configure basicConfig for the root logger first
logging.basicConfig(
    level=logging.DEBUG,  # Set root level to DEBUG
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs go to console
    ],
    force=True # Override any default Uvicorn or library configurations
)

# --- Specific Logger Configurations ---
# Get loggers and set their levels explicitly. This ensures they don't get silenced.
main_logger = logging.getLogger(__name__) # For app.main
files_endpoint_logger = logging.getLogger("app.apis.endpoints.files") # For storage_service files.py

main_logger.setLevel(logging.DEBUG)
files_endpoint_logger.setLevel(logging.DEBUG)

# If using Uvicorn's access logs, you might want to control its logger too
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.setLevel(logging.INFO) # Or DEBUG if you want its detailed access logs
# Prevent uvicorn access logs from propagating to the root logger if you want to separate them
# uvicorn_access_logger.propagate = False 


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FastAPI-based file storage service for SelfDB",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this should be restricted
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(buckets.router, prefix="/buckets", tags=["Buckets"])
app.include_router(files_router_module.router, prefix="/files", tags=["Files"])

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Simple health check endpoint.
    """
    main_logger.info("Health check endpoint called")
    return {"status": "healthy"}

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    """
    main_logger.info("Root endpoint called")
    return {
        "message": "Welcome to SelfDB Storage Service",
        "docs_url": "/docs",
    }

# Ensure storage directory exists
@app.on_event("startup")
async def startup_event():
    main_logger.info(f"Storage service starting up. Storage path: {settings.STORAGE_PATH}")
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    main_logger.info("Storage service startup complete")

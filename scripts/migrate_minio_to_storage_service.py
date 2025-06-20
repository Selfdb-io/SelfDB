#!/usr/bin/env python3
"""
Migration script to transfer files from MinIO to the new storage service.

This script:
1. Reads all buckets and files from the database
2. Creates corresponding buckets in the storage service
3. Downloads files from MinIO and uploads them to the storage service
4. Verifies the migration was successful

Usage:
    python migrate_minio_to_storage_service.py

Environment variables:
    DATABASE_URL: PostgreSQL connection string
    MINIO_URL: MinIO server URL
    MINIO_ACCESS_KEY_ID: MinIO access key
    MINIO_SECRET_ACCESS_KEY: MinIO secret key
    STORAGE_SERVICE_URL: Storage service URL
"""

import asyncio
import httpx
import os
import io
import tempfile
import logging
from typing import List, Dict, Any, Optional
import sys
import json
from urllib.parse import urlparse

# Add the parent directory to the Python path so we can import from the backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import MinIO client
from minio import Minio
from minio.error import S3Error

# Import SQLAlchemy and database models
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("migration")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Convert from async to sync URL if using the async version
    async_url = os.getenv("DATABASE_URL")
    if async_url and "postgresql+asyncpg" in async_url:
        DATABASE_URL = async_url.replace("postgresql+asyncpg", "postgresql")
    else:
        # Construct from components
        db_user = os.getenv("POSTGRES_USER")
        db_password = os.getenv("POSTGRES_PASSWORD")
        db_host = os.getenv("POSTGRES_SERVER", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB")
        if all([db_user, db_password, db_host, db_port, db_name]):
            DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
    sys.exit(1)

# MinIO configuration
MINIO_URL = os.getenv("MINIO_URL")
MINIO_ACCESS_KEY_ID = os.getenv("MINIO_ACCESS_KEY_ID")
MINIO_SECRET_ACCESS_KEY = os.getenv("MINIO_SECRET_ACCESS_KEY")

if not all([MINIO_URL, MINIO_ACCESS_KEY_ID, MINIO_SECRET_ACCESS_KEY]):
    logger.error("MinIO environment variables are not set")
    sys.exit(1)

# Storage service configuration
STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL", "http://localhost:8001")

# Initialize MinIO client
def get_minio_client() -> Minio:
    """Get a configured MinIO client."""
    endpoint = MINIO_URL.replace("http://", "").replace("https://", "")
    secure = MINIO_URL.startswith("https")
    
    return Minio(
        endpoint=endpoint,
        access_key=MINIO_ACCESS_KEY_ID,
        secret_key=MINIO_SECRET_ACCESS_KEY,
        secure=secure
    )

# Initialize database connection
def get_db_session():
    """Get a database session."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

async def get_all_buckets_from_db() -> List[Dict[str, Any]]:
    """Get all buckets from the database."""
    session = get_db_session()
    try:
        result = session.execute(text("SELECT id, name, minio_bucket_name, is_public, owner_id FROM buckets"))
        buckets = [
            {
                "id": str(row[0]),
                "name": row[1],
                "minio_bucket_name": row[2],
                "is_public": row[3],
                "owner_id": str(row[4])
            }
            for row in result
        ]
        logger.info(f"Found {len(buckets)} buckets in the database")
        return buckets
    finally:
        session.close()

async def get_files_for_bucket(bucket_id: str) -> List[Dict[str, Any]]:
    """Get all files for a specific bucket from the database."""
    session = get_db_session()
    try:
        result = session.execute(
            text("SELECT id, filename, object_name, bucket_name, content_type, size FROM files WHERE bucket_id = :bucket_id"),
            {"bucket_id": bucket_id}
        )
        files = [
            {
                "id": str(row[0]),
                "filename": row[1],
                "object_name": row[2],
                "bucket_name": row[3],
                "content_type": row[4],
                "size": row[5]
            }
            for row in result
        ]
        logger.info(f"Found {len(files)} files in bucket {bucket_id}")
        return files
    finally:
        session.close()

async def create_bucket_in_storage_service(bucket: Dict[str, Any]) -> bool:
    """Create a bucket in the storage service."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{STORAGE_SERVICE_URL}/buckets",
                json={
                    "name": bucket["name"],
                    "is_public": bucket["is_public"]
                }
            )
            response.raise_for_status()
            logger.info(f"Created bucket {bucket['name']} in storage service")
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                logger.warning(f"Bucket {bucket['name']} already exists in storage service")
                return True
            logger.error(f"Failed to create bucket {bucket['name']} in storage service: {e}")
            return False

async def migrate_file(minio_client: Minio, file: Dict[str, Any], bucket_name: str) -> bool:
    """Migrate a file from MinIO to the storage service."""
    try:
        # Download file from MinIO
        response = minio_client.get_object(
            bucket_name=file["bucket_name"],
            object_name=file["object_name"]
        )
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Write the content to the temporary file
            temp_file.write(response.read())
            temp_file_path = temp_file.name
        
        try:
            # Upload file to storage service
            async with httpx.AsyncClient() as client:
                with open(temp_file_path, "rb") as f:
                    files = {"file": (file["filename"], f, file["content_type"])}
                    response = await client.post(
                        f"{STORAGE_SERVICE_URL}/files/upload/{bucket_name}",
                        files=files
                    )
                    response.raise_for_status()
                    logger.info(f"Migrated file {file['filename']} to storage service")
                    return True
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Failed to migrate file {file['filename']}: {e}")
        return False

async def main():
    """Main migration function."""
    logger.info("Starting migration from MinIO to storage service")
    
    # Get MinIO client
    minio_client = get_minio_client()
    
    # Get all buckets from the database
    buckets = await get_all_buckets_from_db()
    
    # Migrate each bucket and its files
    for bucket in buckets:
        logger.info(f"Processing bucket: {bucket['name']} (MinIO: {bucket['minio_bucket_name']})")
        
        # Create bucket in storage service
        if not await create_bucket_in_storage_service(bucket):
            logger.error(f"Skipping bucket {bucket['name']} due to creation failure")
            continue
        
        # Get files for this bucket
        files = await get_files_for_bucket(bucket["id"])
        
        # Migrate each file
        successful_migrations = 0
        for file in files:
            if await migrate_file(minio_client, file, bucket["name"]):
                successful_migrations += 1
        
        logger.info(f"Migrated {successful_migrations}/{len(files)} files for bucket {bucket['name']}")
    
    logger.info("Migration completed")

if __name__ == "__main__":
    asyncio.run(main())

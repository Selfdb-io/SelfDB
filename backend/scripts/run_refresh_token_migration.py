#!/usr/bin/env python
"""
Script to apply the refresh token migration.
"""
import os
import asyncio
import logging
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

async def run_migration():
    """Run the refresh token migration script."""
    # Get database connection parameters from environment variables
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_name = os.getenv("POSTGRES_DB")
    db_host = os.getenv("POSTGRES_SERVER", "postgres")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    
    if not all([db_user, db_password, db_name]):
        logger.error("Missing required database environment variables.")
        return
    
    try:
        # Connect to the database
        conn = await asyncpg.connect(
            user=db_user,
            password=db_password,
            database=db_name,
            host=db_host,
            port=db_port
        )
        
        logger.info("Connected to database. Running migration script...")
        
        # Read the migration SQL script
        migration_path = Path(__file__).parent.parent / "migrations" / "add_refresh_tokens_table.sql"
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        # Execute the migration SQL
        await conn.execute(migration_sql)
        
        logger.info("Migration completed successfully.")
        
        # Close the connection
        await conn.close()
        
    except Exception as e:
        logger.error(f"Error running migration: {e}")

if __name__ == "__main__":
    asyncio.run(run_migration()) 
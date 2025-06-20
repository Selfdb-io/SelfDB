"""
Test environment setup module.
This module sets up the necessary environment for testing the storage service.
"""
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to allow importing from app
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Set required environment variables for testing
os.environ["STORAGE_SERVICE_API_KEY"] = "test-api-key"
os.environ["STORAGE_BASE_PATH"] = "/tmp/selfdb-test-storage"

# Create the storage directory if it doesn't exist
Path(os.environ["STORAGE_BASE_PATH"]).mkdir(parents=True, exist_ok=True)

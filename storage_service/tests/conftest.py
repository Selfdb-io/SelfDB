# Import test environment setup first to set environment variables
from tests.test_env import *

import os
import shutil
import pytest
import tempfile
import asyncio
from fastapi.testclient import TestClient
from pathlib import Path

# Import app and settings after environment setup
from app.main import app
from app.core.config import settings
from app.core.storage import storage
from app.core.optimized_storage import optimized_storage


@pytest.fixture(scope="session")
def test_storage_dir():
    """Create a temporary directory for test storage"""
    temp_dir = tempfile.mkdtemp()
    os.environ["STORAGE_BASE_PATH"] = temp_dir
    yield temp_dir
    # Clean up after tests
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_client(test_storage_dir):
    """Create a test client with a temporary storage directory"""
    # Override the storage path for testing
    settings.STORAGE_BASE_PATH = test_storage_dir
    storage.base_path = Path(test_storage_dir)
    optimized_storage.base_path = Path(test_storage_dir)
    
    # Create a test client
    with TestClient(app) as client:
        # Set the API key for authentication
        client.headers.update({"X-API-Key": os.environ["STORAGE_SERVICE_API_KEY"]})
        yield client


@pytest.fixture
def test_bucket_name():
    """Return a test bucket name"""
    return "test-bucket"


@pytest.fixture
def create_test_bucket(test_client, test_bucket_name):
    """Create a test bucket"""
    response = test_client.post(f"/buckets/{test_bucket_name}")
    assert response.status_code == 201
    return test_bucket_name


@pytest.fixture
def create_test_file(tmp_path):
    """Create a test file with specified size in MB"""
    def _create_file(size_mb=1):
        file_path = tmp_path / f"test_file_{size_mb}mb.bin"
        # Create a file with the specified size
        with open(file_path, "wb") as f:
            f.write(os.urandom(size_mb * 1024 * 1024))
        return file_path
    
    return _create_file


@pytest.fixture
def create_large_test_file(tmp_path):
    """Create a large test file (100MB) for testing large uploads"""
    file_path = tmp_path / "large_test_file.bin"
    # Create a 100MB file - but use a smaller size for CI testing
    chunk_size = 1024 * 1024  # 1MB
    size_mb = 20  # Use 20MB instead of 100MB for faster tests
    with open(file_path, "wb") as f:
        for _ in range(size_mb):
            f.write(os.urandom(chunk_size))
    return file_path


# Add event loop fixture for asyncio tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

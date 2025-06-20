# Import test environment setup first
from tests.test_env import *

import os
import time
import pytest
import asyncio
from fastapi import UploadFile
from pathlib import Path
import httpx
import aiofiles
from io import BytesIO

# Import after environment setup
from app.core.storage import FileStorage
from app.core.optimized_storage import OptimizedFileStorage


class TestLargeFileOperations:
    """Tests for large file operations in the storage service"""
    
    def test_bucket_operations(self, test_client, test_bucket_name):
        """Test basic bucket operations"""
        # Create bucket
        response = test_client.post(f"/buckets/{test_bucket_name}")
        assert response.status_code == 201
        
        # Check if bucket exists
        response = test_client.get(f"/buckets/{test_bucket_name}/exists")
        assert response.status_code == 200
        assert response.json()["exists"] is True
        
        # Delete bucket
        response = test_client.delete(f"/buckets/{test_bucket_name}")
        assert response.status_code == 200
        
        # Verify bucket no longer exists
        response = test_client.get(f"/buckets/{test_bucket_name}/exists")
        assert response.status_code == 200
        assert response.json()["exists"] is False
    
    def test_upload_small_file(self, test_client, create_test_bucket, create_test_file):
        """Test uploading a small file (1MB)"""
        bucket_name = create_test_bucket
        file_path = create_test_file(1)  # 1MB file
        object_path = "test/small_file.bin"
        
        # Upload file
        with open(file_path, "rb") as f:
            response = test_client.post(
                f"/buckets/{bucket_name}/objects",
                params={"object_path": object_path},
                files={"file": ("small_file.bin", f, "application/octet-stream")}
            )
        
        assert response.status_code == 201
        result = response.json()
        assert result["bucket_name"] == bucket_name
        assert result["object_path"] == object_path
        assert result["size"] == os.path.getsize(file_path)
    
    def test_upload_medium_file(self, test_client, create_test_bucket, create_test_file):
        """Test uploading a medium file (10MB)"""
        bucket_name = create_test_bucket
        file_path = create_test_file(10)  # 10MB file
        object_path = "test/medium_file.bin"
        
        # Upload file
        with open(file_path, "rb") as f:
            response = test_client.post(
                f"/buckets/{bucket_name}/objects",
                params={"object_path": object_path},
                files={"file": ("medium_file.bin", f, "application/octet-stream")}
            )
        
        assert response.status_code == 201
        result = response.json()
        assert result["bucket_name"] == bucket_name
        assert result["object_path"] == object_path
        assert result["size"] == os.path.getsize(file_path)
    
    def test_upload_large_file(self, test_client, create_test_bucket, create_large_test_file):
        """Test uploading a large file (100MB)"""
        bucket_name = create_test_bucket
        file_path = create_large_test_file
        object_path = "test/large_file.bin"
        
        # Upload file
        with open(file_path, "rb") as f:
            response = test_client.post(
                f"/buckets/{bucket_name}/objects",
                params={"object_path": object_path},
                files={"file": ("large_file.bin", f, "application/octet-stream")}
            )
        
        assert response.status_code == 201
        result = response.json()
        assert result["bucket_name"] == bucket_name
        assert result["object_path"] == object_path
        assert result["size"] == os.path.getsize(file_path)
    
    def test_download_response_time(self, test_client, create_test_bucket, create_test_file):
        """Test that download requests start within 100ms"""
        bucket_name = create_test_bucket
        file_path = create_test_file(10)  # 10MB file
        object_path = "test/response_time_test.bin"
        
        # Upload file first
        with open(file_path, "rb") as f:
            response = test_client.post(
                f"/buckets/{bucket_name}/objects",
                params={"object_path": object_path},
                files={"file": ("response_time_test.bin", f, "application/octet-stream")}
            )
        assert response.status_code == 201
        
        # Test download response time
        start_time = time.time()
        with test_client.stream("GET", f"/buckets/{bucket_name}/objects/{object_path}") as response:
            # We only care about the time to first byte
            first_chunk = next(response.iter_bytes(chunk_size=8192))
            response_time = time.time() - start_time
            
        # Assert response starts within 100ms
        assert response_time < 0.1, f"Download response time was {response_time*1000:.2f}ms, which exceeds the 100ms requirement"
        assert len(first_chunk) > 0
    
    def test_head_object_response_time(self, test_client, create_test_bucket, create_test_file):
        """Test that HEAD requests for object metadata are fast (< 100ms)"""
        bucket_name = create_test_bucket
        file_path = create_test_file(5)  # 5MB file
        object_path = "test/head_response_test.bin"
        
        # Upload file first
        with open(file_path, "rb") as f:
            response = test_client.post(
                f"/buckets/{bucket_name}/objects",
                params={"object_path": object_path},
                files={"file": ("head_response_test.bin", f, "application/octet-stream")}
            )
        assert response.status_code == 201
        
        # Test HEAD response time
        start_time = time.time()
        response = test_client.head(f"/buckets/{bucket_name}/objects/{object_path}")
        response_time = time.time() - start_time
        
        # Assert response is within 100ms
        assert response_time < 0.1, f"HEAD response time was {response_time*1000:.2f}ms, which exceeds the 100ms requirement"
        assert response.status_code == 200


class TestStreamingOperations:
    """Tests for streaming file operations"""
    
    @pytest.mark.asyncio
    async def test_streaming_upload_large_file(self, test_storage_dir, test_bucket_name):
        """Test streaming upload of a large file"""
        # Initialize storage directly
        storage = FileStorage(base_path=test_storage_dir)
        
        # Create bucket
        await storage.create_bucket(test_bucket_name)
        
        # Create a large memory file (50MB)
        file_size = 50 * 1024 * 1024  # 50MB
        content = os.urandom(file_size)
        file_obj = BytesIO(content)
        
        # Create a mock UploadFile
        class MockUploadFile:
            async def read(self, size=-1):
                return file_obj.read(size)
                
            async def seek(self, offset):
                file_obj.seek(offset)
                
            @property
            def content_type(self):
                return "application/octet-stream"
                
        mock_file = MockUploadFile()
        object_path = "test/streaming_large_file.bin"
        
        # Test streaming upload
        result = await storage.save_object_streaming(
            bucket_name=test_bucket_name,
            object_path=object_path,
            file=mock_file,
            content_type="application/octet-stream"
        )
        
        # Verify file was saved correctly
        object_fs_path = storage._get_object_path(test_bucket_name, object_path)
        assert object_fs_path.exists()
        assert object_fs_path.stat().st_size == file_size
        
        # Verify result contains correct metadata
        assert result["size"] == file_size
        assert result["bucket_name"] == test_bucket_name
        assert result["object_path"] == object_path
    
    @pytest.mark.asyncio
    async def test_streaming_download_response_time(self, test_storage_dir, test_bucket_name):
        """Test that streaming download starts quickly"""
        # Initialize storage directly
        storage = FileStorage(base_path=test_storage_dir)
        
        # Create bucket
        await storage.create_bucket(test_bucket_name)
        
        # Create a test file (10MB)
        file_size = 10 * 1024 * 1024  # 10MB
        content = os.urandom(file_size)
        object_path = "test/streaming_download_test.bin"
        
        # Save the file directly
        await storage.save_object(
            bucket_name=test_bucket_name,
            object_path=object_path,
            content=content,
            content_type="application/octet-stream"
        )
        
        # Test streaming download response time
        start_time = time.time()
        generator = storage.get_object_stream(test_bucket_name, object_path)
        
        # Get first chunk
        first_chunk = await anext(generator)
        response_time = time.time() - start_time
        
        # Assert response starts within 100ms
        assert response_time < 0.1, f"Streaming download response time was {response_time*1000:.2f}ms, which exceeds the 100ms requirement"
        assert len(first_chunk) > 0


class TestConcurrentOperations:
    """Tests for concurrent file operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_uploads(self, test_storage_dir, test_bucket_name):
        """Test multiple concurrent uploads"""
        # Initialize storage directly
        storage = FileStorage(base_path=test_storage_dir)
        
        # Create bucket
        await storage.create_bucket(test_bucket_name)
        
        # Create 5 test files (5MB each)
        file_size = 5 * 1024 * 1024  # 5MB
        files = []
        for i in range(5):
            content = os.urandom(file_size)
            files.append((f"test/concurrent_file_{i}.bin", content))
        
        # Upload files concurrently
        async def upload_file(object_path, content):
            return await storage.save_object(
                bucket_name=test_bucket_name,
                object_path=object_path,
                content=content,
                content_type="application/octet-stream"
            )
        
        # Run uploads concurrently
        tasks = [upload_file(path, content) for path, content in files]
        results = await asyncio.gather(*tasks)
        
        # Verify all uploads succeeded
        for i, result in enumerate(results):
            assert result["size"] == file_size
            assert result["bucket_name"] == test_bucket_name
            assert result["object_path"] == files[i][0]
    
    @pytest.mark.asyncio
    async def test_concurrent_downloads(self, test_storage_dir, test_bucket_name):
        """Test multiple concurrent downloads"""
        # Initialize storage directly
        storage = FileStorage(base_path=test_storage_dir)
        
        # Create bucket
        await storage.create_bucket(test_bucket_name)
        
        # Create 5 test files (5MB each)
        file_size = 5 * 1024 * 1024  # 5MB
        files = []
        for i in range(5):
            object_path = f"test/concurrent_download_{i}.bin"
            content = os.urandom(file_size)
            await storage.save_object(
                bucket_name=test_bucket_name,
                object_path=object_path,
                content=content,
                content_type="application/octet-stream"
            )
            files.append((object_path, content))
        
        # Download files concurrently and measure response time
        async def download_file(object_path):
            start_time = time.time()
            generator = storage.get_object_stream(test_bucket_name, object_path)
            first_chunk = await anext(generator)
            response_time = time.time() - start_time
            
            # Consume the rest of the stream to avoid resource leaks
            async for _ in generator:
                pass
                
            return response_time, len(first_chunk)
        
        # Run downloads concurrently
        tasks = [download_file(path) for path, _ in files]
        results = await asyncio.gather(*tasks)
        
        # Verify all downloads started quickly
        for i, (response_time, chunk_size) in enumerate(results):
            assert response_time < 0.1, f"Download {i} response time was {response_time*1000:.2f}ms, which exceeds the 100ms requirement"
            assert chunk_size > 0

# Import test environment setup first
from tests.test_env import *

import os
import time
import pytest
import asyncio
import statistics
from fastapi import UploadFile
from pathlib import Path
import httpx
from io import BytesIO

# Import after environment setup
from app.core.storage import FileStorage
from app.core.optimized_storage import OptimizedFileStorage


class TestDownloadPerformance:
    """Tests focused on download performance and response time"""
    
    def test_download_response_time_multiple_sizes(self, test_client, create_test_bucket, create_test_file):
        """Test download response time for files of various sizes"""
        bucket_name = create_test_bucket
        file_sizes = [1, 10, 50, 100]  # MB
        results = []
        
        for size in file_sizes:
            # Create and upload file
            file_path = create_test_file(size)
            object_path = f"test/perf_test_{size}mb.bin"
            
            with open(file_path, "rb") as f:
                response = test_client.post(
                    f"/buckets/{bucket_name}/objects",
                    params={"object_path": object_path},
                    files={"file": (f"perf_test_{size}mb.bin", f, "application/octet-stream")}
                )
            assert response.status_code == 201
            
            # Test download response time
            start_time = time.time()
            with test_client.stream("GET", f"/buckets/{bucket_name}/objects/{object_path}") as response:
                # We only care about the time to first byte
                first_chunk = next(response.iter_bytes(chunk_size=8192))
                response_time = time.time() - start_time
            
            results.append((size, response_time * 1000))  # Convert to ms
            
            # Assert response starts within 100ms
            assert response_time < 0.1, f"{size}MB file download response time was {response_time*1000:.2f}ms, exceeding 100ms requirement"
        
        # Log results for analysis
        for size, time_ms in results:
            print(f"{size}MB file: {time_ms:.2f}ms response time")
    
    def test_download_under_load(self, test_client, create_test_bucket, create_test_file):
        """Test download response time under simulated load"""
        bucket_name = create_test_bucket
        file_path = create_test_file(10)  # 10MB file
        object_path = "test/load_test.bin"
        
        # Upload file first
        with open(file_path, "rb") as f:
            response = test_client.post(
                f"/buckets/{bucket_name}/objects",
                params={"object_path": object_path},
                files={"file": ("load_test.bin", f, "application/octet-stream")}
            )
        assert response.status_code == 201
        
        # Simulate load by making multiple requests in sequence
        response_times = []
        for _ in range(10):
            start_time = time.time()
            with test_client.stream("GET", f"/buckets/{bucket_name}/objects/{object_path}") as response:
                first_chunk = next(response.iter_bytes(chunk_size=8192))
                response_time = time.time() - start_time
                response_times.append(response_time * 1000)  # Convert to ms
        
        # Calculate statistics
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        
        # Assert all responses start within 100ms
        assert max_time < 100, f"Maximum response time under load was {max_time:.2f}ms, exceeding 100ms requirement"
        print(f"Average response time under load: {avg_time:.2f}ms, Maximum: {max_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_optimized_streaming_implementation(self, test_storage_dir, test_bucket_name):
        """Test an optimized streaming implementation for fast response times"""
        # Initialize storage
        storage = FileStorage(base_path=test_storage_dir)
        await storage.create_bucket(test_bucket_name)
        
        # Create a large test file (50MB)
        file_size = 50 * 1024 * 1024
        content = os.urandom(file_size)
        object_path = "test/optimized_streaming.bin"
        
        # Save the file
        await storage.save_object(
            bucket_name=test_bucket_name,
            object_path=object_path,
            content=content,
            content_type="application/octet-stream"
        )
        
        # Implement an optimized streaming function with pre-buffering
        async def optimized_stream(bucket_name, object_path, chunk_size=8192, pre_buffer_size=65536):
            """Optimized streaming function with pre-buffering for fast response"""
            object_fs_path = storage._get_object_path(bucket_name, object_path)
            
            if not object_fs_path.is_file():
                raise FileNotFoundError(f"Object '{object_path}' not found in bucket '{bucket_name}'")
                
            async with aiofiles.open(object_fs_path, 'rb') as f:
                # Pre-buffer a larger initial chunk for fast response
                first_chunk = await f.read(pre_buffer_size)
                yield first_chunk
                
                # Continue streaming the rest in smaller chunks
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        
        # Test the optimized streaming function
        start_time = time.time()
        generator = optimized_stream(test_bucket_name, object_path)
        first_chunk = await anext(generator)
        response_time = time.time() - start_time
        
        # Assert response is very fast (under 50ms)
        assert response_time < 0.05, f"Optimized streaming response time was {response_time*1000:.2f}ms"
        assert len(first_chunk) > 0
        
        # Consume the rest of the stream
        async for _ in generator:
            pass


# Import needed for the optimized streaming test
import aiofiles


class TestStreamingOptimizations:
    """Tests for optimized streaming implementations"""
    
    @pytest.mark.asyncio
    async def test_chunked_streaming_performance(self, test_storage_dir, test_bucket_name):
        """Test performance of different chunking strategies for streaming"""
        # Initialize storage
        storage = FileStorage(base_path=test_storage_dir)
        await storage.create_bucket(test_bucket_name)
        
        # Create a test file (20MB)
        file_size = 20 * 1024 * 1024
        content = os.urandom(file_size)
        object_path = "test/chunking_test.bin"
        
        # Save the file
        await storage.save_object(
            bucket_name=test_bucket_name,
            object_path=object_path,
            content=content,
            content_type="application/octet-stream"
        )
        
        # Test different chunk sizes
        chunk_sizes = [4096, 8192, 16384, 32768, 65536]
        results = []
        
        for chunk_size in chunk_sizes:
            # Create a custom streaming function with the specified chunk size
            async def custom_stream(bucket_name, object_path, size=chunk_size):
                object_fs_path = storage._get_object_path(bucket_name, object_path)
                async with aiofiles.open(object_fs_path, 'rb') as f:
                    while True:
                        chunk = await f.read(size)
                        if not chunk:
                            break
                        yield chunk
            
            # Measure time to first byte
            start_time = time.time()
            generator = custom_stream(test_bucket_name, object_path)
            first_chunk = await anext(generator)
            ttfb = time.time() - start_time
            
            # Measure time to download entire file
            start_time = time.time()
            total_bytes = len(first_chunk)
            async for chunk in generator:
                total_bytes += len(chunk)
            total_time = time.time() - start_time
            
            results.append((chunk_size, ttfb * 1000, total_time * 1000))
            
            # Assert response starts within 100ms
            assert ttfb < 0.1, f"Time to first byte with {chunk_size} chunk size was {ttfb*1000:.2f}ms"
            assert total_bytes == file_size
        
        # Log results for analysis
        for chunk_size, ttfb, total_time in results:
            print(f"Chunk size {chunk_size}: TTFB {ttfb:.2f}ms, Total time {total_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_memory_mapped_file_performance(self, test_storage_dir, test_bucket_name):
        """Test using memory-mapped files for faster access"""
        # Skip this test if mmap is not available
        try:
            import mmap
        except ImportError:
            pytest.skip("mmap module not available")
            
        # Initialize storage
        storage = FileStorage(base_path=test_storage_dir)
        await storage.create_bucket(test_bucket_name)
        
        # Create a test file (30MB)
        file_size = 30 * 1024 * 1024
        content = os.urandom(file_size)
        object_path = "test/mmap_test.bin"
        
        # Save the file
        await storage.save_object(
            bucket_name=test_bucket_name,
            object_path=object_path,
            content=content,
            content_type="application/octet-stream"
        )
        
        # Implement a memory-mapped file streaming function
        async def mmap_stream(bucket_name, object_path, chunk_size=8192):
            object_fs_path = storage._get_object_path(bucket_name, object_path)
            
            # We need to use a sync file for mmap
            with open(object_fs_path, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    # Simulate async behavior with sleep(0)
                    for i in range(0, len(mm), chunk_size):
                        await asyncio.sleep(0)
                        yield mm[i:i+chunk_size]
        
        # Test the mmap streaming function
        start_time = time.time()
        generator = mmap_stream(test_bucket_name, object_path)
        first_chunk = await anext(generator)
        response_time = time.time() - start_time
        
        # Assert response is fast
        assert response_time < 0.1, f"Memory-mapped file response time was {response_time*1000:.2f}ms"
        assert len(first_chunk) > 0
        
        # Consume the rest of the stream
        total_bytes = len(first_chunk)
        async for chunk in generator:
            total_bytes += len(chunk)
            
        assert total_bytes == file_size

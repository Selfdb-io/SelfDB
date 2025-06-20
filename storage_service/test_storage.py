"""
Test script for the storage service.

This script tests the basic functionality of the storage service:
1. Creating a bucket
2. Uploading a file
3. Listing files
4. Downloading a file
5. Deleting a file
6. Deleting a bucket
"""

import asyncio
import httpx
import os
import tempfile
from pathlib import Path

# Configuration
STORAGE_SERVICE_URL = "http://localhost:8001"  # Adjust if needed

async def test_storage_service():
    """Test the basic functionality of the storage service."""
    print("Testing storage service...")
    
    # Create a test file
    test_content = b"This is a test file for the storage service."
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
        temp.write(test_content)
        test_file_path = temp.name
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Check if the service is running
            print("\n1. Checking if the service is running...")
            try:
                response = await client.get(f"{STORAGE_SERVICE_URL}/health")
                response.raise_for_status()
                print(f"Service is running: {response.json()}")
            except Exception as e:
                print(f"Error: {e}")
                print("Make sure the storage service is running.")
                return
            
            # 2. Create a test bucket
            print("\n2. Creating a test bucket...")
            bucket_name = "test-bucket"
            try:
                response = await client.post(
                    f"{STORAGE_SERVICE_URL}/buckets",
                    json={"name": bucket_name, "is_public": True}
                )
                response.raise_for_status()
                print(f"Bucket created: {response.json()}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409:
                    print(f"Bucket '{bucket_name}' already exists.")
                else:
                    print(f"Error creating bucket: {e}")
                    return
            
            # 3. Upload a test file
            print("\n3. Uploading a test file...")
            filename = os.path.basename(test_file_path)
            with open(test_file_path, "rb") as f:
                files = {"file": (filename, f, "text/plain")}
                response = await client.post(
                    f"{STORAGE_SERVICE_URL}/files/upload/{bucket_name}",
                    files=files
                )
                response.raise_for_status()
                upload_result = response.json()
                print(f"File uploaded: {upload_result}")
            
            # 4. List files in the bucket
            print("\n4. Listing files in the bucket...")
            response = await client.get(f"{STORAGE_SERVICE_URL}/files/list/{bucket_name}")
            response.raise_for_status()
            files_list = response.json()
            print(f"Files in bucket: {files_list}")
            
            # 5. Download the file
            print("\n5. Downloading the file...")
            response = await client.get(f"{STORAGE_SERVICE_URL}/files/download/{bucket_name}/{filename}")
            response.raise_for_status()
            downloaded_content = response.content
            print(f"Downloaded file content length: {len(downloaded_content)}")
            print(f"Content matches: {downloaded_content == test_content}")
            
            # 6. Delete the file
            print("\n6. Deleting the file...")
            response = await client.delete(f"{STORAGE_SERVICE_URL}/files/{bucket_name}/{filename}")
            response.raise_for_status()
            print("File deleted successfully.")
            
            # 7. Delete the bucket
            print("\n7. Deleting the bucket...")
            response = await client.delete(f"{STORAGE_SERVICE_URL}/buckets/{bucket_name}")
            response.raise_for_status()
            print("Bucket deleted successfully.")
            
            print("\nAll tests completed successfully!")
    
    finally:
        # Clean up the test file
        if os.path.exists(test_file_path):
            os.unlink(test_file_path)

if __name__ == "__main__":
    asyncio.run(test_storage_service())

"""
Test suite for File model implementation following TDD principles.
Based on API Contracts Plan specification for File model.
"""

import pytest
import uuid
from datetime import datetime, timezone

from shared.models.file import File
from shared.models.bucket import Bucket
from shared.models.user import User, UserRole


class TestFileModel:
    """Test cases for File model implementation."""
    
    def test_file_creation_with_required_fields(self):
        """Test creating a file with all required fields."""
        bucket_id = uuid.uuid4()
        file = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="documents/report.pdf",
            size=1024 * 1024,  # 1MB
            mime_type="application/pdf",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert file.id is not None
        assert isinstance(file.id, uuid.UUID)
        assert file.bucket_id == bucket_id
        assert file.name == "documents/report.pdf"
        assert file.size == 1024 * 1024
        assert file.mime_type == "application/pdf"
        assert file.owner_id is None  # Nullable for anonymous
        assert isinstance(file.created_at, datetime)
        assert isinstance(file.updated_at, datetime)
    
    def test_file_path_based_organization(self):
        """Test file path-based organization (e.g., 'users/123/avatar.jpg')."""
        paths = [
            "simple-file.txt",
            "folder/file.txt",
            "deep/nested/folder/file.txt",
            "users/123/avatar.jpg",
            "assets/images/logo.png",
            "documents/2024/jan/report.pdf"
        ]
        
        bucket_id = uuid.uuid4()
        
        for path in paths:
            file = File(
                id=uuid.uuid4(),
                bucket_id=bucket_id,
                name=path,
                size=1024,
                mime_type="text/plain",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            assert file.name == path
    
    def test_file_with_owner(self):
        """Test file with owner_id (authenticated user)."""
        owner_id = uuid.uuid4()
        bucket_id = uuid.uuid4()
        
        file = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="user-file.txt",
            owner_id=owner_id,
            size=2048,
            mime_type="text/plain",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert file.owner_id == owner_id
    
    def test_file_anonymous_ownership(self):
        """Test file without owner_id (anonymous/anonymous access)."""
        bucket_id = uuid.uuid4()
        
        file = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="public-file.txt",
            size=1024,
            mime_type="text/plain",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert file.owner_id is None
    
    def test_file_metadata_extraction(self):
        """Test file metadata (content_type, size, checksums)."""
        bucket_id = uuid.uuid4()
        
        file = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="image.jpg",
            size=500 * 1024,  # 500KB
            mime_type="image/jpeg",
            checksum_md5="d41d8cd98f00b204e9800998ecf8427e",
            checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            metadata={"width": 1920, "height": 1080, "camera": "Canon EOS R5"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert file.size == 500 * 1024
        assert file.mime_type == "image/jpeg"
        assert file.checksum_md5 == "d41d8cd98f00b204e9800998ecf8427e"
        assert file.checksum_sha256 == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert file.metadata["width"] == 1920
        assert file.metadata["height"] == 1080
        assert file.metadata["camera"] == "Canon EOS R5"
    
    def test_file_permissions_inheritance_from_bucket(self):
        """Test that file permissions inherit from bucket."""
        # This is a logical test - actual permission checking will be in service layer
        public_bucket_id = uuid.uuid4()
        private_bucket_id = uuid.uuid4()
        
        public_file = File(
            id=uuid.uuid4(),
            bucket_id=public_bucket_id,
            name="public-file.txt",
            size=1024,
            mime_type="text/plain",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        private_file = File(
            id=uuid.uuid4(),
            bucket_id=private_bucket_id,
            name="private-file.txt",
            owner_id=uuid.uuid4(),
            size=1024,
            mime_type="text/plain",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Files exist and have bucket relationship
        assert public_file.bucket_id == public_bucket_id
        assert private_file.bucket_id == private_bucket_id
    
    def test_file_versioning_support(self):
        """Test file versioning structure."""
        bucket_id = uuid.uuid4()
        
        file_v1 = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="document.pdf",
            version=1,
            is_latest=True,
            size=1024,
            mime_type="application/pdf",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        file_v2 = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="document.pdf",
            version=2,
            is_latest=True,
            size=2048,
            mime_type="application/pdf",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert file_v1.version == 1
        assert file_v2.version == 2
        assert file_v1.is_latest is True
        assert file_v2.is_latest is True  # Both marked as latest for this test
    
    def test_file_upload_validation(self):
        """Test file upload constraints."""
        bucket_id = uuid.uuid4()
        
        # Valid file
        valid_file = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="valid-file.txt",
            size=1024,
            mime_type="text/plain",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert valid_file.name == "valid-file.txt"
        
        # Large file
        large_file = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="large-file.zip",
            size=5 * 1024 * 1024 * 1024,  # 5GB
            mime_type="application/zip",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert large_file.size == 5 * 1024 * 1024 * 1024
    
    def test_file_soft_delete_and_recovery(self):
        """Test file soft delete functionality."""
        bucket_id = uuid.uuid4()
        
        file = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="deletable-file.txt",
            size=1024,
            mime_type="text/plain",
            deleted_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Initially not deleted
        assert file.deleted_at is None
        assert file.is_deleted is False
        
        # Soft delete
        file.deleted_at = datetime.now(timezone.utc)
        assert file.deleted_at is not None
        assert file.is_deleted is True
    
    def test_file_to_dict_conversion(self):
        """Test file serialization to dictionary."""
        bucket_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        
        file = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="dict-file.pdf",
            owner_id=owner_id,
            size=1024 * 1024,
            mime_type="application/pdf",
            checksum_md5="abc123",
            metadata={"pages": 10},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        file_dict = file.to_dict()
        
        assert file_dict["id"] == str(file.id)
        assert file_dict["bucket_id"] == str(file.bucket_id)
        assert file_dict["name"] == file.name
        assert file_dict["owner_id"] == str(file.owner_id)
        assert file_dict["size"] == file.size
        assert file_dict["mime_type"] == file.mime_type
        assert file_dict["checksum_md5"] == file.checksum_md5
        assert file_dict["metadata"] == file.metadata
    
    def test_file_string_representation(self):
        """Test file string representation."""
        bucket_id = uuid.uuid4()
        
        file = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="repr-file.txt",
            size=1024,
            mime_type="text/plain",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert str(file) == f"<File {file.name}>"
    
    def test_file_restore_method(self):
        """Test file restore functionality."""
        bucket_id = uuid.uuid4()
        
        file = File(
            id=uuid.uuid4(),
            bucket_id=bucket_id,
            name="restorable-file.txt",
            size=1024,
            mime_type="text/plain",
            deleted_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # File is initially deleted
        assert file.is_deleted is True
        assert file.deleted_at is not None
        
        # Restore the file
        file.restore()
        
        # File should no longer be deleted
        assert file.is_deleted is False
        assert file.deleted_at is None
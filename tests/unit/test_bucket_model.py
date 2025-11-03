"""
Test suite for Bucket model implementation following TDD principles.
Based on API Contracts Plan specification for Bucket model.
"""

import pytest
import uuid
from datetime import datetime, timezone

from shared.models.bucket import Bucket
from shared.models.user import User, UserRole


class TestBucketModel:
    """Test cases for Bucket model implementation."""
    
    def test_bucket_creation_with_required_fields(self):
        """Test creating a bucket with all required fields."""
        owner_id = uuid.uuid4()
        bucket = Bucket(
            id=uuid.uuid4(),
            name="test-bucket",
            owner_id=owner_id,
            public=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert bucket.id is not None
        assert isinstance(bucket.id, uuid.UUID)
        assert bucket.name == "test-bucket"
        assert bucket.owner_id == owner_id
        assert bucket.public is False
        assert isinstance(bucket.created_at, datetime)
        assert isinstance(bucket.updated_at, datetime)
    
    def test_bucket_public_access_flag(self):
        """Test bucket public/private access flag."""
        public_bucket = Bucket(
            id=uuid.uuid4(),
            name="public-assets",
            owner_id=uuid.uuid4(),
            public=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        private_bucket = Bucket(
            id=uuid.uuid4(),
            name="private-docs",
            owner_id=uuid.uuid4(),
            public=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert public_bucket.public is True
        assert private_bucket.public is False
    
    def test_bucket_name_validation(self):
        """Test bucket name validation (URL-safe)."""
        # Valid names
        valid_names = [
            "simple-bucket",
            "bucket123",
            "my_bucket",
            "bucket.with.dots",
            "a"  # Single character
        ]
        
        for name in valid_names:
            bucket = Bucket(
                id=uuid.uuid4(),
                name=name,
                owner_id=uuid.uuid4(),
                public=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            assert bucket.name == name
    
    def test_bucket_name_uniqueness_per_owner(self):
        """Test that bucket names must be unique per owner."""
        owner_id = uuid.uuid4()
        bucket_name = "my-bucket"
        
        bucket1 = Bucket(
            id=uuid.uuid4(),
            name=bucket_name,
            owner_id=owner_id,
            public=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Same owner, same name - should be prevented at database level
        bucket2 = Bucket(
            id=uuid.uuid4(),
            name=bucket_name,
            owner_id=owner_id,
            public=True,  # Different public flag
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert bucket1.name == bucket2.name
        assert bucket1.owner_id == bucket2.owner_id
        # Database constraint should prevent this
    
    def test_bucket_different_owners_can_have_same_name(self):
        """Test that different owners can have buckets with same name."""
        bucket_name = "shared-bucket-name"
        
        bucket1 = Bucket(
            id=uuid.uuid4(),
            name=bucket_name,
            owner_id=uuid.uuid4(),
            public=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        bucket2 = Bucket(
            id=uuid.uuid4(),
            name=bucket_name,
            owner_id=uuid.uuid4(),  # Different owner
            public=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert bucket1.name == bucket2.name
        assert bucket1.owner_id != bucket2.owner_id
    
    def test_bucket_ownership_relationship(self):
        """Test bucket ownership relationship to User."""
        owner = User(
            id=uuid.uuid4(),
            email="owner@example.com",
            password="ownerPassword123!",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        bucket = Bucket(
            id=uuid.uuid4(),
            name="owner-bucket",
            owner_id=owner.id,
            public=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert bucket.owner_id == owner.id
    
    def test_bucket_timestamps(self):
        """Test that created_at and updated_at are datetime objects."""
        now = datetime.now(timezone.utc)
        bucket = Bucket(
            id=uuid.uuid4(),
            name="timestamp-bucket",
            owner_id=uuid.uuid4(),
            public=False,
            created_at=now,
            updated_at=now
        )
        
        assert bucket.created_at == now
        assert bucket.updated_at == now
        assert isinstance(bucket.created_at, datetime)
        assert isinstance(bucket.updated_at, datetime)
    
    def test_bucket_to_dict_conversion(self):
        """Test bucket serialization to dictionary."""
        owner_id = uuid.uuid4()
        bucket = Bucket(
            id=uuid.uuid4(),
            name="dict-bucket",
            owner_id=owner_id,
            public=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        bucket_dict = bucket.to_dict()
        
        assert bucket_dict["id"] == str(bucket.id)
        assert bucket_dict["name"] == bucket.name
        assert bucket_dict["owner_id"] == str(bucket.owner_id)
        assert bucket_dict["public"] == bucket.public
        assert "created_at" in bucket_dict
        assert "updated_at" in bucket_dict
    
    def test_bucket_string_representation(self):
        """Test bucket string representation."""
        bucket = Bucket(
            id=uuid.uuid4(),
            name="repr-bucket",
            owner_id=uuid.uuid4(),
            public=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert str(bucket) == f"<Bucket {bucket.name}>"
    
    def test_bucket_repr(self):
        """Test bucket detailed representation."""
        bucket_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        bucket = Bucket(
            id=bucket_id,
            name="test-bucket",
            owner_id=owner_id,
            public=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        expected = f"<Bucket(id={bucket_id}, name=test-bucket, owner_id={owner_id}, public=True)>"
        assert repr(bucket) == expected
    
    def test_bucket_minio_bucket_name_property(self):
        """Test that bucket has minio_bucket_name property for internal use."""
        bucket = Bucket(
            id=uuid.uuid4(),
            name="my-bucket",
            owner_id=uuid.uuid4(),
            public=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # minio_bucket_name should be generated from id and name
        assert hasattr(bucket, 'minio_bucket_name')
        assert bucket.minio_bucket_name == f"{bucket.id}-{bucket.name}"
    
    def test_bucket_description_field(self):
        """Test optional description field."""
        # Without description
        bucket1 = Bucket(
            id=uuid.uuid4(),
            name="no-desc-bucket",
            owner_id=uuid.uuid4(),
            public=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert bucket1.description is None
        
        # With description
        bucket2 = Bucket(
            id=uuid.uuid4(),
            name="with-desc-bucket",
            owner_id=uuid.uuid4(),
            public=False,
            description="This is my bucket description",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert bucket2.description == "This is my bucket description"
    
    def test_bucket_metadata_field(self):
        """Test optional metadata field."""
        metadata = {"region": "us-east-1", "tier": "standard"}
        
        bucket = Bucket(
            id=uuid.uuid4(),
            name="metadata-bucket",
            owner_id=uuid.uuid4(),
            public=False,
            metadata=metadata,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert bucket.metadata == metadata
    
    def test_bucket_creation_operations(self):
        """Test bucket creation operations."""
        owner_id = uuid.uuid4()
        
        # Create bucket
        bucket = Bucket.create(
            name="created-bucket",
            owner_id=owner_id,
            public=True,
            description="Test bucket creation"
        )
        
        assert bucket.name == "created-bucket"
        assert bucket.owner_id == owner_id
        assert bucket.public is True
        assert bucket.description == "Test bucket creation"
        assert isinstance(bucket.id, uuid.UUID)
        assert isinstance(bucket.created_at, datetime)
        assert isinstance(bucket.updated_at, datetime)
"""
Bucket model implementation following API Contracts Plan specification.
Based on Phase 2.2.2 Bucket Model requirements.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class Bucket:
    """
    Bucket model with UUID, name, owner_id, and public access control.
    
    Attributes:
        id: UUID primary key
        name: Unique, URL-safe bucket name (e.g., "avatars", "documents")
        owner_id: References User.id
        public: Public access flag (public/private)
        description: Optional description
        metadata: Optional metadata dictionary
        minio_bucket_name: Internal MinIO bucket name
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        id: uuid.UUID,
        name: str,
        owner_id: uuid.UUID,
        public: bool = False,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        """
        Initialize a Bucket instance.
        
        Args:
            id: UUID for the bucket
            name: Bucket name (must be URL-safe)
            owner_id: UUID of the bucket owner (User.id)
            public: Public access flag (defaults to False)
            description: Optional description
            metadata: Optional metadata dictionary
            created_at: Creation timestamp (defaults to now)
            updated_at: Update timestamp (defaults to now)
        """
        self.id = id
        self.name = name
        self.owner_id = owner_id
        self.public = public
        self.description = description
        self.metadata = metadata or {}
        
        # Set timestamps
        now = datetime.now(timezone.utc)
        self.created_at = created_at or now
        self.updated_at = updated_at or now
    
    @property
    def minio_bucket_name(self) -> str:
        """
        Generate internal MinIO bucket name from id and name.
        This ensures uniqueness across all buckets.
        """
        return f"{self.id}-{self.name}"
    
    @classmethod
    def create(
        cls,
        name: str,
        owner_id: uuid.UUID,
        public: bool = False,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'Bucket':
        """
        Create a new bucket with generated UUID and timestamps.
        
        Args:
            name: Bucket name
            owner_id: Owner's User ID
            public: Public access flag
            description: Optional description
            metadata: Optional metadata
            
        Returns:
            New Bucket instance
        """
        return cls(
            id=uuid.uuid4(),
            name=name,
            owner_id=owner_id,
            public=public,
            description=description,
            metadata=metadata
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert bucket to dictionary.
        
        Returns:
            Dictionary representation of bucket
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "owner_id": str(self.owner_id),
            "public": self.public,
            "description": self.description,
            "metadata": self.metadata,
            "minio_bucket_name": self.minio_bucket_name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation of bucket."""
        return f"<Bucket {self.name}>"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"<Bucket(id={self.id}, name={self.name}, owner_id={self.owner_id}, public={self.public})>"
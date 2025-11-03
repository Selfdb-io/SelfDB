"""
File model implementation following API Contracts Plan specification.
Based on Phase 2.2.3 File Model requirements.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class File:
    """
    File model with UUID, path-based organization, and metadata.
    
    Attributes:
        id: UUID primary key
        bucket_id: References Bucket.id
        name: Full path (e.g., "users/123/avatar.jpg")
        owner_id: Optional, references User.id (nullable for anonymous)
        size: File size in bytes
        mime_type: MIME type
        metadata: Custom metadata (optional)
        checksum_md5: MD5 checksum
        checksum_sha256: SHA256 checksum
        version: Version number
        is_latest: Whether this is the latest version
        deleted_at: Soft delete timestamp
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        id: uuid.UUID,
        bucket_id: uuid.UUID,
        name: str,
        size: int,
        mime_type: str,
        owner_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        checksum_md5: Optional[str] = None,
        checksum_sha256: Optional[str] = None,
        version: int = 1,
        is_latest: bool = True,
        deleted_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        """
        Initialize a File instance.
        
        Args:
            id: UUID for the file
            bucket_id: UUID of the containing bucket
            name: Full path name
            size: File size in bytes
            mime_type: MIME type
            owner_id: Optional owner's User ID
            metadata: Optional custom metadata
            checksum_md5: Optional MD5 checksum
            checksum_sha256: Optional SHA256 checksum
            version: Version number (defaults to 1)
            is_latest: Whether this is latest version (defaults to True)
            deleted_at: Soft delete timestamp (defaults to None)
            created_at: Creation timestamp (defaults to now)
            updated_at: Update timestamp (defaults to now)
        """
        self.id = id
        self.bucket_id = bucket_id
        self.name = name
        self.owner_id = owner_id
        self.size = size
        self.mime_type = mime_type
        self.metadata = metadata or {}
        self.checksum_md5 = checksum_md5
        self.checksum_sha256 = checksum_sha256
        self.version = version
        self.is_latest = is_latest
        self.deleted_at = deleted_at
        
        # Set timestamps
        now = datetime.now(timezone.utc)
        self.created_at = created_at or now
        self.updated_at = updated_at or now
    
    @property
    def is_deleted(self) -> bool:
        """Check if file is soft deleted."""
        return self.deleted_at is not None
    
    def soft_delete(self) -> None:
        """Mark file as deleted (soft delete)."""
        self.deleted_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def restore(self) -> None:
        """Restore soft deleted file."""
        self.deleted_at = None
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert file to dictionary.
        
        Returns:
            Dictionary representation of file
        """
        return {
            "id": str(self.id),
            "bucket_id": str(self.bucket_id),
            "name": self.name,
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "size": self.size,
            "mime_type": self.mime_type,
            "metadata": self.metadata,
            "checksum_md5": self.checksum_md5,
            "checksum_sha256": self.checksum_sha256,
            "version": self.version,
            "is_latest": self.is_latest,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation of file."""
        return f"<File {self.name}>"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"<File(id={self.id}, name={self.name}, bucket_id={self.bucket_id}, size={self.size})>"
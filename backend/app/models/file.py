from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..db.base_class import Base

class File(Base):
    """
    Represents a file stored in MinIO with metadata in PostgreSQL.
    """
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    object_name = Column(String, nullable=False, unique=True)  # Path in MinIO
    bucket_name = Column(String, nullable=False)  # Legacy field, kept for backward compatibility
    content_type = Column(String)
    size = Column(Integer)  # Size in bytes

    # Owner relationship
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Allow nullable for anonymous uploads
    owner = relationship("User", back_populates="files")

    # Bucket relationship
    bucket_id = Column(UUID(as_uuid=True), ForeignKey("buckets.id"), nullable=True)
    bucket = relationship("Bucket", back_populates="files")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<File(id={self.id}, filename='{self.filename}', owner_id='{self.owner_id}')>"

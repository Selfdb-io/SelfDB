from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..db.base_class import Base

class Bucket(Base):
    """
    Represents a storage bucket owned by a user.
    """
    __tablename__ = "buckets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    minio_bucket_name = Column(String, nullable=False, unique=True)
    is_public = Column(Boolean, default=False)

    # Owner relationship
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="buckets")

    # Files relationship
    files = relationship("File", back_populates="bucket", cascade="all, delete-orphan")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Bucket(id={self.id}, name='{self.name}', owner_id='{self.owner_id}')>"

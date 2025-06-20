from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime

# Base Bucket schema with common attributes
class BucketBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False

# Schema for bucket creation
class BucketCreate(BucketBase):
    pass

# Schema for bucket update
class BucketUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

# Schema for bucket in DB
class BucketInDBBase(BucketBase):
    id: UUID4
    minio_bucket_name: str
    owner_id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

# Schema for returning bucket to client
class Bucket(BucketInDBBase):
    pass

# Schema for bucket with file stats
class BucketWithStats(Bucket):
    file_count: int = 0
    total_size: int = 0  # Total size in bytes

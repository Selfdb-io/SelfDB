from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime

# Base File schema with common attributes
class FileBase(BaseModel):
    filename: str
    content_type: Optional[str] = None

# Schema for file creation (used internally)
class FileCreate(FileBase):
    bucket_name: str
    object_name: str
    size: int
    owner_id: Optional[UUID4] = None  # Make owner_id optional for anonymous uploads
    bucket_id: Optional[UUID4] = None

# Schema for file update
class FileUpdate(BaseModel):
    filename: Optional[str] = None
    content_type: Optional[str] = None

# Schema for file in DB
class FileInDBBase(FileBase):
    id: UUID4
    bucket_name: str
    object_name: str
    size: int
    owner_id: Optional[UUID4] = None  # Make owner_id optional for anonymous uploads
    bucket_id: Optional[UUID4] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

# Schema for returning file to client
class File(FileInDBBase):
    pass

# Schema for file with download URL
class FileWithURL(File):
    download_url: str

from pydantic import BaseModel, Field, AnyHttpUrl
from typing import Optional
from datetime import datetime

class FileBase(BaseModel):
    filename: str
    content_type: Optional[str] = None
    
class FileCreate(FileBase):
    pass

class FileUploadResponse(FileBase):
    size: int
    url: AnyHttpUrl
    bucket: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class FileInfo(FileBase):
    size: int
    bucket: str
    url: AnyHttpUrl
    created_at: datetime
    
    class Config:
        from_attributes = True

from pydantic import BaseModel, Field
from typing import Optional, List
import re

class BucketBase(BaseModel):
    name: str = Field(
        ..., 
        min_length=3, 
        max_length=63, 
        pattern=r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$",
        description="Bucket name. Must be 3-63 chars, lowercase, start/end with letter/number, can contain dots and hyphens."
    )
    is_public: bool = True

class BucketCreate(BucketBase):
    pass

class BucketUpdate(BaseModel):
    is_public: Optional[bool] = None
    
class Bucket(BucketBase):
    """Full bucket representation returned by API"""
    owner_id: str
    
    class Config:
        from_attributes = True

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


# ----------------------------
# Shared / Base Schemas
# ----------------------------

class FunctionBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None  # Raw TS/JS source
    is_active: Optional[bool] = True


# ----------------------------
# Create / Update Schemas
# ----------------------------

class FunctionCreate(FunctionBase):
    name: str
    code: str


class FunctionUpdate(FunctionBase):
    pass


# ----------------------------
# In‑DB & Response Schemas
# ----------------------------

class FunctionInDBBase(FunctionBase):
    id: UUID
    owner_id: UUID
    version_number: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # ORM mode


class Function(FunctionInDBBase):
    """Response model returned to clients"""

    pass


# ------------------------------------------------------------------
# Version Schemas
# ------------------------------------------------------------------

class FunctionVersionBase(BaseModel):
    version_number: int
    code: str


class FunctionVersion(FunctionVersionBase):
    id: UUID
    created_at: datetime
    created_by: Optional[UUID] = None

    class Config:
        from_attributes = True


# ------------------------------------------------------------------
# Env Var Schemas
# ------------------------------------------------------------------

class FunctionEnvVarBase(BaseModel):
    key: str
    value: str  # Stored encrypted but represented here as raw string
    is_secret: bool = True


class FunctionEnvVar(FunctionEnvVarBase):
    id: UUID

    class Config:
        from_attributes = True


# ----------------------------
# Aggregated Schemas
# ----------------------------

class FunctionWithEnv(Function):
    env_vars: List[FunctionEnvVar] = Field(default_factory=list)
    versions: List[FunctionVersion] = Field(default_factory=list)
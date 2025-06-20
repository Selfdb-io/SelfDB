from __future__ import annotations

import enum
import uuid
from typing import List, ClassVar

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Enum as PgEnum,
    ForeignKey,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped

from ..db.base_class import Base


class FunctionRuntime(str, enum.Enum):
    """Supported runtimes for cloud functions."""

    deno = "deno"


class Function(Base):
    __allow_unmapped__ = True
    """Represents a cloud function definition owned by a *User*.

    The actual source code lives in the *code* column **and** is also materialised
    on disk under the `./functions` host directory so that the dedicated Deno
    runtime container can import it at run‑time.
    """

    __tablename__ = "functions"

    # Core identifiers & metadata
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)

    # Source code (Deno TS/JS)
    code = Column(Text, nullable=False)

    # Runtime configuration
    runtime = Column(PgEnum(FunctionRuntime, name="function_runtime"), nullable=False, default=FunctionRuntime.deno)

    # Versioning
    version_id = Column(UUID(as_uuid=True), ForeignKey("function_versions.id", ondelete="SET NULL"))
    version_number = Column(Integer, nullable=False, default=1)

    # State
    is_active = Column(Boolean, default=True, index=True)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    versions: List["FunctionVersion"] = relationship(
        "FunctionVersion", back_populates="function", cascade="all, delete-orphan", lazy="selectin",
        foreign_keys="[FunctionVersion.function_id]"
    )
    env_vars: List["FunctionEnvVar"] = relationship(
        "FunctionEnvVar", back_populates="function", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Function(id={self.id}, name='{self.name}')>"


class FunctionVersion(Base):
    __allow_unmapped__ = True
    """Immutable snapshot of a *Function* at a particular version number."""

    __tablename__ = "function_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    function_id = Column(UUID(as_uuid=True), ForeignKey("functions.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    code = Column(Text, nullable=False)
    metadata_json = Column("metadata", Text, nullable=False)  # Store JSON string for simplicity

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationship back‑references
    function: "Function" = relationship("Function", back_populates="versions", foreign_keys=[function_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FunctionVersion(function_id={self.function_id}, version={self.version_number})>"


class FunctionEnvVar(Base):
    __allow_unmapped__ = True
    """Environment variables scoped to a single *Function* instance."""

    __tablename__ = "function_env_vars"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    function_id = Column(UUID(as_uuid=True), ForeignKey("functions.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    is_secret = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship back‑reference
    function: "Function" = relationship("Function", back_populates="env_vars")

    __table_args__ = (
        # Ensure uniqueness of `key` per function
        {
            "sqlite_autoincrement": True,
            "postgresql_partition_by": None,
            "comment": "Environment variables per function",
        },
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FunctionEnvVar(function_id={self.function_id}, key='{self.key}')>"
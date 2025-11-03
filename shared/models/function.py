"""
Function model implementation for SelfDB serverless functions.
Based on Functions & Webhooks Improvement Plan requirements.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, Annotated

from pydantic import BaseModel, Field, UUID4, ValidationError, constr, conint
from pydantic_core import PydanticCustomError


class FunctionRuntime(str, Enum):
    """Function runtime enumeration."""
    DENO = "deno"
    NODE = "node"
    PYTHON = "python"


class DeploymentStatus(str, Enum):
    """Function deployment status enumeration."""
    PENDING = "pending"
    DEPLOYED = "deployed"
    FAILED = "failed"
    UNDEPLOYED = "undeployed"


class TriggerType(str, Enum):
    """Function trigger type enumeration."""
    HTTP = "http"
    SCHEDULE = "schedule"
    DATABASE = "database"
    EVENT = "event"
    WEBHOOK = "webhook"


class ExecutionStatus(str, Enum):
    """Function execution status enumeration."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Function(BaseModel):
    """
    Function model for serverless function management.
    
    Uses Pydantic for automatic validation and type safety.
    """
    
    # Primary key - must be valid UUID
    id: UUID4
    
    # Required fields with constraints
    name: Annotated[str, constr(min_length=1, max_length=255, pattern=r'^[a-zA-Z0-9_-]+$')]
    code: Annotated[str, constr(min_length=1)]
    owner_id: UUID4
    
    # Optional description
    description: Optional[Annotated[str, constr(max_length=1000)]] = None
    
    # Runtime with default
    runtime: FunctionRuntime = FunctionRuntime.DENO
    
    # Status fields with defaults
    is_active: bool = True
    deployment_status: DeploymentStatus = DeploymentStatus.PENDING
    deployment_error: Optional[Annotated[str, constr(max_length=1000)]] = None
    
    # Version and constraints
    version: Annotated[int, conint(ge=1)] = 1
    timeout_seconds: Annotated[int, conint(ge=5, le=300)] = 30
    memory_limit_mb: Annotated[int, conint(ge=128, le=4096)] = 512
    max_concurrent: Annotated[int, conint(ge=1, le=100)] = 10
    
    # Environment variables
    env_vars: Dict[str, Any] = Field(default_factory=dict)
    env_vars_updated_at: Optional[datetime] = None
    
    # Execution statistics
    execution_count: Annotated[int, conint(ge=0)] = 0
    execution_success_count: Annotated[int, conint(ge=0)] = 0
    execution_error_count: Annotated[int, conint(ge=0)] = 0
    
    # Timestamps
    last_executed_at: Optional[datetime] = None
    avg_execution_time_ms: Optional[Annotated[float, conint(ge=0)]] = None
    last_deployed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __init__(self, **data):
        # Set default timestamps if not provided
        if 'created_at' not in data:
            data['created_at'] = datetime.now(timezone.utc)
        if 'updated_at' not in data:
            data['updated_at'] = datetime.now(timezone.utc)
        
        super().__init__(**data)
    
    @classmethod
    def create(
        cls,
        name: str,
        code: str,
        owner_id: uuid.UUID,
        description: Optional[str] = None,
        runtime: FunctionRuntime = FunctionRuntime.DENO,
        timeout_seconds: int = 30,
        memory_limit_mb: int = 512,
        max_concurrent: int = 10
    ) -> 'Function':
        """
        Create a new function instance.
        
        Args:
            name: Function name
            code: Function source code
            owner_id: Owner UUID
            description: Optional description
            runtime: Runtime environment
            timeout_seconds: Execution timeout
            memory_limit_mb: Memory limit
            max_concurrent: Max concurrent executions
            
        Returns:
            New Function instance
        """
        return cls(
            id=uuid.uuid4(),
            name=name,
            code=code,
            owner_id=owner_id,
            description=description,
            runtime=runtime,
            timeout_seconds=timeout_seconds,
            memory_limit_mb=memory_limit_mb,
            max_concurrent=max_concurrent
        )
    
    def update_code(self, new_code: str) -> None:
        """
        Update function code and increment version.
        
        Args:
            new_code: New function source code
        """
        if not new_code:
            raise ValueError("Function code cannot be empty")
        
        self.code = new_code
        self.version += 1
        self.deployment_status = DeploymentStatus.PENDING
        self.updated_at = datetime.now(timezone.utc)
    
    def set_env_vars(self, env_vars: Dict[str, Any]) -> None:
        """
        Update environment variables.
        
        Args:
            env_vars: New environment variables dictionary
        """
        self.env_vars = env_vars or {}
        self.env_vars_updated_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def record_execution(
        self,
        success: bool,
        execution_time_ms: Optional[int] = None
    ) -> None:
        """
        Record a function execution.
        
        Args:
            success: Whether execution was successful
            execution_time_ms: Execution time in milliseconds
        """
        self.execution_count += 1
        if success:
            self.execution_success_count += 1
        else:
            self.execution_error_count += 1
        
        self.last_executed_at = datetime.now(timezone.utc)
        
        if execution_time_ms is not None:
            if self.avg_execution_time_ms is None:
                self.avg_execution_time_ms = execution_time_ms
            else:
                # Calculate running average
                total_time = self.avg_execution_time_ms * (self.execution_count - 1)
                self.avg_execution_time_ms = (total_time + execution_time_ms) // self.execution_count
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert function to dictionary, excluding sensitive data.
        
        Returns:
            Dictionary representation of function
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "runtime": self.runtime.value,
            "owner_id": str(self.owner_id),
            "is_active": self.is_active,
            "deployment_status": self.deployment_status.value,
            "deployment_error": self.deployment_error,
            "version": self.version,
            "timeout_seconds": self.timeout_seconds,
            "memory_limit_mb": self.memory_limit_mb,
            "max_concurrent": self.max_concurrent,
            "env_vars": list(self.env_vars.keys()) if self.env_vars else [],  # Only keys, not values
            "env_vars_updated_at": self.env_vars_updated_at.isoformat() if self.env_vars_updated_at else None,
            "execution_count": self.execution_count,
            "execution_success_count": self.execution_success_count,
            "execution_error_count": self.execution_error_count,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "last_deployed_at": self.last_deployed_at.isoformat() if self.last_deployed_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation of function."""
        return f"<Function {self.name} ({self.runtime.value})>"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"<Function(id={self.id}, name={self.name}, runtime={self.runtime.value}, status={self.deployment_status.value})>"
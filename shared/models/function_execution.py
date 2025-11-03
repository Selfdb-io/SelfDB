"""
FunctionExecution model implementation for SelfDB function execution tracking.
Based on Functions & Webhooks Improvement Plan requirements.
"""

import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, UUID4, ValidationError, conint, confloat, constr


class FunctionExecution(BaseModel):
    """
    FunctionExecution model for tracking function execution attempts and results.
    
    Attributes:
        id: UUID primary key
        function_id: References Function.id
        user_id: References User.id
        trigger_type: How execution was triggered
        trigger_source: Source of the trigger
        webhook_delivery_id: Associated webhook delivery if triggered by webhook
        status: Execution status
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
        duration_ms: Total execution time in milliseconds
        timeout_at: Timeout timestamp (calculated, not stored)
        error_message: Error message if failed
        result: Execution result/output (JSON)
        memory_used_mb: Memory usage
        cpu_usage_percent: CPU usage percentage
        error_stack_trace: Full error stack trace
        error_type: Error type/category
        env_vars_used: Environment variables used during execution
        execution_trace: Execution trace/debugging information
        metadata: Additional metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    id: UUID4 = Field(..., description="UUID primary key")
    function_id: UUID4 = Field(..., description="References Function.id")
    user_id: UUID4 = Field(..., description="References User.id")
    trigger_type: constr(min_length=1, max_length=50) = Field(..., description="How execution was triggered")
    trigger_source: Optional[constr(max_length=255)] = Field(None, description="Source of the trigger")
    webhook_delivery_id: Optional[UUID4] = Field(None, description="Associated webhook delivery if triggered by webhook")
    status: constr(pattern=r'^(running|completed|failed|timeout)$') = Field("running", description="Execution status")
    started_at: datetime = Field(..., description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Execution completion timestamp")
    duration_ms: Optional[conint(ge=0)] = Field(None, description="Total execution time in milliseconds")
    error_message: Optional[constr(max_length=1000)] = Field(None, description="Error message if failed")
    result: Optional[Any] = Field(None, description="Execution result/output (JSON)")
    memory_used_mb: Optional[confloat(ge=0)] = Field(None, description="Memory usage")
    cpu_usage_percent: Optional[confloat(ge=0, le=100)] = Field(None, description="CPU usage percentage")
    error_stack_trace: Optional[str] = Field(None, description="Full error stack trace")
    error_type: Optional[constr(max_length=100)] = Field(None, description="Error type/category")
    env_vars_used: List[str] = Field(default_factory=list, description="Environment variables used during execution")
    execution_trace: Optional[Any] = Field(None, description="Execution trace/debugging information")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    @property
    def timeout_seconds(self) -> Optional[int]:
        """
        Get the timeout duration in seconds.
        
        Returns:
            Timeout duration in seconds, or None if not set
        """
        # This is a calculated property, not stored in DB
        # Default timeout is typically 30 seconds for functions
        return self.metadata.get("timeout_seconds", 30)
    
    @classmethod
    def create(
        cls,
        function_id: uuid.UUID,
        user_id: uuid.UUID,
        trigger_type: str,
        trigger_source: Optional[str] = None,
        webhook_delivery_id: Optional[uuid.UUID] = None,
        timeout_seconds: int = 30
    ) -> 'FunctionExecution':
        """
        Create a new function execution instance.
        
        Args:
            function_id: Function UUID
            user_id: User UUID
            trigger_type: Trigger type
            trigger_source: Trigger source
            webhook_delivery_id: Webhook delivery UUID
            timeout_seconds: Timeout duration (stored as metadata)
            
        Returns:
            New FunctionExecution instance
        """
        started_at = datetime.now(timezone.utc)
        
        return cls(
            id=uuid.uuid4(),
            function_id=function_id,
            user_id=user_id,
            trigger_type=trigger_type,
            trigger_source=trigger_source,
            webhook_delivery_id=webhook_delivery_id,
            started_at=started_at,
            metadata={"timeout_seconds": timeout_seconds},
            created_at=started_at,
            updated_at=started_at
        )
    
    def complete(
        self,
        success: bool,
        result: Optional[Any] = None,
        memory_used_mb: Optional[float] = None,
        cpu_usage_percent: Optional[float] = None,
        error_message: Optional[str] = None,
        error_stack_trace: Optional[str] = None,
        error_type: Optional[str] = None,
        env_vars_used: Optional[List[str]] = None,
        execution_trace: Optional[Any] = None
    ) -> 'FunctionExecution':
        """
        Mark execution as completed.
        
        Args:
            success: Whether execution was successful
            result: Execution result
            memory_used_mb: Memory usage
            cpu_usage_percent: CPU usage percentage
            error_message: Error message if failed
            error_stack_trace: Full error stack trace
            error_type: Error type/category
            env_vars_used: Environment variables used
            execution_trace: Execution trace information
            
        Returns:
            Updated FunctionExecution instance
        """
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - self.started_at).total_seconds() * 1000) if self.started_at else None
        
        return self.model_copy(update={
            'completed_at': completed_at,
            'duration_ms': duration_ms,
            'result': result,
            'memory_used_mb': memory_used_mb,
            'cpu_usage_percent': cpu_usage_percent,
            'error_message': error_message,
            'error_stack_trace': error_stack_trace,
            'error_type': error_type,
            'env_vars_used': env_vars_used or [],
            'execution_trace': execution_trace,
            'status': "completed" if success else "failed",
            'updated_at': completed_at
        })
    
    def mark_timeout(self) -> 'FunctionExecution':
        """Mark execution as timed out."""
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - self.started_at).total_seconds() * 1000) if self.started_at else None
        
        return self.model_copy(update={
            'completed_at': completed_at,
            'duration_ms': duration_ms,
            'status': "timeout",
            'error_message': "Function execution timed out",
            'error_type': "timeout",
            'updated_at': completed_at
        })
    
    def is_timed_out(self) -> bool:
        """
        Check if execution has timed out.
        
        Returns:
            True if timed out, False otherwise
        """
        if self.status == "running" and self.started_at:
            timeout_seconds = self.metadata.get("timeout_seconds", 30)
            return datetime.now(timezone.utc) > (self.started_at + timedelta(seconds=timeout_seconds))
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert execution to dictionary.
        
        Returns:
            Dictionary representation of execution
        """
        data = self.model_dump()
        # Convert UUIDs to strings for JSON serialization
        data['id'] = str(data['id'])
        data['function_id'] = str(data['function_id'])
        data['user_id'] = str(data['user_id'])
        if data.get('webhook_delivery_id'):
            data['webhook_delivery_id'] = str(data['webhook_delivery_id'])
        return data
    
    def __str__(self) -> str:
        """String representation of execution."""
        return f"<FunctionExecution {self.id} ({self.status})>"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"<FunctionExecution(id={self.id}, function={self.function_id}, status={self.status}, trigger={self.trigger_type})>"
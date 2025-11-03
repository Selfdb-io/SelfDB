"""
FunctionLog model implementation for SelfDB function execution logs.
Based on Functions & Webhooks Improvement Plan requirements.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict
from pydantic import BaseModel, Field, UUID4, ValidationError, conint, constr


class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class FunctionLog(BaseModel):
    """
    FunctionLog model for storing raw function execution logs.
    
    Attributes:
        id: Auto-increment primary key
        execution_id: References FunctionExecution.id
        function_id: References Function.id
        log_level: Log level (debug, info, warn, error)
        message: Log message
        timestamp: Log timestamp
        source: Log source (e.g., 'runtime', 'function', 'system')
        context: Additional context information (JSON)
    """
    
    id: Optional[conint(ge=1)] = Field(None, description="Auto-increment primary key")
    execution_id: Optional[UUID4] = Field(None, description="References FunctionExecution.id")
    function_id: Optional[UUID4] = Field(None, description="References Function.id")
    log_level: LogLevel = Field(LogLevel.INFO, description="Log level")
    message: constr(min_length=1, max_length=10000) = Field(..., description="Log message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Log timestamp")
    source: constr(min_length=1, max_length=100) = Field("function", description="Log source")
    context: Dict = Field(default_factory=dict, description="Additional context information")
    
    @classmethod
    def create(
        cls,
        execution_id: uuid.UUID,
        function_id: uuid.UUID,
        message: str,
        log_level: LogLevel = LogLevel.INFO,
        source: str = "function",
        context: Optional[Dict] = None
    ) -> 'FunctionLog':
        """
        Create a new function log instance.
        
        Args:
            execution_id: Execution UUID
            function_id: Function UUID
            message: Log message
            log_level: Log level
            source: Log source
            context: Additional context
            
        Returns:
            New FunctionLog instance
        """
        return cls(
            execution_id=execution_id,
            function_id=function_id,
            message=message,
            log_level=log_level,
            source=source,
            context=context or {}
        )
    
    @classmethod
    def system_log(
        cls,
        function_id: uuid.UUID,
        message: str,
        log_level: LogLevel = LogLevel.INFO,
        context: Optional[Dict] = None
    ) -> 'FunctionLog':
        """
        Create a system-level log (not associated with specific execution).
        
        Args:
            function_id: Function UUID
            message: Log message
            log_level: Log level
            context: Additional context
            
        Returns:
            New FunctionLog instance
        """
        return cls(
            function_id=function_id,
            message=message,
            log_level=log_level,
            source="system",
            context=context or {}
        )
    
    def to_dict(self) -> dict:
        """
        Convert log to dictionary.
        
        Returns:
            Dictionary representation of log
        """
        data = self.model_dump()
        # Convert UUIDs to strings for JSON serialization
        if data.get('execution_id'):
            data['execution_id'] = str(data['execution_id'])
        if data.get('function_id'):
            data['function_id'] = str(data['function_id'])
        return data
    
    def __str__(self) -> str:
        """String representation of log."""
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp_str}] {self.log_level.value.upper()}: {self.message}"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"<FunctionLog(id={self.id}, level={self.log_level.value}, message='{self.message[:50]}...')>"
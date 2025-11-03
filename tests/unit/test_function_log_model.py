"""
Test suite for FunctionLog model implementation following TDD principles.
Based on Functions & Webhooks Improvement Plan requirements.
"""

import pytest
import uuid
from datetime import datetime, timezone
from pydantic import ValidationError as PydanticValidationError

from shared.models.function_log import FunctionLog, LogLevel


class TestFunctionLogModel:
    """Test cases for FunctionLog model implementation."""
    
    def test_log_level_enum_values(self):
        """Test that LogLevel enum has correct values."""
        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert LogLevel.WARN.value == "warn"
        assert LogLevel.ERROR.value == "error"
    
    def test_function_log_creation_with_required_fields(self):
        """Test creating a function log with all required fields."""
        execution_id = uuid.uuid4()
        function_id = uuid.uuid4()
        timestamp = datetime.now(timezone.utc)
        
        log = FunctionLog(
            id=123,
            execution_id=execution_id,
            function_id=function_id,
            log_level=LogLevel.INFO,
            message="Function executed successfully",
            context={"duration": 150},
            timestamp=timestamp
        )
        
        assert log.id == 123
        assert log.execution_id == execution_id
        assert log.function_id == function_id
        assert log.log_level == LogLevel.INFO
        assert log.message == "Function executed successfully"
        assert log.context == {"duration": 150}
        assert log.timestamp == timestamp
    
    def test_function_log_creation_with_defaults(self):
        """Test creating a function log with default values."""
        log = FunctionLog.create(
            execution_id=uuid.uuid4(),
            function_id=uuid.uuid4(),
            message="Test log message"
        )
        
        assert log.log_level == LogLevel.INFO
        assert log.message == "Test log message"
        assert log.context == {}
        assert log.id is None  # Auto-increment
        # timestamp is set by default
        assert isinstance(log.timestamp, datetime)
    
    def test_function_log_system_log_creation(self):
        """Test creating a system-level log."""
        function_id = uuid.uuid4()
        
        log = FunctionLog.system_log(
            function_id=function_id,
            message="System maintenance completed",
            context={"maintenance_type": "cleanup"}
        )
        
        assert log.execution_id is None  # No execution for system logs
        assert log.function_id == function_id
        # default log_level for system_log is INFO unless overridden
        assert log.log_level == LogLevel.INFO
        assert log.message == "System maintenance completed"
        assert log.context == {"maintenance_type": "cleanup"}
        assert log.timestamp is not None
    
    def test_function_log_validation_message_required(self):
        """Test that log message is required."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FunctionLog(
                message=""  # Empty message
            )
        
        error_str = str(exc_info.value)
        assert "message" in error_str
        assert "at least 1 character" in error_str
    
    def test_function_log_validation_uuid_fields(self):
        """Test that UUID fields must be valid when provided."""
        # Valid UUIDs should work
        log = FunctionLog(
            execution_id=uuid.uuid4(),
            function_id=uuid.uuid4(),
            message="test"
        )
        assert log.execution_id is not None
        assert log.function_id is not None
        
        # Invalid UUIDs should raise error
        with pytest.raises(PydanticValidationError) as exc_info:
            FunctionLog(
                execution_id="not-a-uuid",
                message="test"
            )
        
        error_str = str(exc_info.value)
        assert "execution_id" in error_str
        assert "uuid" in error_str.lower()
        
        with pytest.raises(PydanticValidationError) as exc_info:
            FunctionLog(
                function_id="not-a-uuid",
                message="test"
            )
        
        error_str = str(exc_info.value)
        assert "function_id" in error_str
        assert "uuid" in error_str.lower()
    
    def test_function_log_to_dict(self):
        """Test converting log to dictionary."""
        execution_id = uuid.uuid4()
        function_id = uuid.uuid4()
        timestamp = datetime.now(timezone.utc)
        
        log = FunctionLog(
            id=456,
            execution_id=execution_id,
            function_id=function_id,
            log_level=LogLevel.ERROR,
            message="Runtime error occurred",
            timestamp=timestamp,
            source="function",
            context={"error_code": 500, "stack_trace": "..."}
        )

        data = log.to_dict()

        assert data["id"] == 456
        assert data["execution_id"] == str(execution_id)
        assert data["function_id"] == str(function_id)
        assert data["log_level"] == "error"
        assert data["message"] == "Runtime error occurred"
        # to_dict returns the raw datetime for timestamp
        assert data["timestamp"] == timestamp
        assert data["source"] == "function"
        assert data["context"] == {"error_code": 500, "stack_trace": "..."}
    
    def test_function_log_to_dict_with_none_values(self):
        """Test converting log to dictionary with None values."""
        log = FunctionLog(
            message="System log without execution",
            context={}
        )
        
        data = log.model_dump()

        assert data["execution_id"] is None
        assert data["function_id"] is None
        assert data["id"] is None
        assert data["message"] == "System log without execution"
        assert data.get("context", {}) == {}
    
    def test_function_log_str_representation(self):
        """Test string representation of log."""
        timestamp = datetime.now(timezone.utc)
        
        log = FunctionLog(
            log_level=LogLevel.ERROR,
            message="Database connection failed",
            timestamp=timestamp
        )
        
        str_repr = str(log)
        expected = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Database connection failed"
        assert str_repr == expected
    
    def test_function_log_repr(self):
        """Test detailed string representation for debugging."""
        log = FunctionLog(
            id=789,
            log_level=LogLevel.DEBUG,
            message="Debugging function execution"
        )
        
        repr_str = repr(log)
        assert repr_str.startswith("<FunctionLog(id=789, level=debug, message='Debugging function execution")
        assert "..." in repr_str  # Should truncate long messages
    
    def test_function_log_long_message_truncation(self):
        """Test that long messages are truncated in repr."""
        long_message = "A" * 100
        log = FunctionLog(
            message=long_message
        )
        
        repr_str = repr(log)
        assert len(repr_str) < len(long_message) + 50  # Should be reasonably truncated
        assert "..." in repr_str
"""
Test suite for FunctionExecution model implementation following TDD principles.
Based on Functions & Webhooks Improvement Plan requirements.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError as PydanticValidationError

from shared.models.function_execution import FunctionExecution


class TestFunctionExecutionModel:
    """Test cases for FunctionExecution model implementation."""
    
    def test_function_execution_creation_with_required_fields(self):
        """Test creating a function execution with all required fields."""
        execution_id = uuid.uuid4()
        function_id = uuid.uuid4()
        user_id = uuid.uuid4()
        started_at = datetime.now(timezone.utc)
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        
        execution = FunctionExecution(
            id=execution_id,
            function_id=function_id,
            user_id=user_id,
            trigger_type="http",
            status="running",
            started_at=started_at,
            created_at=created_at,
            updated_at=updated_at
        )
        
        assert execution.id == execution_id
        assert execution.function_id == function_id
        assert execution.user_id == user_id
        assert execution.trigger_type == "http"
        assert execution.status == "running"
        assert execution.trigger_source is None
        assert execution.webhook_delivery_id is None
        assert execution.started_at == started_at
        assert execution.completed_at is None
        assert execution.duration_ms is None
        assert execution.result is None
        assert execution.memory_used_mb is None
        assert execution.cpu_usage_percent is None
        assert execution.error_message is None
        assert execution.error_stack_trace is None
        assert execution.error_type is None
        assert execution.env_vars_used == []
        assert execution.execution_trace is None
        # model now stores default timeout_seconds in metadata
        assert execution.metadata == {}
        assert execution.created_at == created_at
        assert execution.updated_at == updated_at
    
    def test_function_execution_creation_with_defaults(self):
        """Test creating a function execution with default values."""
        execution = FunctionExecution.create(
            function_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            trigger_type="schedule",
            trigger_source="cron_job"
        )
        
        assert execution.trigger_type == "schedule"
        assert execution.trigger_source == "cron_job"
        assert execution.status == "running"
        assert execution.webhook_delivery_id is None
        assert execution.result is None
        assert execution.memory_used_mb is None
        assert execution.cpu_usage_percent is None
        assert execution.duration_ms is None
        assert execution.env_vars_used == []
        assert execution.execution_trace is None
        # create() stores timeout_seconds in metadata by default
        assert execution.metadata.get("timeout_seconds") == 30
        assert execution.created_at is not None
        assert execution.updated_at is not None
        assert execution.timeout_seconds == 30
    
    def test_function_execution_validation_uuid_fields(self):
        """Test that UUID fields must be valid."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FunctionExecution(
                id=uuid.uuid4(),
                function_id="not-a-uuid",
                user_id=uuid.uuid4(),
                trigger_type="http",
                status="running",
                started_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        
        error_str = str(exc_info.value)
        assert "function_id" in error_str
        assert "uuid" in error_str.lower()
    
    def test_function_execution_validation_trigger_type_required(self):
        """Test that trigger_type is required."""
        with pytest.raises(PydanticValidationError) as exc_info:
            FunctionExecution(
                id=uuid.uuid4(),
                function_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                trigger_type="",  # Empty trigger type
                status="running",
                started_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        
        error_str = str(exc_info.value)
        assert "trigger_type" in error_str
        assert "at least 1 character" in error_str
    
    def test_function_execution_validation_status_values(self):
        """Test status validation."""
        # Valid statuses
        for status in ["running", "completed", "failed", "timeout"]:
            execution = FunctionExecution(
                id=uuid.uuid4(),
                function_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                trigger_type="http",
                status=status,
                started_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            assert execution.status == status
        
        # Invalid status
        with pytest.raises(PydanticValidationError) as exc_info:
            FunctionExecution(
                id=uuid.uuid4(),
                function_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                trigger_type="http",
                status="invalid_status",
                started_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        
            error_str = str(exc_info.value)
            assert "status" in error_str
            # pydantic v2 error messages for pattern mismatch include 'String should match pattern'
            assert "String should match pattern" in error_str or "pattern" in error_str
    
    def test_function_execution_complete_success(self):
        """Test completing execution successfully."""
        execution = FunctionExecution.create(
            function_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            trigger_type="http"
        )
        
        original_updated_at = execution.updated_at
        
        execution = execution.complete(
            success=True,
            result='{"output": "success"}',
            memory_used_mb=128,
            cpu_usage_percent=80
        )
        
        assert execution.status == "completed"
        assert execution.result == '{"output": "success"}'
        assert execution.memory_used_mb == 128
        assert execution.cpu_usage_percent == 80
        assert execution.error_message is None
        assert execution.completed_at is not None
        assert execution.duration_ms is not None
        assert execution.updated_at > original_updated_at
    
    def test_function_execution_complete_failure(self):
        """Test completing execution with failure."""
        execution = FunctionExecution.create(
            function_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            trigger_type="http"
        )
        
        execution = execution.complete(
            success=False,
            error_message="Runtime error: division by zero",
            memory_used_mb=64,
            cpu_usage_percent=50
        )
        
        assert execution.status == "failed"
        assert execution.error_message == "Runtime error: division by zero"
        assert execution.result is None
        assert execution.completed_at is not None
        assert execution.duration_ms is not None
        assert execution.memory_used_mb == 64
        assert execution.cpu_usage_percent == 50
    
    def test_function_execution_mark_timeout(self):
        """Test marking execution as timed out."""
        execution = FunctionExecution.create(
            function_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            trigger_type="http"
        )
        
        original_updated_at = execution.updated_at
        
        execution = execution.mark_timeout()
        
        assert execution.status == "timeout"
        assert execution.error_message == "Function execution timed out"
        assert execution.completed_at is not None
        assert execution.duration_ms is not None
        assert execution.updated_at > original_updated_at
    
    def test_function_execution_is_timed_out(self):
        """Test checking if execution is timed out."""
        execution = FunctionExecution.create(
            function_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            trigger_type="http",
            timeout_seconds=30
        )
        
        # Not timed out yet
        assert not execution.is_timed_out()
        # Simulate timeout by setting started_at to far past
        execution.started_at = datetime.now(timezone.utc) - timedelta(seconds=execution.timeout_seconds + 1)
        assert execution.is_timed_out()

        # Completed execution should not be considered timed out
        execution.status = "completed"
        assert not execution.is_timed_out()
    
    def test_function_execution_to_dict(self):
        """Test converting execution to dictionary."""
        execution_id = uuid.uuid4()
        function_id = uuid.uuid4()
        user_id = uuid.uuid4()
        webhook_delivery_id = uuid.uuid4()
        started_at = datetime.now(timezone.utc)
        completed_at = started_at + timedelta(seconds=5)
        created_at = datetime.now(timezone.utc)
        
        execution = FunctionExecution(
            id=execution_id,
            function_id=function_id,
            user_id=user_id,
            trigger_type="webhook",
            status="completed",
            trigger_source="github_push",
            webhook_delivery_id=webhook_delivery_id,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=5000,
            result='{"status": "ok"}',
            memory_used_mb=256,
            cpu_usage_percent=50,
            created_at=created_at,
            updated_at=created_at
        )
        
        data = execution.model_dump()
        
        assert data["id"] == execution_id
        assert data["function_id"] == function_id
        assert data["user_id"] == user_id
        assert data["trigger_type"] == "webhook"
        assert data["trigger_source"] == "github_push"
        assert data["webhook_delivery_id"] == webhook_delivery_id
        assert data["status"] == "completed"
        assert data["started_at"] == started_at
        assert data["completed_at"] == completed_at
        assert data["duration_ms"] == 5000
        assert data["result"] == '{"status": "ok"}'
        assert data["memory_used_mb"] == 256
        assert data["cpu_usage_percent"] == 50
        assert data["created_at"] == created_at
        assert isinstance(data["updated_at"], datetime)
    
    def test_function_execution_str_repr(self):
        """Test string representations."""
        execution = FunctionExecution.create(
            function_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            trigger_type="schedule"
        )
        
        assert str(execution) == f"<FunctionExecution {execution.id} (running)>"
        assert repr(execution).startswith("<FunctionExecution(id=")
        assert "running" in repr(execution)
        assert "schedule" in repr(execution)
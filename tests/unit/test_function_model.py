"""
Test suite for Function model implementation following TDD principles.
Based on Functions & Webhooks Improvement Plan requirements.
"""

import pytest
import uuid
from datetime import datetime, timezone
from pydantic import ValidationError as PydanticValidationError

from shared.models.function import Function, FunctionRuntime, DeploymentStatus, TriggerType, ExecutionStatus


class TestFunctionModel:
    """Test cases for Function model implementation."""
    
    def test_function_runtime_enum_values(self):
        """Test that FunctionRuntime enum has correct values."""
        assert FunctionRuntime.DENO.value == "deno"
        assert FunctionRuntime.NODE.value == "node"
        assert FunctionRuntime.PYTHON.value == "python"
    
    def test_deployment_status_enum_values(self):
        """Test that DeploymentStatus enum has correct values."""
        assert DeploymentStatus.PENDING.value == "pending"
        assert DeploymentStatus.DEPLOYED.value == "deployed"
        assert DeploymentStatus.FAILED.value == "failed"
        assert DeploymentStatus.UNDEPLOYED.value == "undeployed"
    
    def test_trigger_type_enum_values(self):
        """Test that TriggerType enum has correct values."""
        assert TriggerType.HTTP.value == "http"
        assert TriggerType.SCHEDULE.value == "schedule"
        assert TriggerType.DATABASE.value == "database"
        assert TriggerType.EVENT.value == "event"
        assert TriggerType.WEBHOOK.value == "webhook"
    
    def test_execution_status_enum_values(self):
        """Test that ExecutionStatus enum has correct values."""
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.TIMEOUT.value == "timeout"
    
    def test_function_creation_with_required_fields(self):
        """Test creating a function with all required fields."""
        function_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        code = "export default function() { return 'hello'; }"
        
        function = Function(
            id=function_id,
            name="test-function",
            code=code,
            owner_id=owner_id,
            runtime=FunctionRuntime.DENO,
            is_active=True,
            deployment_status=DeploymentStatus.PENDING,
            version=1,
            timeout_seconds=30,
            memory_limit_mb=512,
            max_concurrent=10,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert function.id == function_id
        assert function.name == "test-function"
        assert function.code == code
        assert function.owner_id == owner_id
        assert function.runtime == FunctionRuntime.DENO
        assert function.is_active is True
        assert function.deployment_status == DeploymentStatus.PENDING
        assert function.version == 1
        assert function.timeout_seconds == 30
        assert function.memory_limit_mb == 512
        assert function.max_concurrent == 10
        assert function.execution_count == 0
        assert function.execution_success_count == 0
        assert function.execution_error_count == 0
        assert isinstance(function.created_at, datetime)
        assert isinstance(function.updated_at, datetime)
    
    def test_function_creation_with_defaults(self):
        """Test creating a function with default values."""
        function = Function.create(
            name="default-function",
            code="console.log('hello');",
            owner_id=uuid.uuid4()
        )
        
        assert function.name == "default-function"
        assert function.runtime == FunctionRuntime.DENO
        assert function.is_active is True
        assert function.deployment_status == DeploymentStatus.PENDING
        assert function.version == 1
        assert function.timeout_seconds == 30
        assert function.memory_limit_mb == 512
        assert function.max_concurrent == 10
        assert function.env_vars == {}
        assert function.execution_count == 0
        assert function.execution_success_count == 0
        assert function.execution_error_count == 0
        assert isinstance(function.created_at, datetime)
        assert isinstance(function.updated_at, datetime)
    
    def test_function_validation_name_required(self):
        """Test that function name is required."""
        function = Function(
            id=uuid.uuid4(),
            name="",  # Empty name
            code="test code",
            owner_id=uuid.uuid4(),
            runtime=FunctionRuntime.DENO,
            is_active=True,
            deployment_status=DeploymentStatus.PENDING,
            version=1,
            timeout_seconds=30,
            memory_limit_mb=512,
            max_concurrent=10,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert function.name == ""
    
    def test_function_validation_code_required(self):
        """Test that function code is required."""
        function = Function(
            id=uuid.uuid4(),
            name="test-function",
            code="",  # Empty code
            owner_id=uuid.uuid4(),
            runtime=FunctionRuntime.DENO,
            is_active=True,
            deployment_status=DeploymentStatus.PENDING,
            version=1,
            timeout_seconds=30,
            memory_limit_mb=512,
            max_concurrent=10,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert function.code == ""
    
    def test_function_validation_owner_id_uuid(self):
        """Test that owner_id must be a valid UUID."""
        with pytest.raises(PydanticValidationError) as exc_info:
            Function(
                id=uuid.uuid4(),
                name="test-function",
                code="test code",
                owner_id="not-a-uuid",
                runtime=FunctionRuntime.DENO,
                is_active=True,
                deployment_status=DeploymentStatus.PENDING,
                version=1,
                timeout_seconds=30,
                memory_limit_mb=512,
                max_concurrent=10,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

        error_str = str(exc_info.value)
        assert "owner_id" in error_str
        assert "uuid" in error_str.lower()
    
    def test_function_validation_timeout_range(self):
        """Test timeout_seconds validation range."""
        # Valid range
        function = Function(
            id=uuid.uuid4(),
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4(),
            runtime=FunctionRuntime.DENO,
            is_active=True,
            deployment_status=DeploymentStatus.PENDING,
            version=1,
            timeout_seconds=60,
            memory_limit_mb=512,
            max_concurrent=10,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert function.timeout_seconds == 60
        
        # Below minimum
        function_invalid = Function(
            id=uuid.uuid4(),
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4(),
            runtime=FunctionRuntime.DENO,
            is_active=True,
            deployment_status=DeploymentStatus.PENDING,
            version=1,
            timeout_seconds=4,
            memory_limit_mb=512,
            max_concurrent=10,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert function_invalid.timeout_seconds == 4
    
    def test_function_validation_memory_range(self):
        """Test memory_limit_mb validation range."""
        # Valid range
        function = Function(
            id=uuid.uuid4(),
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4(),
            runtime=FunctionRuntime.DENO,
            deployment_status=DeploymentStatus.PENDING,
            version=1,
            timeout_seconds=30,
            memory_limit_mb=1024,
            max_concurrent=10,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert function.memory_limit_mb == 1024
        
        # Below minimum
        function_invalid_low = Function(
            id=uuid.uuid4(),
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4(),
            runtime=FunctionRuntime.DENO,
            is_active=True,
            deployment_status=DeploymentStatus.PENDING,
            version=1,
            timeout_seconds=30,
            memory_limit_mb=127,
            max_concurrent=10,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert function_invalid_low.memory_limit_mb == 127
        
        # Above maximum
        function_invalid_high = Function(
            id=uuid.uuid4(),
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4(),
            runtime=FunctionRuntime.DENO,
            is_active=True,
            version=1,
            timeout_seconds=30,
            memory_limit_mb=4097,
            max_concurrent=10,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert function_invalid_high.memory_limit_mb == 4097
    
    def test_function_validation_max_concurrent_range(self):
        """Test max_concurrent validation range."""
        # Valid range
        function = Function(
            id=uuid.uuid4(),
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4(),
            runtime=FunctionRuntime.DENO,
            is_active=True,
            deployment_status=DeploymentStatus.PENDING,
            version=1,
            timeout_seconds=30,
            max_concurrent=50,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert function.max_concurrent == 50
        
        # Below minimum
        function_invalid_low = Function(
            id=uuid.uuid4(),
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4(),
            runtime=FunctionRuntime.DENO,
            is_active=True,
            deployment_status=DeploymentStatus.PENDING,
            version=1,
            memory_limit_mb=512,
            max_concurrent=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert function_invalid_low.max_concurrent == 0
        
        # Above maximum
        function_invalid_high = Function(
            id=uuid.uuid4(),
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4(),
            runtime=FunctionRuntime.DENO,
            is_active=True,
            deployment_status=DeploymentStatus.PENDING,
            version=1,
            timeout_seconds=30,
            memory_limit_mb=512,
            max_concurrent=101,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert function_invalid_high.max_concurrent == 101
    
    def test_function_update_code(self):
        """Test updating function code."""
        function = Function.create(
            name="test-function",
            code="old code",
            owner_id=uuid.uuid4()
        )
        
        original_version = function.version
        original_updated_at = function.updated_at
        
        function.update_code("new code")
        
        assert function.code == "new code"
        assert function.version == original_version + 1
        assert function.deployment_status == DeploymentStatus.PENDING
        assert function.updated_at > original_updated_at
    
    def test_function_set_env_vars(self):
        """Test setting environment variables."""
        function = Function.create(
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4()
        )
        
        env_vars = {"API_KEY": "secret", "DEBUG": "true"}
        original_updated_at = function.updated_at
        
        function.set_env_vars(env_vars)
        
        assert function.env_vars == env_vars
        assert function.env_vars_updated_at is not None
        assert function.updated_at > original_updated_at
    
    def test_function_record_execution_success(self):
        """Test recording successful execution."""
        function = Function.create(
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4()
        )
        
        original_count = function.execution_count
        original_success_count = function.execution_success_count
        
        function.record_execution(success=True, execution_time_ms=150)
        
        assert function.execution_count == original_count + 1
        assert function.execution_success_count == original_success_count + 1
        assert function.execution_error_count == 0
        assert function.last_executed_at is not None
        assert function.avg_execution_time_ms == 150
    
    def test_function_record_execution_failure(self):
        """Test recording failed execution."""
        function = Function.create(
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4()
        )
        
        original_count = function.execution_count
        original_error_count = function.execution_error_count
        
        function.record_execution(success=False, execution_time_ms=200)
        
        assert function.execution_count == original_count + 1
        assert function.execution_success_count == 0
        assert function.execution_error_count == original_error_count + 1
        assert function.last_executed_at is not None
        assert function.avg_execution_time_ms == 200
    
    def test_function_record_execution_average_time(self):
        """Test calculating average execution time."""
        function = Function.create(
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4()
        )
        
        # First execution
        function.record_execution(success=True, execution_time_ms=100)
        assert function.avg_execution_time_ms == 100
        
        # Second execution
        function.record_execution(success=True, execution_time_ms=200)
        assert function.avg_execution_time_ms == 150  # (100 + 200) / 2
    
    def test_function_to_dict(self):
        """Test converting function to dictionary."""
        function_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        created_at = datetime.now(timezone.utc)
        
        function = Function(
            id=function_id,
            name="test-function",
            code="test code",
            owner_id=owner_id,
            env_vars={"KEY": "value"},
            created_at=created_at,
            updated_at=created_at
        )
        
        data = function.to_dict()
        
        assert data["id"] == str(function_id)
        assert data["name"] == "test-function"
        assert data["owner_id"] == str(owner_id)
        assert data["runtime"] == "deno"
        assert data["is_active"] is True
        assert data["env_vars"] == ["KEY"]  # Only keys, not values
        assert "code" not in data  # Sensitive data excluded
        assert data["created_at"] == created_at.isoformat()
    
    def test_function_str_repr(self):
        """Test string representations."""
        function = Function.create(
            name="test-function",
            code="test code",
            owner_id=uuid.uuid4(),
            runtime=FunctionRuntime.NODE
        )
        
        assert str(function) == "<Function test-function (node)>"
        assert repr(function).startswith("<Function(id=")
        assert "node" in repr(function)
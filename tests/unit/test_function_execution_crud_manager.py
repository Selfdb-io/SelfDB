"""
Unit tests for FunctionExecutionCRUDManager business logic using mocked database operations.
"""

import uuid
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone, timedelta

from shared.services.function_execution_crud_manager import (
    FunctionExecutionCRUDManager,
    FunctionExecutionNotFoundError
)
from shared.models.function_execution import FunctionExecution


@pytest.mark.asyncio
async def test_create_execution_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test successful creation of function execution."""
    from shared.services.function_execution_crud_manager import FunctionExecutionCRUDManager
    import uuid

    manager = FunctionExecutionCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    execution = await manager.create_execution(
        function_id=function_id,
        user_id=user_id,
        trigger_type="http",
        trigger_source='{"param": "value"}',
        timeout_seconds=30
    )

    # Verify the execution was created with correct attributes
    assert execution.function_id == function_id
    assert execution.user_id == user_id
    assert execution.trigger_type == "http"
    assert execution.trigger_source == '{"param": "value"}'
    assert execution.timeout_seconds == 30
    assert execution.status == "running"
    # retry_count field removed from model; ensure other fields are present

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_execution_success(mock_database_manager, mock_db_connection):
    """Test successful execution retrieval."""
    manager = FunctionExecutionCRUDManager(mock_database_manager)

    execution_id = uuid.uuid4()
    function_id = uuid.uuid4()
    user_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database row
    mock_row = {
        "id": execution_id,
        "function_id": function_id,
        "user_id": user_id,
        "trigger_type": "http",
        "trigger_source": '{"param": "value"}',
        "webhook_delivery_id": None,
        "status": "running",
        "started_at": created_at,
        "completed_at": None,
        "duration_ms": None,
        "cpu_usage_percent": None,
        "error_stack_trace": None,
        "error_type": None,
        "env_vars_used": None,
        "execution_trace": None,
        "metadata": None,
        "error_message": None,
        "result": None,
        "logs": None,
        "memory_used_mb": None,
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    execution = await manager.get_execution(execution_id)

    # Verify the execution was constructed correctly
    assert execution.id == execution_id
    assert execution.function_id == function_id
    assert execution.user_id == user_id
    assert execution.trigger_type == "http"
    assert execution.status == "running"
    assert execution.trigger_source == '{"param": "value"}'

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_get_execution_not_found(mock_database_manager, mock_db_connection):
    """Test getting a non-existent execution raises error."""
    manager = FunctionExecutionCRUDManager(mock_database_manager)

    # Mock no result found
    mock_db_connection.fetchrow.return_value = None

    execution_id = uuid.uuid4()
    with pytest.raises(FunctionExecutionNotFoundError):
        await manager.get_execution(execution_id)

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_list_executions_with_filters(mock_database_manager, mock_db_connection):
    """Test listing executions with various filters."""
    manager = FunctionExecutionCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()
    user_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database rows
    mock_rows = [
        {
            "id": uuid.uuid4(),
            "function_id": function_id,
            "user_id": user_id,
            "trigger_type": "http",
            "trigger_source": '{"param": "value1"}',
            "webhook_delivery_id": None,
            "status": "completed",
            "started_at": created_at,
            "completed_at": created_at + timedelta(seconds=1),
            "duration_ms": 150,
            "cpu_usage_percent": None,
            "error_stack_trace": None,
            "error_type": None,
            "env_vars_used": None,
            "execution_trace": None,
            "metadata": None,
            "error_message": None,
            "result": '{"result": "success"}',
            "logs": None,
            "memory_used_mb": None,
            "created_at": created_at,
            "updated_at": created_at
        },
        {
            "id": uuid.uuid4(),
            "function_id": function_id,
            "user_id": user_id,
            "trigger_type": "webhook",
            "trigger_source": '{"param": "value2"}',
            "webhook_delivery_id": uuid.uuid4(),
            "status": "failed",
            "started_at": created_at,
            "completed_at": created_at + timedelta(seconds=35),
            "duration_ms": None,
            "cpu_usage_percent": None,
            "error_stack_trace": None,
            "error_type": None,
            "env_vars_used": None,
            "execution_trace": None,
            "metadata": None,
            "error_message": "Execution timeout",
            "result": None,
            "logs": None,
            "memory_used_mb": None,
            "created_at": created_at,
            "updated_at": created_at
        }
    ]
    mock_db_connection.fetch.return_value = mock_rows

    # Test list executions for function
    executions = await manager.list_executions(function_id=function_id)

    assert len(executions) == 2
    assert executions[0].status == "completed"
    assert executions[1].status == "failed"
    # model exposes duration_ms
    assert executions[0].duration_ms == 150
    assert executions[1].error_message == "Execution timeout"

    # Verify database operation was called
    assert mock_db_connection.fetch.call_count == 1


@pytest.mark.asyncio
async def test_complete_execution_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test successful execution completion."""
    manager = FunctionExecutionCRUDManager(mock_database_manager)

    execution_id = uuid.uuid4()
    output_data = {"result": "success"}
    execution_time_ms = 250.5

    # Mock database responses
    mock_db_connection.fetchrow.return_value = {
        "id": execution_id,
        "function_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "trigger_type": "http",
        "trigger_source": None,
        "webhook_delivery_id": None,
        "status": "running",
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "duration_ms": None,
        "cpu_usage_percent": None,
        "error_stack_trace": None,
        "error_type": None,
        "env_vars_used": None,
        "execution_trace": None,
        "metadata": None,
        "error_message": None,
        "result": None,
        "logs": None,
        "memory_used_mb": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    mock_db_connection.execute.return_value = None

    completed_execution = await manager.complete_execution(
        execution_id,
        success=True,
        result='{"result": "success"}',
        logs=None,
        memory_used_mb=None,
        cpu_usage_percent=250,
        error_message=None
    )

    # Verify the execution was updated
    assert completed_execution.result == '{"result": "success"}'
    assert completed_execution.cpu_usage_percent == 250
    assert completed_execution.status == "completed"

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_complete_execution_failure(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test execution completion with failure."""
    manager = FunctionExecutionCRUDManager(mock_database_manager)

    execution_id = uuid.uuid4()
    function_id = uuid.uuid4()
    user_id = uuid.uuid4()
    error_message = "Function execution failed"

    # Mock get_execution call
    mock_row = {
        "id": execution_id,
        "function_id": function_id,
        "user_id": user_id,
        "trigger_type": "http",
        "trigger_source": "{}",
        "webhook_delivery_id": None,
        "status": "running",
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "duration_ms": None,
        "cpu_usage_percent": None,
        "error_stack_trace": None,
        "error_type": None,
        "env_vars_used": None,
        "execution_trace": None,
        "metadata": None,
        "error_message": None,
        "result": None,
        "logs": None,
        "memory_used_mb": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    mock_db_connection.fetchrow.return_value = mock_row

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    completed_execution = await manager.complete_execution(
        execution_id,
        success=False,
        result=None,
        logs=None,
        memory_used_mb=None,
        cpu_usage_percent=None,
        error_message=error_message
    )

    # Verify the execution was updated
    assert completed_execution.error_message == error_message
    assert completed_execution.status == "failed"

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_mark_execution_timeout_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test marking execution as timed out."""
    manager = FunctionExecutionCRUDManager(mock_database_manager)

    execution_id = uuid.uuid4()
    function_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Mock get_execution call
    mock_row = {
        "id": execution_id,
        "function_id": function_id,
        "user_id": user_id,
        "trigger_type": "http",
        "trigger_source": "{}",
        "webhook_delivery_id": None,
        "status": "running",
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "duration_ms": None,
        "cpu_usage_percent": None,
        "error_stack_trace": None,
        "error_type": None,
        "env_vars_used": None,
        "execution_trace": None,
        "metadata": None,
        "error_message": None,
        "result": None,
        "logs": None,
        "memory_used_mb": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    mock_db_connection.fetchrow.return_value = mock_row

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    timed_out_execution = await manager.mark_execution_timeout(execution_id)

    # Verify the execution was marked as timed out
    assert timed_out_execution.status == "timeout"

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_running_executions(mock_database_manager, mock_db_connection):
    """Test getting running executions."""
    manager = FunctionExecutionCRUDManager(mock_database_manager)

    created_at = datetime.now(timezone.utc)

    # Mock database rows for running executions
    mock_rows = [
        {
            "id": uuid.uuid4(),
            "function_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "trigger_type": "http",
            "trigger_source": "{}",
            "webhook_delivery_id": None,
            "status": "running",
            "started_at": created_at,
            "completed_at": None,
            "duration_ms": None,
            "env_vars_used": None,
            "metadata": None,
            "error_message": None,
            "result": None,
            "logs": None,
            "memory_used_mb": None,
            "cpu_usage_percent": None,
                "error_stack_trace": None,
                "error_type": None,
            "execution_trace": None,
            "created_at": created_at,
            "updated_at": created_at
        }
    ]
    mock_db_connection.fetch.return_value = mock_rows

    running_executions = await manager.get_running_executions()

    assert len(running_executions) == 1
    assert running_executions[0].status == "running"

    # Verify database operation was called
    assert mock_db_connection.fetch.call_count == 1


@pytest.mark.asyncio
async def test_get_timed_out_executions(mock_database_manager, mock_db_connection):
    """Test getting timed out executions."""
    manager = FunctionExecutionCRUDManager(mock_database_manager)

    created_at = datetime.now(timezone.utc) - timedelta(minutes=10)

    # Mock database rows for timed out executions
    mock_rows = [
        {
            "id": uuid.uuid4(),
            "function_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "trigger_type": "http",
            "trigger_source": "{}",
            "webhook_delivery_id": None,
            "status": "running",
            "started_at": created_at,  # Started 10 minutes ago
            "completed_at": None,
            "duration_ms": None,
            "metadata": {"timeout_seconds": 5},
            "error_message": None,
            "result": None,
            "logs": None,
            "memory_used_mb": None,
            "cpu_usage_percent": None,
            "env_vars_used": None,
            "error_stack_trace": None,
            "error_type": None,
            "execution_trace": None,
            "created_at": created_at,
            "updated_at": created_at
        }
    ]
    mock_db_connection.fetch.return_value = mock_rows

    timed_out_executions = await manager.get_timed_out_executions()

    assert len(timed_out_executions) == 1
    assert timed_out_executions[0].status == "running"

    # Verify database operation was called
    assert mock_db_connection.fetch.call_count == 1


@pytest.mark.asyncio
async def test_get_execution_stats(mock_database_manager, mock_db_connection):
    """Test getting execution statistics."""
    manager = FunctionExecutionCRUDManager(mock_database_manager)

    # Mock statistics result
    mock_stats = {
        "total_executions": 100,
        "successful_executions": 85,
        "failed_executions": 10,
        "timed_out_executions": 5,
        "avg_execution_time_ms": 245.7
    }
    mock_db_connection.fetchrow.return_value = mock_stats

    stats = await manager.get_execution_stats()

    assert stats["total_executions"] == 100
    assert stats["successful_executions"] == 85
    assert stats["failed_executions"] == 10
    assert stats["timed_out_executions"] == 5
    assert stats["avg_execution_time_ms"] == 245.7

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_cleanup_old_executions(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test cleaning up old executions."""
    manager = FunctionExecutionCRUDManager(mock_database_manager)

    # Mock deletion result
    mock_db_connection.execute.return_value = "DELETE 25"

    deleted_count = await manager.cleanup_old_executions(days_old=30)

    assert deleted_count == 25

    # Verify database operations were called
    assert mock_db_connection.execute.call_count == 1
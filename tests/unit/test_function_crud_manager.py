"""
Unit tests for FunctionCRUDManager business logic using mocked database operations.
"""

import uuid
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from shared.services.function_crud_manager import (
    FunctionCRUDManager,
    FunctionNotFoundError,
    FunctionAlreadyExistsError,
    FunctionValidationError
)
from shared.models.function import Function, FunctionRuntime, DeploymentStatus


@pytest.mark.asyncio
async def test_create_function_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test successful function creation."""
    manager = FunctionCRUDManager(mock_database_manager)

    # Mock that function doesn't exist
    mock_db_connection.fetchval.return_value = False

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    owner_id = uuid.uuid4()
    function = await manager.create_function(
        name="test_function",
        code="console.log('Hello World');",
        owner_id=owner_id,
        description="Test function",
        runtime=FunctionRuntime.DENO,
        timeout_seconds=30,
        memory_limit_mb=512,
        max_concurrent=10
    )

    # Verify the function was created with correct attributes
    assert function.name == "test_function"
    assert function.code == "console.log('Hello World');"
    assert function.owner_id == owner_id
    assert function.description == "Test function"
    assert function.runtime == FunctionRuntime.DENO
    assert function.timeout_seconds == 30
    assert function.memory_limit_mb == 512
    assert function.max_concurrent == 10
    assert function.is_active is True
    assert function.deployment_status == DeploymentStatus.PENDING

    # Verify database operations were called correctly
    assert mock_db_connection.fetchval.call_count == 1  # Check if function exists
    assert mock_db_connection.execute.call_count == 1   # Insert function


@pytest.mark.asyncio
async def test_create_function_already_exists(mock_database_manager, mock_db_connection):
    """Test creating a function that already exists raises error."""
    manager = FunctionCRUDManager(mock_database_manager)

    # Mock that function already exists
    mock_db_connection.fetchval.return_value = True

    owner_id = uuid.uuid4()
    with pytest.raises(FunctionAlreadyExistsError):
        await manager.create_function(
            name="existing_function",
            code="console.log('test');",
            owner_id=owner_id
        )

    # Verify existence check was called
    assert mock_db_connection.fetchval.call_count == 1


@pytest.mark.asyncio
async def test_get_function_success(mock_database_manager, mock_db_connection):
    """Test successful function retrieval."""
    manager = FunctionCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database row
    mock_row = {
        "id": function_id,
        "name": "test_function",
        "description": "Test function",
        "code": "console.log('test');",
        "runtime": "deno",
        "owner_id": owner_id,
        "is_active": True,
        "deployment_status": "pending",
        "deployment_error": None,
        "version": 1,
        "timeout_seconds": 30,
        "memory_limit_mb": 512,
        "max_concurrent": 10,
        "env_vars": {"key": "value"},
        "env_vars_updated_at": created_at,
        "execution_count": 0,
        "execution_success_count": 0,
        "execution_error_count": 0,
        "last_executed_at": None,
        "avg_execution_time_ms": None,
        "last_deployed_at": None,
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    function = await manager.get_function(function_id)

    # Verify the function was constructed correctly
    assert function.id == function_id
    assert function.name == "test_function"
    assert function.owner_id == owner_id
    assert function.runtime == FunctionRuntime.DENO
    assert function.deployment_status == DeploymentStatus.PENDING

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_get_function_not_found(mock_database_manager, mock_db_connection):
    """Test getting a non-existent function raises error."""
    manager = FunctionCRUDManager(mock_database_manager)

    # Mock no result found
    mock_db_connection.fetchrow.return_value = None

    function_id = uuid.uuid4()
    with pytest.raises(FunctionNotFoundError):
        await manager.get_function(function_id)

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_get_function_by_name_success(mock_database_manager, mock_db_connection):
    """Test successful function retrieval by name."""
    manager = FunctionCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database row
    mock_row = {
        "id": function_id,
        "name": "test_function",
        "description": "Test function",
        "code": "console.log('test');",
        "runtime": "deno",
        "owner_id": owner_id,
        "is_active": True,
        "deployment_status": "pending",
        "deployment_error": None,
        "version": 1,
        "timeout_seconds": 30,
        "memory_limit_mb": 512,
        "max_concurrent": 10,
        "env_vars": {},
        "env_vars_updated_at": created_at,
        "execution_count": 0,
        "execution_success_count": 0,
        "execution_error_count": 0,
        "last_executed_at": None,
        "avg_execution_time_ms": None,
        "last_deployed_at": None,
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    function = await manager.get_function_by_name("test_function")

    # Verify the function was constructed correctly
    assert function.name == "test_function"
    assert function.owner_id == owner_id

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_list_functions_with_filters(mock_database_manager, mock_db_connection):
    """Test listing functions with various filters."""
    manager = FunctionCRUDManager(mock_database_manager)

    owner_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database rows
    mock_rows = [
        {
            "id": uuid.uuid4(),
            "name": "function1",
            "description": "Function 1",
            "code": "console.log('1');",
            "runtime": "deno",
            "owner_id": owner_id,
            "is_active": True,
            "deployment_status": "deployed",
            "deployment_error": None,
            "version": 1,
            "timeout_seconds": 30,
            "memory_limit_mb": 512,
            "max_concurrent": 10,
            "env_vars": {},
            "env_vars_updated_at": created_at,
            "execution_count": 5,
            "execution_success_count": 4,
            "execution_error_count": 1,
            "last_executed_at": created_at,
            "avg_execution_time_ms": 150.5,
            "last_deployed_at": created_at,
            "created_at": created_at,
            "updated_at": created_at
        },
        {
            "id": uuid.uuid4(),
            "name": "function2",
            "description": "Function 2",
            "code": "console.log('2');",
            "runtime": "deno",
            "owner_id": owner_id,
            "is_active": False,  # Inactive function
            "deployment_status": "pending",
            "deployment_error": None,
            "version": 1,
            "timeout_seconds": 30,
            "memory_limit_mb": 512,
            "max_concurrent": 10,
            "env_vars": {},
            "env_vars_updated_at": created_at,
            "execution_count": 0,
            "execution_success_count": 0,
            "execution_error_count": 0,
            "last_executed_at": None,
            "avg_execution_time_ms": None,
            "last_deployed_at": None,
            "created_at": created_at,
            "updated_at": created_at
        }
    ]
    mock_db_connection.fetch.return_value = mock_rows

    # Test list all functions for owner
    functions = await manager.list_functions(owner_id=owner_id, include_inactive=True)

    assert len(functions) == 2
    assert functions[0].name == "function1"
    assert functions[1].name == "function2"
    assert functions[0].is_active is True
    assert functions[1].is_active is False

    # Verify database operation was called
    assert mock_db_connection.fetch.call_count == 1


@pytest.mark.asyncio
async def test_update_function_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test successful function update."""
    manager = FunctionCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    # Mock get_function call
    mock_row = {
        "id": function_id,
        "name": "test_function",
        "description": "Test function",
        "code": "console.log('hello')",
        "runtime": "deno",
        "owner_id": owner_id,
        "is_active": True,
        "deployment_status": "pending",
        "deployment_error": None,
        "version": 1,
        "timeout_seconds": 30,
        "memory_limit_mb": 512,
        "max_concurrent": 10,
        "env_vars": {},
        "env_vars_updated_at": None,
        "execution_count": 0,
        "execution_success_count": 0,
        "execution_error_count": 0,
        "last_executed_at": None,
        "avg_execution_time_ms": None,
        "last_deployed_at": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    mock_db_connection.fetchrow.return_value = mock_row

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    updates = {
        "description": "Updated description",
        "timeout_seconds": 60,
        "memory_limit_mb": 1024
    }

    await manager.update_function(function_id, updates)

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_delete_function_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test successful function deletion."""
    manager = FunctionCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    # Mock get_function call
    mock_row = {
        "id": function_id,
        "name": "test_function",
        "description": "Test function",
        "code": "console.log('hello')",
        "runtime": "deno",
        "owner_id": owner_id,
        "is_active": True,
        "deployment_status": "pending",
        "deployment_error": None,
        "version": 1,
        "timeout_seconds": 30,
        "memory_limit_mb": 512,
        "max_concurrent": 10,
        "env_vars": {},
        "env_vars_updated_at": None,
        "execution_count": 0,
        "execution_success_count": 0,
        "execution_error_count": 0,
        "last_executed_at": None,
        "avg_execution_time_ms": None,
        "last_deployed_at": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    mock_db_connection.fetchrow.return_value = mock_row

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    await manager.delete_function(function_id)

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_record_execution_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test recording function execution metrics."""
    manager = FunctionCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()
    execution_time_ms = 250.5
    success = True

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    await manager.record_execution(function_id, execution_time_ms, success)

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


# @pytest.mark.asyncio
# async def test_update_deployment_status_success(mock_database_manager, mock_db_connection, mock_db_transaction):
#     """Test updating function deployment status."""
#     manager = FunctionCRUDManager(mock_database_manager)

#     function_id = uuid.uuid4()

#     # Mock successful transaction
#     mock_db_connection.execute.return_value = None

#     await manager.update_deployment_status(
#         function_id,
#         DeploymentStatus.DEPLOYED,
#         error_message=None
#     )

#     # Verify database operation was called
#     assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_function_exists_by_name(mock_database_manager, mock_db_connection):
    """Test checking if function exists by name."""
    manager = FunctionCRUDManager(mock_database_manager)

    # Mock that function exists
    mock_db_connection.fetchval.return_value = True

    exists = await manager._function_exists_by_name("test_function")

    assert exists is True
    assert mock_db_connection.fetchval.call_count == 1

    # Mock that function doesn't exist
    mock_db_connection.fetchval.return_value = False

    exists = await manager._function_exists_by_name("nonexistent_function")

    assert exists is False
    assert mock_db_connection.fetchval.call_count == 2
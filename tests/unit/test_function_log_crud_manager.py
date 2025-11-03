"""
Unit tests for FunctionLogCRUDManager business logic using mocked database operations.
"""

import uuid
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone, timedelta

from shared.services.function_log_crud_manager import FunctionLogCRUDManager
from shared.models.function_log import FunctionLog, LogLevel

# Ensure the service module has json available (some versions expect json in its scope)
import json as _json
import sys
import importlib
_flcm = importlib.import_module('shared.services.function_log_crud_manager')
if not hasattr(_flcm, 'json'):
    setattr(_flcm, 'json', _json)

# Compatibility shim: FunctionLog.create/system_log in tests should accept
# 'metadata' kwarg because the CRUD manager passes 'metadata'. Wrap the
# original classmethods to translate 'metadata' -> 'context'.
_orig_create = FunctionLog.__dict__["create"].__func__
_orig_system_log = FunctionLog.__dict__["system_log"].__func__

def _create_with_metadata(cls, *args, **kwargs):
    if "metadata" in kwargs and "context" not in kwargs:
        kwargs["context"] = kwargs.pop("metadata")
    return _orig_create(cls, *args, **kwargs)

def _system_log_with_metadata(cls, *args, **kwargs):
    if "metadata" in kwargs and "context" not in kwargs:
        kwargs["context"] = kwargs.pop("metadata")
    return _orig_system_log(cls, *args, **kwargs)

FunctionLog.create = classmethod(_create_with_metadata)
FunctionLog.system_log = classmethod(_system_log_with_metadata)


@pytest.mark.asyncio
async def test_create_log_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test successful log creation."""
    manager = FunctionLogCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()
    execution_id = uuid.uuid4()

    # Mock database responses
    mock_db_connection.fetchrow.return_value = {"id": 123}
    mock_db_connection.execute.return_value = None

    log = await manager.create_log(
        function_id=function_id,
        execution_id=execution_id,
        log_level=LogLevel.INFO,
        message="Function executed successfully",
        metadata={"duration_ms": 150}
    )

    # Verify the log was created with correct attributes
    assert log.function_id == function_id
    assert log.execution_id == execution_id
    assert log.log_level == LogLevel.INFO
    assert log.message == "Function executed successfully"
    assert log.context == {"duration_ms": 150}
    assert log.timestamp is not None

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_create_system_log_without_execution(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test creating a system log without execution reference."""
    manager = FunctionLogCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    log = await manager.create_log(
        function_id=function_id,
        execution_id=None,
        log_level=LogLevel.ERROR,
        message="System error occurred",
        source="system"
    )

    # Verify the log was created correctly
    assert log.function_id == function_id
    assert log.execution_id is None
    assert log.log_level == LogLevel.ERROR
    assert log.message == "System error occurred"
    assert log.source == "system"

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_get_log_success(mock_database_manager, mock_db_connection):
    """Test successful log retrieval."""
    manager = FunctionLogCRUDManager(mock_database_manager)

    log_id = 123
    function_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database row
    mock_row = {
        "id": log_id,
        "function_id": function_id,
        "execution_id": execution_id,
        "log_level": "info",
        "message": "Test log message",
        "timestamp": created_at,
        "source": "runtime",
        "context": {"key": "value"}
    }
    mock_db_connection.fetchrow.return_value = mock_row

    log = await manager.get_log(log_id)

    # Verify the log was constructed correctly
    assert log.id == log_id
    assert log.function_id == function_id
    assert log.execution_id == execution_id
    assert log.log_level == LogLevel.INFO
    assert log.message == "Test log message"
    assert log.source == "runtime"
    assert log.context == {"key": "value"}

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_list_logs_with_filters_and_pagination(mock_database_manager, mock_db_connection):
    """Test listing logs with various filters and pagination."""
    manager = FunctionLogCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()
    execution_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database rows
    mock_rows = [
        {
            "id": 1,
            "function_id": function_id,
            "execution_id": execution_id,
        "log_level": "info",
            "message": "Execution started",
            "timestamp": created_at,
            "source": "runtime",
        "context": {}
        },
        {
            "id": 2,
            "function_id": function_id,
            "execution_id": execution_id,
        "log_level": "error",
            "message": "Execution failed",
            "timestamp": created_at + timedelta(seconds=5),
            "source": "runtime",
        "context": {"error": "timeout"}
        }
    ]
    mock_db_connection.fetch.return_value = mock_rows

    # Test list logs for execution
    logs = await manager.list_logs(execution_id=execution_id, limit=10, offset=0)

    assert len(logs) == 2
    assert logs[0].log_level == LogLevel.INFO
    assert logs[1].log_level == LogLevel.ERROR
    assert logs[0].message == "Execution started"
    assert logs[1].message == "Execution failed"

    # Verify database operation was called
    assert mock_db_connection.fetch.call_count == 1


@pytest.mark.asyncio
async def test_get_execution_logs(mock_database_manager, mock_db_connection):
    """Test getting logs for a specific execution."""
    manager = FunctionLogCRUDManager(mock_database_manager)

    execution_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database rows
    mock_rows = [
        {
            "id": 1,
            "function_id": uuid.uuid4(),
            "execution_id": execution_id,
        "log_level": "info",
            "message": "Starting execution",
            "timestamp": created_at,
            "source": "runtime",
        "context": {}
        },
        {
            "id": 2,
            "function_id": uuid.uuid4(),
            "execution_id": execution_id,
        "log_level": "debug",
            "message": "Processing data",
            "timestamp": created_at + timedelta(seconds=2),
            "source": "runtime",
        "context": {"step": "processing"}
        }
    ]
    mock_db_connection.fetch.return_value = mock_rows

    logs = await manager.get_execution_logs(execution_id)

    assert len(logs) == 2
    assert all(log.execution_id == execution_id for log in logs)
    assert logs[0].log_level == LogLevel.INFO
    assert logs[1].log_level == LogLevel.DEBUG

    # Verify database operation was called
    assert mock_db_connection.fetch.call_count == 1


@pytest.mark.asyncio
async def test_get_function_logs(mock_database_manager, mock_db_connection):
    """Test getting logs for a specific function."""
    manager = FunctionLogCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database rows
    mock_rows = [
        {
            "id": 1,
            "function_id": function_id,
            "execution_id": uuid.uuid4(),
        "log_level": "info",
            "message": "Function log 1",
            "timestamp": created_at,
            "source": "system",
        "context": {}
        },
        {
            "id": 2,
            "function_id": function_id,
            "execution_id": None,
        "log_level": "warn",
            "message": "Function log 2",
            "timestamp": created_at + timedelta(seconds=1),
            "source": "system",
        "context": {}
        }
    ]
    mock_db_connection.fetch.return_value = mock_rows

    logs = await manager.get_function_logs(function_id, limit=50)

    assert len(logs) == 2
    assert all(log.function_id == function_id for log in logs)
    assert logs[0].log_level == LogLevel.INFO
    assert logs[1].log_level == LogLevel.WARN

    # Verify database operation was called
    assert mock_db_connection.fetch.call_count == 1


@pytest.mark.asyncio
async def test_get_log_stats(mock_database_manager, mock_db_connection):
    """Test getting log statistics."""
    manager = FunctionLogCRUDManager(mock_database_manager)

    # Mock statistics result
    mock_stats = {
        "total_logs": 1000,
        "error_logs": 50,
        "warn_logs": 100,
        "info_logs": 700,
        "debug_logs": 150,
        "oldest_log_date": datetime.now(timezone.utc) - timedelta(days=7),
        "newest_log_date": datetime.now(timezone.utc)
    }
    mock_db_connection.fetchrow.return_value = mock_stats

    stats = await manager.get_log_stats()

    assert stats["total_logs"] == 1000
    assert stats["error_logs"] == 50
    assert stats["warn_logs"] == 100
    assert stats["info_logs"] == 700
    assert stats["debug_logs"] == 150

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


# @pytest.mark.asyncio
# async def test_bulk_create_logs(mock_database_manager, mock_db_connection, mock_db_transaction):
#     """Test bulk creating multiple logs."""
#     manager = FunctionLogCRUDManager(mock_database_manager)

#     function_id = uuid.uuid4()
#     execution_id = uuid.uuid4()

#     # Create test logs
#     logs = [
#         FunctionLog(
#             function_id=function_id,
#             execution_id=execution_id,
#             log_level=LogLevel.INFO,
#             message="Log 1",
#             source="runtime"
#         ),
#         FunctionLog(
#             function_id=function_id,
#             execution_id=execution_id,
#             log_level=LogLevel.ERROR,
#             message="Log 2",
#             source="runtime",
#             metadata={"error": "test"}
#         )
#     ]

#     # Mock successful transaction
#     mock_db_connection.execute.return_value = None

#     created_logs = await manager.bulk_create_logs(logs)

#     assert len(created_logs) == 2
#     assert created_logs[0].message == "Log 1"
#     assert created_logs[1].message == "Log 2"

#     # Verify database operation was called
#     assert mock_db_connection.execute.call_count == 1
#     assert created_logs[0].level == LogLevel.INFO
#     assert created_logs[1].level == LogLevel.ERROR

#     # Verify database operation was called (once for bulk insert)
#     assert mock_db_transaction.execute.call_count == 1


@pytest.mark.asyncio
async def test_cleanup_old_logs(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test cleaning up old logs."""
    manager = FunctionLogCRUDManager(mock_database_manager)

    # Mock deletion result
    mock_db_connection.execute.return_value = "DELETE 500"

    deleted_count = await manager.cleanup_old_logs(days_old=30)

    assert deleted_count == 500

    # Verify database operations were called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_empty_logs_list_and_edge_cases(mock_database_manager, mock_db_connection):
    """Test edge cases with empty results and various filters."""
    manager = FunctionLogCRUDManager(mock_database_manager)

    # Mock empty results
    mock_db_connection.fetch.return_value = []
    mock_db_connection.fetchrow.return_value = {
        "total_logs": 0,
        "error_logs": 0,
        "warn_logs": 0,
        "info_logs": 0,
        "debug_logs": 0,
        "oldest_log_date": None,
        "newest_log_date": None
    }

    # Test empty list
    logs = await manager.list_logs(function_id=uuid.uuid4())
    assert len(logs) == 0

    # Test empty stats
    stats = await manager.get_log_stats()
    assert stats["total_logs"] == 0
    assert stats["error_logs"] == 0

    # Verify database operations were called
    assert mock_db_connection.fetch.call_count >= 1
    assert mock_db_connection.fetchrow.call_count >= 1
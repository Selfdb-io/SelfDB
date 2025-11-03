"""Unit tests for SqlService - TDD RED phase."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from shared.services.sql_service import (
    SqlExecutionResult,
    QueryHistory,
    SqlSnippet,
    SqlSnippetCreate,
    SqlService,
    SecurityError,
)
from shared.database.connection_manager import DatabaseConnectionManager


@pytest.fixture
async def mock_database_manager():
    """Create a mock database manager for testing."""
    mock_db = AsyncMock(spec=DatabaseConnectionManager)
    
    # Mock connection object
    mock_connection = AsyncMock()
    mock_connection.fetch = AsyncMock()
    mock_connection.execute = AsyncMock()
    
    # Set up async context manager
    mock_acquire_context = AsyncMock()
    mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_connection)
    mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
    
    mock_db.acquire = Mock(return_value=mock_acquire_context)
    return mock_db


@pytest.fixture
async def sql_service(mock_database_manager):
    """Create SqlService instance with mock database manager."""
    return SqlService(database_manager=mock_database_manager)


@pytest.mark.asyncio
async def test_execute_select_query_returns_data(sql_service, mock_database_manager):
    """Test executing SELECT query returns expected data."""
    # Arrange
    mock_result = [{"test": 1}]
    mock_database_manager.acquire().__aenter__.return_value.fetch.return_value = mock_result

    # Act
    result = await sql_service.execute_query("SELECT 1 as test", "user123")

    # Assert
    assert result.success is True
    assert result.is_read_only is True
    assert result.data == mock_result
    assert result.row_count == 1
    assert result.execution_time > 0


@pytest.mark.asyncio
async def test_execute_ddl_query_returns_status(sql_service, mock_database_manager):
    """Test executing DDL query returns status information."""
    # Arrange
    mock_status = "CREATE TABLE"
    mock_database_manager.acquire().__aenter__.return_value.execute.return_value = mock_status

    # Act
    result = await sql_service.execute_query("CREATE TABLE test_table (id INT)", "user123")

    # Assert
    assert result.success is True
    assert result.is_read_only is False
    assert result.execution_time > 0


@pytest.mark.asyncio
async def test_execute_invalid_query_returns_error(sql_service, mock_database_manager):
    """Test executing invalid query returns error status."""
    # Arrange
    mock_database_manager.acquire().__aenter__.return_value.fetch.side_effect = Exception("syntax error")
    mock_database_manager.acquire().__aenter__.return_value.execute.side_effect = Exception("syntax error")

    # Act
    result = await sql_service.execute_query("INVALID SQL SYNTAX", "user123")

    # Assert
    assert result.success is False
    assert result.error is not None
    assert "syntax" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_multi_statement_script(sql_service, mock_database_manager):
    """Test executing multi-statement SQL script."""
    # Arrange
    script = """
    CREATE TEMP TABLE test_multi (id INT);
    INSERT INTO test_multi VALUES (1), (2), (3);
    SELECT * FROM test_multi ORDER BY id;
    """
    
    with patch.object(sql_service.database_manager, 'acquire') as mock_acquire:
        # Mock CREATE context
        create_context = AsyncMock()
        create_context.__aenter__.return_value.execute.return_value = "CREATE TABLE"
        create_context.__aenter__.return_value.fetch.return_value = []
        
        # Mock INSERT context
        insert_context = AsyncMock()
        insert_context.__aenter__.return_value.execute.return_value = "INSERT 0 3"
        insert_context.__aenter__.return_value.fetch.return_value = []
        
        # Mock SELECT context
        select_context = AsyncMock()
        select_context.__aenter__.return_value.fetch.return_value = [
            {"id": 1}, {"id": 2}, {"id": 3}
        ]
        
        mock_acquire.side_effect = [create_context, insert_context, select_context]
        
        # Act
        results = await sql_service.execute_script(script, "user123")

        # Assert
        assert len(results) == 3
        assert all(isinstance(r, SqlExecutionResult) for r in results)
        assert results[0].success is True  # CREATE
        assert results[1].success is True  # INSERT
        assert results[2].success is True  # SELECT
        assert results[2].data == [{"id": 1}, {"id": 2}, {"id": 3}]


@pytest.mark.asyncio
async def test_is_read_only_query_detects_select(sql_service):
    """Test read-only detection for SELECT queries."""
    # Act
    result = await sql_service._is_read_only_query("SELECT * FROM users WHERE id = 1")

    # Assert
    assert result is True


@pytest.mark.asyncio
async def test_is_read_only_query_detects_non_read_only(sql_service):
    """Test read-only detection for non-read-only queries."""
    # Arrange
    queries = [
        "INSERT INTO users (name) VALUES ('test')",
        "UPDATE users SET name = 'new' WHERE id = 1",
        "DELETE FROM users WHERE id = 1",
        "CREATE TABLE new_table (id INT)",
        "DROP TABLE old_table",
        "ALTER TABLE users ADD COLUMN email VARCHAR(255)",
    ]

    # Act & Assert
    for query in queries:
        result = await sql_service._is_read_only_query(query)
        assert result is False, f"Query '{query}' should not be read-only"


@pytest.mark.asyncio
async def test_query_history_operations(sql_service):
    """Test saving and retrieving query history."""
    # Arrange
    query = "SELECT 42"
    result = SqlExecutionResult(
        success=True,
        is_read_only=True,
        execution_time=0.1,
        row_count=1,
        data=[{"value": 42}],
        message="Query executed successfully",
        error=None,
    )

    # Act
    await sql_service.save_query_history(query, result, "user123")
    history = await sql_service.get_query_history("user123", limit=10)

    # Assert
    assert len(history) >= 1
    assert history[0].query == query
    assert history[0].is_read_only is True
    assert history[0].row_count == 1


@pytest.mark.asyncio
async def test_snippet_creation_and_retrieval(sql_service):
    """Test creating and retrieving SQL snippets."""
    # Arrange
    snippet_data = SqlSnippetCreate(
        name="Test Query",
        sql_code="SELECT * FROM information_schema.tables LIMIT 5",
        description="Get table information",
        is_shared=False,
    )

    # Act
    created_snippet = await sql_service.save_snippet(snippet_data, "user123")
    snippets = await sql_service.get_snippets("user123")

    # Assert
    assert created_snippet.name == "Test Query"
    assert created_snippet.sql_code == "SELECT * FROM information_schema.tables LIMIT 5"
    assert any(s.id == created_snippet.id for s in snippets)


@pytest.mark.asyncio
async def test_snippet_deletion(sql_service):
    """Test deleting a SQL snippet."""
    # Arrange
    snippet_data = SqlSnippetCreate(
        name="Test Delete Query",
        sql_code="SELECT 1",
        description="Test deletion",
        is_shared=False,
    )
    created_snippet = await sql_service.save_snippet(snippet_data, "user123")
    snippet_id = created_snippet.id

    # Act
    await sql_service.delete_snippet(snippet_id, "user123")
    snippets = await sql_service.get_snippets("user123")

    # Assert
    assert not any(s.id == snippet_id for s in snippets)


@pytest.mark.asyncio
async def test_security_blocks_dangerous_operations(sql_service):
    """Test security validation blocks dangerous operations."""
    # Arrange
    dangerous_queries = [
        "DROP DATABASE postgres",
        "ALTER SYSTEM SET shared_buffers = '4GB'",
        "CREATE ROLE admin",
    ]

    # Act & Assert
    for query in dangerous_queries:
        with pytest.raises(SecurityError):
            await sql_service.execute_query(query, "user123")


@pytest.mark.asyncio
async def test_validate_query_security_allows_safe_queries(sql_service):
    """Test security validation allows safe queries."""
    # Arrange
    safe_queries = [
        "SELECT * FROM users WHERE id = 1",
        "INSERT INTO users (name) VALUES ('test')",
        "UPDATE users SET name = 'new' WHERE id = 1",
        "DELETE FROM users WHERE id = 1",
        "CREATE TABLE temp_test (id INT)",
        "DROP TABLE temp_test",
    ]

    # Act & Assert - should not raise exceptions
    for query in safe_queries:
        try:
            await sql_service._validate_query_security(query)
        except SecurityError:
            pytest.fail(f"Query '{query}' should not be blocked as dangerous")


@pytest.mark.asyncio
async def test_parse_multi_statement_script(sql_service):
    """Test parsing multi-statement script into individual statements."""
    # Arrange
    script = """
    SELECT 1;
    SELECT 2;
    SELECT 3;
    """

    # Act
    statements = await sql_service._parse_multi_statement_script(script)

    # Assert
    assert len(statements) == 3
    assert "SELECT 1" in statements[0]
    assert "SELECT 2" in statements[1]
    assert "SELECT 3" in statements[2]


@pytest.mark.asyncio
async def test_parse_multi_statement_script_with_comments(sql_service):
    """Test parsing handles comments correctly."""
    # Arrange
    script = """
    -- This is a comment
    SELECT 1;
    /* Another comment */
    SELECT 2;
    """

    # Act
    statements = await sql_service._parse_multi_statement_script(script)

    # Assert
    assert len(statements) == 2
    assert "SELECT 1" in statements[0]
    assert "SELECT 2" in statements[1]

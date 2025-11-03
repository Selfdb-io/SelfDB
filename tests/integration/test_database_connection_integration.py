"""
Integration tests for DatabaseConnectionManager using shared PostgreSQL container.

These tests use the shared session-based PostgreSQL container from conftest.py
to reduce test execution time from 3-5 minutes to under 30 seconds.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock

from shared.database.connection_manager import (
    DatabaseConnectionManager,
    DatabaseConnectionError,
    HealthCheckError
)
from shared.config.config_manager import ConfigManager


@pytest.mark.integration
@pytest.mark.asyncio
class TestConnectionPoolingIntegration:
    """Test connection pooling with shared PostgreSQL container."""
    

    
    async def test_single_connection_acquisition_and_release(self, test_database_manager):
        """Test that single connection can be acquired and released properly."""
        # Use shared database manager from conftest.py
        db_manager = test_database_manager

        # Act & Assert - Acquire connection and verify it works
        async with db_manager.acquire() as conn:
            assert conn is not None
            # Verify connection works by running a simple query
            result = await conn.fetchval('SELECT 1')
            assert result == 1

        # Test sequential acquisitions (single connection architecture)
        for i in range(1, 4):
            async with db_manager.acquire() as conn:
                result = await conn.fetchval(f'SELECT {i}')
                assert result == i


@pytest.mark.integration
@pytest.mark.asyncio
class TestHealthChecksIntegration:
    """Test health check functionality with shared PostgreSQL container."""
    
    async def test_health_check_with_pool(self, test_database_manager):
        """Test that health check works with connection pool."""
        # Use shared database manager from conftest.py
        db_manager = test_database_manager
        
        # Act
        is_healthy = await db_manager.health_check()
        
        # Assert
        assert is_healthy is True


@pytest.mark.integration
@pytest.mark.asyncio
class TestTransactionManagementIntegration:
    """Test transaction management with shared PostgreSQL container."""
    
    @pytest.fixture
    async def db_manager_with_schema(self, test_database_manager):
        """Create test schema using shared database manager."""
        db_manager = test_database_manager
        
        # Create test table for transactions
        await db_manager.execute("""
            CREATE TABLE IF NOT EXISTS test_users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Clean up any existing data
        await db_manager.execute("DELETE FROM test_users")
        
        yield db_manager
        
        # Cleanup test data after each test
        await db_manager.execute("DELETE FROM test_users")
    
    async def test_transaction_commit_success(self, db_manager_with_schema):
        """Test successful transaction commit."""
        db_manager = db_manager_with_schema
        
        # Act - Execute transaction that should commit
        async with db_manager.transaction() as tx:
            await tx.execute("INSERT INTO test_users (name) VALUES ($1)", "test_user_1")
            await tx.execute("INSERT INTO test_users (name) VALUES ($1)", "test_user_2")
        
        # Assert - Verify data was committed
        count = await db_manager._connection.fetchval("SELECT COUNT(*) FROM test_users")
        assert count == 2
        
        names = await db_manager._connection.fetch("SELECT name FROM test_users ORDER BY id")
        assert [record['name'] for record in names] == ["test_user_1", "test_user_2"]
    
    async def test_transaction_rollback_on_error(self, db_manager_with_schema):
        """Test transaction rollback on error."""
        db_manager = db_manager_with_schema
        
        # Act & Assert - Execute transaction that should rollback
        with pytest.raises(ValueError, match="Simulated error"):
            async with db_manager.transaction() as tx:
                await tx.execute("INSERT INTO test_users (name) VALUES ($1)", "test_user_rollback")
                # Simulate an error
                raise ValueError("Simulated error")
        
        # Assert - Verify no data was committed due to rollback
        count = await db_manager._connection.fetchval("SELECT COUNT(*) FROM test_users")
        assert count == 0
    
    async def test_nested_transactions_savepoints(self, db_manager_with_schema):
        """Test nested transactions using savepoints."""
        db_manager = db_manager_with_schema
        
        # Act - Execute nested transactions
        async with db_manager.transaction() as outer_tx:
            await outer_tx.execute("INSERT INTO test_users (name) VALUES ($1)", "outer_user")
            
            try:
                async with db_manager.transaction() as inner_tx:
                    await inner_tx.execute("INSERT INTO test_users (name) VALUES ($1)", "inner_user")
                    # Simulate error in inner transaction
                    raise ValueError("Inner transaction error")
            except ValueError:
                # Inner transaction should be rolled back, outer should continue
                pass
            
            # Add another user in outer transaction after inner rollback
            await outer_tx.execute("INSERT INTO test_users (name) VALUES ($1)", "outer_user_2")
        
        # Assert - Only outer transaction data should be committed
        count = await db_manager._connection.fetchval("SELECT COUNT(*) FROM test_users")
        assert count == 2
        
        names = await db_manager._connection.fetch("SELECT name FROM test_users ORDER BY id")
        committed_names = [record['name'] for record in names]
        assert "outer_user" in committed_names
        assert "outer_user_2" in committed_names
        assert "inner_user" not in committed_names
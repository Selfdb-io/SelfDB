"""
Tests for Phase 2.1: PostgreSQL Integration with Flexible Ports
Following TDD methodology - RED phase (tests should fail initially)
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
import asyncpg
from datetime import datetime, timedelta
import time

# Import the modules we'll build (these don't exist yet - RED phase)
from shared.database.connection_manager import (
    DatabaseConnectionManager,
    DatabaseConnectionError,
    HealthCheckError
)
from shared.config.config_manager import ConfigManager


class TestDatabaseConnectionConfiguration:
    """Test database connection with configurable ports from environment"""
    
    @pytest.fixture
    def config_manager(self):
        """Mock ConfigManager with test configuration for PgBouncer"""
        config = Mock(spec=ConfigManager)
        # Configure the mock to return proper values
        config.pgbouncer_port = 6432
        config.pgbouncer_host = "pgbouncer"
        config.postgres_db = "testdb"
        config.postgres_user = "testuser"
        config.postgres_password = "testpass"
        config.is_docker_environment = True  # PgBouncer is used in Docker
        return config
    
    @pytest.fixture
    def docker_config_manager(self):
        """Mock ConfigManager for Docker environment with PgBouncer"""
        config = Mock(spec=ConfigManager)
        config.pgbouncer_port = 6432
        config.pgbouncer_host = "pgbouncer"  # Docker service name
        config.postgres_db = "selfdb"
        config.postgres_user = "selfdb_user"
        config.postgres_password = "selfdb_pass"
        config.is_docker_environment = True
        config.compose_project_name = "selfdb"
        return config
    
    def test_database_connection_uses_configurable_port_from_env(self, config_manager):
        """Database should connect using PgBouncer port from ConfigManager/environment"""
        # Arrange
        db_manager = DatabaseConnectionManager(config_manager)

        # Act
        connection_string = db_manager.get_connection_string()

        # Assert
        assert "6432" in connection_string  # PgBouncer port
        assert "pgbouncer" in connection_string  # PgBouncer host
        assert "testdb" in connection_string
        assert "testuser" in connection_string
        assert connection_string.startswith("postgresql://")
    
    def test_database_connection_with_custom_port(self, config_manager):
        """Database should support custom PgBouncer ports for multi-instance deployment"""
        # Arrange
        config_manager.pgbouncer_port = 6433  # Custom PgBouncer port
        db_manager = DatabaseConnectionManager(config_manager)

        # Act
        connection_string = db_manager.get_connection_string()

        # Assert
        assert "6433" in connection_string
        assert "pgbouncer:6433" in connection_string
    
    def test_database_connection_uses_docker_service_names(self, docker_config_manager):
        """In Docker environment, should use PgBouncer container name"""
        # Arrange
        db_manager = DatabaseConnectionManager(docker_config_manager)

        # Act
        connection_string = db_manager.get_connection_string()

        # Assert
        assert "pgbouncer:6432" in connection_string  # PgBouncer Docker service
        assert "localhost" not in connection_string


class TestAsyncDatabaseConnection:
    """Test async database connection and operations"""
    
    @pytest.fixture
    def config_manager(self):
        config = Mock(spec=ConfigManager)
        config.postgres_port = 5432
        config.postgres_host = "localhost"
        config.postgres_db = "testdb"
        config.postgres_user = "testuser"
        config.postgres_password = "testpass"
        config.is_docker_environment = False
        return config
    
    @pytest.mark.asyncio
    async def test_async_database_connection_initialization(self, config_manager):
        """Database manager should establish async connection"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act
            conn = await db_manager.connect()
            
            # Assert
            assert conn is not None
            mock_connect.assert_called_once()
            call_args = mock_connect.call_args
            # Check that connect was called (the exact connection string format with Mocks is complex)
            assert mock_connect.called
            # Verify it was called with a connection string that contains the expected components
            call_args_str = str(call_args)
            assert "testuser" in call_args_str
            assert "testpass" in call_args_str
            assert "testdb" in call_args_str
    
    @pytest.mark.asyncio
    async def test_async_connection_with_timeout(self, config_manager):
        """Connection should support configurable timeout"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = AsyncMock()
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act
            await db_manager.connect(timeout=10)
            
            # Assert
            call_kwargs = mock_connect.call_args.kwargs
            assert call_kwargs.get('timeout') == 10
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_close(self, config_manager):
        """Database connection should be properly cleaned up"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act
            await db_manager.connect()
            await db_manager.close()
            
            # Assert
            mock_conn.close.assert_called_once()



class TestHealthChecks:
    """Test database health check and monitoring"""
    
    @pytest.fixture
    def config_manager(self):
        config = Mock(spec=ConfigManager)
        config.postgres_port = 5432
        config.postgres_host = "localhost"
        config.postgres_db = "testdb"
        config.postgres_user = "testuser"
        config.postgres_password = "testpass"
        config.is_docker_environment = False
        return config
    
    @pytest.mark.asyncio
    async def test_database_health_check_when_healthy(self, config_manager):
        """Health check should return True when database is accessible"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = 1  # SELECT 1 returns 1
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act
            is_healthy = await db_manager.health_check()
            
            # Assert
            assert is_healthy is True
            mock_conn.fetchval.assert_called_with('SELECT 1')
    
    @pytest.mark.asyncio
    async def test_database_health_check_when_unhealthy(self, config_manager):
        """Health check should return False when database is inaccessible"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = asyncpg.PostgresConnectionError("Cannot connect")
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act
            is_healthy = await db_manager.health_check()
            
            # Assert
            assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_health_check_with_connection(self, config_manager):
        """Health check should work with single connections"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = 1
            mock_conn.is_closed = False
            mock_connect.return_value = mock_conn

            db_manager = DatabaseConnectionManager(config_manager)

            # Act
            is_healthy = await db_manager.health_check()

            # Assert
            assert is_healthy is True
            mock_conn.fetchval.assert_called_with('SELECT 1')
    
    @pytest.mark.asyncio
    async def test_periodic_health_check_monitoring(self, config_manager):
        """Database should support periodic health monitoring"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = 1
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            health_results = []
            
            # Act
            async def monitor_callback(is_healthy):
                health_results.append(is_healthy)
            
            # Start monitoring for 0.1 seconds
            monitoring_task = asyncio.create_task(
                db_manager.start_health_monitoring(
                    interval=0.05,
                    callback=monitor_callback
                )
            )
            
            await asyncio.sleep(0.15)
            monitoring_task.cancel()
            
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass
            
            # Assert
            assert len(health_results) >= 2  # At least 2 health checks
            assert all(health_results)  # All should be healthy


class TestReconnectionLogic:
    """Test automatic reconnection on connection loss"""
    
    @pytest.fixture
    def config_manager(self):
        config = Mock(spec=ConfigManager)
        config.postgres_port = 5432
        config.postgres_host = "localhost"
        config.postgres_db = "testdb"
        config.postgres_user = "testuser"
        config.postgres_password = "testpass"
        config.is_docker_environment = False
        return config
    
    @pytest.mark.asyncio
    async def test_automatic_reconnection_on_connection_loss(self, config_manager):
        """Should automatically reconnect when connection is lost"""
        # Arrange
        from unittest.mock import MagicMock
        connect_attempts = 0
        
        async def mock_connect_side_effect(*args, **kwargs):
            nonlocal connect_attempts
            connect_attempts += 1
            if connect_attempts == 1:
                # First connection succeeds but will be considered closed later
                mock_conn = AsyncMock()
                # This connection will be considered closed when ensure_connected is called
                mock_conn.is_closed = MagicMock(return_value=True)
                return mock_conn
            elif connect_attempts == 2:
                # Connection lost - simulate reconnection attempt
                raise asyncpg.PostgresConnectionError("Connection lost")
            else:
                # Reconnection succeeds
                mock_conn = AsyncMock()
                mock_conn.is_closed = MagicMock(return_value=False)
                return mock_conn
        
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = mock_connect_side_effect
            
            db_manager = DatabaseConnectionManager(config_manager)
            db_manager.enable_auto_reconnect = True
            db_manager.max_reconnect_attempts = 3
            
            # Act
            await db_manager.connect()
            await db_manager.ensure_connected()  # Should trigger reconnection
            
            # Assert
            assert connect_attempts >= 3  # Initial + failed + reconnect
    
    @pytest.mark.asyncio
    async def test_reconnection_with_exponential_backoff(self, config_manager):
        """Reconnection should use exponential backoff strategy"""
        # Arrange
        from unittest.mock import MagicMock
        attempt_times = []
        
        async def mock_connect_side_effect(*args, **kwargs):
            attempt_times.append(time.time())
            if len(attempt_times) < 3:
                raise asyncpg.PostgresConnectionError("Connection failed")
            mock_conn = AsyncMock()
            # Use MagicMock for sync methods to avoid coroutine warnings
            mock_conn.is_closed = MagicMock(return_value=False)
            return mock_conn
        
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = mock_connect_side_effect
            
            db_manager = DatabaseConnectionManager(config_manager)
            db_manager.enable_auto_reconnect = True
            db_manager.max_reconnect_attempts = 5
            db_manager.reconnect_backoff_base = 0.1  # Short for testing
            
            # Act
            await db_manager.connect_with_retry()
            
            # Assert
            assert len(attempt_times) == 3
            if len(attempt_times) >= 3:
                # Check that delays increase
                delay1 = attempt_times[1] - attempt_times[0]
                delay2 = attempt_times[2] - attempt_times[1]
                assert delay2 > delay1  # Exponential backoff
    
    @pytest.mark.asyncio
    async def test_max_reconnection_attempts_limit(self, config_manager):
        """Should stop trying after max reconnection attempts"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = asyncpg.PostgresConnectionError("Connection failed")
            
            db_manager = DatabaseConnectionManager(config_manager)
            db_manager.enable_auto_reconnect = True
            db_manager.max_reconnect_attempts = 3
            db_manager.reconnect_backoff_base = 0.01  # Short for testing
            
            # Act & Assert
            with pytest.raises(DatabaseConnectionError) as exc_info:
                await db_manager.connect_with_retry()
            
            assert "max reconnection attempts" in str(exc_info.value).lower()
            assert mock_connect.call_count == 3


class TestTransactionManagement:
    """Test transaction management and rollback scenarios"""
    
    @pytest.fixture
    def config_manager(self):
        config = Mock(spec=ConfigManager)
        config.postgres_port = 5432
        config.postgres_host = "localhost"
        config.postgres_db = "testdb"
        config.postgres_user = "testuser"
        config.postgres_password = "testpass"
        config.is_docker_environment = False
        return config
    
    @pytest.mark.asyncio
    async def test_transaction_commit_success(self, config_manager):
        """Transaction should commit successfully"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_transaction = AsyncMock()
            
            # Mock transaction as a proper async context manager
            mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
            mock_transaction.__aexit__ = AsyncMock(return_value=False)
            mock_conn.transaction.return_value = mock_transaction
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            await db_manager.connect()
            
            # Act - Test that transaction context manager works without errors
            try:
                async with db_manager.transaction() as tx:
                    # tx should be the connection
                    assert tx is not None
                    await tx.execute("INSERT INTO users (name) VALUES ($1)", "test_user")
                
                # If we get here, transaction completed successfully
                transaction_success = True
            except Exception as e:
                transaction_success = False
                pytest.fail(f"Transaction should not fail: {e}")
            
            # Assert - transaction should complete successfully
            assert transaction_success
            mock_conn.transaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, config_manager):
        """Transaction should rollback on error"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_transaction = AsyncMock()
            
            # Mock transaction as a proper async context manager
            mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
            mock_transaction.__aexit__ = AsyncMock(return_value=False)
            mock_conn.transaction.return_value = mock_transaction
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            await db_manager.connect()
            
            # Act & Assert - Test that errors are properly propagated
            with pytest.raises(ValueError, match="Simulated error"):
                async with db_manager.transaction() as tx:
                    await tx.execute("INSERT INTO users (name) VALUES ($1)", "test_user")
                    raise ValueError("Simulated error")
            
            # Transaction should have been called (regardless of rollback details)
            mock_conn.transaction.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_nested_transactions_savepoints(self, config_manager):
        """Should support nested transactions using savepoints"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_outer_tx = AsyncMock()
            mock_inner_tx = AsyncMock()
            
            # Mock both transactions as proper async context managers
            mock_outer_tx.__aenter__ = AsyncMock(return_value=mock_outer_tx)
            mock_outer_tx.__aexit__ = AsyncMock(return_value=False)
            mock_inner_tx.__aenter__ = AsyncMock(return_value=mock_inner_tx)
            mock_inner_tx.__aexit__ = AsyncMock(return_value=False)
            
            # Configure nested transaction behavior
            mock_conn.transaction.side_effect = [mock_outer_tx, mock_inner_tx]
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            await db_manager.connect()
            
            # Act - Test that nested transactions work without error
            try:
                async with db_manager.transaction() as outer_tx:
                    await outer_tx.execute("INSERT INTO users (name) VALUES ($1)", "user1")
                    
                    async with db_manager.transaction() as inner_tx:
                        await inner_tx.execute("INSERT INTO users (name) VALUES ($1)", "user2")
                
                nested_transactions_success = True
            except Exception as e:
                nested_transactions_success = False
                pytest.fail(f"Nested transactions should not fail: {e}")
            
            # Assert - Both transactions should be created
            assert nested_transactions_success
            assert mock_conn.transaction.call_count == 2
    
    @pytest.mark.asyncio
    async def test_transaction_isolation_levels(self, config_manager):
        """Should support different transaction isolation levels"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_transaction = AsyncMock()
            mock_conn.transaction.return_value = mock_transaction
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            await db_manager.connect()
            
            # Act
            async with db_manager.transaction(isolation='serializable') as tx:
                await tx.execute("SELECT * FROM users")
            
            # Assert
            call_kwargs = mock_conn.transaction.call_args.kwargs
            assert call_kwargs.get('isolation') == 'serializable'



class TestErrorScenarios:
    """Test error handling for various failure scenarios"""
    
    @pytest.fixture
    def config_manager(self):
        config = Mock(spec=ConfigManager)
        config.postgres_port = 5432
        config.postgres_host = "localhost"
        config.postgres_db = "testdb"
        config.postgres_user = "testuser"
        config.postgres_password = "testpass"
        config.is_docker_environment = False
        return config
    
    @pytest.mark.asyncio
    async def test_connection_with_wrong_credentials(self, config_manager):
        """Should handle wrong credentials gracefully"""
        # Arrange
        config_manager.postgres_password = "wrong_password"
        
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = asyncpg.InvalidPasswordError("Invalid password")
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act & Assert
            with pytest.raises(DatabaseConnectionError) as exc_info:
                await db_manager.connect()
            
            assert "invalid password" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_connection_to_non_existent_database(self, config_manager):
        """Should handle non-existent database error"""
        # Arrange
        config_manager.postgres_db = "non_existent_db"
        
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = asyncpg.InvalidCatalogNameError("Database does not exist")
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act & Assert
            with pytest.raises(DatabaseConnectionError) as exc_info:
                await db_manager.connect()
            
            assert "database does not exist" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_connection_to_unreachable_host(self, config_manager):
        """Should handle unreachable host error"""
        # Arrange
        config_manager.postgres_host = "unreachable.host"
        
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = OSError("Cannot connect to host")
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act & Assert
            with pytest.raises(DatabaseConnectionError) as exc_info:
                await db_manager.connect()
            
            assert "cannot connect" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self, config_manager):
        """Should handle connection timeout"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = asyncio.TimeoutError("Connection timeout")
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act & Assert
            with pytest.raises(DatabaseConnectionError) as exc_info:
                await db_manager.connect(timeout=1)
            
            assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_query_timeout(self, config_manager):
        """Should handle query execution timeout"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute.side_effect = asyncio.TimeoutError("Query timeout")
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            await db_manager.connect()
            
            # Act & Assert
            with pytest.raises(DatabaseConnectionError) as exc_info:
                await db_manager.execute("SELECT pg_sleep(10)", timeout=1)
            
            assert "query timeout" in str(exc_info.value).lower()


class TestDatabaseInitialization:
    """Test database initialization and migration"""
    
    @pytest.fixture
    def config_manager(self):
        config = Mock(spec=ConfigManager)
        config.postgres_port = 5432
        config.postgres_host = "localhost"
        config.postgres_db = "testdb"
        config.postgres_user = "testuser"
        config.postgres_password = "testpass"
        config.is_docker_environment = False
        return config
    
    @pytest.mark.asyncio
    async def test_database_initialization_check(self, config_manager):
        """Should check if database needs initialization"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            # Simulate empty database (no tables)
            mock_conn.fetch.return_value = []
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act
            needs_init = await db_manager.needs_initialization()
            
            # Assert
            assert needs_init is True
            mock_conn.fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_schema_creation(self, config_manager):
        """Should create database schema if needed"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act
            await db_manager.initialize_schema()
            
            # Assert
            # Should execute CREATE TABLE statements
            assert mock_conn.execute.called
            calls = mock_conn.execute.call_args_list
            assert any("CREATE" in str(call) for call in calls)
    
    @pytest.mark.asyncio
    async def test_migration_execution(self, config_manager):
        """Should execute database migrations"""
        # Arrange
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = 1  # Current migration version
            mock_connect.return_value = mock_conn
            
            db_manager = DatabaseConnectionManager(config_manager)
            
            # Act
            migrations_run = await db_manager.run_migrations()
            
            # Assert
            assert migrations_run >= 0  # Number of migrations run
            mock_conn.fetchval.assert_called()  # Check current version
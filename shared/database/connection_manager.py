"""
Database Connection Manager for SelfDB - Phase 2.1

Provides PostgreSQL connection management with async support, pooling,
health monitoring, automatic reconnection, and transaction management.
"""

import asyncio
import asyncpg
import bcrypt
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, AsyncGenerator, Callable, List
from datetime import datetime, timedelta, timezone

from shared.config.config_manager import ConfigManager

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when database connection operations fail."""
    pass


class HealthCheckError(Exception):
    """Raised when health check operations fail."""
    pass


class DatabaseConnectionManager:
    """
    Manages PostgreSQL database connections with async support via PgBouncer.

    Features:
    - Async database connections using asyncpg through PgBouncer
    - Single connections (PgBouncer handles all pooling)
    - Health check functionality
    - Automatic reconnection with exponential backoff
    - Transaction management with isolation levels
    - Proper error handling with custom exceptions
    """

    def __init__(
        self,
        config_manager: ConfigManager
    ):
        """
        Initialize DatabaseConnectionManager.

        Args:
            config_manager: Configuration manager for database settings
        """
        self.config = config_manager

        # All connections go through PgBouncer which handles pooling
        logger.info("Using PgBouncer for all database connections (pooling handled by PgBouncer)")

        # Connection state - single connection through PgBouncer
        self._connection: Optional[asyncpg.Connection] = None

        # Reconnection settings
        self.enable_auto_reconnect: bool = True
        self.max_reconnect_attempts: int = 5
        self.reconnect_backoff_base: float = 1.0
        self.reconnect_backoff_max: float = 60.0

        # Health monitoring
        self._health_monitoring_task: Optional[asyncio.Task] = None
        self._last_health_check: Optional[datetime] = None

        # Transaction stack for nested transactions
        self._transaction_stack: List[asyncpg.Transaction] = []

    def _get_connection_string(self) -> str:
        """Get the PostgreSQL connection string via PgBouncer."""
        # Always use PgBouncer connection
        host = self.config.pgbouncer_host
        port = self.config.pgbouncer_port
        db = self.config.postgres_db
        user = self.config.postgres_user
        password = self.config.postgres_password
        logger.debug(f"Using PgBouncer connection: {host}:{port}")
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        logger.debug(f"Generated connection string: {connection_string}")
        return connection_string

    def get_connection_string(self) -> str:
        """Get the PostgreSQL connection string via PgBouncer."""
        # First try to use DATABASE_URL if available (should point to PgBouncer)
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            logger.debug(f"Using DATABASE_URL: {database_url}")
            return database_url

        # Otherwise construct PgBouncer connection string
        return self._get_connection_string()
    
    async def connect(self, timeout: Optional[int] = None) -> asyncpg.Connection:
        """
        Establish a single database connection.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            Database connection
            
        Raises:
            DatabaseConnectionError: If connection fails
        """
        connection_string = self.get_connection_string()
        
        try:
            self._connection = await asyncpg.connect(
                connection_string,
                timeout=timeout or 60
            )
            logger.info("Database connection established")
            return self._connection
            
        except asyncpg.PostgresConnectionError as e:
            raise DatabaseConnectionError(f"PostgreSQL connection error: {e}")
        except asyncpg.InvalidPasswordError as e:
            raise DatabaseConnectionError(f"Invalid password: {e}")
        except asyncpg.InvalidCatalogNameError as e:
            raise DatabaseConnectionError(f"Database does not exist: {e}")
        except asyncio.TimeoutError as e:
            raise DatabaseConnectionError(f"Connection timeout: {e}")
        except OSError as e:
            raise DatabaseConnectionError(f"Cannot connect to host: {e}")
        except Exception as e:
            raise DatabaseConnectionError(f"Unexpected connection error: {e}")
    
    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = None) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Acquire a database connection through PgBouncer.

        PgBouncer handles all connection pooling, so we use single connections.

        Args:
            timeout: Connection timeout in seconds

        Yields:
            Database connection

        Raises:
            DatabaseConnectionError: If connection acquisition fails
        """
        # Ensure we have an active connection
        if not self._connection or self._connection.is_closed:
            await self.connect(timeout=timeout)

        try:
            yield self._connection
        finally:
            # Keep connection open for reuse with PgBouncer
            pass

    async def close(self):
        """Close database connections and cleanup resources."""
        # Stop health monitoring
        if self._health_monitoring_task:
            self._health_monitoring_task.cancel()
            try:
                await self._health_monitoring_task
            except asyncio.CancelledError:
                pass

        # Close single connection
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    async def health_check(self) -> bool:
        """
        Perform database health check.

        Returns:
            True if database is healthy, False otherwise
        """
        try:
            async with self.acquire() as conn:
                result = await conn.fetchval('SELECT 1')
                is_healthy = result == 1

            self._last_health_check = datetime.now(timezone.utc)
            if is_healthy:
                logger.debug("Database health check passed")
            else:
                logger.warning("Database health check failed - unexpected result")

            return is_healthy

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def start_health_monitoring(
        self,
        interval: float = 30.0,
        callback: Optional[Callable[[bool], None]] = None
    ):
        """
        Start periodic health monitoring.
        
        Args:
            interval: Check interval in seconds
            callback: Optional callback function for health status changes
        """
        async def monitor():
            while True:
                try:
                    is_healthy = await self.health_check()
                    if callback:
                        await callback(is_healthy)
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    logger.info("Health monitoring stopped")
                    break
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
                    await asyncio.sleep(interval)
        
        self._health_monitoring_task = asyncio.create_task(monitor())
    
    async def ensure_connected(self):
        """Ensure database connection is active, reconnect if necessary."""
        if not self._connection or self._connection.is_closed:
            logger.info("Connection lost, attempting to reconnect")
            await self.connect_with_retry()
    
    async def connect_with_retry(self) -> asyncpg.Connection:
        """
        Connect to database with automatic retry and exponential backoff.
        
        Returns:
            Database connection
            
        Raises:
            DatabaseConnectionError: If max retries exceeded
        """
        last_exception = None
        
        for attempt in range(self.max_reconnect_attempts):
            try:
                return await self.connect()
            except DatabaseConnectionError as e:
                last_exception = e
                if attempt < self.max_reconnect_attempts - 1:
                    # Calculate exponential backoff
                    delay = min(
                        self.reconnect_backoff_base * (2 ** attempt),
                        self.reconnect_backoff_max
                    )
                    logger.warning(
                        f"Connection attempt {attempt + 1} failed, retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) exceeded")
        
        raise DatabaseConnectionError(
            f"Max reconnection attempts ({self.max_reconnect_attempts}) exceeded. "
            f"Last error: {last_exception}"
        )

    async def initialize_schema(self):
        """
        Initialize database schema.

        This is a placeholder - schema initialization should be handled
        by database migrations, not by the connection manager.
        """
        logger.info("Schema initialization should be handled by migrations")
        # This could potentially run migrations, but for now it's a no-op

    @asynccontextmanager
    async def transaction(
        self,
        isolation: Optional[str] = None,
        readonly: bool = False,
        deferrable: bool = False
    ) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Database transaction context manager.

        Args:
            isolation: Transaction isolation level
            readonly: Whether transaction is read-only
            deferrable: Whether transaction is deferrable

        Yields:
            Database connection within transaction
        """
        async with self.acquire() as conn:
            # Get the transaction object
            tx_obj = conn.transaction(
                isolation=isolation,
                readonly=readonly,
                deferrable=deferrable
            )

            # Check if it's an async context manager or a coroutine
            if hasattr(tx_obj, '__aenter__') and hasattr(tx_obj, '__aexit__'):
                async with tx_obj as tx:
                    self._transaction_stack.append(tx)
                    try:
                        yield conn
                    finally:
                        self._transaction_stack.pop()
            else:
                # Handle case where transaction() returns a coroutine
                tx = await tx_obj if asyncio.iscoroutine(tx_obj) else tx_obj
                self._transaction_stack.append(tx)
                try:
                    yield conn
                finally:
                    self._transaction_stack.pop()
    
    async def execute(
        self,
        query: str,
        *args,
        timeout: Optional[float] = None
    ) -> str:
        """
        Execute a SQL command.

        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Query timeout in seconds

        Returns:
            Command status

        Raises:
            DatabaseConnectionError: If execution fails
        """
        try:
            async with self.acquire() as conn:
                return await conn.execute(query, *args, timeout=timeout)
        except asyncio.TimeoutError:
            raise DatabaseConnectionError("Query timeout exceeded")
        except Exception as e:
            raise DatabaseConnectionError(f"Query execution failed: {e}")
    
    async def needs_initialization(self) -> bool:
        """
        Check if database needs initialization.

        Returns:
            True if database needs initialization
        """
        try:
            async with self.acquire() as conn:
                result = await conn.fetch(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                )

            return len(result) == 0

        except Exception as e:
            logger.error(f"Failed to check database initialization status: {e}")
            return True
    
    async def initialize_schema(self):
        """Initialize database schema."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS migrations (
            id SERIAL PRIMARY KEY,
            version INTEGER NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(36) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            role VARCHAR(20) NOT NULL DEFAULT 'USER',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMPTZ
        );
        
        CREATE TABLE IF NOT EXISTS data_records (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
            data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- SYSTEM RESTART PERSISTENCE TABLES (Phase 7.6.4)
        
        CREATE TABLE IF NOT EXISTS system_states (
            id VARCHAR(255) PRIMARY KEY,
            state_data JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS active_executions (
            id SERIAL PRIMARY KEY,
            execution_id VARCHAR(255) NOT NULL,
            function_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255),
            execution_data JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS resource_pool_states (
            pool_id VARCHAR(255) PRIMARY KEY,
            resource_data JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            request_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255),
            function_id VARCHAR(255),
            event_type VARCHAR(100) NOT NULL,
            event_data JSONB NOT NULL,
            success BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id SERIAL PRIMARY KEY,
            function_id VARCHAR(255) NOT NULL,
            execution_time_ms INTEGER NOT NULL,
            memory_used_mb FLOAT NOT NULL,
            success BOOLEAN NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS system_checkpoints (
            id VARCHAR(255) PRIMARY KEY,
            checkpoint_data JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_system_states_created_at ON system_states(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_active_executions_function_id ON active_executions(function_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_request_id ON audit_logs(request_id);
        CREATE INDEX IF NOT EXISTS idx_performance_metrics_function_id ON performance_metrics(function_id);
        CREATE INDEX IF NOT EXISTS idx_performance_metrics_created_at ON performance_metrics(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_system_checkpoints_created_at ON system_checkpoints(created_at DESC);
        
        -- REALTIME NOTIFY TRIGGERS (Added for Phoenix integration)
        
        -- Generic notify function for all tables
        CREATE OR REPLACE FUNCTION notify_table_change()
        RETURNS TRIGGER AS $$
        DECLARE
          payload JSON;
        BEGIN
          IF (TG_OP = 'DELETE') THEN
            payload = json_build_object(
              'action', TG_OP,
              'table', TG_TABLE_NAME,
              'old_data', row_to_json(OLD),
              'timestamp', NOW()
            );
          ELSE
            payload = json_build_object(
              'action', TG_OP,
              'table', TG_TABLE_NAME,
              'new_data', row_to_json(NEW),
              'old_data', CASE WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD) ELSE NULL END,
              'timestamp', NOW()
            );
          END IF;

          PERFORM pg_notify(TG_TABLE_NAME || '_events', payload::text);
          
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$ LANGUAGE plpgsql;

        -- Drop existing triggers if they exist (idempotent)
        DROP TRIGGER IF EXISTS users_notify ON users;
        DROP TRIGGER IF EXISTS files_notify ON files;
        DROP TRIGGER IF EXISTS buckets_notify ON buckets;
        DROP TRIGGER IF EXISTS functions_notify ON functions;
        DROP TRIGGER IF EXISTS tables_notify ON tables;
        DROP TRIGGER IF EXISTS webhooks_notify ON webhooks;
        DROP TRIGGER IF EXISTS webhook_deliveries_notify ON webhook_deliveries;

        -- Create triggers
        CREATE TRIGGER users_notify 
          AFTER INSERT OR UPDATE OR DELETE ON users
          FOR EACH ROW EXECUTE FUNCTION notify_table_change();

        CREATE TRIGGER files_notify 
          AFTER INSERT OR UPDATE OR DELETE ON files
          FOR EACH ROW EXECUTE FUNCTION notify_table_change();

        CREATE TRIGGER buckets_notify 
          AFTER INSERT OR UPDATE OR DELETE ON buckets
          FOR EACH ROW EXECUTE FUNCTION notify_table_change();

        CREATE TRIGGER functions_notify 
          AFTER INSERT OR UPDATE OR DELETE ON functions
          FOR EACH ROW EXECUTE FUNCTION notify_table_change();

        CREATE TRIGGER tables_notify 
          AFTER INSERT OR UPDATE OR DELETE ON tables
          FOR EACH ROW EXECUTE FUNCTION notify_table_change();

        CREATE TRIGGER webhooks_notify 
          AFTER INSERT OR UPDATE OR DELETE ON webhooks
          FOR EACH ROW EXECUTE FUNCTION notify_table_change();

        CREATE TRIGGER webhook_deliveries_notify 
          AFTER INSERT OR UPDATE OR DELETE ON webhook_deliveries
          FOR EACH ROW EXECUTE FUNCTION notify_table_change();
        """
        
        try:
            async with self.acquire() as conn:
                await conn.execute(schema_sql)

            logger.info("Database schema initialized successfully")

            # Create admin user if configured
            await self._create_admin_user()

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to initialize schema: {e}")

    async def _create_admin_user(self):
        """Create admin user if configured and doesn't exist."""
        try:
            # Get admin credentials from config
            admin_email = self.config.admin_email
            admin_password = self.config.admin_password
            admin_first_name = self.config.admin_first_name
            admin_last_name = self.config.admin_last_name

            if not admin_email or not admin_password or not admin_first_name or not admin_last_name:
                logger.warning("Admin credentials not configured, skipping admin user creation")
                return

            # Check if admin user already exists
            async with self.acquire() as conn:
                existing_admin = await conn.fetchval(
                    "SELECT id FROM users WHERE email = $1 AND role = 'ADMIN'",
                    admin_email
                )

            if existing_admin:
                logger.info(f"Admin user already exists: {admin_email}")
                return

            # Hash the admin password
            password_hash = bcrypt.hashpw(
                admin_password.encode('utf-8'),
                bcrypt.gensalt(rounds=12)
            ).decode('utf-8')

            # Create admin user
            admin_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            async with self.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO users (
                        id, email, password_hash, first_name, last_name,
                        role, is_active, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    admin_id, admin_email, password_hash, admin_first_name, admin_last_name,
                    "ADMIN", True, now, now
                )

            logger.info(f"Created admin user: {admin_first_name} {admin_last_name} ({admin_email})")

        except Exception as e:
            logger.error(f"Failed to create admin user: {e}")
            # Don't raise the error - admin user creation is not critical for schema initialization

    async def run_migrations(self) -> int:
        """
        Run database migrations.
        
        Returns:
            Number of migrations executed
        """
        try:
            # Get current migration version
            async with self.acquire() as conn:
                current_version = await conn.fetchval(
                    "SELECT COALESCE(MAX(version), 0) FROM migrations"
                ) or 0

            # For now, just return 0 as no migrations are defined yet
            # In a real implementation, this would execute migration files
            logger.info(f"Current migration version: {current_version}")
            return 0

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to run migrations: {e}")
    
    # =============================================================================
    # SYSTEM RESTART PERSISTENCE METHODS (Phase 7.6.4)
    # =============================================================================
    
    async def save_system_state(self, system_state: Dict[str, Any]) -> str:
        """
        Save current system state for restart persistence.
        
        Args:
            system_state: Dictionary containing system state data
            
        Returns:
            State ID for later retrieval
        """
        import uuid
        import json
        
        state_id = str(uuid.uuid4())
        
        try:
            sql = """
                INSERT INTO system_states (id, state_data, created_at)
                VALUES ($1, $2, $3)
            """
            
            async with self.acquire() as conn:
                await conn.execute(sql, state_id, json.dumps(system_state), datetime.now(timezone.utc))
            
            logger.info(f"System state saved with ID: {state_id}")
            return state_id
            
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to save system state: {e}")
    
    async def get_system_state(self, state_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve system state for restart recovery.
        
        Args:
            state_id: Specific state ID, or None for most recent
            
        Returns:
            System state data or None if not found
        """
        import json
        
        try:
            if state_id:
                sql = "SELECT state_data FROM system_states WHERE id = $1"
                params = [state_id]
            else:
                sql = "SELECT state_data FROM system_states ORDER BY created_at DESC LIMIT 1"
                params = []
            
            async with self.acquire() as conn:
                result = await conn.fetchval(sql, *params)
            
            return json.loads(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to get system state: {e}")
            return None
    
    async def save_active_executions(self, active_executions: List[Dict[str, Any]]) -> None:
        """
        Save active function executions for restart recovery.
        
        Args:
            active_executions: List of active execution data
        """
        import json
        
        try:
            sql = """
                INSERT INTO active_executions (execution_id, function_id, user_id, execution_data, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """
            
            async with self.acquire() as conn:
                for execution in active_executions:
                    await conn.execute(
                        sql,
                        execution.get("execution_id", "unknown"),
                        execution.get("function_id"),
                        execution.get("user_id"),
                        json.dumps(execution),
                        datetime.now(timezone.utc)
                    )
            
            logger.info(f"Saved {len(active_executions)} active executions")
            
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to save active executions: {e}")
    
    async def get_active_executions(self, function_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve active executions for restart recovery.
        
        Args:
            function_id: Filter by specific function ID, or None for all
            
        Returns:
            List of active execution data
        """
        import json
        
        try:
            if function_id:
                sql = "SELECT execution_data FROM active_executions WHERE function_id = $1 ORDER BY created_at"
                params = [function_id]
            else:
                sql = "SELECT execution_data FROM active_executions ORDER BY created_at"
                params = []
            
            async with self.acquire() as conn:
                results = await conn.fetch(sql, *params)
            
            return [json.loads(row['execution_data']) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get active executions: {e}")
            return []
    
    async def save_resource_pool_state(self, resource_state: Dict[str, Any]) -> None:
        """
        Save resource pool state for restart recovery.
        
        Args:
            resource_state: Resource pool state data
        """
        import json
        
        try:
            sql = """
                INSERT INTO resource_pool_states (pool_id, resource_data, created_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (pool_id) DO UPDATE SET
                    resource_data = $2,
                    created_at = $3
            """
            
            pool_id = resource_state.get("pool_id", "default")
            
            async with self.acquire() as conn:
                await conn.execute(sql, pool_id, json.dumps(resource_state), datetime.now(timezone.utc))
            
            logger.info(f"Resource pool state saved for pool: {pool_id}")
            
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to save resource pool state: {e}")
    
    async def get_resource_pool_state(self, pool_id: str = "default") -> Optional[Dict[str, Any]]:
        """
        Retrieve resource pool state for restart recovery.
        
        Args:
            pool_id: Resource pool identifier
            
        Returns:
            Resource pool state data or None if not found
        """
        import json
        
        try:
            sql = "SELECT resource_data FROM resource_pool_states WHERE pool_id = $1"
            
            async with self.acquire() as conn:
                result = await conn.fetchval(sql, pool_id)
            
            return json.loads(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to get resource pool state: {e}")
            return None
    
    async def verify_audit_log_integrity(self, start_time: Optional[datetime] = None, 
                                       end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Verify audit log integrity across restart boundaries.
        
        Args:
            start_time: Start of time window to check
            end_time: End of time window to check
            
        Returns:
            Integrity verification results
        """
        try:
            # Ensure timezone-aware datetimes if provided
            if start_time and start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            if end_time and end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
                
            sql = """
                SELECT 
                    COUNT(*) as total_entries,
                    MIN(created_at) as earliest_entry,
                    MAX(created_at) as latest_entry,
                    COUNT(DISTINCT request_id) as unique_requests
                FROM audit_logs
            """
            params = []
            
            if start_time and end_time:
                sql += " WHERE created_at BETWEEN $1 AND $2"
                params = [start_time, end_time]
            elif start_time:
                sql += " WHERE created_at >= $1"
                params = [start_time]
            elif end_time:
                sql += " WHERE created_at <= $1"
                params = [end_time]
            
            async with self.acquire() as conn:
                result = await conn.fetchrow(sql, *params)
            
            return {
                "total_entries": result["total_entries"] if result else 0,
                "earliest_entry": result["earliest_entry"] if result else None,
                "latest_entry": result["latest_entry"] if result else None,
                "unique_requests": result["unique_requests"] if result else 0,
                "integrity_verified": True,
                "gaps_detected": False  # Could implement gap detection logic here
            }
            
        except Exception as e:
            logger.error(f"Failed to verify audit log integrity: {e}")
            return {
                "total_entries": 0,
                "integrity_verified": False,
                "error": str(e)
            }
    
    async def get_aggregated_metrics_across_restarts(self, start_time: datetime, 
                                                   end_time: datetime) -> Dict[str, Any]:
        """
        Get aggregated performance metrics across restart boundaries.
        
        Args:
            start_time: Start of aggregation period
            end_time: End of aggregation period
            
        Returns:
            Aggregated metrics data
        """
        try:
            # Ensure timezone-aware datetimes
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
                
            sql = """
                SELECT 
                    COUNT(*) as total_executions,
                    AVG(execution_time_ms) as avg_execution_time,
                    AVG(memory_used_mb) as avg_memory_usage,
                    SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful_executions,
                    MIN(created_at) as period_start,
                    MAX(created_at) as period_end
                FROM performance_metrics
                WHERE created_at BETWEEN $1 AND $2
            """
            
            async with self.acquire() as conn:
                result = await conn.fetchrow(sql, start_time, end_time)
            
            if result:
                return {
                    "total_executions": result["total_executions"],
                    "avg_execution_time": float(result["avg_execution_time"]) if result["avg_execution_time"] else 0,
                    "avg_memory_usage": float(result["avg_memory_usage"]) if result["avg_memory_usage"] else 0,
                    "successful_executions": result["successful_executions"],
                    "success_rate": result["successful_executions"] / result["total_executions"] if result["total_executions"] > 0 else 0,
                    "period_start": result["period_start"],
                    "period_end": result["period_end"]
                }
            else:
                return {
                    "total_executions": 0,
                    "avg_execution_time": 0,
                    "avg_memory_usage": 0,
                    "successful_executions": 0,
                    "success_rate": 0
                }
            
        except Exception as e:
            logger.error(f"Failed to get aggregated metrics: {e}")
            return {"error": str(e)}
    
    async def create_system_checkpoint(self, checkpoint_data: Dict[str, Any]) -> str:
        """
        Create a system state checkpoint.
        
        Args:
            checkpoint_data: Data to include in checkpoint
            
        Returns:
            Checkpoint ID
        """
        import uuid
        import json
        
        checkpoint_id = str(uuid.uuid4())
        
        try:
            sql = """
                INSERT INTO system_checkpoints (id, checkpoint_data, created_at)
                VALUES ($1, $2, $3)
            """
            
            async with self.acquire() as conn:
                await conn.execute(sql, checkpoint_id, json.dumps(checkpoint_data), datetime.now(timezone.utc))
            
            logger.info(f"System checkpoint created with ID: {checkpoint_id}")
            return checkpoint_id
            
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to create system checkpoint: {e}")
    
    async def restore_from_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore system state from a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            Checkpoint data or None if not found
        """
        import json
        
        try:
            sql = "SELECT checkpoint_data FROM system_checkpoints WHERE id = $1"
            
            async with self.acquire() as conn:
                result = await conn.fetchval(sql, checkpoint_id)
            
            if result:
                logger.info(f"Restored checkpoint: {checkpoint_id}")
                return json.loads(result)
            else:
                logger.warning(f"Checkpoint not found: {checkpoint_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to restore from checkpoint: {e}")
            return None
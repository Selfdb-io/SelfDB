"""
FunctionLog CRUD manager for SelfDB function log storage and retrieval.
Based on Functions & Webhooks Improvement Plan requirements.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Sequence

from shared.database.connection_manager import DatabaseConnectionManager
from shared.models.function_log import FunctionLog, LogLevel


class FunctionLogNotFoundError(Exception):
    """Raised when a function log cannot be located."""


class FunctionLogValidationError(Exception):
    """Raised when function log data fails validation."""


class FunctionLogCRUDManager:
    """Manage function log CRUD operations and storage."""

    def __init__(self, database_manager: DatabaseConnectionManager):
        self._db = database_manager

    async def create_log(
        self,
        execution_id: Optional[uuid.UUID],
        function_id: uuid.UUID,
        message: str,
        log_level: LogLevel = LogLevel.INFO,
        source: str = "function",
        metadata: Optional[Dict[str, Any]] = None
    ) -> FunctionLog:
        """
        Create a new function log entry.
        
        Args:
            execution_id: Associated execution UUID (None for system logs)
            function_id: Associated function UUID
            message: Log message
            log_level: Log level
            source: Log source
            metadata: Additional metadata
            
        Returns:
            Created FunctionLog instance
        """
        # Create log instance
        if execution_id:
            log = FunctionLog.create(
                execution_id=execution_id,
                function_id=function_id,
                message=message,
                log_level=log_level,
                source=source,
                metadata=metadata
            )
        else:
            log = FunctionLog.system_log(
                function_id=function_id,
                message=message,
                log_level=log_level,
                metadata=metadata
            )

        # Insert into database
        async with self._db.transaction() as conn:
            row = await conn.fetchrow("""
                INSERT INTO function_logs (
                    execution_id, function_id, log_level, message,
                    timestamp, source, context
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7
                )
                RETURNING id
            """,
            str(log.execution_id) if log.execution_id else None,
            str(log.function_id),
            log.log_level.value,
            log.message,
            log.timestamp,
            log.source,
            json.dumps(log.context) if log.context else None
            )

        # Set the auto-generated ID
        log.id = row["id"]

        return log

    async def get_log(self, log_id: int) -> FunctionLog:
        """
        Get a function log by ID.
        
        Args:
            log_id: Log ID
            
        Returns:
            FunctionLog instance
            
        Raises:
            FunctionLogNotFoundError: If log doesn't exist
        """
        async with self._db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id, execution_id, function_id, log_level, message,
                    timestamp, source, context
                FROM function_logs
                WHERE id = $1
            """, log_id)

        if row is None:
            raise FunctionLogNotFoundError(f"Function log with ID {log_id} not found")

        return self._row_to_log(row)

    async def list_logs(
        self,
        function_id: Optional[uuid.UUID] = None,
        execution_id: Optional[uuid.UUID] = None,
        log_level: Optional[LogLevel] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FunctionLog]:
        """
        List function logs with optional filtering.
        
        Args:
            function_id: Filter by function (None for all)
            execution_id: Filter by execution (None for all)
            log_level: Filter by log level (None for all)
            source: Filter by source (None for all)
            since: Only include logs since this time
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of FunctionLog instances
        """
        query = """
            SELECT
                id, execution_id, function_id, log_level, message,
                timestamp, source, context
            FROM function_logs
        """
        
        params = []
        conditions = []
        
        if function_id is not None:
            conditions.append("function_id = $1")
            params.append(str(function_id))
            
        if execution_id is not None:
            conditions.append("execution_id = $2")
            params.append(str(execution_id))
            
        if log_level is not None:
            conditions.append("log_level = $3")
            params.append(log_level.value)
            
        if source is not None:
            conditions.append("source = $4")
            params.append(source)
            
        if since is not None:
            conditions.append("timestamp >= $5")
            params.append(since)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY timestamp DESC LIMIT $%d OFFSET $%d" % (len(params) + 1, len(params) + 2)
        params.extend([limit, offset])

        async with self._db.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_log(row) for row in rows]

    async def get_execution_logs(
        self,
        execution_id: uuid.UUID,
        limit: int = 1000
    ) -> List[FunctionLog]:
        """
        Get all logs for a specific execution.
        
        Args:
            execution_id: Execution UUID
            limit: Maximum number of logs to return
            
        Returns:
            List of FunctionLog instances for the execution
        """
        async with self._db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    id, execution_id, function_id, log_level, message,
                    timestamp, source, context
                FROM function_logs
                WHERE execution_id = $1
                ORDER BY timestamp ASC
                LIMIT $2
            """, str(execution_id), limit)

        return [self._row_to_log(row) for row in rows]

    async def get_function_logs(
        self,
        function_id: uuid.UUID,
        since: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FunctionLog]:
        """
        Get logs for a specific function.
        
        Args:
            function_id: Function UUID
            since: Only include logs since this time
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of FunctionLog instances for the function
        """
        query = """
            SELECT
                id, execution_id, function_id, log_level, message,
                timestamp, source, context
            FROM function_logs
            WHERE function_id = $1
        """
        
        params = [str(function_id)]
        
        if since is not None:
            query += " AND timestamp >= $2"
            params.append(since)
            
        query += " ORDER BY timestamp DESC LIMIT $%d OFFSET $%d" % (len(params) + 1, len(params) + 2)
        params.extend([limit, offset])

        async with self._db.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_log(row) for row in rows]

    async def get_log_stats(
        self,
        function_id: Optional[uuid.UUID] = None,
        execution_id: Optional[uuid.UUID] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get log statistics.
        
        Args:
            function_id: Filter by function (None for all)
            execution_id: Filter by execution (None for all)
            since: Only include logs since this time
            
        Returns:
            Statistics dictionary
        """
        query = """
            SELECT
                COUNT(*) as total_logs,
                COUNT(CASE WHEN log_level = 'debug' THEN 1 END) as debug_logs,
                COUNT(CASE WHEN log_level = 'info' THEN 1 END) as info_logs,
                COUNT(CASE WHEN log_level = 'warn' THEN 1 END) as warn_logs,
                COUNT(CASE WHEN log_level = 'error' THEN 1 END) as error_logs,
                MIN(timestamp) as oldest_log,
                MAX(timestamp) as newest_log
            FROM function_logs
        """
        
        params = []
        conditions = []
        
        if function_id is not None:
            conditions.append("function_id = $1")
            params.append(str(function_id))
            
        if execution_id is not None:
            conditions.append("execution_id = $2")
            params.append(str(execution_id))
            
        if since is not None:
            conditions.append("timestamp >= $3")
            params.append(since)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        async with self._db.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        return dict(row) if row else {}

    async def cleanup_old_logs(self, days_old: int = 30) -> int:
        """
        Delete logs older than specified days.
        
        Args:
            days_old: Delete logs older than this many days
            
        Returns:
            Number of logs deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        async with self._db.transaction() as conn:
            result = await conn.execute("""
                DELETE FROM function_logs
                WHERE timestamp < $1
            """, cutoff_date)
            
        # Return number of affected rows
        return int(result.split()[-1]) if result else 0

    async def bulk_create_logs(self, logs: List[FunctionLog]) -> List[FunctionLog]:
        """
        Bulk create multiple log entries.
        
        Args:
            logs: List of FunctionLog instances to create
            
        Returns:
            List of created FunctionLog instances with IDs set
        """
        if not logs:
            return []
            
        # Prepare bulk insert data
        values = []
        for log in logs:
            values.extend([
                str(log.execution_id) if log.execution_id else None,
                str(log.function_id),
                log.log_level.value,
                log.message,
                log.timestamp,
                log.source,
                json.dumps(log.context) if log.context else None
            ])
        
        # Build query with multiple value tuples
        placeholders = []
        for i in range(len(logs)):
            base = i * 7
            placeholders.append(f"(${base + 1}, ${base + 2}, ${base + 3}, ${base + 4}, ${base + 5}, ${base + 6}, ${base + 7})")
        
        query = f"""
            INSERT INTO function_logs (
                execution_id, function_id, log_level, message,
                timestamp, source, context
            ) VALUES {', '.join(placeholders)}
            RETURNING id
        """
        
        async with self._db.transaction() as conn:
            rows = await conn.fetch(query, *values)
            
        # Set IDs on the log instances
        for log, row in zip(logs, rows):
            log.id = row["id"]
            
        return logs

    def _row_to_log(self, row) -> FunctionLog:
        """Convert database row to FunctionLog instance."""
        # Convert string UUIDs to UUID objects for Pydantic validation
        def _to_uuid(val):
            try:
                if isinstance(val, str):
                    return uuid.UUID(val)
                elif isinstance(val, uuid.UUID):
                    return val
                else:
                    return None  # Allow None for optional UUIDs
            except Exception as e:
                raise ValueError(f"Invalid UUID value: {val}") from e
        
        # Ensure context is a dict (DB driver may return JSON as str)
        context = row["context"] or {}
        try:
            if isinstance(context, str):
                import json
                context = json.loads(context)
        except Exception:
            # leave as-is (fallback to empty dict)
            context = {} if context is None else context

        return FunctionLog(
            id=row["id"],
            execution_id=_to_uuid(row["execution_id"]),
            function_id=_to_uuid(row["function_id"]),
            log_level=LogLevel(row["log_level"]),
            message=row["message"],
            timestamp=row["timestamp"],
            source=row["source"],
            context=context
        )
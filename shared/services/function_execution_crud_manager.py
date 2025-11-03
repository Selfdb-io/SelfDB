"""
FunctionExecution CRUD manager for SelfDB function execution tracking.
Based on Functions & Webhooks Improvement Plan requirements.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Sequence

from shared.database.connection_manager import DatabaseConnectionManager
from shared.models.function_execution import FunctionExecution


class FunctionExecutionNotFoundError(Exception):
    """Raised when a function execution cannot be located."""


class FunctionExecutionValidationError(Exception):
    """Raised when function execution data fails validation."""


class FunctionExecutionCRUDManager:
    """Manage function execution CRUD operations and tracking."""

    def __init__(self, database_manager: DatabaseConnectionManager):
        self._db = database_manager

    async def create_execution(
        self,
        function_id: uuid.UUID,
        user_id: uuid.UUID,
        trigger_type: str,
        trigger_source: Optional[str] = None,
        webhook_delivery_id: Optional[uuid.UUID] = None,
        timeout_seconds: int = 30
    ) -> FunctionExecution:
        """
        Create a new function execution record.
        
        Args:
            function_id: Associated function UUID
            user_id: User who triggered execution
            trigger_type: Trigger type (http, schedule, database, event, webhook)
            trigger_source: Trigger source details
            webhook_delivery_id: Associated webhook delivery UUID
            timeout_seconds: Execution timeout in seconds
            
        Returns:
            Created FunctionExecution instance
        """
        # Create execution instance
        execution = FunctionExecution.create(
            function_id=function_id,
            user_id=user_id,
            trigger_type=trigger_type,
            trigger_source=trigger_source,
            webhook_delivery_id=webhook_delivery_id,
            timeout_seconds=timeout_seconds
        )

        # Insert into database
        async with self._db.transaction() as conn:
            await conn.execute("""
                INSERT INTO function_executions (
                    id, function_id, user_id, trigger_type, trigger_source,
                    webhook_delivery_id, status, started_at, completed_at,
                    duration_ms, memory_used_mb, cpu_usage_percent, result,
                    error_message, error_stack_trace, error_type, env_vars_used,
                    execution_trace, metadata, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                    $14, $15, $16, $17, $18, $19, $20, $21
                )
            """,
            str(execution.id),
            str(execution.function_id),
            str(execution.user_id),
            execution.trigger_type,
            execution.trigger_source,
            str(execution.webhook_delivery_id) if execution.webhook_delivery_id else None,
            execution.status,
            execution.started_at,
            execution.completed_at,
            execution.duration_ms,
            execution.memory_used_mb,
            execution.cpu_usage_percent,
            execution.result,
            execution.error_message,
            execution.error_stack_trace,
            execution.error_type,
            json.dumps(execution.env_vars_used) if execution.env_vars_used else None,
            execution.execution_trace,
            json.dumps(execution.metadata) if execution.metadata else None,
            execution.created_at,
            execution.updated_at
            )

        return execution

    async def get_execution(self, execution_id: uuid.UUID) -> FunctionExecution:
        """
        Get a function execution by ID.
        
        Args:
            execution_id: Execution UUID
            
        Returns:
            FunctionExecution instance
            
        Raises:
            FunctionExecutionNotFoundError: If execution doesn't exist
        """
        async with self._db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id, function_id, user_id, trigger_type, trigger_source,
                    webhook_delivery_id, status, started_at, completed_at,
                    duration_ms, memory_used_mb, cpu_usage_percent, result,
                    error_message, error_stack_trace, error_type, env_vars_used,
                    execution_trace, metadata, created_at, updated_at
                FROM function_executions
                WHERE id = $1
            """, str(execution_id))

        if row is None:
            raise FunctionExecutionNotFoundError(f"Function execution with ID {execution_id} not found")

        return self._row_to_execution(row)

    async def list_executions(
        self,
        function_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        trigger_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FunctionExecution]:
        """
        List function executions with optional filtering.
        
        Args:
            function_id: Filter by function (None for all)
            user_id: Filter by user (None for all)
            trigger_type: Filter by trigger type (None for all)
            status: Filter by status (None for all)
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of FunctionExecution instances
        """
        query = """
            SELECT
                id, function_id, user_id, trigger_type, trigger_source,
                webhook_delivery_id, status, started_at, completed_at,
                duration_ms, memory_used_mb, cpu_usage_percent, result,
                error_message, error_stack_trace, error_type, env_vars_used,
                execution_trace, metadata, created_at, updated_at
            FROM function_executions
        """
        
        params = []
        conditions = []
        
        if function_id is not None:
            conditions.append("function_id = $1")
            params.append(str(function_id))
            
        if user_id is not None:
            param_index = len(params) + 1
            conditions.append(f"user_id = ${param_index}")
            params.append(str(user_id))
            
        if trigger_type is not None:
            param_index = len(params) + 1
            conditions.append(f"trigger_type = ${param_index}")
            params.append(trigger_type)
            
        if status is not None:
            param_index = len(params) + 1
            conditions.append(f"status = ${param_index}")
            params.append(status)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY started_at DESC LIMIT $%d OFFSET $%d" % (len(params) + 1, len(params) + 2)
        params.extend([limit, offset])

        async with self._db.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_execution(row) for row in rows]

    async def complete_execution(
        self,
        execution_id: uuid.UUID,
        success: bool,
        result: Optional[str] = None,
        logs: Optional[str] = None,
        memory_used_mb: Optional[float] = None,
        cpu_usage_percent: Optional[float] = None,
        error_message: Optional[str] = None,
        error_stack_trace: Optional[str] = None,
        error_type: Optional[str] = None,
        env_vars_used: Optional[List[str]] = None,
        execution_trace: Optional[Any] = None
    ) -> FunctionExecution:
        """
        Mark execution as completed.
        
        Args:
            execution_id: Execution UUID
            success: Whether execution was successful
            result: Execution result
            logs: Execution logs
            memory_used_mb: Memory usage
            cpu_usage_percent: CPU usage percentage
            error_message: Error message if failed
            error_stack_trace: Full error stack trace
            error_type: Error type/category
            env_vars_used: Environment variables used
            execution_trace: Execution trace information
            
        Returns:
            Updated FunctionExecution instance
            
        Raises:
            FunctionExecutionNotFoundError: If execution doesn't exist
        """
        # Get current execution
        execution = await self.get_execution(execution_id)
        
        # Mark as completed
        execution = execution.complete(
            success=success,
            result=result,
            memory_used_mb=memory_used_mb,
            cpu_usage_percent=cpu_usage_percent,
            error_message=error_message,
            error_stack_trace=error_stack_trace,
            error_type=error_type,
            env_vars_used=env_vars_used,
            execution_trace=execution_trace
        )

        # Update in database
        async with self._db.transaction() as conn:
            await conn.execute("""
                UPDATE function_executions SET
                    status = $2, completed_at = $3, duration_ms = $4,
                    error_message = $5, result = $6, memory_used_mb = $7,
                    cpu_usage_percent = $8, error_stack_trace = $9,
                    error_type = $10, env_vars_used = $11, execution_trace = $12,
                    updated_at = $13
                WHERE id = $1
            """,
            str(execution.id),
            execution.status,
            execution.completed_at,
            execution.duration_ms,
            execution.error_message,
            execution.result,
            execution.memory_used_mb,
            execution.cpu_usage_percent,
            execution.error_stack_trace,
            execution.error_type,
            json.dumps(execution.env_vars_used) if execution.env_vars_used else None,
            execution.execution_trace,
            execution.updated_at
            )

        return execution

    async def mark_execution_timeout(self, execution_id: uuid.UUID) -> FunctionExecution:
        """
        Mark execution as timed out.
        
        Args:
            execution_id: Execution UUID
            
        Returns:
            Updated FunctionExecution instance
            
        Raises:
            FunctionExecutionNotFoundError: If execution doesn't exist
        """
        # Get current execution
        execution = await self.get_execution(execution_id)
        
        # Mark as timeout
        execution = execution.mark_timeout()

        # Update in database
        async with self._db.transaction() as conn:
            await conn.execute("""
                UPDATE function_executions SET
                    status = $2, completed_at = $3, duration_ms = $4,
                    error_message = $5, error_type = $6, updated_at = $7
                WHERE id = $1
            """,
            str(execution.id),
            execution.status,
            execution.completed_at,
            execution.duration_ms,
            execution.error_message,
            execution.error_type,
            execution.updated_at
            )

        return execution

    async def get_running_executions(
        self,
        function_id: Optional[uuid.UUID] = None,
        limit: int = 100
    ) -> List[FunctionExecution]:
        """
        Get currently running executions.
        
        Args:
            function_id: Filter by function (None for all)
            limit: Maximum number of results
            
        Returns:
            List of running FunctionExecution instances
        """
        query = """
            SELECT
                id, function_id, user_id, trigger_type, trigger_source,
                webhook_delivery_id, status, started_at, completed_at,
                duration_ms, memory_used_mb, cpu_usage_percent, result,
                error_message, error_stack_trace, error_type, env_vars_used,
                execution_trace, metadata, created_at, updated_at
            FROM function_executions
            WHERE status = 'running'
        """
        
        params = []
        
        if function_id is not None:
            query += " AND function_id = $1"
            params.append(str(function_id))
            
        query += " ORDER BY started_at DESC LIMIT $%d" % (len(params) + 1)
        params.append(limit)

        async with self._db.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_execution(row) for row in rows]

    async def get_timed_out_executions(self, limit: int = 100) -> List[FunctionExecution]:
        """
        Get executions that have timed out.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of timed out FunctionExecution instances
        """
        now = datetime.now(timezone.utc)
        
        async with self._db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    id, function_id, user_id, trigger_type, trigger_source,
                    webhook_delivery_id, status, started_at, completed_at,
                    duration_ms, memory_used_mb, cpu_usage_percent, result,
                    error_message, error_stack_trace, error_type, env_vars_used,
                    execution_trace, metadata, created_at, updated_at
                FROM function_executions
                WHERE status = 'running' AND started_at < $1
                ORDER BY started_at ASC
                LIMIT $2
            """, now, limit)

        return [self._row_to_execution(row) for row in rows]

    async def get_execution_stats(
        self,
        function_id: Optional[uuid.UUID] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Args:
            function_id: Filter by function (None for all)
            since: Only include executions since this time
            
        Returns:
            Statistics dictionary
        """
        query = """
            SELECT
                COUNT(*) as total_executions,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_executions,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_executions,
                COUNT(CASE WHEN status = 'timeout' THEN 1 END) as timed_out_executions,
                COUNT(CASE WHEN status = 'running' THEN 1 END) as running_executions,
                AVG(duration_ms) as avg_execution_time,
                MIN(duration_ms) as min_execution_time,
                MAX(duration_ms) as max_execution_time,
                AVG(memory_used_mb) as avg_memory_usage,
                MIN(started_at) as oldest_execution,
                MAX(started_at) as newest_execution
            FROM function_executions
        """
        
        params = []
        conditions = []
        
        if function_id is not None:
            conditions.append("function_id = $1")
            params.append(str(function_id))
            
        if since is not None:
            param_index = len(params) + 1
            conditions.append(f"started_at >= ${param_index}")
            params.append(since)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        async with self._db.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        return dict(row) if row else {}

    async def cleanup_old_executions(self, days_old: int = 30) -> int:
        """
        Delete executions older than specified days.
        
        Args:
            days_old: Delete executions older than this many days
            
        Returns:
            Number of executions deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        async with self._db.transaction() as conn:
            result = await conn.execute("""
                DELETE FROM function_executions
                WHERE created_at < $1 AND status != 'running'
            """, cutoff_date)
            
        # Return number of affected rows
        return int(result.split()[-1]) if result else 0

    def _row_to_execution(self, row) -> FunctionExecution:
        """Convert database row to FunctionExecution instance."""
        # Convert string UUIDs to UUID objects for Pydantic validation
        def _to_uuid(val):
            try:
                if isinstance(val, str):
                    return uuid.UUID(val)
                elif isinstance(val, uuid.UUID):
                    return val
                else:
                    raise ValueError(f"Cannot convert {type(val)} to UUID")
            except Exception as e:
                raise ValueError(f"Invalid UUID value: {val}") from e
        
        # Ensure env_vars_used is a list (DB driver may return JSON as str)
        env_vars = row["env_vars_used"] or []
        try:
            if isinstance(env_vars, str):
                import json
                env_vars = json.loads(env_vars)
        except Exception:
            # leave as-is (fallback to empty list)
            env_vars = [] if env_vars is None else env_vars

        # Ensure metadata is a dict (DB driver may return JSON as str)
        metadata = row["metadata"] or {}
        try:
            if isinstance(metadata, str):
                import json
                metadata = json.loads(metadata)
        except Exception:
            # leave as-is (fallback to empty dict)
            metadata = {} if metadata is None else metadata

        return FunctionExecution(
            id=_to_uuid(row["id"]),
            function_id=_to_uuid(row["function_id"]),
            user_id=_to_uuid(row["user_id"]),
            trigger_type=row["trigger_type"],
            trigger_source=row["trigger_source"],
            webhook_delivery_id=_to_uuid(row["webhook_delivery_id"]) if row["webhook_delivery_id"] else None,
            status=row["status"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            duration_ms=row["duration_ms"],
            error_message=row["error_message"],
            result=row["result"],
            memory_used_mb=row["memory_used_mb"],
            cpu_usage_percent=row["cpu_usage_percent"],
            error_stack_trace=row["error_stack_trace"],
            error_type=row["error_type"],
            env_vars_used=env_vars,
            execution_trace=row["execution_trace"],
            metadata=metadata,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
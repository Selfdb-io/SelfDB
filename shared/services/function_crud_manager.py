"""
Function CRUD manager for SelfDB function management.
Based on Functions & Webhooks Improvement Plan requirements.
"""

from __future__ import annotations

import uuid
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from shared.database.connection_manager import DatabaseConnectionManager
from shared.models.function import Function, FunctionRuntime, DeploymentStatus


class FunctionNotFoundError(Exception):
    """Raised when a function cannot be located."""


class FunctionAlreadyExistsError(Exception):
    """Raised when attempting to create a function with a name that already exists."""


class FunctionValidationError(Exception):
    """Raised when function data fails validation."""


class FunctionCRUDManager:
    """Manage function CRUD operations and metadata persistence."""

    def __init__(self, database_manager: DatabaseConnectionManager):
        self._db = database_manager

    async def create_function(
        self,
        name: str,
        code: str,
        owner_id: uuid.UUID,
        description: Optional[str] = None,
        runtime: FunctionRuntime = FunctionRuntime.DENO,
        timeout_seconds: int = 30,
        memory_limit_mb: int = 512,
        max_concurrent: int = 10,
        env_vars: Optional[Dict[str, Any]] = None
    ) -> Function:
        """
        Create a new function.
        
        Args:
            name: Function name (must be unique)
            code: Function source code
            owner_id: Owner UUID
            description: Optional description
            runtime: Runtime environment
            timeout_seconds: Execution timeout
            memory_limit_mb: Memory limit
            max_concurrent: Max concurrent executions
            env_vars: Environment variables
            
        Returns:
            Created Function instance
            
        Raises:
            FunctionAlreadyExistsError: If function name already exists
            FunctionValidationError: If validation fails
        """
        # Check if function name already exists
        if await self._function_exists_by_name(name):
            raise FunctionAlreadyExistsError(f"Function '{name}' already exists")

        # Create function instance
        function = Function.create(
            name=name,
            code=code,
            owner_id=owner_id,
            description=description,
            runtime=runtime,
            timeout_seconds=timeout_seconds,
            memory_limit_mb=memory_limit_mb,
            max_concurrent=max_concurrent
        )
        
        if env_vars:
            function.set_env_vars(env_vars)

        # Insert into database
        async with self._db.transaction() as conn:
            await conn.execute("""
                INSERT INTO functions (
                    id, name, description, code, runtime, owner_id, is_active,
                    deployment_status, version, timeout_seconds, memory_limit_mb,
                    max_concurrent, env_vars, env_vars_updated_at,
                    execution_count, execution_success_count, execution_error_count,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18, $19
                )
            """,
            str(function.id),
            function.name,
            function.description,
            function.code,
            function.runtime.value,
            str(function.owner_id),
            function.is_active,
            function.deployment_status.value,
            function.version,
            function.timeout_seconds,
            function.memory_limit_mb,
            function.max_concurrent,
            json.dumps(function.env_vars) if function.env_vars else '{}',
            function.env_vars_updated_at,
            function.execution_count,
            function.execution_success_count,
            function.execution_error_count,
            function.created_at,
            function.updated_at
            )

        return function

    async def get_function(self, function_id: uuid.UUID) -> Function:
        """
        Get a function by ID.
        
        Args:
            function_id: Function UUID
            
        Returns:
            Function instance
            
        Raises:
            FunctionNotFoundError: If function doesn't exist
        """
        async with self._db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id, name, description, code, runtime, owner_id, is_active,
                    deployment_status, deployment_error, version, timeout_seconds,
                    memory_limit_mb, max_concurrent, env_vars, env_vars_updated_at,
                    execution_count, execution_success_count, execution_error_count,
                    last_executed_at, avg_execution_time_ms, last_deployed_at,
                    created_at, updated_at
                FROM functions
                WHERE id = $1
            """, str(function_id))

        if row is None:
            raise FunctionNotFoundError(f"Function with ID {function_id} not found")

        return self._row_to_function(row)

    async def get_function_by_name(self, name: str) -> Function:
        """
        Get a function by name.
        
        Args:
            name: Function name
            
        Returns:
            Function instance
            
        Raises:
            FunctionNotFoundError: If function doesn't exist
        """
        async with self._db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id, name, description, code, runtime, owner_id, is_active,
                    deployment_status, deployment_error, version, timeout_seconds,
                    memory_limit_mb, max_concurrent, env_vars, env_vars_updated_at,
                    execution_count, execution_success_count, execution_error_count,
                    last_executed_at, avg_execution_time_ms, last_deployed_at,
                    created_at, updated_at
                FROM functions
                WHERE name = $1
            """, name)

        if row is None:
            raise FunctionNotFoundError(f"Function '{name}' not found")

        return self._row_to_function(row)

    async def list_functions(
        self,
        owner_id: Optional[uuid.UUID] = None,
        include_inactive: bool = False
    ) -> List[Function]:
        """
        List functions with optional filtering.
        
        Args:
            owner_id: Filter by owner (None for all)
            include_inactive: Include inactive functions
            
        Returns:
            List of Function instances
        """
        query = """
            SELECT
                id, name, description, code, runtime, owner_id, is_active,
                deployment_status, deployment_error, version, timeout_seconds,
                memory_limit_mb, max_concurrent, env_vars, env_vars_updated_at,
                execution_count, execution_success_count, execution_error_count,
                last_executed_at, avg_execution_time_ms, last_deployed_at,
                created_at, updated_at
            FROM functions
        """
        
        params = []
        conditions = []
        
        if owner_id is not None:
            conditions.append("owner_id = $1")
            params.append(str(owner_id))
            
        if not include_inactive:
            conditions.append("is_active = true")
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY name"

        async with self._db.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_function(row) for row in rows]

    async def update_function(
        self,
        function_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> Function:
        """
        Update a function.
        
        Args:
            function_id: Function UUID
            updates: Dictionary of fields to update
            
        Returns:
            Updated Function instance
            
        Raises:
            FunctionNotFoundError: If function doesn't exist
            FunctionValidationError: If validation fails
        """
        # Get current function
        function = await self.get_function(function_id)
        
        # Apply updates
        if "name" in updates:
            new_name = updates["name"]
            if new_name != function.name and await self._function_exists_by_name(new_name):
                raise FunctionAlreadyExistsError(f"Function '{new_name}' already exists")
            function.name = new_name
            
        if "description" in updates:
            function.description = updates["description"]
            
        if "code" in updates:
            function.update_code(updates["code"])
            
        if "runtime" in updates:
            function.runtime = FunctionRuntime(updates["runtime"])
            
        if "timeout_seconds" in updates:
            function.timeout_seconds = updates["timeout_seconds"]
            
        if "memory_limit_mb" in updates:
            function.memory_limit_mb = updates["memory_limit_mb"]
            
        if "max_concurrent" in updates:
            function.max_concurrent = updates["max_concurrent"]
            
        if "env_vars" in updates:
            function.set_env_vars(updates["env_vars"])
            
        if "is_active" in updates:
            function.is_active = updates["is_active"]
            
        if "deployment_status" in updates:
            function.deployment_status = DeploymentStatus(updates["deployment_status"])
            
        if "deployment_error" in updates:
            function.deployment_error = updates["deployment_error"]

        function.updated_at = datetime.now(timezone.utc)

        # Update in database
        async with self._db.transaction() as conn:
            await conn.execute("""
                UPDATE functions SET
                    name = $2, description = $3, code = $4, runtime = $5,
                    is_active = $6, deployment_status = $7, deployment_error = $8,
                    version = $9, timeout_seconds = $10, memory_limit_mb = $11,
                    max_concurrent = $12, env_vars = $13, env_vars_updated_at = $14,
                    updated_at = $15
                WHERE id = $1
            """,
            str(function.id),
            function.name,
            function.description,
            function.code,
            function.runtime.value,
            function.is_active,
            function.deployment_status.value,
            function.deployment_error,
            function.version,
            function.timeout_seconds,
            function.memory_limit_mb,
            function.max_concurrent,
            json.dumps(function.env_vars) if function.env_vars else '{}',
            function.env_vars_updated_at,
            function.updated_at
            )

        return function

    async def delete_function(self, function_id: uuid.UUID) -> None:
        """
        Delete a function.
        
        Args:
            function_id: Function UUID
            
        Raises:
            FunctionNotFoundError: If function doesn't exist
        """
        # Check if function exists
        await self.get_function(function_id)

        # Delete from database (cascade will handle related records)
        async with self._db.transaction() as conn:
            await conn.execute("DELETE FROM functions WHERE id = $1", str(function_id))

    async def record_execution(
        self,
        function_id: uuid.UUID,
        success: bool,
        execution_time_ms: Optional[int] = None
    ) -> None:
        """
        Record a function execution.
        
        Args:
            function_id: Function UUID
            success: Whether execution was successful
            execution_time_ms: Execution time in milliseconds
        """
        async with self._db.transaction() as conn:
            await conn.execute("""
                UPDATE functions SET
                    execution_count = execution_count + 1,
                    execution_success_count = CASE WHEN $2 THEN execution_success_count + 1 ELSE execution_success_count END,
                    execution_error_count = CASE WHEN NOT $2 THEN execution_error_count + 1 ELSE execution_error_count END,
                    last_executed_at = $3,
                    avg_execution_time_ms = CASE
                        WHEN avg_execution_time_ms IS NULL THEN $4
                        ELSE (avg_execution_time_ms * (execution_count) + $4) / (execution_count + 1)
                    END,
                    updated_at = $3
                WHERE id = $1
            """,
            str(function_id),
            success,
            datetime.now(timezone.utc),
            execution_time_ms
            )

    async def update_deployment_status(
        self,
        function_id: uuid.UUID,
        status: DeploymentStatus,
        error: Optional[str] = None
    ) -> None:
        """
        Update function deployment status.
        
        Args:
            function_id: Function UUID
            status: New deployment status
            error: Deployment error message (if any)
        """
        update_fields = ["deployment_status = $2", "updated_at = $3"]
        params = [str(function_id), status.value, datetime.now(timezone.utc)]

        if error is not None:
            update_fields.append("deployment_error = $4")
            params.append(error)

        if status == DeploymentStatus.DEPLOYED:
            update_fields.append("last_deployed_at = $3")

        query = f"UPDATE functions SET {', '.join(update_fields)} WHERE id = $1"

        async with self._db.transaction() as conn:
            await conn.execute(query, *params)

    async def _function_exists_by_name(self, name: str) -> bool:
        """Check if a function exists by name."""
        async with self._db.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM functions WHERE name = $1)",
                name
            )
        return bool(result)

    def _row_to_function(self, row) -> Function:
        """Convert database row to Function instance."""
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
        # Ensure env_vars is a dict (DB driver may return JSON as str)
        env = row["env_vars"] or {}
        try:
            if isinstance(env, str):
                env = json.loads(env)
        except Exception:
            # leave as-is (fallback to empty dict)
            env = {} if env is None else env

        return Function(
            id=_to_uuid(row["id"]),
            name=row["name"],
            description=row["description"],
            code=row["code"],
            runtime=FunctionRuntime(row["runtime"]),
            owner_id=_to_uuid(row["owner_id"]),
            is_active=row["is_active"],
            deployment_status=DeploymentStatus(row["deployment_status"]),
            deployment_error=row["deployment_error"],
            version=row["version"],
            timeout_seconds=row["timeout_seconds"],
            memory_limit_mb=row["memory_limit_mb"],
            max_concurrent=row["max_concurrent"],
            env_vars=env,
            env_vars_updated_at=row["env_vars_updated_at"],
            execution_count=row["execution_count"],
            execution_success_count=row["execution_success_count"],
            execution_error_count=row["execution_error_count"],
            last_executed_at=row["last_executed_at"],
            avg_execution_time_ms=row["avg_execution_time_ms"],
            last_deployed_at=row["last_deployed_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
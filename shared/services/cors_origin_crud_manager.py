"""
CORS Origin CRUD manager for SelfDB CORS management.
Based on admin access control requirements for CORS origin management.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Sequence

from shared.database.connection_manager import DatabaseConnectionManager
from shared.models.cors_origin import CorsOrigin


class CorsOriginNotFoundError(Exception):
    """Raised when a CORS origin cannot be located."""


class CorsOriginAlreadyExistsError(Exception):
    """Raised when attempting to create a CORS origin with an origin that already exists."""


class CorsOriginValidationError(Exception):
    """Raised when CORS origin data fails validation."""


class CorsOriginCRUDManager:
    """Manage CORS origin CRUD operations and metadata persistence."""

    def __init__(self, database_manager: DatabaseConnectionManager):
        self._db = database_manager

    async def create_cors_origin(
        self,
        origin: str,
        created_by: uuid.UUID,
        description: Optional[str] = None,
        is_active: bool = True,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> CorsOrigin:
        """
        Create a new CORS origin.

        Args:
            origin: The origin URL to allow
            created_by: UUID of the user creating this origin
            description: Optional description
            is_active: Whether the origin is active (defaults to True)
            extra_metadata: Additional metadata

        Returns:
            Created CorsOrigin instance

        Raises:
            CorsOriginAlreadyExistsError: If origin already exists
            CorsOriginValidationError: If validation fails
        """
        # Check if origin already exists
        if await self._cors_origin_exists(origin):
            raise CorsOriginAlreadyExistsError(f"CORS origin '{origin}' already exists")

        # Create CORS origin instance
        cors_origin = CorsOrigin(
            id=uuid.uuid4(),
            origin=origin,
            description=description,
            is_active=is_active,
            extra_metadata=extra_metadata,
            created_by=created_by
        )

        # Persist to database
        await self._insert_cors_origin(cors_origin)

        return cors_origin

    async def get_cors_origin_by_id(self, origin_id: uuid.UUID) -> CorsOrigin:
        """
        Get a CORS origin by ID.

        Args:
            origin_id: UUID of the CORS origin

        Returns:
            CorsOrigin instance

        Raises:
            CorsOriginNotFoundError: If origin not found
        """
        async with self._db.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT id, origin, description, is_active, extra_metadata,
                       created_by, created_at, updated_at
                FROM cors_origins
                WHERE id = $1
                """,
                str(origin_id)
            )

            if not result:
                raise CorsOriginNotFoundError(f"CORS origin with ID {origin_id} not found")
            # Ensure extra_metadata is a dict (asyncpg may return JSON as a string)
            extra_meta = result['extra_metadata'] or {}
            if isinstance(extra_meta, str):
                try:
                    extra_meta = json.loads(extra_meta)
                except Exception:
                    # Fallback: leave as empty dict if decoding fails
                    extra_meta = {}

            return CorsOrigin(
                id=result['id'],
                origin=result['origin'],
                description=result['description'],
                is_active=result['is_active'],
                extra_metadata=extra_meta,
                created_by=result['created_by'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )

    async def list_cors_origins(
        self,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[CorsOrigin]:
        """
        List CORS origins with optional filtering.

        Args:
            active_only: Only return active origins
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of CorsOrigin instances
        """
        async with self._db.acquire() as conn:
            query = """
                SELECT id, origin, description, is_active, extra_metadata,
                       created_by, created_at, updated_at
                FROM cors_origins
            """
            params = []

            if active_only:
                # Use a literal true in the query (no parameter needed). Do not append
                # a value to params here because the final query uses $1/$2 for
                # LIMIT/OFFSET only.
                query += " WHERE is_active = true"
            else:
                query += " WHERE 1=1"

            query += " ORDER BY created_at DESC LIMIT $1 OFFSET $2"
            params.extend([limit, offset])

            results = await conn.fetch(query, *params)

            return [
                # Normalize extra_metadata to dict if necessary
                (lambda row: CorsOrigin(
                    id=row['id'],
                    origin=row['origin'],
                    description=row['description'],
                    is_active=row['is_active'],
                    extra_metadata=(json.loads(row['extra_metadata']) if isinstance(row['extra_metadata'], str) else (row['extra_metadata'] or {})),
                    created_by=row['created_by'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))(row)
                for row in results
            ]

    async def update_cors_origin(
        self,
        origin_id: uuid.UUID,
        origin: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> CorsOrigin:
        """
        Update a CORS origin.

        Args:
            origin_id: UUID of the CORS origin to update
            origin: New origin URL
            description: New description
            is_active: New active status
            extra_metadata: New metadata

        Returns:
            Updated CorsOrigin instance

        Raises:
            CorsOriginNotFoundError: If origin not found
            CorsOriginAlreadyExistsError: If new origin already exists
        """
        # Get existing origin
        existing = await self.get_cors_origin_by_id(origin_id)

        # Check if new origin conflicts with existing ones
        if origin and origin != existing.origin:
            if await self._cors_origin_exists(origin):
                raise CorsOriginAlreadyExistsError(f"CORS origin '{origin}' already exists")

        # Update the instance
        update_data = {}
        if origin is not None:
            update_data['origin'] = origin
        if description is not None:
            update_data['description'] = description
        if is_active is not None:
            update_data['is_active'] = is_active
        if extra_metadata is not None:
            update_data['extra_metadata'] = extra_metadata

        existing.update(**update_data)

        # Persist to database
        await self._update_cors_origin(existing)

        return existing

    async def delete_cors_origin(self, origin_id: uuid.UUID, hard_delete: bool = True) -> None:
        """
        Delete a CORS origin.

        Args:
            origin_id: UUID of the CORS origin to delete
            hard_delete: If True, permanently delete; otherwise soft delete by deactivating

        Raises:
            CorsOriginNotFoundError: If origin not found
        """
        # Verify origin exists
        await self.get_cors_origin_by_id(origin_id)

        async with self._db.transaction() as conn:
            if hard_delete:
                await conn.execute("DELETE FROM cors_origins WHERE id = $1", str(origin_id))
            else:
                await conn.execute(
                    "UPDATE cors_origins SET is_active = false, updated_at = $1 WHERE id = $2",
                    datetime.now(timezone.utc),
                    str(origin_id)
                )

    async def validate_origin_url(self, origin: str) -> Dict[str, Any]:
        """
        Validate an origin URL format.

        Args:
            origin: The origin URL to validate

        Returns:
            Validation result with is_valid and error_message
        """
        try:
            # Create a temporary CorsOrigin to validate
            temp_origin = CorsOrigin(
                id=uuid.uuid4(),
                origin=origin,
                created_by=uuid.uuid4()
            )
            return {"is_valid": True, "error_message": None}
        except ValueError as e:
            return {"is_valid": False, "error_message": str(e)}

    async def refresh_cors_cache(self) -> Dict[str, Any]:
        """
        Refresh the CORS origins cache (placeholder for future caching implementation).

        Returns:
            Cache refresh result
        """
        # For now, just return success
        # In the future, this could refresh Redis cache or similar
        return {"message": "CORS cache refreshed successfully"}

    async def _cors_origin_exists(self, origin: str) -> bool:
        """Check if a CORS origin already exists."""
        async with self._db.acquire() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM cors_origins WHERE origin = $1",
                origin
            )
            return result > 0

    async def _webhook_exists_by_name_and_owner(self, name: str, owner_id: uuid.UUID) -> bool:
        """Check if a webhook exists by name and owner (not used in CORS, but keeping for compatibility)."""
        return False

    async def _insert_cors_origin(self, cors_origin: CorsOrigin) -> None:
        """Insert a new CORS origin into the database."""
        async with self._db.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO cors_origins (
                    id, origin, description, is_active, extra_metadata,
                    created_by, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                str(cors_origin.id),
                cors_origin.origin,
                cors_origin.description,
                cors_origin.is_active,
                json.dumps(cors_origin.extra_metadata),
                str(cors_origin.created_by) if cors_origin.created_by else None,
                cors_origin.created_at,
                cors_origin.updated_at
            )

    async def _update_cors_origin(self, cors_origin: CorsOrigin) -> None:
        """Update an existing CORS origin in the database."""
        async with self._db.transaction() as conn:
            await conn.execute(
                """
                UPDATE cors_origins
                SET origin = $1, description = $2, is_active = $3,
                    extra_metadata = $4, updated_at = $5
                WHERE id = $6
                """,
                cors_origin.origin,
                cors_origin.description,
                cors_origin.is_active,
                json.dumps(cors_origin.extra_metadata),
                cors_origin.updated_at,
                str(cors_origin.id)
            )
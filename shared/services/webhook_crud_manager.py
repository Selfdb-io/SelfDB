"""
Webhook CRUD manager for SelfDB webhook management.
Based on Functions & Webhooks Improvement Plan requirements.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Sequence

from shared.database.connection_manager import DatabaseConnectionManager
from shared.models.webhook import Webhook, RetryBackoffStrategy


class WebhookNotFoundError(Exception):
    """Raised when a webhook cannot be located."""


class WebhookAlreadyExistsError(Exception):
    """Raised when attempting to create a webhook with a name that already exists."""


class WebhookValidationError(Exception):
    """Raised when webhook data fails validation."""


class WebhookCRUDManager:
    """Manage webhook CRUD operations and metadata persistence."""

    def __init__(self, database_manager: DatabaseConnectionManager):
        self._db = database_manager

    async def create_webhook(
        self,
        function_id: uuid.UUID,
        owner_id: uuid.UUID,
        name: str,
        secret_key: str,
        description: Optional[str] = None,
        provider: Optional[str] = None,
        provider_event_type: Optional[str] = None,
        source_url: Optional[str] = None,
        rate_limit_per_minute: int = 100,
        retry_attempts: int = 3,
        retry_backoff_strategy: RetryBackoffStrategy = RetryBackoffStrategy.EXPONENTIAL,
        retry_delay_seconds: int = 60,
        retry_max_delay_seconds: int = 3600,
        payload_schema: Optional[Dict[str, Any]] = None,
        expected_headers: Optional[Dict[str, str]] = None,
        transform_script: Optional[str] = None
    ) -> Webhook:
        """
        Create a new webhook.
        
        Args:
            function_id: Associated function UUID
            owner_id: Owner UUID
            name: Webhook name (must be unique for owner)
            secret_key: HMAC secret for signature verification
            description: Optional description
            provider: External provider name
            provider_event_type: Provider event type
            source_url: External source URL
            rate_limit_per_minute: Rate limiting (1-10000)
            retry_attempts: Max retry attempts (1-10)
            retry_backoff_strategy: Retry backoff strategy
            retry_delay_seconds: Initial retry delay (1-3600)
            retry_max_delay_seconds: Maximum retry delay
            payload_schema: JSON schema for payload validation
            expected_headers: Expected HTTP headers
            transform_script: Payload transformation script
            
        Returns:
            Created Webhook instance
            
        Raises:
            WebhookAlreadyExistsError: If webhook name already exists for owner
            WebhookValidationError: If validation fails
        """
        # Check if webhook name already exists for this owner
        if await self._webhook_exists_by_name_and_owner(name, owner_id):
            raise WebhookAlreadyExistsError(f"Webhook '{name}' already exists for this owner")

        # Create webhook instance
        webhook = Webhook.create(
            function_id=function_id,
            owner_id=owner_id,
            name=name,
            secret_key=secret_key,
            description=description,
            provider=provider,
            provider_event_type=provider_event_type,
            source_url=source_url,
            rate_limit_per_minute=rate_limit_per_minute,
            retry_attempts=retry_attempts,
            retry_backoff_strategy=retry_backoff_strategy
        )
        
        # Set additional properties
        webhook.retry_delay_seconds = retry_delay_seconds
        webhook.retry_max_delay_seconds = retry_max_delay_seconds
        webhook.payload_schema = payload_schema
        webhook.expected_headers = expected_headers or {}
        webhook.transform_script = transform_script

        # Insert into database
        async with self._db.transaction() as conn:
            await conn.execute("""
                INSERT INTO webhooks (
                    id, function_id, owner_id, name, description, provider,
                    provider_event_type, source_url, webhook_token, secret_key,
                    is_active, rate_limit_per_minute, max_queue_size,
                    retry_enabled, retry_attempts, retry_backoff_strategy,
                    retry_delay_seconds, retry_max_delay_seconds, payload_schema,
                    expected_headers, transform_script, is_active_delivery,
                    last_received_at, last_delivery_status, successful_delivery_count,
                    failed_delivery_count, total_delivery_count, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26,
                    $27, $28, $29
                )
            """,
            str(webhook.id),
            str(webhook.function_id),
            str(webhook.owner_id),  # Convert UUID to string
            webhook.name,
            webhook.description,
            webhook.provider,
            webhook.provider_event_type,
            webhook.source_url,
            webhook.webhook_token,
            webhook.secret_key,
            webhook.is_active,
            webhook.rate_limit_per_minute,
            webhook.max_queue_size,
            webhook.retry_enabled,
            webhook.retry_attempts,
            webhook.retry_backoff_strategy.value,
            webhook.retry_delay_seconds,
            webhook.retry_max_delay_seconds,
            json.dumps(webhook.payload_schema) if webhook.payload_schema is not None else '{}',
            json.dumps(webhook.expected_headers) if webhook.expected_headers is not None else '{}',
            webhook.transform_script,
            webhook.is_active_delivery,
            webhook.last_received_at,
            webhook.last_delivery_status,
            webhook.successful_delivery_count,
            webhook.failed_delivery_count,
            webhook.total_delivery_count,
            webhook.created_at,
            webhook.updated_at
            )

        return webhook

    async def get_webhook(self, webhook_id: uuid.UUID) -> Webhook:
        """
        Get a webhook by ID.
        
        Args:
            webhook_id: Webhook UUID
            
        Returns:
            Webhook instance
            
        Raises:
            WebhookNotFoundError: If webhook doesn't exist
        """
        async with self._db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id, function_id, owner_id, name, description, provider,
                    provider_event_type, source_url, webhook_token, secret_key,
                    path_segment, is_active, rate_limit_per_minute, max_queue_size,
                    retry_enabled, retry_attempts, retry_backoff_strategy,
                    retry_delay_seconds, retry_max_delay_seconds, payload_schema,
                    expected_headers, transform_script, is_active_delivery,
                    last_received_at, last_delivery_status, successful_delivery_count,
                    failed_delivery_count, total_delivery_count, created_at, updated_at
                FROM webhooks
                WHERE id = $1
            """, str(webhook_id))

        if row is None:
            raise WebhookNotFoundError(f"Webhook with ID {webhook_id} not found")

        return self._row_to_webhook(row)

    async def get_webhook_by_token(self, webhook_token: str) -> Webhook:
        """
        Get a webhook by token.
        
        Args:
            webhook_token: Webhook token
            
        Returns:
            Webhook instance
            
        Raises:
            WebhookNotFoundError: If webhook doesn't exist
        """
        async with self._db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id, function_id, owner_id, name, description, provider,
                    provider_event_type, source_url, webhook_token, secret_key,
                    path_segment, is_active, rate_limit_per_minute, max_queue_size,
                    retry_enabled, retry_attempts, retry_backoff_strategy,
                    retry_delay_seconds, retry_max_delay_seconds, payload_schema,
                    expected_headers, transform_script, is_active_delivery,
                    last_received_at, last_delivery_status, successful_delivery_count,
                    failed_delivery_count, total_delivery_count, created_at, updated_at
                FROM webhooks
                WHERE webhook_token = $1
            """, webhook_token)

        if row is None:
            raise WebhookNotFoundError(f"Webhook with token '{webhook_token}' not found")

        return self._row_to_webhook(row)

    async def list_webhooks(
        self,
        owner_id: Optional[uuid.UUID] = None,
        function_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
        include_inactive: bool = False
    ) -> List[Webhook]:
        """
        List webhooks with optional filtering.
        
        Args:
            owner_id: Filter by owner (None for all)
            function_id: Filter by function (None for all)
            provider: Filter by provider (None for all)
            include_inactive: Include inactive webhooks
            
        Returns:
            List of Webhook instances
        """
        query = """
            SELECT
                id, function_id, owner_id, name, description, provider,
                provider_event_type, source_url, webhook_token, secret_key,
                path_segment, is_active, rate_limit_per_minute, max_queue_size,
                retry_enabled, retry_attempts, retry_backoff_strategy,
                retry_delay_seconds, retry_max_delay_seconds, payload_schema,
                expected_headers, transform_script, is_active_delivery,
                last_received_at, last_delivery_status, successful_delivery_count,
                failed_delivery_count, total_delivery_count, created_at, updated_at
            FROM webhooks
        """
        
        params = []
        conditions = []
        
        if owner_id is not None:
            conditions.append("owner_id = $1")
            params.append(str(owner_id))
            
        if function_id is not None:
            conditions.append("function_id = $2")
            params.append(str(function_id))
            
        if provider is not None:
            conditions.append("provider = $3")
            params.append(provider)
            
        if not include_inactive:
            conditions.append("is_active = true")
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY name"

        async with self._db.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_webhook(row) for row in rows]

    async def update_webhook(
        self,
        webhook_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> Webhook:
        """
        Update a webhook.
        
        Args:
            webhook_id: Webhook UUID
            updates: Dictionary of fields to update
            
        Returns:
            Updated Webhook instance
            
        Raises:
            WebhookNotFoundError: If webhook doesn't exist
            WebhookValidationError: If validation fails
        """
        # Get current webhook
        webhook = await self.get_webhook(webhook_id)
        
        # Apply updates
        if "name" in updates:
            new_name = updates["name"]
            if new_name != webhook.name and await self._webhook_exists_by_name_and_owner(new_name, webhook.owner_id):
                raise WebhookAlreadyExistsError(f"Webhook '{new_name}' already exists for this owner")
            webhook.name = new_name
            
        if "description" in updates:
            webhook.description = updates["description"]
            
        if "provider" in updates:
            webhook.provider = updates["provider"]
            webhook.path_segment = webhook._generate_path_segment()  # Regenerate path segment
            
        if "provider_event_type" in updates:
            webhook.provider_event_type = updates["provider_event_type"]
            
        if "source_url" in updates:
            webhook.source_url = updates["source_url"]
            
        if "secret_key" in updates:
            webhook.secret_key = updates["secret_key"]
            
        if "is_active" in updates:
            webhook.is_active = updates["is_active"]
            
        if "rate_limit_per_minute" in updates:
            webhook.rate_limit_per_minute = updates["rate_limit_per_minute"]
            
        if "max_queue_size" in updates:
            webhook.max_queue_size = updates["max_queue_size"]
            
        if "retry_enabled" in updates:
            webhook.retry_enabled = updates["retry_enabled"]
            
        if "retry_attempts" in updates:
            webhook.retry_attempts = updates["retry_attempts"]
            
        if "retry_backoff_strategy" in updates:
            webhook.retry_backoff_strategy = RetryBackoffStrategy(updates["retry_backoff_strategy"])
            
        if "retry_delay_seconds" in updates:
            webhook.retry_delay_seconds = updates["retry_delay_seconds"]
            
        if "retry_max_delay_seconds" in updates:
            webhook.retry_max_delay_seconds = updates["retry_max_delay_seconds"]
            
        if "payload_schema" in updates:
            webhook.payload_schema = updates["payload_schema"]
            
        if "expected_headers" in updates:
            webhook.expected_headers = updates["expected_headers"]
            
        if "transform_script" in updates:
            webhook.transform_script = updates["transform_script"]

        webhook.updated_at = datetime.now(timezone.utc)

        # Update in database
        async with self._db.transaction() as conn:
            await conn.execute("""
                UPDATE webhooks SET
                    name = $2, description = $3, provider = $4,
                    provider_event_type = $5, source_url = $6, secret_key = $7,
                    is_active = $8, rate_limit_per_minute = $9,
                    max_queue_size = $11, retry_enabled = $12, retry_attempts = $13,
                    retry_backoff_strategy = $14, retry_delay_seconds = $15,
                    retry_max_delay_seconds = $16, payload_schema = $17,
                    expected_headers = $18, transform_script = $19, updated_at = $20
                WHERE id = $1
            """,
            str(webhook.id),
            webhook.name,
            webhook.description,
            webhook.provider,
            webhook.provider_event_type,
            webhook.source_url,
            webhook.secret_key,
            webhook.is_active,
            webhook.rate_limit_per_minute,
            webhook.max_queue_size,
            webhook.retry_enabled,
            webhook.retry_attempts,
            webhook.retry_backoff_strategy.value,
            webhook.retry_delay_seconds,
            webhook.retry_max_delay_seconds,
            json.dumps(webhook.payload_schema) if webhook.payload_schema is not None else '{}',
            json.dumps(webhook.expected_headers) if webhook.expected_headers is not None else '{}',
            webhook.transform_script,
            webhook.updated_at
            )

        return webhook

    async def delete_webhook(self, webhook_id: uuid.UUID) -> None:
        """
        Delete a webhook.
        
        Args:
            webhook_id: Webhook UUID
            
        Raises:
            WebhookNotFoundError: If webhook doesn't exist
        """
        # Check if webhook exists
        await self.get_webhook(webhook_id)

        # Delete from database (cascade will handle related records)
        async with self._db.transaction() as conn:
            await conn.execute("DELETE FROM webhooks WHERE id = $1", str(webhook_id))

    async def record_delivery(
        self,
        webhook_id: uuid.UUID,
        success: bool,
        status: str
    ) -> None:
        """
        Record a webhook delivery attempt.
        
        Args:
            webhook_id: Webhook UUID
            success: Whether delivery was successful
            status: Delivery status string
        """
        async with self._db.transaction() as conn:
            await conn.execute("""
                UPDATE webhooks SET
                    total_delivery_count = total_delivery_count + 1,
                    successful_delivery_count = CASE WHEN $2 THEN successful_delivery_count + 1 ELSE successful_delivery_count END,
                    failed_delivery_count = CASE WHEN NOT $2 THEN failed_delivery_count + 1 ELSE failed_delivery_count END,
                    last_delivery_status = $3,
                    last_received_at = $4,
                    updated_at = $4
                WHERE id = $1
            """,
            str(webhook_id),
            success,
            status,
            datetime.now(timezone.utc)
            )

    async def _webhook_exists_by_name_and_owner(self, name: str, owner_id: uuid.UUID) -> bool:
        """Check if a webhook exists by name and owner."""
        async with self._db.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM webhooks WHERE name = $1 AND owner_id = $2)",
                name, str(owner_id)
            )
        return bool(result)

    def _row_to_webhook(self, row) -> Webhook:
        """Convert database row to Webhook instance."""
        # Normalize UUID fields: DB may return strings for UUID columns depending on driver
        def _to_uuid(val):
            try:
                if isinstance(val, str):
                    return uuid.UUID(val)
                return val
            except Exception:
                return val

        return Webhook(
            id=_to_uuid(row["id"]),
            function_id=_to_uuid(row["function_id"]),
            owner_id=_to_uuid(row["owner_id"]),
            name=row["name"],
            description=row["description"],
            provider=row["provider"],
            provider_event_type=row["provider_event_type"],
            source_url=row["source_url"],
            webhook_token=row["webhook_token"],
            secret_key=row["secret_key"],
            is_active=row["is_active"],
            rate_limit_per_minute=row["rate_limit_per_minute"],
            max_queue_size=row["max_queue_size"],
            retry_enabled=row["retry_enabled"],
            retry_attempts=row["retry_attempts"],
            retry_backoff_strategy=RetryBackoffStrategy(row["retry_backoff_strategy"]),
            retry_delay_seconds=row["retry_delay_seconds"],
            retry_max_delay_seconds=row["retry_max_delay_seconds"],
            payload_schema=row["payload_schema"],
            expected_headers=row["expected_headers"] or {},
            transform_script=row["transform_script"],
            is_active_delivery=row["is_active_delivery"],
            last_received_at=row["last_received_at"],
            last_delivery_status=row["last_delivery_status"],
            successful_delivery_count=row["successful_delivery_count"],
            failed_delivery_count=row["failed_delivery_count"],
            total_delivery_count=row["total_delivery_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
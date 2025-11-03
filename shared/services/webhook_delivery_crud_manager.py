"""
WebhookDelivery CRUD manager for SelfDB webhook delivery audit trail.
Based on Functions & Webhooks Improvement Plan requirements.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from shared.database.connection_manager import DatabaseConnectionManager
from shared.models.webhook_delivery import WebhookDelivery, WebhookDeliveryStatus


class WebhookDeliveryNotFoundError(Exception):
    """Raised when a webhook delivery cannot be located."""


class WebhookDeliveryValidationError(Exception):
    """Raised when webhook delivery data fails validation."""


class WebhookDeliveryCRUDManager:
    """Manage webhook delivery CRUD operations and audit trail."""

    def __init__(self, database_manager: DatabaseConnectionManager):
        self._db = database_manager

    async def create_delivery(
        self,
        webhook_id: uuid.UUID,
        function_id: uuid.UUID,
        request_headers: Dict[str, str],
        request_body: str,
        request_method: str = "POST",
        request_url: Optional[str] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        signature_valid: Optional[bool] = None,
        signature_header: Optional[str] = None
    ) -> WebhookDelivery:
        """
        Create a new webhook delivery record.
        
        Args:
            webhook_id: Associated webhook UUID
            function_id: Associated function UUID
            request_headers: HTTP request headers
            request_body: Raw request body
            request_method: HTTP method
            request_url: Request URL
            source_ip: Sender IP address
            user_agent: User agent string
            signature_valid: Whether signature was valid
            signature_header: Signature header value
            
        Returns:
            Created WebhookDelivery instance
        """
        # Create delivery instance
        delivery = WebhookDelivery.create(
            webhook_id=webhook_id,
            function_id=function_id,
            request_headers=request_headers,
            request_body=request_body,
            request_method=request_method,
            request_url=request_url,
            source_ip=source_ip,
            user_agent=user_agent
        )
        
        # Set additional validation fields
        delivery.signature_valid = signature_valid
        delivery.signature_header = signature_header

        # Insert into database
        async with self._db.transaction() as conn:
            # The DB schema for webhook_deliveries does not include delivery_attempt
            # and uses slightly different column names (signature_provided, source_user_agent)
            await conn.execute("""
                INSERT INTO webhook_deliveries (
                    id, webhook_id, function_id, delivery_attempt, status,
                    source_ip, source_user_agent, request_headers, request_body,
                    request_body_size_bytes, request_method, request_url,
                    signature_header_name, signature_provided, signature_valid,
                    validation_errors, queued_at, processing_started_at,
                    processing_completed_at, execution_time_ms,
                    response_status_code, response_headers, response_body,
                    error_message, retry_count, next_retry_at, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28
                )
            """,
            str(delivery.id),
            str(delivery.webhook_id),
            str(delivery.function_id),
            delivery.delivery_attempt,
            delivery.status.value,
            delivery.source_ip,
            delivery.user_agent,
            json.dumps(delivery.request_headers) if isinstance(delivery.request_headers, dict) else delivery.request_headers,
            delivery.request_body,
            len(delivery.request_body) if delivery.request_body else 0,
            delivery.request_method,
            delivery.request_url,
            None,  # signature_header_name not stored separately here
            delivery.signature_header,
            delivery.signature_valid,
            json.dumps(delivery.validation_errors) if delivery.validation_errors else None,
            delivery.queued_at,
            delivery.processing_started_at,
            delivery.processing_completed_at,
            delivery.execution_time_ms,
            delivery.response_status_code,
            json.dumps(delivery.response_headers) if isinstance(delivery.response_headers, dict) else delivery.response_headers,
            delivery.response_body,
            delivery.error_message,
            delivery.retry_count,
            delivery.next_retry_at,
            delivery.created_at,
            delivery.updated_at
            )

        return delivery

    async def get_delivery(self, delivery_id: uuid.UUID) -> WebhookDelivery:
        """
        Get a webhook delivery by ID.
        
        Args:
            delivery_id: Delivery UUID
            
        Returns:
            WebhookDelivery instance
            
        Raises:
            WebhookDeliveryNotFoundError: If delivery doesn't exist
        """
        async with self._db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    id, webhook_id, function_id, delivery_attempt, status,
                    source_ip, source_user_agent, request_headers, request_body,
                    request_method, request_url, signature_valid, signature_provided,
                    validation_errors, queued_at, processing_started_at,
                    processing_completed_at, execution_time_ms,
                    response_status_code, response_headers, response_body,
                    error_message, retry_count, next_retry_at, created_at, updated_at
                FROM webhook_deliveries
                WHERE id = $1
            """, str(delivery_id))

        if row is None:
            raise WebhookDeliveryNotFoundError(f"Webhook delivery with ID {delivery_id} not found")

        return self._row_to_delivery(row)

    async def list_deliveries(
        self,
        webhook_id: Optional[uuid.UUID] = None,
        function_id: Optional[uuid.UUID] = None,
        status: Optional[WebhookDeliveryStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[WebhookDelivery]:
        """
        List webhook deliveries with optional filtering.
        
        Args:
            webhook_id: Filter by webhook (None for all)
            function_id: Filter by function (None for all)
            status: Filter by status (None for all)
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of WebhookDelivery instances
        """
        query = """
            SELECT
                id, webhook_id, function_id, delivery_attempt, status,
                source_ip, source_user_agent, request_headers, request_body,
                request_method, request_url, signature_valid, signature_provided,
                validation_errors, queued_at, processing_started_at,
                processing_completed_at, execution_time_ms,
                response_status_code, response_headers, response_body,
                error_message, retry_count, next_retry_at, created_at, updated_at
            FROM webhook_deliveries
        """
        
        params = []
        conditions = []
        
        if webhook_id is not None:
            conditions.append("webhook_id = $1")
            # Cast UUID to string for the DB driver which expects str parameters
            params.append(str(webhook_id))
            
        if function_id is not None:
            conditions.append("function_id = $2")
            params.append(str(function_id))
            
        if status is not None:
            conditions.append("status = $3")
            params.append(status.value)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY created_at DESC LIMIT $%d OFFSET $%d" % (len(params) + 1, len(params) + 2)
        params.extend([limit, offset])

        async with self._db.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_delivery(row) for row in rows]

    async def update_delivery_status(
        self,
        delivery_id: uuid.UUID,
        status: WebhookDeliveryStatus,
        updates: Optional[Dict[str, Any]] = None
    ) -> WebhookDelivery:
        """
        Update delivery status and optional fields.
        
        Args:
            delivery_id: Delivery UUID
            status: New status
            updates: Additional fields to update
            
        Returns:
            Updated WebhookDelivery instance
            
        Raises:
            WebhookDeliveryNotFoundError: If delivery doesn't exist
        """
        # Get current delivery
        delivery = await self.get_delivery(delivery_id)
        
        # Apply status change
        delivery.status = status
        
        # Apply additional updates
        if updates:
            for key, value in updates.items():
                if hasattr(delivery, key):
                    setattr(delivery, key, value)
        
        delivery.updated_at = datetime.now(timezone.utc)

        # Build dynamic update query
        update_fields = ["status = $2", "updated_at = $3"]
        params = [str(delivery_id), status.value, delivery.updated_at]
        
        field_mappings = {
            "signature_valid": "signature_valid",
            "signature_header": "signature_header",
            "validation_errors": "validation_errors",
            "processing_started_at": "processing_started_at",
            "processing_completed_at": "processing_completed_at",
            "execution_time_ms": "execution_time_ms",
            "response_status_code": "response_status_code",
            "response_headers": "response_headers",
            "response_body": "response_body",
            "error_message": "error_message",
            "retry_count": "retry_count",
            "next_retry_at": "next_retry_at"
        }
        
        for field, db_field in field_mappings.items():
            if field in updates:
                update_fields.append(f"{db_field} = ${len(params) + 1}")
                value = getattr(delivery, field)
                # JSON serialize dict fields for JSONB columns
                if field in ["response_headers", "validation_errors"] and isinstance(value, dict):
                    value = json.dumps(value)
                params.append(value)

        query = f"UPDATE webhook_deliveries SET {', '.join(update_fields)} WHERE id = $1"
        
        async with self._db.transaction() as conn:
            await conn.execute(query, *params)

        return delivery

    async def start_processing(self, delivery_id: uuid.UUID) -> WebhookDelivery:
        """
        Mark delivery as started processing.
        
        Args:
            delivery_id: Delivery UUID
            
        Returns:
            Updated WebhookDelivery instance
        """
        now = datetime.now(timezone.utc)
        updates = {
            "processing_started_at": now,
            "status": WebhookDeliveryStatus.EXECUTING
        }
        
        async with self._db.transaction() as conn:
            await conn.execute("""
                UPDATE webhook_deliveries SET
                    status = $2, processing_started_at = $3, updated_at = $3
                WHERE id = $1
            """, str(delivery_id), WebhookDeliveryStatus.EXECUTING.value, now)

        # Return updated delivery
        return await self.get_delivery(delivery_id)

    async def complete_processing(
        self,
        delivery_id: uuid.UUID,
        success: bool,
        response_status_code: Optional[int] = None,
        response_headers: Optional[Dict[str, str]] = None,
        response_body: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> WebhookDelivery:
        """
        Mark delivery as completed.
        
        Args:
            delivery_id: Delivery UUID
            success: Whether processing was successful
            response_status_code: HTTP response status
            response_headers: Response headers
            response_body: Response body
            execution_time_ms: Execution duration
            error_message: Error message if failed
            
        Returns:
            Updated WebhookDelivery instance
        """
        status = WebhookDeliveryStatus.COMPLETED if success else WebhookDeliveryStatus.FAILED
        now = datetime.now(timezone.utc)
        
        async with self._db.transaction() as conn:
            await conn.execute("""
                UPDATE webhook_deliveries SET
                    status = $2, processing_completed_at = $3,
                    execution_time_ms = $4, response_status_code = $5,
                    response_headers = $6, response_body = $7,
                    error_message = $8, updated_at = $3
                WHERE id = $1
            """,
            str(delivery_id),
            status.value,
            now,
            execution_time_ms,
            response_status_code,
            json.dumps(response_headers or {}),
            response_body,
            error_message
            )

        # Return updated delivery
        return await self.get_delivery(delivery_id)

    async def schedule_retry(
        self,
        delivery_id: uuid.UUID,
        next_retry_at: datetime
    ) -> WebhookDelivery:
        """
        Schedule a retry for delivery.
        
        Args:
            delivery_id: Delivery UUID
            next_retry_at: When to retry
            
        Returns:
            Updated WebhookDelivery instance
        """
        now = datetime.now(timezone.utc)
        
        async with self._db.transaction() as conn:
            await conn.execute("""
                UPDATE webhook_deliveries SET
                    status = $2, retry_count = retry_count + 1,
                    next_retry_at = $3, updated_at = $4
                WHERE id = $1
            """,
            str(delivery_id),
            WebhookDeliveryStatus.RETRY_PENDING.value,
            next_retry_at,
            now
            )

        # Return updated delivery
        return await self.get_delivery(delivery_id)

    async def get_pending_retries(self, limit: int = 100) -> List[WebhookDelivery]:
        """
        Get deliveries pending retry.
        
        Args:
            limit: Maximum number of deliveries to return
            
        Returns:
            List of deliveries ready for retry
        """
        now = datetime.now(timezone.utc)
        
        async with self._db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    id, webhook_id, function_id, delivery_attempt, status,
                    source_ip, user_agent, request_headers, request_body,
                    request_method, request_url, signature_valid, signature_header,
                    validation_errors, queued_at, processing_started_at,
                    processing_completed_at, execution_time_ms,
                    response_status_code, response_headers, response_body,
                    error_message, retry_count, next_retry_at, created_at, updated_at
                FROM webhook_deliveries
                WHERE status = $1 AND next_retry_at <= $2
                ORDER BY next_retry_at ASC
                LIMIT $3
            """,
            WebhookDeliveryStatus.RETRY_PENDING.value,
            now,
            limit
            )

        return [self._row_to_delivery(row) for row in rows]

    async def get_delivery_stats(
        self,
        webhook_id: Optional[uuid.UUID] = None,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get delivery statistics.
        
        Args:
            webhook_id: Filter by webhook (None for all)
            since: Only include deliveries since this time
            
        Returns:
            Statistics dictionary
        """
        query = """
            SELECT
                COUNT(*) as total_deliveries,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_deliveries,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_deliveries,
                COUNT(CASE WHEN status = 'retry_pending' THEN 1 END) as pending_retries,
                AVG(execution_time_ms) as avg_execution_time,
                MIN(created_at) as oldest_delivery,
                MAX(created_at) as newest_delivery
            FROM webhook_deliveries
        """
        
        params = []
        conditions = []
        
        if webhook_id is not None:
            conditions.append("webhook_id = $1")
            params.append(str(webhook_id))
            
        if since is not None:
            conditions.append("created_at >= $2")
            params.append(since)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        async with self._db.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        return dict(row) if row else {}

    def _row_to_delivery(self, row) -> WebhookDelivery:
        """Convert database row to WebhookDelivery instance."""
        # Some DB drivers return JSONB as dicts or strings; normalize
        def _parse_json(val):
            try:
                if val is None:
                    return None
                if isinstance(val, str):
                    return json.loads(val)
                return val
            except Exception:
                return val

        req_headers = _parse_json(row.get("request_headers")) or {}
        validation_errors = _parse_json(row.get("validation_errors")) or []
        response_headers = _parse_json(row.get("response_headers")) or {}

        # signature_provided in schema maps to signature_header in model
        signature_header = row.get("signature_provided") or row.get("signature_header")

        # Normalize DB id fields to uuid.UUID objects when possible
        def _to_uuid(val):
            try:
                if isinstance(val, uuid.UUID):
                    return val
                return uuid.UUID(str(val))
            except Exception:
                return val

        return WebhookDelivery(
            id=_to_uuid(row["id"]),
            webhook_id=_to_uuid(row["webhook_id"]),
            function_id=_to_uuid(row["function_id"]),
            # delivery_attempt is not present in DB schema; default to 1
            delivery_attempt=1,
            status=WebhookDeliveryStatus(row["status"]),
            source_ip=row.get("source_ip"),
            user_agent=row.get("source_user_agent") or row.get("user_agent"),
            request_headers=req_headers,
            request_body=row.get("request_body"),
            request_method=row.get("request_method"),
            request_url=row.get("request_url"),
            signature_valid=row.get("signature_valid"),
            signature_header=signature_header,
            validation_errors=validation_errors,
            queued_at=row.get("queued_at"),
            processing_started_at=row.get("processing_started_at"),
            processing_completed_at=row.get("processing_completed_at"),
            execution_time_ms=row.get("execution_time_ms"),
            response_status_code=row.get("response_status_code"),
            response_headers=response_headers,
            response_body=row.get("response_body"),
            error_message=row.get("error_message"),
            retry_count=row.get("retry_count") or 0,
            next_retry_at=row.get("next_retry_at"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )
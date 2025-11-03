"""
Unit tests for WebhookDeliveryCRUDManager business logic using mocked database operations.
"""

import uuid
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone, timedelta

from shared.services.webhook_delivery_crud_manager import (
    WebhookDeliveryCRUDManager,
    WebhookDeliveryNotFoundError
)
from shared.models.webhook_delivery import WebhookDelivery, WebhookDeliveryStatus


@pytest.mark.asyncio
async def test_create_delivery_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test successful delivery creation."""
    manager = WebhookDeliveryCRUDManager(mock_database_manager)

    webhook_id = uuid.uuid4()
    function_id = uuid.uuid4()

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    delivery = await manager.create_delivery(
        webhook_id=webhook_id,
        function_id=function_id,
        request_headers={"Content-Type": "application/json"},
        request_body='{"event": "test"}',
        request_method="POST",
        source_ip="192.168.1.100"
    )

    # Verify the delivery was created with correct attributes
    assert delivery.webhook_id == webhook_id
    assert delivery.function_id == function_id
    assert delivery.request_headers == {"Content-Type": "application/json"}
    assert delivery.request_body == '{"event": "test"}'
    assert delivery.request_method == "POST"
    assert delivery.source_ip == "192.168.1.100"
    assert delivery.status == WebhookDeliveryStatus.RECEIVED
    assert delivery.retry_count == 0

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_delivery_success(mock_database_manager, mock_db_connection):
    """Test successful delivery retrieval."""
    manager = WebhookDeliveryCRUDManager(mock_database_manager)

    delivery_id = uuid.uuid4()
    webhook_id = uuid.uuid4()
    function_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database row
    mock_row = {
        "id": delivery_id,
        "webhook_id": webhook_id,
        "function_id": function_id,
        "delivery_attempt": 1,
        "status": "executing",
        "source_ip": "192.168.1.100",
        "user_agent": "Stripe/1.0",
        "request_headers": {"Content-Type": "application/json"},
        "request_body": '{"event": "test"}',
        "request_method": "POST",
        "request_url": "https://api.example.com/webhook",
        "signature_valid": True,
        "signature_header": "t=123,v1=signature",
        "validation_errors": [],
        "queued_at": created_at,
        "processing_started_at": created_at,
        "processing_completed_at": None,
        "execution_time_ms": None,
        "response_status_code": None,
        "response_headers": {},
        "response_body": None,
        "error_message": None,
        "retry_count": 1,
        "next_retry_at": created_at + timedelta(minutes=5),
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    delivery = await manager.get_delivery(delivery_id)

    # Verify the delivery was constructed correctly
    assert delivery.id == delivery_id
    assert delivery.webhook_id == webhook_id
    assert delivery.function_id == function_id
    assert delivery.status == WebhookDeliveryStatus.EXECUTING
    assert delivery.retry_count == 1
    assert delivery.signature_valid is True

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_get_delivery_not_found(mock_database_manager, mock_db_connection):
    """Test getting a non-existent delivery raises error."""
    manager = WebhookDeliveryCRUDManager(mock_database_manager)

    # Mock no result found
    mock_db_connection.fetchrow.return_value = None

    delivery_id = uuid.uuid4()
    with pytest.raises(WebhookDeliveryNotFoundError):
        await manager.get_delivery(delivery_id)

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_list_deliveries_with_filters_and_pagination(mock_database_manager, mock_db_connection):
    """Test listing deliveries with various filters and pagination."""
    manager = WebhookDeliveryCRUDManager(mock_database_manager)

    webhook_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database rows
    mock_rows = [
        {
            "id": uuid.uuid4(),
            "webhook_id": webhook_id,
            "function_id": uuid.uuid4(),
            "delivery_attempt": 1,
            "status": "completed",
            "source_ip": "192.168.1.100",
            "user_agent": "Stripe/1.0",
            "request_headers": {"Content-Type": "application/json"},
            "request_body": '{"event": "payment.succeeded"}',
            "request_method": "POST",
            "request_url": "https://api.stripe.com/webhooks",
            "signature_valid": True,
            "signature_header": "t=123,v1=signature",
            "validation_errors": [],
            "queued_at": created_at,
            "processing_started_at": created_at,
            "processing_completed_at": created_at + timedelta(seconds=1),
            "execution_time_ms": 150.5,
            "response_status_code": 200,
            "response_headers": {"Content-Type": "application/json"},
            "response_body": '{"received": true}',
            "error_message": None,
            "retry_count": 0,
            "next_retry_at": None,
            "created_at": created_at,
            "updated_at": created_at
        },
        {
            "id": uuid.uuid4(),
            "webhook_id": webhook_id,
            "function_id": uuid.uuid4(),
            "delivery_attempt": 1,
            "status": "failed",
            "source_ip": "192.168.1.101",
            "user_agent": "Stripe/1.0",
            "request_headers": {"Content-Type": "application/json"},
            "request_body": '{"event": "payment.failed"}',
            "request_method": "POST",
            "request_url": "https://api.stripe.com/webhooks",
            "signature_valid": False,
            "signature_header": None,
            "validation_errors": [],
            "queued_at": created_at,
            "processing_started_at": created_at,
            "processing_completed_at": created_at + timedelta(seconds=5),
            "execution_time_ms": None,
            "response_status_code": 500,
            "response_headers": {"Content-Type": "application/json"},
            "response_body": '{"error": "Internal server error"}',
            "error_message": "Function execution failed",
            "retry_count": 2,
            "next_retry_at": created_at + timedelta(minutes=10),
            "created_at": created_at,
            "updated_at": created_at
        }
    ]
    mock_db_connection.fetch.return_value = mock_rows

    # Test list deliveries for webhook
    deliveries = await manager.list_deliveries(webhook_id=webhook_id, limit=10, offset=0)

    assert len(deliveries) == 2
    assert deliveries[0].status == WebhookDeliveryStatus.COMPLETED
    assert deliveries[1].status == WebhookDeliveryStatus.FAILED
    assert deliveries[0].response_status_code == 200
    assert deliveries[1].error_message == "Function execution failed"
    assert deliveries[0].execution_time_ms == 150.5

    # Verify database operation was called
    assert mock_db_connection.fetch.call_count == 1


@pytest.mark.asyncio
async def test_update_delivery_status_with_metadata(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test updating delivery status with response metadata."""
    manager = WebhookDeliveryCRUDManager(mock_database_manager)

    delivery_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock the get_delivery call
    mock_row = {
        "id": delivery_id,
        "webhook_id": uuid.uuid4(),
        "function_id": uuid.uuid4(),
        "delivery_attempt": 1,
        "status": "completed",
        "source_ip": "192.168.1.100",
        "user_agent": "Stripe/1.0",
        "request_headers": {"Content-Type": "application/json"},
        "request_body": '{"event": "test"}',
        "request_method": "POST",
        "request_url": "https://api.example.com/webhook",
        "signature_valid": True,
        "signature_header": "t=123,v1=signature",
        "validation_errors": [],
        "queued_at": created_at,
        "processing_started_at": created_at,
        "processing_completed_at": created_at + timedelta(seconds=1),
        "execution_time_ms": 250.5,
        "response_status_code": 200,
        "response_headers": {"Content-Type": "application/json"},
        "response_body": '{"success": true}',
        "error_message": None,
        "retry_count": 0,
        "next_retry_at": None,
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    updates = {
        "response_status_code": 200,
        "response_headers": {"Content-Type": "application/json"},
        "response_body": '{"success": true}',
        "execution_time_ms": 250.5
    }

    delivery = await manager.update_delivery_status(
        delivery_id=delivery_id,
        status=WebhookDeliveryStatus.COMPLETED,
        updates=updates
    )

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_start_processing_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test starting delivery processing."""
    manager = WebhookDeliveryCRUDManager(mock_database_manager)

    delivery_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock the get_delivery call
    mock_row = {
        "id": delivery_id,
        "webhook_id": uuid.uuid4(),
        "function_id": uuid.uuid4(),
        "delivery_attempt": 1,
        "status": "executing",
        "source_ip": "192.168.1.100",
        "user_agent": "Stripe/1.0",
        "request_headers": {"Content-Type": "application/json"},
        "request_body": '{"event": "test"}',
        "request_method": "POST",
        "request_url": "https://api.example.com/webhook",
        "signature_valid": True,
        "signature_header": "t=123,v1=signature",
        "validation_errors": [],
        "queued_at": created_at,
        "processing_started_at": created_at,
        "processing_completed_at": None,
        "execution_time_ms": None,
        "response_status_code": None,
        "response_headers": {},
        "response_body": None,
        "error_message": None,
        "retry_count": 1,
        "next_retry_at": None,
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    delivery = await manager.start_processing(delivery_id)

    # Verify the delivery status was updated
    assert delivery.status == WebhookDeliveryStatus.EXECUTING

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_complete_processing_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test completing delivery processing."""
    manager = WebhookDeliveryCRUDManager(mock_database_manager)

    delivery_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock the get_delivery call
    mock_row = {
        "id": delivery_id,
        "webhook_id": uuid.uuid4(),
        "function_id": uuid.uuid4(),
        "delivery_attempt": 1,
        "status": "completed",
        "source_ip": "192.168.1.100",
        "user_agent": "Stripe/1.0",
        "request_headers": {"Content-Type": "application/json"},
        "request_body": '{"event": "test"}',
        "request_method": "POST",
        "request_url": "https://api.example.com/webhook",
        "signature_valid": True,
        "signature_header": "t=123,v1=signature",
        "validation_errors": [],
        "queued_at": created_at,
        "processing_started_at": created_at,
        "processing_completed_at": created_at + timedelta(seconds=1),
        "execution_time_ms": 300.0,
        "response_status_code": 200,
        "response_headers": {"Content-Type": "application/json"},
        "response_body": '{"processed": true}',
        "error_message": None,
        "retry_count": 0,
        "next_retry_at": None,
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    delivery = await manager.complete_processing(
        delivery_id=delivery_id,
        success=True,
        response_status_code=200,
        response_body='{"processed": true}',
        execution_time_ms=300.0
    )

    # Verify the delivery was completed
    assert delivery.status == WebhookDeliveryStatus.COMPLETED
    assert delivery.response_status_code == 200
    assert delivery.execution_time_ms == 300.0

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_schedule_retry_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test scheduling a delivery retry."""
    manager = WebhookDeliveryCRUDManager(mock_database_manager)

    delivery_id = uuid.uuid4()
    retry_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    created_at = datetime.now(timezone.utc)

    # Mock the get_delivery call
    mock_row = {
        "id": delivery_id,
        "webhook_id": uuid.uuid4(),
        "function_id": uuid.uuid4(),
        "delivery_attempt": 1,
        "status": "retry_pending",
        "source_ip": "192.168.1.100",
        "user_agent": "Stripe/1.0",
        "request_headers": {"Content-Type": "application/json"},
        "request_body": '{"event": "test"}',
        "request_method": "POST",
        "request_url": "https://api.example.com/webhook",
        "signature_valid": True,
        "signature_header": "t=123,v1=signature",
        "validation_errors": [],
        "queued_at": created_at,
        "processing_started_at": created_at,
        "processing_completed_at": None,
        "execution_time_ms": None,
        "response_status_code": None,
        "response_headers": {},
        "response_body": None,
        "error_message": "Temporary failure",
        "retry_count": 1,
        "next_retry_at": retry_at,
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    await manager.schedule_retry(delivery_id, retry_at)

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_pending_retries(mock_database_manager, mock_db_connection):
    """Test getting deliveries pending retry."""
    manager = WebhookDeliveryCRUDManager(mock_database_manager)

    created_at = datetime.now(timezone.utc)

    # Mock database rows for pending retries
    mock_rows = [
        {
            "id": uuid.uuid4(),
            "webhook_id": uuid.uuid4(),
            "function_id": uuid.uuid4(),
            "delivery_attempt": 1,
            "status": "retry_pending",
            "source_ip": "192.168.1.100",
            "user_agent": "Test/1.0",
            "request_headers": {},
            "request_body": "{}",
            "request_method": "POST",
            "request_url": "https://api.example.com/webhook",
            "signature_valid": True,
            "signature_header": None,
            "validation_errors": [],
            "queued_at": created_at,
            "processing_started_at": created_at,
            "processing_completed_at": None,
            "execution_time_ms": None,
            "response_status_code": None,
            "response_headers": {},
            "response_body": None,
            "error_message": "Temporary failure",
            "retry_count": 1,
            "next_retry_at": created_at + timedelta(minutes=5),
            "created_at": created_at,
            "updated_at": created_at
        }
    ]
    mock_db_connection.fetch.return_value = mock_rows

    pending_retries = await manager.get_pending_retries(limit=50)

    assert len(pending_retries) == 1
    assert pending_retries[0].status == WebhookDeliveryStatus.RETRY_PENDING
    assert pending_retries[0].retry_count == 1

    # Verify database operation was called
    assert mock_db_connection.fetch.call_count == 1


@pytest.mark.asyncio
async def test_get_delivery_stats(mock_database_manager, mock_db_connection):
    """Test getting delivery statistics."""
    manager = WebhookDeliveryCRUDManager(mock_database_manager)

    # Mock statistics result
    mock_stats = {
        "total_deliveries": 1000,
        "successful_deliveries": 850,
        "failed_deliveries": 100,
        "retry_scheduled_deliveries": 30,
        "processing_deliveries": 20,
        "avg_execution_time_ms": 245.7,
        "total_retry_count": 150
    }
    mock_db_connection.fetchrow.return_value = mock_stats

    stats = await manager.get_delivery_stats()

    assert stats["total_deliveries"] == 1000
    assert stats["successful_deliveries"] == 850
    assert stats["failed_deliveries"] == 100
    assert stats["retry_scheduled_deliveries"] == 30
    assert stats["processing_deliveries"] == 20
    assert stats["avg_execution_time_ms"] == 245.7
    assert stats["total_retry_count"] == 150

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1
"""
Unit tests for WebhookCRUDManager business logic using mocked database operations.
"""

import uuid
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from shared.services.webhook_crud_manager import (
    WebhookCRUDManager,
    WebhookNotFoundError,
    WebhookAlreadyExistsError
)
from shared.models.webhook import Webhook, RetryBackoffStrategy


@pytest.mark.asyncio
async def test_create_webhook_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test successful webhook creation."""
    manager = WebhookCRUDManager(mock_database_manager)

    function_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    # Mock that webhook doesn't exist
    mock_db_connection.fetchval.return_value = False

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    webhook = await manager.create_webhook(
        function_id=function_id,
        owner_id=owner_id,
        name="test_webhook",
        secret_key="webhook_secret",
        description="Test webhook",
        provider="stripe",
        provider_event_type="payment.succeeded",
        rate_limit_per_minute=100,
        retry_attempts=3,
        retry_backoff_strategy=RetryBackoffStrategy.EXPONENTIAL
    )

    # Verify the webhook was created with correct attributes
    assert webhook.function_id == function_id
    assert webhook.owner_id == owner_id
    assert webhook.name == "test_webhook"
    assert webhook.secret_key == "webhook_secret"
    assert webhook.description == "Test webhook"
    assert webhook.provider == "stripe"
    assert webhook.provider_event_type == "payment.succeeded"
    assert webhook.rate_limit_per_minute == 100
    assert webhook.retry_attempts == 3
    assert webhook.retry_backoff_strategy == RetryBackoffStrategy.EXPONENTIAL
    assert webhook.is_active is True
    assert webhook.webhook_token is not None

    # Verify database operations were called correctly
    assert mock_db_connection.fetchval.call_count == 1  # Check if webhook exists
    assert mock_db_connection.execute.call_count == 1   # Insert webhook


@pytest.mark.asyncio
async def test_create_webhook_already_exists(mock_database_manager, mock_db_connection):
    """Test creating a webhook that already exists raises error."""
    manager = WebhookCRUDManager(mock_database_manager)

    # Mock that webhook already exists
    mock_db_connection.fetchval.return_value = True

    owner_id = uuid.uuid4()
    function_id = uuid.uuid4()

    with pytest.raises(WebhookAlreadyExistsError):
        await manager.create_webhook(
            function_id=function_id,
            owner_id=owner_id,
            name="existing_webhook",
            secret_key="secret"
        )

    # Verify existence check was called
    assert mock_db_connection.fetchval.call_count == 1


@pytest.mark.asyncio
async def test_get_webhook_success(mock_database_manager, mock_db_connection):
    """Test successful webhook retrieval."""
    manager = WebhookCRUDManager(mock_database_manager)

    webhook_id = uuid.uuid4()
    function_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database row
    mock_row = {
        "id": webhook_id,
        "function_id": function_id,
        "owner_id": owner_id,
        "name": "test_webhook",
        "webhook_token": "token_12345",
        "secret_key": "secret_key",
        "description": "Test webhook",
        "provider": "stripe",
        "provider_event_type": "payment.succeeded",
        "source_url": "https://api.stripe.com/v1/webhooks",
        "is_active": True,
        "rate_limit_per_minute": 100,
        "max_queue_size": 1000,
        "retry_enabled": True,
        "retry_attempts": 3,
        "retry_backoff_strategy": "exponential",
        "retry_delay_seconds": 60,
        "retry_max_delay_seconds": 3600,
        "payload_schema": {"type": "object"},
        "expected_headers": {"Content-Type": "application/json"},
        "transform_script": "function transform(payload) { return payload; }",
        "path_segment": "stripe_token_12345",
        "is_active_delivery": True,
        "total_delivery_count": 50,
        "successful_delivery_count": 45,
        "failed_delivery_count": 5,
        "last_delivery_status": "delivered",
        "last_received_at": created_at,
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    webhook = await manager.get_webhook(webhook_id)

    # Verify the webhook was constructed correctly
    assert webhook.id == webhook_id
    assert webhook.name == "test_webhook"
    assert webhook.webhook_token == "token_12345"
    assert webhook.provider == "stripe"
    assert webhook.is_active is True
    assert webhook.total_delivery_count == 50
    assert webhook.successful_delivery_count == 45

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_get_webhook_by_token_success(mock_database_manager, mock_db_connection):
    """Test successful webhook retrieval by token."""
    manager = WebhookCRUDManager(mock_database_manager)

    webhook_id = uuid.uuid4()
    token = "test_token_12345"
    created_at = datetime.now(timezone.utc)

    # Mock database row
    mock_row = {
        "id": webhook_id,
        "function_id": uuid.uuid4(),
        "owner_id": uuid.uuid4(),
        "name": "test_webhook",
        "webhook_token": token,
        "secret_key": "secret_key",
        "description": "Test webhook",
        "provider": "github",
        "provider_event_type": "push",
        "source_url": "https://api.github.com/webhooks",
        "is_active": True,
        "rate_limit_per_minute": 60,
        "max_queue_size": 500,
        "retry_enabled": True,
        "retry_attempts": 2,
        "retry_backoff_strategy": "linear",
        "retry_delay_seconds": 30,
        "retry_max_delay_seconds": 1800,
        "payload_schema": None,
        "expected_headers": {},
        "transform_script": None,
        "path_segment": "github_test_token_12345",
        "is_active_delivery": False,
        "total_delivery_count": 10,
        "successful_delivery_count": 8,
        "failed_delivery_count": 2,
        "last_delivery_status": "failed",
        "last_received_at": created_at,
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    webhook = await manager.get_webhook_by_token(token)

    # Verify the webhook was retrieved correctly
    assert webhook.id == webhook_id
    assert webhook.webhook_token == token
    assert webhook.provider == "github"
    assert webhook.retry_backoff_strategy == RetryBackoffStrategy.LINEAR

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_get_webhook_not_found(mock_database_manager, mock_db_connection):
    """Test getting a non-existent webhook raises error."""
    manager = WebhookCRUDManager(mock_database_manager)

    # Mock no result found
    mock_db_connection.fetchrow.return_value = None

    webhook_id = uuid.uuid4()
    with pytest.raises(WebhookNotFoundError):
        await manager.get_webhook(webhook_id)

    # Verify database operation was called
    assert mock_db_connection.fetchrow.call_count == 1


@pytest.mark.asyncio
async def test_list_webhooks_with_filters(mock_database_manager, mock_db_connection):
    """Test listing webhooks with various filters."""
    manager = WebhookCRUDManager(mock_database_manager)

    owner_id = uuid.uuid4()
    function_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock database rows
    mock_rows = [
        {
            "id": uuid.uuid4(),
            "function_id": function_id,
            "owner_id": owner_id,
            "name": "webhook1",
            "webhook_token": "token1",
            "secret_key": "secret1",
            "description": "Webhook 1",
            "provider": "stripe",
            "provider_event_type": "payment.succeeded",
            "source_url": "https://api.stripe.com/v1/webhooks",
            "is_active": True,
            "rate_limit_per_minute": 100,
            "max_queue_size": 1000,
            "retry_enabled": True,
            "retry_attempts": 3,
            "retry_backoff_strategy": "exponential",
            "retry_delay_seconds": 60,
            "retry_max_delay_seconds": 3600,
            "payload_schema": None,
            "expected_headers": {},
            "transform_script": None,
            "path_segment": "stripe_token1",
            "is_active_delivery": True,
            "total_delivery_count": 20,
            "successful_delivery_count": 18,
            "failed_delivery_count": 2,
            "last_delivery_status": "delivered",
            "last_received_at": created_at,
            "created_at": created_at,
            "updated_at": created_at
        },
        {
            "id": uuid.uuid4(),
            "function_id": function_id,
            "owner_id": owner_id,
            "name": "webhook2",
            "webhook_token": "token2",
            "secret_key": "secret2",
            "description": "Webhook 2",
            "provider": "github",
            "provider_event_type": "push",
            "source_url": "https://api.github.com/webhooks",
            "is_active": False,  # Inactive webhook
            "rate_limit_per_minute": 60,
            "max_queue_size": 500,
            "retry_enabled": True,
            "retry_attempts": 2,
            "retry_backoff_strategy": "linear",
            "retry_delay_seconds": 30,
            "retry_max_delay_seconds": 1800,
            "payload_schema": None,
            "expected_headers": {},
            "transform_script": None,
            "path_segment": "github_token2",
            "is_active_delivery": False,
            "total_delivery_count": 5,
            "successful_delivery_count": 3,
            "failed_delivery_count": 2,
            "last_delivery_status": "failed",
            "last_received_at": created_at,
            "created_at": created_at,
            "updated_at": created_at
        }
    ]
    mock_db_connection.fetch.return_value = mock_rows

    # Test list all webhooks for owner including inactive
    webhooks = await manager.list_webhooks(owner_id=owner_id, include_inactive=True)

    assert len(webhooks) == 2
    assert webhooks[0].name == "webhook1"
    assert webhooks[1].name == "webhook2"
    assert webhooks[0].is_active is True
    assert webhooks[1].is_active is False

    # Verify database operation was called
    assert mock_db_connection.fetch.call_count == 1


@pytest.mark.asyncio
async def test_update_webhook_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test successful webhook update."""
    manager = WebhookCRUDManager(mock_database_manager)

    webhook_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock the get_webhook call
    mock_row = {
        "id": webhook_id,
        "function_id": uuid.uuid4(),
        "owner_id": uuid.uuid4(),
        "name": "test_webhook",
        "webhook_token": "token_12345",
        "secret_key": "secret_key",
        "description": "Test webhook",
        "provider": "stripe",
        "provider_event_type": "payment.succeeded",
        "source_url": "https://api.stripe.com/v1/webhooks",
        "is_active": True,
        "rate_limit_per_minute": 100,
        "max_queue_size": 1000,
        "retry_enabled": True,
        "retry_attempts": 3,
        "retry_backoff_strategy": "exponential",
        "retry_delay_seconds": 60,
        "retry_max_delay_seconds": 3600,
        "payload_schema": {"type": "object"},
        "expected_headers": {"Content-Type": "application/json"},
        "transform_script": "function transform(payload) { return payload; }",
        "path_segment": "stripe_token_12345",
        "is_active_delivery": True,
        "total_delivery_count": 50,
        "successful_delivery_count": 45,
        "failed_delivery_count": 5,
        "last_delivery_status": "delivered",
        "last_received_at": created_at,
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    updates = {
        "description": "Updated webhook description",
        "rate_limit_per_minute": 200,
        "is_active": False,
        "expected_headers": {"Authorization": "Bearer token"}
    }

    await manager.update_webhook(webhook_id, updates)

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_delete_webhook_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test successful webhook deletion."""
    manager = WebhookCRUDManager(mock_database_manager)

    webhook_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    # Mock the get_webhook call
    mock_row = {
        "id": webhook_id,
        "function_id": uuid.uuid4(),
        "owner_id": uuid.uuid4(),
        "name": "test_webhook",
        "webhook_token": "token_12345",
        "secret_key": "secret_key",
        "description": "Test webhook",
        "provider": "stripe",
        "provider_event_type": "payment.succeeded",
        "source_url": "https://api.stripe.com/v1/webhooks",
        "is_active": True,
        "rate_limit_per_minute": 100,
        "max_queue_size": 1000,
        "retry_enabled": True,
        "retry_attempts": 3,
        "retry_backoff_strategy": "exponential",
        "retry_delay_seconds": 60,
        "retry_max_delay_seconds": 3600,
        "payload_schema": {"type": "object"},
        "expected_headers": {"Content-Type": "application/json"},
        "transform_script": "function transform(payload) { return payload; }",
        "path_segment": "stripe_token_12345",
        "is_active_delivery": True,
        "total_delivery_count": 50,
        "successful_delivery_count": 45,
        "failed_delivery_count": 5,
        "last_delivery_status": "delivered",
        "last_received_at": created_at,
        "created_at": created_at,
        "updated_at": created_at
    }
    mock_db_connection.fetchrow.return_value = mock_row

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    await manager.delete_webhook(webhook_id)

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_record_delivery_success(mock_database_manager, mock_db_connection, mock_db_transaction):
    """Test recording webhook delivery statistics."""
    manager = WebhookCRUDManager(mock_database_manager)

    webhook_id = uuid.uuid4()

    # Mock successful transaction
    mock_db_connection.execute.return_value = None

    await manager.record_delivery(webhook_id, success=True, status="delivered")

    # Verify database operation was called
    assert mock_db_connection.execute.call_count == 1


@pytest.mark.asyncio
async def test_webhook_exists_by_name_and_owner(mock_database_manager, mock_db_connection):
    """Test checking if webhook exists by name and owner."""
    manager = WebhookCRUDManager(mock_database_manager)

    name = "test_webhook"
    owner_id = uuid.uuid4()

    # Mock that webhook exists
    mock_db_connection.fetchval.return_value = True

    exists = await manager._webhook_exists_by_name_and_owner(name, owner_id)

    assert exists is True
    assert mock_db_connection.fetchval.call_count == 1

    # Mock that webhook doesn't exist
    mock_db_connection.fetchval.return_value = False

    exists = await manager._webhook_exists_by_name_and_owner("nonexistent", owner_id)

    assert exists is False
    assert mock_db_connection.fetchval.call_count == 2
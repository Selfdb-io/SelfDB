"""Unit tests for FastAPI webhooks endpoints."""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import uuid

import pytest

from shared.auth.jwt_service import JWTService
from shared.models.webhook import Webhook, RetryBackoffStrategy


class TestWebhookEndpoints:
    """Test suite for /api/v1/webhooks endpoints."""

    @pytest.fixture(autouse=True)
    def _set_client(self, api_client):
        self._api_client = api_client

    def setup_method(self):
        self.api_key = "test_webhook_api_key"
        self.jwt_secret = "test_webhooks_jwt_secret"
        os.environ["API_KEY"] = self.api_key
        os.environ["JWT_SECRET_KEY"] = self.jwt_secret
        os.environ["JWT_ISSUER"] = "selfdb"
        os.environ["API_PORT"] = "8000"
        os.environ["STORAGE_PORT"] = "8001"
        os.environ["DENO_PORT"] = "8090"
        os.environ["POSTGRES_PORT"] = "5432"
        os.environ["FRONTEND_PORT"] = "3000"

        self.jwt_service = JWTService(
            secret_key=self.jwt_secret,
            algorithm="HS256",
            access_token_expire_minutes=30,
            issuer="selfdb",
        )
        self.user_id = str(uuid.uuid4())
        self.function_id = str(uuid.uuid4())

    def teardown_method(self):
        for key in [
            "API_KEY",
            "JWT_SECRET_KEY",
            "JWT_ISSUER",
            "API_PORT",
            "STORAGE_PORT",
            "DENO_PORT",
            "POSTGRES_PORT",
            "FRONTEND_PORT",
        ]:
            os.environ.pop(key, None)

    def _create_token(self, user_id: str = None, role: str = "USER") -> str:
        """Create a valid JWT token for testing."""
        if user_id is None:
            user_id = self.user_id
        payload = {
            "user_id": user_id,
            "email": f"{user_id}@example.com",
            "role": role,
            "is_active": True,
        }
        return self.jwt_service.generate_access_token(payload)

    def _get_client(self):
        """Get a fresh TestClient."""
        return self._api_client

    def _create_test_webhook(self, owner_id: str = None, function_id: str = None) -> Webhook:
        """Create a test webhook object."""
        if owner_id is None:
            owner_id = self.user_id
        if function_id is None:
            function_id = self.function_id
        
        owner_uuid = uuid.UUID(owner_id) if isinstance(owner_id, str) else owner_id
        func_uuid = uuid.UUID(function_id) if isinstance(function_id, str) else function_id
            
        return Webhook(
            id=uuid.uuid4(),
            function_id=func_uuid,
            owner_id=owner_uuid,
            name="test_webhook",
            webhook_token="test_token_12345",
            secret_key="test_secret_key",
            description="Test webhook",
            provider="stripe",
            provider_event_type="checkout.session.completed",
            is_active=True,
            rate_limit_per_minute=100,
            retry_attempts=3,
            retry_backoff_strategy=RetryBackoffStrategy.EXPONENTIAL,
            successful_delivery_count=5,
            failed_delivery_count=1,
            total_delivery_count=6,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @patch("endpoints.webhooks.webhook_crud_manager")
    def test_create_webhook_success(self, mock_manager):
        """Test successful webhook creation."""
        test_webhook = self._create_test_webhook()
        mock_manager.create_webhook = AsyncMock(return_value=test_webhook)

        client = self._get_client()
        token = self._create_token()
        
        response = client.post(
            "/api/v1/webhooks",
            json={
                "name": "test_webhook",
                "function_id": self.function_id,
                "secret_key": "test_secret_key",
                "provider": "stripe",
                "provider_event_type": "checkout.session.completed",
                "rate_limit_per_minute": 100,
                "retry_attempts": 3,
            },
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_webhook"
        assert data["provider"] == "stripe"
        assert data["is_active"] is True

    @patch("endpoints.webhooks.webhook_crud_manager")
    def test_list_webhooks_success(self, mock_manager):
        """Test listing webhooks."""
        test_webhook = self._create_test_webhook()
        mock_manager.list_webhooks = AsyncMock(return_value=[test_webhook])

        client = self._get_client()
        token = self._create_token()
        
        response = client.get(
            "/api/v1/webhooks",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "webhooks" in data
        assert len(data["webhooks"]) == 1

    @patch("endpoints.webhooks.webhook_crud_manager")
    def test_get_webhook_success(self, mock_manager):
        """Test retrieving a specific webhook."""
        test_webhook = self._create_test_webhook()
        mock_manager.get_webhook = AsyncMock(return_value=test_webhook)

        client = self._get_client()
        token = self._create_token()
        
        response = client.get(
            f"/api/v1/webhooks/{test_webhook.id}",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_webhook"

    @patch("endpoints.webhooks.webhook_crud_manager")
    def test_update_webhook_success(self, mock_manager):
        """Test updating a webhook."""
        test_webhook = self._create_test_webhook()
        updated_webhook = self._create_test_webhook()
        updated_webhook.is_active = False

        mock_manager.get_webhook = AsyncMock(return_value=test_webhook)
        mock_manager.update_webhook = AsyncMock(return_value=updated_webhook)

        client = self._get_client()
        token = self._create_token()
        
        response = client.put(
            f"/api/v1/webhooks/{test_webhook.id}",
            json={"is_active": False},
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    @patch("endpoints.webhooks.webhook_crud_manager")
    def test_delete_webhook_success(self, mock_manager):
        """Test deleting a webhook."""
        test_webhook = self._create_test_webhook()
        mock_manager.get_webhook = AsyncMock(return_value=test_webhook)
        mock_manager.delete_webhook = AsyncMock(return_value=None)

        client = self._get_client()
        token = self._create_token()
        
        response = client.delete(
            f"/api/v1/webhooks/{test_webhook.id}",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 204

    @patch("endpoints.webhooks.webhook_delivery_crud_manager")
    @patch("endpoints.webhooks.webhook_crud_manager")
    def test_get_webhook_deliveries_success(self, mock_webhook_manager, mock_delivery_manager):
        """Test retrieving webhook delivery history."""
        from shared.models.webhook_delivery import WebhookDelivery, WebhookDeliveryStatus
        
        test_webhook = self._create_test_webhook()
        test_delivery = WebhookDelivery(
            id=uuid.uuid4(),
            webhook_id=test_webhook.id,
            function_id=test_webhook.function_id,
            status=WebhookDeliveryStatus.COMPLETED,
            signature_valid=True,
            created_at=datetime.now(timezone.utc)
        )
        
        mock_webhook_manager.get_webhook = AsyncMock(return_value=test_webhook)
        mock_delivery_manager.list_deliveries = AsyncMock(return_value=[test_delivery])

        client = self._get_client()
        token = self._create_token()
        
        response = client.get(
            f"/api/v1/webhooks/{test_webhook.id}/deliveries",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "deliveries" in data
        assert len(data["deliveries"]) == 1

    def test_create_webhook_unauthorized(self):
        """Test that unauthorized requests are rejected."""
        client = self._get_client()
        client.app.dependency_overrides.clear()
        
        response = client.post(
            "/api/v1/webhooks",
            json={
                "name": "test",
                "function_id": self.function_id,
                "secret_key": "secret",
            },
            headers={"x-api-key": self.api_key},  # No auth token
        )

        assert response.status_code == 401

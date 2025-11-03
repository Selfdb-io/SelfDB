"""Unit tests for FastAPI functions endpoints."""

import importlib
import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient

from shared.auth.jwt_service import JWTService
from shared.models.function import Function, FunctionRuntime, DeploymentStatus


class TestFunctionEndpoints:
    """Test suite for /api/v1/functions endpoints."""

    def setup_method(self):
        self.api_key = "test_function_api_key"
        self.jwt_secret = "test_functions_jwt_secret"
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

    def _get_client(self) -> TestClient:
        """Get a fresh TestClient."""
        if "backend.main" in sys.modules:
            importlib.reload(sys.modules["backend.main"])
        from backend.main import app
        return TestClient(app)

    def _create_test_function(self, owner_id: str = None) -> Function:
        """Create a test function object."""
        if owner_id is None:
            owner_id = self.user_id
        
        # Ensure owner_id is a UUID
        if isinstance(owner_id, str):
            try:
                owner_uuid = uuid.UUID(owner_id)
            except ValueError:
                owner_uuid = uuid.uuid4()
        else:
            owner_uuid = owner_id
            
        return Function(
            id=uuid.uuid4(),
            name="test_function",
            code="console.log('test');",
            owner_id=owner_uuid,
            description="Test function",
            runtime=FunctionRuntime.DENO,
            is_active=True,
            deployment_status=DeploymentStatus.DEPLOYED,
            version=1,
            timeout_seconds=30,
            memory_limit_mb=512,
            max_concurrent=10,
            env_vars={"API_KEY": "secret"},
            execution_count=5,
            execution_success_count=4,
            execution_error_count=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @patch("endpoints.functions.function_deployment_manager")
    @patch("endpoints.functions.function_crud_manager")
    def test_create_function_success(self, mock_manager, mock_deployment):
        """Test successful function creation."""
        test_func = self._create_test_function()
        mock_manager.create_function = AsyncMock(return_value=test_func)
        mock_manager.update_deployment_status = AsyncMock()
        mock_deployment.deploy_function = AsyncMock(return_value={"success": True})

        client = self._get_client()
        token = self._create_token()
        
        response = client.post(
            "/api/v1/functions",
            json={
                "name": "test_function",
                "code": "console.log('test');",
                "description": "Test function",
                "runtime": "deno",
                "timeout_seconds": 30,
                "memory_limit_mb": 512,
                "max_concurrent": 10,
            },
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_function"
        assert data["runtime"] == "deno"
        assert data["is_active"] is True

    @patch("endpoints.functions.function_crud_manager")
    def test_list_functions_success(self, mock_manager):
        """Test listing functions."""
        test_func = self._create_test_function()
        mock_manager.list_functions = AsyncMock(return_value=[test_func])

        client = self._get_client()
        token = self._create_token()
        
        response = client.get(
            "/api/v1/functions",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "functions" in data
        assert len(data["functions"]) == 1

    @patch("endpoints.functions.function_crud_manager")
    def test_get_function_success(self, mock_manager):
        """Test retrieving a specific function."""
        test_func = self._create_test_function()
        mock_manager.get_function = AsyncMock(return_value=test_func)

        client = self._get_client()
        token = self._create_token()
        
        response = client.get(
            f"/api/v1/functions/{test_func.id}",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_function"

    @patch("endpoints.functions.function_crud_manager")
    def test_delete_function_success(self, mock_manager):
        """Test deleting a function."""
        test_func = self._create_test_function()
        mock_manager.get_function = AsyncMock(return_value=test_func)
        mock_manager.delete_function = AsyncMock(return_value=None)

        client = self._get_client()
        token = self._create_token()
        
        response = client.delete(
            f"/api/v1/functions/{test_func.id}",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 204

    def test_create_function_unauthorized(self):
        """Test that unauthorized requests are rejected."""
        client = self._get_client()
        
        response = client.post(
            "/api/v1/functions",
            json={"name": "test", "code": "code"},
            headers={"x-api-key": self.api_key},  # No auth token
        )

        assert response.status_code == 401

    @patch("endpoints.functions.function_log_crud_manager")
    @patch("endpoints.functions.function_crud_manager")
    def test_get_function_logs_success(self, mock_func_manager, mock_log_manager):
        """Test retrieving function execution logs."""
        from shared.models.function_log import FunctionLog
        
        test_func = self._create_test_function()
        test_log = FunctionLog(
            execution_id=uuid.uuid4(),
            function_id=test_func.id,
            log_level="info",
            message="Function executed successfully",
            timestamp=datetime.now(timezone.utc),
            source="function"
        )
        
        mock_func_manager.get_function = AsyncMock(return_value=test_func)
        mock_log_manager.get_function_logs = AsyncMock(return_value=[test_log])

        client = self._get_client()
        token = self._create_token()
        
        response = client.get(
            f"/api/v1/functions/{test_func.id}/logs",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert len(data["logs"]) == 1

    @patch("endpoints.functions.function_execution_crud_manager")
    @patch("endpoints.functions.function_crud_manager")
    def test_get_function_metrics_success(self, mock_func_manager, mock_exec_manager):
        """Test retrieving function execution metrics."""
        from shared.models.function_execution import FunctionExecution
        
        test_func = self._create_test_function()
        now = datetime.now(timezone.utc)
        test_exec = FunctionExecution(
            id=uuid.uuid4(),
            function_id=test_func.id,
            user_id=uuid.UUID(self.user_id),
            trigger_type="http",
            status="completed",
            duration_ms=250,
            started_at=now,
            completed_at=now,
            created_at=now,
            updated_at=now,
            metadata={"timeout_seconds": 30}
        )
        
        mock_func_manager.get_function = AsyncMock(return_value=test_func)
        mock_exec_manager.list_executions = AsyncMock(return_value=[test_exec])

        client = self._get_client()
        token = self._create_token()
        
        response = client.get(
            f"/api/v1/functions/{test_func.id}/metrics",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_executions" in data
        assert "success_rate" in data
        assert "average_execution_time_ms" in data

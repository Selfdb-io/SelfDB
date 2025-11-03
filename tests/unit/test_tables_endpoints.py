"""Unit tests for FastAPI table management endpoints."""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from shared.auth.jwt_service import JWTService


class TestTableEndpoints:
    """Test suite for /api/v1/tables endpoints."""

    @pytest.fixture(autouse=True)
    def _set_client(self, api_client):
        self._api_client = api_client

    def setup_method(self):
        self.api_key = "test_table_api_key"
        self.jwt_secret = "test_tables_jwt_secret"
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

        for module_name in ("backend.endpoints.tables", "endpoints.tables"):
            if module_name in sys.modules:
                del sys.modules[module_name]
        if "backend.main" in sys.modules:
            del sys.modules["backend.main"]

    def _create_token(self, user_id: str = "user_123", role: str = "USER") -> str:
        payload = {
            "user_id": user_id,
            "email": f"{user_id}@example.com",
            "role": role,
            "is_active": True,
        }
        return self.jwt_service.generate_access_token(payload)

    def _get_client(self):
        return self._api_client

    @patch("endpoints.tables.table_crud_manager")
    def test_list_tables_returns_owner_tables(self, mock_table_manager):
        mock_table_manager.list_tables = AsyncMock(return_value=[
            {
                "name": "project_data",
                "public": False,
                "owner_id": "user_123",
                "schema": {"columns": []},
                "row_count": 0,
                "metadata": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ])

        client = self._get_client()
        token = self._create_token()
        response = client.get(
            "/api/v1/tables",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["name"] == "project_data"
        mock_table_manager.list_tables.assert_awaited_once()

    @patch("endpoints.tables.table_crud_manager")
    def test_create_table_uses_authenticated_user(self, mock_table_manager):
        mock_table_manager.create_table = AsyncMock(return_value={
            "name": "audit_logs",
            "public": False,
            "owner_id": "user_123",
            "schema": {"columns": []},
            "metadata": {},
            "row_count": 0,
        })

        client = self._get_client()
        token = self._create_token()
        payload = {
            "name": "audit_logs",
            "description": "Audit logging table",
            "public": False,
            "schema": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "action", "type": "text"},
                ]
            },
        }

        response = client.post(
            "/api/v1/tables",
            json=payload,
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 201
        response_body = response.json()
        assert response_body["name"] == "audit_logs"
        mock_table_manager.create_table.assert_awaited_once()
        call_kwargs = mock_table_manager.create_table.await_args.kwargs
        assert call_kwargs["owner_id"] == "user_123"

    @patch("endpoints.tables.table_crud_manager")
    def test_get_table_metadata(self, mock_table_manager):
        mock_table_manager.get_table = AsyncMock(return_value={
            "name": "orders",
            "schema": {"columns": []},
            "public": False,
            "owner_id": "user_123",
            "metadata": {},
            "row_count": 10,
        })

        client = self._get_client()
        token = self._create_token()

        response = client.get(
            "/api/v1/tables/orders",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "orders"
        mock_table_manager.get_table.assert_awaited_once_with("orders")

    @patch("endpoints.tables.table_crud_manager")
    def test_insert_table_row(self, mock_table_manager):
        inserted_row = {"id": "row1", "value": 42}
        mock_table_manager.insert_row = AsyncMock(return_value=inserted_row)

        client = self._get_client()
        token = self._create_token()

        response = client.post(
            "/api/v1/tables/metrics/data",
            json={"value": 42},
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        assert response.json() == inserted_row
        mock_table_manager.insert_row.assert_awaited_once_with("metrics", {"value": 42})

    @patch("endpoints.tables.table_crud_manager")
    def test_update_table_row(self, mock_table_manager):
        updated_row = {"id": "row1", "status": "archived"}
        mock_table_manager.update_row = AsyncMock(return_value=updated_row)

        client = self._get_client()
        token = self._create_token()

        response = client.put(
            "/api/v1/tables/events/data/row1?id_column=id",
            json={"status": "archived"},
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "archived"
        mock_table_manager.update_row.assert_awaited_once()

    @patch("endpoints.tables.table_crud_manager")
    def test_delete_table_row(self, mock_table_manager):
        mock_table_manager.delete_row = AsyncMock(return_value=None)

        client = self._get_client()
        token = self._create_token()

        response = client.delete(
            "/api/v1/tables/events/data/row1?id_column=id",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 204
        mock_table_manager.delete_row.assert_awaited_once()

    @patch("endpoints.tables.table_crud_manager")
    def test_get_table_sql(self, mock_table_manager):
        mock_table_manager.get_table_sql = AsyncMock(return_value="CREATE TABLE ...")

        client = self._get_client()
        token = self._create_token()

        response = client.get(
            "/api/v1/tables/orders/sql",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        assert "CREATE TABLE" in response.json()["sql"]
        mock_table_manager.get_table_sql.assert_awaited_once_with("orders")

    @patch("endpoints.tables.table_crud_manager")
    def test_add_column(self, mock_table_manager):
        mock_table_manager.add_column = AsyncMock(return_value=None)

        client = self._get_client()
        token = self._create_token(role="ADMIN")

        response = client.post(
            "/api/v1/tables/orders/columns",
            json={"name": "status", "type": "text"},
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200
        mock_table_manager.add_column.assert_awaited_once()

    @patch("endpoints.tables.table_crud_manager")
    def test_delete_table(self, mock_table_manager):
        mock_table_manager.delete_table = AsyncMock(return_value=None)

        client = self._get_client()
        token = self._create_token(role="ADMIN")

        response = client.delete(
            "/api/v1/tables/archive",
            headers={
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 204
        mock_table_manager.delete_table.assert_awaited_once_with("archive")

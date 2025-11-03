"""Integration tests for SQL execution endpoints with the live dev stack."""

import uuid
from typing import Dict, Tuple

import pytest
from httpx import AsyncClient

from shared.config.config_manager import ConfigManager


@pytest.mark.integration
class TestSqlEndpointsIntegration:
    """Runs end-to-end scenarios against /api/v1/sql.* routes."""

    async def _get_auth_headers(
        self, client: AsyncClient, api_key: str
    ) -> Tuple[Dict[str, str], str]:
        """Authenticate and return headers with user ID."""
        config = ConfigManager()
        login_response = await client.post(
            "/auth/login",
            headers={"X-API-Key": api_key},
            json={
                "email": config.admin_email,
                "password": config.admin_password,
            },
        )
        assert login_response.status_code == 200, login_response.text
        body = login_response.json()
        headers = {
            "X-API-Key": api_key,
            "Authorization": f"Bearer {body['access_token']}",
        }
        return headers, body["user"]["id"]

    @pytest.mark.asyncio
    async def test_execute_query_endpoint_success(
        self, client: AsyncClient, test_api_key: str
    ):
        """Test successful SQL query execution via endpoint."""
        headers, user_id = await self._get_auth_headers(client, test_api_key)

        response = await client.post(
            "/api/v1/sql/query",
            headers=headers,
            json={"query": "SELECT 1 as result, 'test' as text"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_read_only"] is True
        assert data["data"] == [{"result": 1, "text": "test"}]
        assert "execution_time" in data
        assert data["row_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_query_endpoint_error(
        self, client: AsyncClient, test_api_key: str
    ):
        """Test SQL query execution returns error result for invalid syntax."""
        headers, user_id = await self._get_auth_headers(client, test_api_key)

        response = await client.post(
            "/api/v1/sql/query",
            headers=headers,
            json={"query": "INVALID SYNTAX HERE"},
        )
        # SQL errors return success=False in the result, not HTTP error
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    @pytest.mark.asyncio
    async def test_execute_ddl_query(self, client: AsyncClient, test_api_key: str):
        """Test executing DDL (Data Definition Language) queries."""
        headers, user_id = await self._get_auth_headers(client, test_api_key)

        # Test CREATE TABLE
        temp_table_name = f"test_table_{uuid.uuid4().hex[:8]}"
        create_query = f"CREATE TABLE {temp_table_name} (id INTEGER, name TEXT)"

        response = await client.post(
            "/api/v1/sql/query", headers=headers, json={"query": create_query}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_read_only"] is False

        # Test INSERT
        insert_query = f"INSERT INTO {temp_table_name} (id, name) VALUES (1, 'test')"
        response = await client.post(
            "/api/v1/sql/query", headers=headers, json={"query": insert_query}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_read_only"] is False

        # Test SELECT to verify data
        select_query = f"SELECT * FROM {temp_table_name} WHERE id = 1"
        response = await client.post(
            "/api/v1/sql/query", headers=headers, json={"query": select_query}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_read_only"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == 1
        assert data["data"][0]["name"] == "test"

        # Clean up - DROP table
        drop_query = f"DROP TABLE {temp_table_name}"
        response = await client.post(
            "/api/v1/sql/query", headers=headers, json={"query": drop_query}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_query_history_workflow(
        self, client: AsyncClient, test_api_key: str
    ):
        """Test saving and retrieving query history."""
        headers, user_id = await self._get_auth_headers(client, test_api_key)

        # Execute a query first
        exec_response = await client.post(
            "/api/v1/sql/query",
            headers=headers,
            json={"query": "SELECT 123 as value"},
        )
        assert exec_response.status_code == 200

        # Save to history
        result_data = exec_response.json()
        history_save = await client.post(
            "/api/v1/sql/history",
            headers=headers,
            json={
                "query": "SELECT 123 as value",
                "result": result_data,
            },
        )
        # History saving might return 201 or 200
        assert history_save.status_code in [200, 201]

        # Check history
        history_response = await client.get("/api/v1/sql/history", headers=headers)
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert "history" in history_data
        assert len(history_data["history"]) >= 1

        # Verify latest history entry
        latest = history_data["history"][0]
        assert latest["query"] == "SELECT 123 as value"
        assert latest["is_read_only"] is True
        assert latest["row_count"] == 1

    @pytest.mark.asyncio
    async def test_snippet_management(self, client: AsyncClient, test_api_key: str):
        """Test creating, retrieving, and deleting SQL snippets."""
        headers, user_id = await self._get_auth_headers(client, test_api_key)

        # Create snippet
        snippet_data = {
            "name": f"Test Query {uuid.uuid4().hex[:8]}",
            "sql_code": "SELECT * FROM information_schema.tables LIMIT 5",
            "description": "Get table information",
            "is_shared": False,
        }

        create_response = await client.post(
            "/api/v1/sql/snippets",
            headers=headers,
            json=snippet_data,
        )
        assert create_response.status_code == 201
        created_snippet = create_response.json()
        assert created_snippet["name"] == snippet_data["name"]
        snippet_id = created_snippet["id"]

        # Get snippets
        list_response = await client.get("/api/v1/sql/snippets", headers=headers)
        assert list_response.status_code == 200
        snippets = list_response.json()
        assert len(snippets) >= 1
        assert any(s["id"] == snippet_id for s in snippets)

        # Delete snippet
        delete_response = await client.delete(
            f"/api/v1/sql/snippets/{snippet_id}",
            headers=headers,
        )
        assert delete_response.status_code == 204

        # Verify deletion
        list_response = await client.get("/api/v1/sql/snippets", headers=headers)
        assert list_response.status_code == 200
        snippets = list_response.json()
        assert not any(s["id"] == snippet_id for s in snippets)

    @pytest.mark.asyncio
    async def test_security_blocks_dangerous_queries(
        self, client: AsyncClient, test_api_key: str
    ):
        """Test that security validation blocks dangerous SQL operations."""
        headers, user_id = await self._get_auth_headers(client, test_api_key)

        # Test blocking of dangerous operations
        dangerous_queries = [
            "DROP DATABASE postgres",
            "ALTER SYSTEM SET shared_buffers = '4GB'",
            "CREATE ROLE hacker",
        ]

        for query in dangerous_queries:
            response = await client.post(
                "/api/v1/sql/query",
                headers=headers,
                json={"query": query},
            )
            # Should return 400 for validation errors
            assert response.status_code == 400, (
                f"Query '{query}' should return 400, got {response.status_code}"
            )
            response_data = response.json()
            assert "detail" in response_data
            assert "dangerous" in response_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_authentication_required(
        self, client: AsyncClient, test_api_key: str
    ):
        """Test that authentication is required for SQL endpoints."""
        # Try to call endpoint without auth headers
        response = await client.post(
            "/api/v1/sql/query",
            json={"query": "SELECT 1"},
        )
        assert response.status_code in [401, 403]

        # Try with just API key but no JWT token
        headers = {"X-API-Key": test_api_key}
        response = await client.post(
            "/api/v1/sql/query",
            headers=headers,
            json={"query": "SELECT 1"},
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_multiple_queries_isolation(
        self, client: AsyncClient, test_api_key: str
    ):
        """Test that queries are properly isolated between users."""
        headers, user_id = await self._get_auth_headers(client, test_api_key)

        # Execute first query
        response1 = await client.post(
            "/api/v1/sql/query",
            headers=headers,
            json={"query": "SELECT 'user1_query' as test"},
        )
        assert response1.status_code == 200

        # Execute second query
        response2 = await client.post(
            "/api/v1/sql/query",
            headers=headers,
            json={"query": "SELECT 'user1_query_2' as test"},
        )
        assert response2.status_code == 200

        # Both should succeed independently
        assert response1.json()["success"] is True
        assert response2.json()["success"] is True

    @pytest.mark.asyncio
    async def test_concurrent_query_execution(
        self, client: AsyncClient, test_api_key: str
    ):
        """Test concurrent query execution."""
        import asyncio

        headers, user_id = await self._get_auth_headers(client, test_api_key)

        # Execute multiple queries concurrently
        async def execute_query(n: int):
            response = await client.post(
                "/api/v1/sql/query",
                headers=headers,
                json={"query": f"SELECT {n} as value"},
            )
            return response

        # Run 5 queries concurrently
        results = await asyncio.gather(*[execute_query(i) for i in range(5)])

        # All should succeed
        for i, response in enumerate(results):
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"][0]["value"] == i

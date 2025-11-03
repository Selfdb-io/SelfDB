"""Integration tests for table management endpoints with the live dev stack."""

from __future__ import annotations

import time
import uuid
from typing import Dict, Tuple

import pytest
from httpx import AsyncClient

from shared.config.config_manager import ConfigManager


@pytest.mark.integration
class TestTableEndpointsIntegration:
    """Runs end-to-end scenarios against /api/v1/tables.* routes."""

    async def _get_admin_headers(self, client: AsyncClient, api_key: str) -> Tuple[Dict[str, str], str]:
        """Authenticate as the seeded admin user and return auth headers plus user id."""
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
    async def test_table_lifecycle_crud(self, client: AsyncClient, test_api_key: str) -> None:
        """Create a table, verify metadata endpoints, and clean it up."""
        headers, admin_user_id = await self._get_admin_headers(client, test_api_key)
        table_name = f"integration_tables_{uuid.uuid4().hex[:12]}"
        create_payload = {
            "name": table_name,
            "description": "Integration test table",
            "public": False,
            "schema": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "title", "type": "text", "nullable": False},
                ]
            },
        }

        try:
            create_response = await client.post("/api/v1/tables", headers=headers, json=create_payload)
            assert create_response.status_code == 201, create_response.text
            created = create_response.json()
            assert created["name"] == table_name
            assert created["owner_id"] == admin_user_id

            list_response = await client.get("/api/v1/tables", headers=headers)
            assert list_response.status_code == 200, list_response.text
            names = {table["name"] for table in list_response.json()}
            assert table_name in names

            metadata_response = await client.get(f"/api/v1/tables/{table_name}", headers=headers)
            assert metadata_response.status_code == 200, metadata_response.text
            metadata = metadata_response.json()
            assert metadata["name"] == table_name
            assert metadata["schema"]["columns"][0]["name"] == "id"

            sql_response = await client.get(f"/api/v1/tables/{table_name}/sql", headers=headers)
            assert sql_response.status_code == 200, sql_response.text
            assert "CREATE TABLE" in sql_response.json()["sql"].upper()
        finally:
            await client.delete(f"/api/v1/tables/{table_name}", headers=headers)

    @pytest.mark.asyncio
    async def test_row_operations_flow(self, client: AsyncClient, test_api_key: str) -> None:
        """Exercise insert, update, filter, and delete row endpoints."""
        headers, _ = await self._get_admin_headers(client, test_api_key)
        table_name = f"integration_rows_{int(time.time())}"
        create_payload = {
            "name": table_name,
            "description": "Row operations table",
            "public": False,
            "schema": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "amount", "type": "integer"},
                    {"name": "status", "type": "text"},
                ]
            },
        }

        create_response = await client.post("/api/v1/tables", headers=headers, json=create_payload)
        assert create_response.status_code == 201, create_response.text

        try:
            row_id = "11111111-1111-1111-1111-111111111111"
            insert_payload = {"id": row_id, "amount": 25, "status": "pending"}
            insert_response = await client.post(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                json=insert_payload,
            )
            assert insert_response.status_code == 200, insert_response.text

            second_insert = await client.post(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                json={"id": "22222222-2222-2222-2222-222222222222", "amount": 75, "status": "done"},
            )
            assert second_insert.status_code == 200, second_insert.text

            data_response = await client.get(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                params={"order_by": "amount", "page": 1, "page_size": 10},
            )
            assert data_response.status_code == 200, data_response.text
            table_data = data_response.json()
            assert len(table_data["data"]) == 2
            assert table_data["metadata"]["total_count"] == 2

            update_payload = {"status": "archived"}
            update_response = await client.put(
                f"/api/v1/tables/{table_name}/data/{row_id}",
                headers=headers,
                params={"id_column": "id"},
                json=update_payload,
            )
            assert update_response.status_code == 200, update_response.text
            assert update_response.json()["status"] == "archived"

            filter_response = await client.get(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                params={"filter_column": "status", "filter_value": "archived"},
            )
            assert filter_response.status_code == 200, filter_response.text
            filtered = filter_response.json()["data"]
            assert len(filtered) == 1
            assert filtered[0]["status"] == "archived"

            delete_row_response = await client.delete(
                f"/api/v1/tables/{table_name}/data/{row_id}",
                headers=headers,
                params={"id_column": "id"},
            )
            assert delete_row_response.status_code == 204, delete_row_response.text
        finally:
            await client.delete(f"/api/v1/tables/{table_name}", headers=headers)

    @pytest.mark.asyncio
    async def test_column_management_flow(self, client: AsyncClient, test_api_key: str) -> None:
        """Validate admin-only column add/update/delete endpoints."""
        headers, _ = await self._get_admin_headers(client, test_api_key)
        table_name = f"integration_columns_{uuid.uuid4().hex[:10]}"
        create_payload = {
            "name": table_name,
            "description": "Column operations table",
            "public": False,
            "schema": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "label", "type": "text"},
                ]
            },
        }

        create_response = await client.post("/api/v1/tables", headers=headers, json=create_payload)
        assert create_response.status_code == 201, create_response.text

        try:
            add_column_response = await client.post(
                f"/api/v1/tables/{table_name}/columns",
                headers=headers,
                json={
                    "name": "value",
                    "type": "integer",
                    "nullable": True,
                },
            )
            assert add_column_response.status_code == 200, add_column_response.text

            update_column_response = await client.put(
                f"/api/v1/tables/{table_name}/columns/value",
                headers=headers,
                json={
                    "type": "text",
                    "nullable": False,
                },
            )
            assert update_column_response.status_code == 200, update_column_response.text

            delete_column_response = await client.delete(
                f"/api/v1/tables/{table_name}/columns/value",
                headers=headers,
            )
            assert delete_column_response.status_code == 200, delete_column_response.text
        finally:
            await client.delete(f"/api/v1/tables/{table_name}", headers=headers)

    @pytest.mark.asyncio
    async def test_comprehensive_table_crud_with_data(self, client: AsyncClient, test_api_key: str) -> None:
        """Comprehensive test covering full table lifecycle with data operations."""
        headers, admin_user_id = await self._get_admin_headers(client, test_api_key)
        table_name = f"products_test_{uuid.uuid4().hex[:8]}"

        # Step 1: Create table with multiple column types
        create_payload = {
            "name": table_name,
            "description": "Test products table",
            "public": False,
            "schema": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "name", "type": "text", "nullable": False},
                    {"name": "price", "type": "numeric", "nullable": False},
                    {"name": "stock", "type": "integer", "nullable": True},
                ]
            },
        }

        create_response = await client.post("/api/v1/tables", headers=headers, json=create_payload)
        assert create_response.status_code == 201, create_response.text
        created = create_response.json()
        assert created["name"] == table_name
        assert created["owner_id"] == admin_user_id
        assert created["public"] is False
        assert len(created["schema"]["columns"]) == 4

        try:
            # Step 2: Insert multiple rows
            product1_id = "11111111-1111-1111-1111-111111111111"
            product2_id = "22222222-2222-2222-2222-222222222222"
            product3_id = "33333333-3333-3333-3333-333333333333"

            insert1 = await client.post(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                json={"id": product1_id, "name": "Laptop", "price": 999.99, "stock": 50},
            )
            assert insert1.status_code == 200, insert1.text
            assert insert1.json()["name"] == "Laptop"

            insert2 = await client.post(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                json={"id": product2_id, "name": "Mouse", "price": 25.50, "stock": 200},
            )
            assert insert2.status_code == 200, insert2.text

            insert3 = await client.post(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                json={"id": product3_id, "name": "Keyboard", "price": 75.00, "stock": 100},
            )
            assert insert3.status_code == 200, insert3.text

            # Step 3: Verify all rows retrieved
            get_data = await client.get(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                params={"page": 1, "page_size": 10},
            )
            assert get_data.status_code == 200, get_data.text
            data_result = get_data.json()
            assert len(data_result["data"]) == 3
            assert data_result["metadata"]["total_count"] == 3

            # Step 4: Add a new column
            add_column = await client.post(
                f"/api/v1/tables/{table_name}/columns",
                headers=headers,
                json={"name": "category", "type": "text", "nullable": True},
            )
            assert add_column.status_code == 200, add_column.text

            # Step 5: Update rows to add category values
            update1 = await client.put(
                f"/api/v1/tables/{table_name}/data/{product1_id}",
                headers=headers,
                params={"id_column": "id"},
                json={"category": "Electronics"},
            )
            assert update1.status_code == 200, update1.text
            assert update1.json()["category"] == "Electronics"

            update2 = await client.put(
                f"/api/v1/tables/{table_name}/data/{product2_id}",
                headers=headers,
                params={"id_column": "id"},
                json={"category": "Accessories", "price": 29.99, "stock": 250},
            )
            assert update2.status_code == 200, update2.text
            # Price can be returned as string or number depending on numeric precision
            assert float(update2.json()["price"]) == 29.99
            assert update2.json()["stock"] == 250

            # Step 6: Filter by category
            filter_result = await client.get(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                params={"filter_column": "category", "filter_value": "Electronics"},
            )
            assert filter_result.status_code == 200, filter_result.text
            filtered = filter_result.json()["data"]
            assert len(filtered) == 1
            assert filtered[0]["name"] == "Laptop"

            # Step 7: Update table metadata
            update_table = await client.put(
                f"/api/v1/tables/{table_name}",
                headers=headers,
                json={"description": "Updated product inventory", "public": True},
            )
            assert update_table.status_code == 200, update_table.text
            assert update_table.json()["description"] == "Updated product inventory"
            assert update_table.json()["public"] is True

            # Step 8: Get table SQL
            sql_response = await client.get(f"/api/v1/tables/{table_name}/sql", headers=headers)
            assert sql_response.status_code == 200, sql_response.text
            sql_text = sql_response.json()["sql"]
            assert "CREATE TABLE" in sql_text.upper()
            assert table_name in sql_text

            # Step 9: Delete a row
            delete_row = await client.delete(
                f"/api/v1/tables/{table_name}/data/{product3_id}",
                headers=headers,
                params={"id_column": "id"},
            )
            assert delete_row.status_code == 204

            # Verify deletion
            get_after_delete = await client.get(
                f"/api/v1/tables/{table_name}/data", headers=headers
            )
            assert get_after_delete.status_code == 200
            remaining = get_after_delete.json()["data"]
            assert len(remaining) == 2
            assert all(row["id"] != product3_id for row in remaining)

            # Step 10: Delete a column
            delete_col = await client.delete(
                f"/api/v1/tables/{table_name}/columns/stock",
                headers=headers,
            )
            assert delete_col.status_code == 200, delete_col.text

            # Verify column deleted
            metadata_after_col_delete = await client.get(
                f"/api/v1/tables/{table_name}", headers=headers
            )
            assert metadata_after_col_delete.status_code == 200
            columns = metadata_after_col_delete.json()["schema"]["columns"]
            assert all(col["name"] != "stock" for col in columns)

        finally:
            # Cleanup: Delete the table
            delete_response = await client.delete(f"/api/v1/tables/{table_name}", headers=headers)
            assert delete_response.status_code == 204

    @pytest.mark.asyncio
    async def test_table_with_ordering_and_pagination(self, client: AsyncClient, test_api_key: str) -> None:
        """Test data retrieval with ordering and pagination."""
        headers, _ = await self._get_admin_headers(client, test_api_key)
        table_name = f"pagination_test_{uuid.uuid4().hex[:8]}"

        create_payload = {
            "name": table_name,
            "description": "Pagination test table",
            "public": False,
            "schema": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "sequence", "type": "integer", "nullable": False},
                    {"name": "value", "type": "text", "nullable": False},
                ]
            },
        }

        create_response = await client.post("/api/v1/tables", headers=headers, json=create_payload)
        assert create_response.status_code == 201, create_response.text

        try:
            # Insert 5 rows
            for i in range(1, 6):
                row_id = f"{i:08d}-0000-0000-0000-000000000000"
                await client.post(
                    f"/api/v1/tables/{table_name}/data",
                    headers=headers,
                    json={"id": row_id, "sequence": i * 10, "value": f"Item {i}"},
                )

            # Test ordering by sequence ascending
            ordered_asc = await client.get(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                params={"order_by": "sequence", "page": 1, "page_size": 10},
            )
            assert ordered_asc.status_code == 200
            asc_data = ordered_asc.json()["data"]
            assert asc_data[0]["sequence"] == 10
            assert asc_data[-1]["sequence"] == 50

            # Test pagination - first page
            page1 = await client.get(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                params={"page": 1, "page_size": 2, "order_by": "sequence"},
            )
            assert page1.status_code == 200
            page1_data = page1.json()
            assert len(page1_data["data"]) == 2
            assert page1_data["metadata"]["total_count"] == 5
            assert page1_data["metadata"]["total_pages"] == 3

            # Test pagination - second page
            page2 = await client.get(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                params={"page": 2, "page_size": 2, "order_by": "sequence"},
            )
            assert page2.status_code == 200
            page2_data = page2.json()
            assert len(page2_data["data"]) == 2
            assert page2_data["data"][0]["sequence"] == 30

        finally:
            await client.delete(f"/api/v1/tables/{table_name}", headers=headers)

    @pytest.mark.asyncio
    async def test_table_error_handling(self, client: AsyncClient, test_api_key: str) -> None:
        """Test error handling for various edge cases."""
        headers, _ = await self._get_admin_headers(client, test_api_key)

        # Test: Create table with duplicate name
        table_name = f"error_test_{uuid.uuid4().hex[:8]}"
        create_payload = {
            "name": table_name,
            "schema": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                ]
            },
        }

        create1 = await client.post("/api/v1/tables", headers=headers, json=create_payload)
        assert create1.status_code == 201

        try:
            # Duplicate table name should fail
            create2 = await client.post("/api/v1/tables", headers=headers, json=create_payload)
            assert create2.status_code == 409, "Should fail with conflict for duplicate table"

            # Test: Get non-existent table
            get_missing = await client.get("/api/v1/tables/nonexistent_table_xyz", headers=headers)
            assert get_missing.status_code == 404

            # Test: Insert row with missing required field
            insert_invalid = await client.post(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                json={"wrong_field": "value"},  # Missing 'id' field
            )
            assert insert_invalid.status_code in [400, 500]  # Should fail with bad request or server error

            # Test: Update non-existent row
            update_missing = await client.put(
                f"/api/v1/tables/{table_name}/data/99999999-9999-9999-9999-999999999999",
                headers=headers,
                params={"id_column": "id"},
                json={"some_field": "value"},
            )
            assert update_missing.status_code in [400, 404, 500]

            # Test: Delete non-existent column
            delete_col = await client.delete(
                f"/api/v1/tables/{table_name}/columns/nonexistent_column",
                headers=headers,
            )
            assert delete_col.status_code in [400, 404, 500]

        finally:
            await client.delete(f"/api/v1/tables/{table_name}", headers=headers)

    @pytest.mark.asyncio
    async def test_multiple_data_types(self, client: AsyncClient, test_api_key: str) -> None:
        """Test table with various PostgreSQL data types."""
        headers, _ = await self._get_admin_headers(client, test_api_key)
        table_name = f"types_test_{uuid.uuid4().hex[:8]}"

        create_payload = {
            "name": table_name,
            "description": "Data types test",
            "public": False,
            "schema": {
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "int_val", "type": "integer", "nullable": True},
                    {"name": "text_val", "type": "text", "nullable": True},
                    {"name": "numeric_val", "type": "numeric", "nullable": True},
                    {"name": "bool_val", "type": "boolean", "nullable": True},
                    {"name": "timestamp_val", "type": "timestamp", "nullable": True},
                ]
            },
        }

        create_response = await client.post("/api/v1/tables", headers=headers, json=create_payload)
        assert create_response.status_code == 201, create_response.text

        try:
            # Insert row with various types
            test_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            insert_response = await client.post(
                f"/api/v1/tables/{table_name}/data",
                headers=headers,
                json={
                    "id": test_id,
                    "int_val": 42,
                    "text_val": "Hello, World!",
                    "numeric_val": 123.456,
                    "bool_val": True,
                },
            )
            assert insert_response.status_code == 200, insert_response.text
            inserted = insert_response.json()
            assert inserted["int_val"] == 42
            assert inserted["text_val"] == "Hello, World!"
            assert inserted["bool_val"] is True

            # Verify retrieval
            get_response = await client.get(
                f"/api/v1/tables/{table_name}/data", headers=headers
            )
            assert get_response.status_code == 200
            data = get_response.json()["data"]
            assert len(data) == 1
            assert data[0]["id"] == test_id

        finally:
            await client.delete(f"/api/v1/tables/{table_name}", headers=headers)

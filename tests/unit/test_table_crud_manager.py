"""
Unit tests for TableCRUDManager business logic using real PostgreSQL test container.
"""

import uuid
import pytest

from shared.services.table_crud_manager import TableCRUDManager


async def _cleanup_table(db_manager, table_name: str):
    """Drop dynamic test table and remove metadata."""
    try:
        async with db_manager.acquire() as conn:
            await conn.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
        async with db_manager.acquire() as conn:
            await conn.execute('DELETE FROM tables WHERE name = $1', table_name)
    except Exception:
        # Cleanup best-effort only
        pass


async def _create_admin_user(db_manager):
    """Get or create the admin user from config manager."""
    from shared.config.config_manager import ConfigManager
    config = ConfigManager()
    admin_email = config.admin_email or 'admin@example.com'
    
    # First, try to find existing admin user
    try:
        async with db_manager.acquire() as conn:
            result = await conn.fetchval('SELECT id FROM users WHERE email = $1', admin_email)
            if result:
                return result
    except Exception:
        pass
    
    # If not found, create it
    admin_id = "admin-user-uuid"  # Fixed ID for admin
    try:
        async with db_manager.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (id, email, password_hash, first_name, last_name, role, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING
            ''', admin_id, admin_email, "hashed_" + (config.admin_password or 'password'), config.admin_first_name or 'Admin', config.admin_last_name or 'User', "ADMIN", True)
    except Exception:
        # User might already exist
        pass
    return admin_id


@pytest.mark.asyncio
async def test_create_table_and_metadata_persistence(test_database_manager):
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"tdd_tables_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {
                "name": "id",
                "type": "uuid",
                "primary_key": True,
                "default": "uuid_generate_v4()",
            },
            {
                "name": "name",
                "type": "text",
                "nullable": False,
            },
            {
                "name": "created_at",
                "type": "timestamptz",
                "default": "now()",
            },
        ],
        "indexes": [
            {
                "name": f"idx_{table_name}_name",
                "columns": ["name"],
                "unique": True,
            }
        ],
    }

    try:
        result = await manager.create_table(
            owner_id=owner_id,
            table_definition={
                "name": table_name,
                "description": "Table for CRUD manager TDD tests",
                "public": False,
                "schema": schema,
                "metadata": {"tags": ["pytest", "tdd"]},
            },
        )

        assert result["name"] == table_name
        assert result["public"] is False
        assert result["owner_id"] == str(owner_id)

        stored_table = await manager.get_table(table_name)
        assert stored_table["name"] == table_name
        assert stored_table["schema"]["columns"][0]["name"] == "id"
        assert stored_table["metadata"]["tags"] == ["pytest", "tdd"]

        tables = await manager.list_tables(owner_id=owner_id)
        assert any(t["name"] == table_name for t in tables)
    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_insert_query_update_and_delete_rows(test_database_manager):
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"tdd_data_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {
                "name": "id",
                "type": "uuid",
                "primary_key": True,
                "default": "uuid_generate_v4()",
            },
            {
                "name": "email",
                "type": "text",
                "nullable": False,
                "unique": True,
            },
            {
                "name": "age",
                "type": "integer",
                "nullable": True,
            },
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={
                "name": table_name,
                "description": "Data flow verification table",
                "public": False,
                "schema": schema,
            },
        )

        inserted = await manager.insert_row(
            table_name,
            {
                "email": "alice@example.com",
                "age": 30,
            },
        )

        assert inserted["email"] == "alice@example.com"
        inserted_id = inserted["id"]

        page = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page["metadata"]["total_count"] == 1
        assert page["data"][0]["email"] == "alice@example.com"

        updated = await manager.update_row(
            table_name,
            row_id=inserted_id,
            id_column="id",
            updates={"age": 31},
        )
        assert updated["age"] == 31

        await manager.delete_row(table_name, row_id=inserted_id, id_column="id")
        page_after_delete = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page_after_delete["metadata"]["total_count"] == 0
    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_add_and_remove_column_updates_metadata(test_database_manager):
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"tdd_schema_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {
                "name": "id",
                "type": "uuid",
                "primary_key": True,
                "default": "uuid_generate_v4()",
            },
            {
                "name": "title",
                "type": "text",
                "nullable": False,
            },
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={
                "name": table_name,
                "schema": schema,
                "public": False,
            },
        )

        await manager.add_column(
            table_name,
            {
                "name": "status",
                "type": "text",
                "default": "'draft'",
                "nullable": False,
            },
        )

        metadata_after_add = await manager.get_table(table_name)
        assert any(col["name"] == "status" for col in metadata_after_add["schema"]["columns"])

        await manager.delete_column(table_name, "status")
        metadata_after_drop = await manager.get_table(table_name)
        assert all(col["name"] != "status" for col in metadata_after_drop["schema"]["columns"])

        create_sql = await manager.get_table_sql(table_name)
        assert table_name in create_sql
        assert "CREATE TABLE" in create_sql.upper()
    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_type_conversion_numeric_types(test_database_manager):
    """Test type conversion for all PostgreSQL numeric types."""
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"test_numeric_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {"name": "id", "type": "uuid", "primary_key": True, "default": "uuid_generate_v4()"},
            {"name": "smallint_col", "type": "smallint", "nullable": True},
            {"name": "int_col", "type": "integer", "nullable": True},
            {"name": "bigint_col", "type": "bigint", "nullable": True},
            {"name": "real_col", "type": "real", "nullable": True},
            {"name": "double_col", "type": "double precision", "nullable": True},
            {"name": "numeric_col", "type": "numeric", "nullable": True},
            {"name": "decimal_col", "type": "decimal", "nullable": True},
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={"name": table_name, "schema": schema, "public": False}
        )

        # Test inserting string values that should be converted
        test_data = {
            "smallint_col": "100",
            "int_col": "50000",
            "bigint_col": "9876543210",
            "real_col": "3.14",
            "double_col": "2.718281828",
            "numeric_col": "123.456",
            "decimal_col": "999.99"
        }

        inserted = await manager.insert_row(table_name, test_data)
        assert inserted is not None
        row_id = inserted.get("id")

        # Query and verify conversion worked
        page = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page["metadata"]["total_count"] >= 1
        # Find our row
        row = next((r for r in page["data"] if r.get("id") == row_id), None)
        assert row is not None
        
        assert row["smallint_col"] == 100
        assert row["int_col"] == 50000
        assert row["bigint_col"] == 9876543210
        assert abs(row["real_col"] - 3.14) < 0.01
        assert abs(row["double_col"] - 2.718281828) < 0.0001

    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_type_conversion_datetime_types(test_database_manager):
    """Test type conversion for date/time types."""
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"test_datetime_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {"name": "id", "type": "uuid", "primary_key": True, "default": "uuid_generate_v4()"},
            {"name": "date_col", "type": "date", "nullable": True},
            {"name": "time_col", "type": "time", "nullable": True},
            {"name": "timestamp_col", "type": "timestamp", "nullable": True},
            {"name": "timestamptz_col", "type": "timestamptz", "nullable": True},
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={"name": table_name, "schema": schema, "public": False}
        )

        # Test inserting string values (without interval for now)
        test_data = {
            "date_col": "2025-03-15",
            "time_col": "14:30:00",
            "timestamp_col": "2025-03-15 14:30:00",
            "timestamptz_col": "2025-03-15T14:30:00Z",
        }

        inserted = await manager.insert_row(table_name, test_data)
        assert inserted is not None
        row_id = inserted.get("id")

        # Query and verify
        page = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page["metadata"]["total_count"] >= 1
        row = next((r for r in page["data"] if r.get("id") == row_id), None)
        assert row is not None
        
        # Verify date/time values were properly converted
        assert row["date_col"] is not None
        assert row["time_col"] is not None
        assert row["timestamp_col"] is not None

    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_type_conversion_interval(test_database_manager):
    """Test type conversion for interval type separately."""
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"test_interval_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {"name": "id", "type": "uuid", "primary_key": True, "default": "uuid_generate_v4()"},
            {"name": "interval_col", "type": "interval", "nullable": True},
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={"name": table_name, "schema": schema, "public": False}
        )

        # Test various interval formats
        test_data = {
            "interval_col": "2 days"
        }

        inserted = await manager.insert_row(table_name, test_data)
        assert inserted is not None
        row_id = inserted.get("id")

        page = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page["metadata"]["total_count"] >= 1
        row = next((r for r in page["data"] if r.get("id") == row_id), None)
        assert row is not None
        assert row["interval_col"] is not None

    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_type_conversion_text_and_boolean(test_database_manager):
    """Test type conversion for text and boolean types."""
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"test_text_bool_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {"name": "id", "type": "uuid", "primary_key": True, "default": "uuid_generate_v4()"},
            {"name": "text_col", "type": "text", "nullable": True},
            {"name": "varchar_col", "type": "varchar", "nullable": True},
            {"name": "bool_col", "type": "boolean", "nullable": True},
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={"name": table_name, "schema": schema, "public": False}
        )

        # Test boolean conversion from various string formats
        test_data = {
            "text_col": "Hello World",
            "varchar_col": "Test String",
            "bool_col": "true"
        }

        inserted = await manager.insert_row(table_name, test_data)
        assert inserted is not None
        row_id = inserted.get("id")

        page = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page["metadata"]["total_count"] >= 1
        row = next((r for r in page["data"] if r.get("id") == row_id), None)
        assert row is not None
        assert row["bool_col"] is True

        # Test false value
        test_data2 = {
            "text_col": "Test 2",
            "varchar_col": "Another test",
            "bool_col": "false"
        }
        inserted2 = await manager.insert_row(table_name, test_data2)
        row_id2 = inserted2.get("id")
        page2 = await manager.get_table_data(table_name, page=1, page_size=20)
        row2 = next((r for r in page2["data"] if r.get("id") == row_id2), None)
        assert row2 is not None
        assert row2["bool_col"] is False

    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_type_conversion_json_and_uuid(test_database_manager):
    """Test type conversion for JSON and UUID types."""
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"test_json_uuid_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {"name": "id", "type": "uuid", "primary_key": True, "default": "uuid_generate_v4()"},
            {"name": "json_col", "type": "json", "nullable": True},
            {"name": "jsonb_col", "type": "jsonb", "nullable": True},
            {"name": "uuid_col", "type": "uuid", "nullable": True},
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={"name": table_name, "schema": schema, "public": False}
        )

        test_uuid = str(uuid.uuid4())
        test_data = {
            "json_col": '{"key": "value", "number": 42}',
            "jsonb_col": '{"status": "active", "count": 100}',
            "uuid_col": test_uuid
        }

        inserted = await manager.insert_row(table_name, test_data)
        assert inserted is not None
        row_id = inserted.get("id")

        page = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page["metadata"]["total_count"] >= 1
        row = next((r for r in page["data"] if r.get("id") == row_id), None)
        assert row is not None
        # UUID might be returned as UUID object or string, convert to string for comparison
        assert str(row["uuid_col"]) == test_uuid

    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_type_conversion_array_types(test_database_manager):
    """Test type conversion for PostgreSQL array types."""
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"test_arrays_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {"name": "id", "type": "uuid", "primary_key": True, "default": "uuid_generate_v4()"},
            {"name": "int_array", "type": "integer[]", "nullable": True},
            {"name": "text_array", "type": "text[]", "nullable": True},
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={"name": table_name, "schema": schema, "public": False}
        )

        # Test JSON array format
        test_data = {
            "int_array": "[1, 2, 3, 4, 5]",
            "text_array": '["apple", "banana", "cherry"]'
        }

        inserted = await manager.insert_row(table_name, test_data)
        assert inserted is not None
        row_id = inserted.get("id")

        page = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page["metadata"]["total_count"] >= 1
        row = next((r for r in page["data"] if r.get("id") == row_id), None)
        assert row is not None
        assert row["int_array"] == [1, 2, 3, 4, 5]
        assert row["text_array"] == ["apple", "banana", "cherry"]

    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_type_conversion_network_types(test_database_manager):
    """Test type conversion for network address types (inet, cidr, macaddr)."""
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"test_network_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {"name": "id", "type": "uuid", "primary_key": True, "default": "uuid_generate_v4()"},
            {"name": "inet_col", "type": "inet", "nullable": True},
            {"name": "cidr_col", "type": "cidr", "nullable": True},
            {"name": "macaddr_col", "type": "macaddr", "nullable": True},
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={"name": table_name, "schema": schema, "public": False}
        )

        test_data = {
            "inet_col": "192.168.1.100",
            "cidr_col": "192.168.1.0/24",
            "macaddr_col": "08:00:2b:01:02:03"
        }

        inserted = await manager.insert_row(table_name, test_data)
        assert inserted is not None
        row_id = inserted.get("id")

        page = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page["metadata"]["total_count"] >= 1
        row = next((r for r in page["data"] if r.get("id") == row_id), None)
        assert row is not None
        assert row["inet_col"] is not None
        assert row["macaddr_col"] is not None

    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_type_conversion_geometric_types(test_database_manager):
    """Test type conversion for geometric types (point, box, circle)."""
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"test_geometric_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {"name": "id", "type": "uuid", "primary_key": True, "default": "uuid_generate_v4()"},
            {"name": "point_col", "type": "point", "nullable": True},
            {"name": "box_col", "type": "box", "nullable": True},
            {"name": "circle_col", "type": "circle", "nullable": True},
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={"name": table_name, "schema": schema, "public": False}
        )

        test_data = {
            "point_col": "(1.5, 2.5)",
            "box_col": "((0,0),(1,1))",
            "circle_col": "<(0,0),5>"
        }

        inserted = await manager.insert_row(table_name, test_data)
        assert inserted is not None
        row_id = inserted.get("id")

        page = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page["metadata"]["total_count"] >= 1
        row = next((r for r in page["data"] if r.get("id") == row_id), None)
        assert row is not None
        assert row["point_col"] is not None

    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_type_conversion_null_and_empty_values(test_database_manager):
    """Test type conversion with null and empty string values."""
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"test_nulls_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {"name": "id", "type": "uuid", "primary_key": True, "default": "uuid_generate_v4()"},
            {"name": "nullable_int", "type": "integer", "nullable": True},
            {"name": "nullable_text", "type": "text", "nullable": True},
            {"name": "nullable_bool", "type": "boolean", "nullable": True},
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={"name": table_name, "schema": schema, "public": False}
        )

        # Test with empty strings (should convert to NULL for nullable columns)
        test_data = {
            "nullable_int": "",
            "nullable_text": "",
            "nullable_bool": ""
        }

        inserted = await manager.insert_row(table_name, test_data)
        assert inserted is not None
        row_id = inserted.get("id")

        page = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page["metadata"]["total_count"] >= 1
        row = next((r for r in page["data"] if r.get("id") == row_id), None)
        assert row is not None
        # Empty strings for nullable columns should become NULL
        assert row["nullable_int"] is None
        assert row["nullable_text"] is None or row["nullable_text"] == ""
        assert row["nullable_bool"] is None

    finally:
        await _cleanup_table(test_database_manager, table_name)


@pytest.mark.asyncio
async def test_type_conversion_money_type(test_database_manager):
    """Test type conversion for money type."""
    if test_database_manager is None:
        pytest.skip("Database manager not available")

    manager = TableCRUDManager(test_database_manager)
    owner_id = await _create_admin_user(test_database_manager)
    table_name = f"test_money_{uuid.uuid4().hex[:8]}"

    schema = {
        "columns": [
            {"name": "id", "type": "uuid", "primary_key": True, "default": "uuid_generate_v4()"},
            {"name": "price", "type": "money", "nullable": True},
        ]
    }

    try:
        await manager.create_table(
            owner_id=owner_id,
            table_definition={"name": table_name, "schema": schema, "public": False}
        )

        # Test with $ symbol and commas
        test_data = {
            "price": "$1,234.56"
        }

        inserted = await manager.insert_row(table_name, test_data)
        assert inserted is not None
        row_id = inserted.get("id")

        page = await manager.get_table_data(table_name, page=1, page_size=20)
        assert page["metadata"]["total_count"] >= 1
        row = next((r for r in page["data"] if r.get("id") == row_id), None)
        assert row is not None
        assert row["price"] is not None

    finally:
        await _cleanup_table(test_database_manager, table_name)

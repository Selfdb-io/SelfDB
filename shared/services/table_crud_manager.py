"""Table CRUD manager for dynamic table management in SelfDB."""

from __future__ import annotations

import json
import math
import re
import uuid
from datetime import datetime, date, time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from shared.database.connection_manager import DatabaseConnectionManager


TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class TableValidationError(Exception):
    """Raised when a table definition fails validation."""


class TableAlreadyExistsError(Exception):
    """Raised when attempting to create a table that already exists."""


class TableNotFoundError(Exception):
    """Raised when a table cannot be located."""


class TableColumnError(Exception):
    """Raised when column operations are invalid."""


class TableCRUDManager:
    """Manage dynamic database tables and metadata persistence."""

    def __init__(self, database_manager: DatabaseConnectionManager):
        self._db = database_manager
        self._metadata_initialized = False

    async def create_table(self, owner_id: uuid.UUID, table_definition: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure_metadata_table()
        definition = self._normalize_table_definition(table_definition)
        table_name = definition["name"]

        if await self._table_exists(table_name):
            raise TableAlreadyExistsError(f"Table '{table_name}' already exists")

        creation_sql, index_statements = self._build_create_statements(table_name, definition["schema"])

        async with self._db.transaction() as conn:
            await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
            await conn.execute(creation_sql)
            for statement in index_statements:
                await conn.execute(statement)

            metadata = dict(definition["metadata"]) if definition["metadata"] else {}
            metadata["creation_sql"] = creation_sql

            await conn.execute(
                """
                INSERT INTO tables (name, schema, public, owner_id, description, metadata, row_count)
                VALUES ($1, $2::jsonb, $3, $4, $5, $6::jsonb, 0)
                """,
                table_name,
                json.dumps(definition["schema"]),
                definition["public"],
                str(owner_id),
                definition.get("description"),
                json.dumps(metadata),
            )

        return await self.get_table(table_name)

    async def list_tables(self, owner_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
        params: Sequence[Any]
        await self._ensure_metadata_table()
        sql = (
            "SELECT name, schema, public, owner_id, description, metadata, row_count, created_at, updated_at "
            "FROM tables"
        )
        if owner_id is not None:
            sql += " WHERE owner_id = $1"
            params = (str(owner_id),)
        else:
            params = ()
        sql += " ORDER BY name"

        async with self._db.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        return [self._row_to_dict(row) for row in rows]

    async def get_table(self, table_name: str) -> Dict[str, Any]:
        await self._ensure_metadata_table()
        normalized_name = self._normalize_table_name(table_name)

        async with self._db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT name, schema, public, owner_id, description, metadata, row_count, created_at, updated_at
                FROM tables
                WHERE name = $1
                """,
                normalized_name,
            )

        if row is None:
            raise TableNotFoundError(f"Table '{normalized_name}' not found")

        return self._row_to_dict(row)

    async def delete_table(self, table_name: str, *, cascade: bool = False) -> None:
        await self._ensure_metadata_table()
        normalized_name = self._normalize_table_name(table_name)

        if not await self._table_exists(normalized_name):
            raise TableNotFoundError(f"Table '{normalized_name}' not found")

        drop_sql = f'DROP TABLE IF EXISTS "{normalized_name}" {"CASCADE" if cascade else ""}'.strip()

        async with self._db.transaction() as conn:
            await conn.execute(drop_sql)
            await conn.execute("DELETE FROM tables WHERE name = $1", normalized_name)

    async def get_table_sql(self, table_name: str) -> str:
        """Generate CREATE TABLE SQL by introspecting current database structure."""
        normalized_name = self._normalize_table_name(table_name)
        
        async with self._db.acquire() as conn:
            # Get column definitions with constraints
            columns = await conn.fetch("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, normalized_name)
            
            if not columns:
                raise TableNotFoundError(f"Table '{table_name}' not found in database")
            
            # Get primary key columns
            pk_columns = await conn.fetch("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = $1::regclass AND i.indisprimary
            """, normalized_name)
            
            pk_set = {row['attname'] for row in pk_columns}
            
            # Build column definitions
            col_defs = []
            for col in columns:
                parts = [f'"{col["column_name"]}"']
                
                # Data type with length
                if col["character_maximum_length"]:
                    parts.append(f'{col["data_type"].upper()}({col["character_maximum_length"]})')
                else:
                    parts.append(col["data_type"].upper())
                
                # Constraints
                if col["column_default"]:
                    parts.append(f'DEFAULT {col["column_default"]}')
                if col["is_nullable"] == 'NO':
                    parts.append('NOT NULL')
                if col["column_name"] in pk_set:
                    parts.append('PRIMARY KEY')
                    
                col_defs.append(' '.join(parts))
            
            return f'CREATE TABLE "{normalized_name}" (\n  {",\n  ".join(col_defs)}\n);'

    async def insert_row(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data:
            raise TableValidationError("Row data cannot be empty")

        await self._ensure_metadata_table()
        table = await self.get_table(table_name)
        allowed_columns = {col["name"]: col for col in table["schema"].get("columns", [])}

        invalid_columns = set(data.keys()) - set(allowed_columns.keys())
        if invalid_columns:
            raise TableColumnError(f"Unknown columns for insert: {', '.join(sorted(invalid_columns))}")

        columns = list(data.keys())
        placeholders = ", ".join(f"${idx}" for idx in range(1, len(columns) + 1))
        column_list = ", ".join(f'"{col}"' for col in columns)
        
        # Convert values to appropriate types based on column definitions
        values = []
        for col_name in columns:
            col_def = allowed_columns[col_name]
            raw_value = data[col_name]
            converted_value = self._convert_value_to_type(raw_value, col_def)
            values.append(converted_value)

        sql = f'INSERT INTO "{table["name"]}" ({column_list}) VALUES ({placeholders}) RETURNING *'

        async with self._db.acquire() as conn:
            record = await conn.fetchrow(sql, *values)

        await self._refresh_row_count(table["name"])
        return dict(record)

    async def get_table_data(
        self,
        table_name: str,
        *,
        page: int = 1,
        page_size: int = 100,
        order_by: Optional[str] = None,
        filter_column: Optional[str] = None,
        filter_value: Optional[Any] = None,
    ) -> Dict[str, Any]:
        if page < 1:
            raise TableValidationError("Page number must be >= 1")
        if page_size < 1:
            raise TableValidationError("Page size must be >= 1")

        await self._ensure_metadata_table()
        table = await self.get_table(table_name)
        valid_columns = {col["name"] for col in table["schema"].get("columns", [])}

        order_clause = ""
        params: List[Any] = []

        if order_by:
            if order_by not in valid_columns:
                raise TableColumnError(f"Invalid order_by column '{order_by}'")
            order_clause = f' ORDER BY "{order_by}"'

        where_clause = ""
        if filter_column and filter_value is not None:
            if filter_column not in valid_columns:
                raise TableColumnError(f"Invalid filter column '{filter_column}'")
            where_clause = f' WHERE "{filter_column}" = $1'
            params.append(filter_value)

        limit = page_size
        offset = (page - 1) * page_size

        base_query = f'SELECT * FROM "{table["name"]}"'

        async with self._db.acquire() as conn:
            data_query = (
                f"{base_query}{where_clause}{order_clause} LIMIT {limit} OFFSET {offset}"
            )
            rows = await conn.fetch(data_query, *params)

            count_query = f"SELECT COUNT(*) FROM \"{table['name']}\""
            if where_clause:
                count_query += where_clause
                total = await conn.fetchval(count_query, *params)
            else:
                total = await conn.fetchval(count_query)

        total_pages = math.ceil(total / page_size) if total else 0
        await self._set_row_count(table["name"], total)

        # Convert data to JSON-serializable format
        processed_data = []
        for row in rows:
            row_dict = dict(row)
            # Convert ipaddress objects to strings for JSON serialization
            for key, value in row_dict.items():
                if hasattr(value, '__class__') and 'ipaddress' in str(type(value)):
                    row_dict[key] = str(value)
            processed_data.append(row_dict)

        return {
            "data": processed_data,
            "metadata": {
                "total_count": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "columns": table["schema"].get("columns", []),
            },
        }

    async def update_row(self, table_name: str, row_id: Any, id_column: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if not updates:
            raise TableValidationError("Update payload cannot be empty")

        await self._ensure_metadata_table()
        table = await self.get_table(table_name)
        column_definitions = {col["name"]: col for col in table["schema"].get("columns", [])}
        valid_columns = set(column_definitions.keys())
        
        if id_column not in valid_columns:
            raise TableColumnError(f"Invalid identifier column '{id_column}'")

        invalid_columns = set(updates.keys()) - valid_columns
        if invalid_columns:
            raise TableColumnError(f"Unknown columns for update: {', '.join(sorted(invalid_columns))}")

        set_parts = []
        values: List[Any] = []
        idx = 1
        for column, value in updates.items():
            set_parts.append(f'"{column}" = ${idx}')
            # Convert value to appropriate type
            col_def = column_definitions[column]
            converted_value = self._convert_value_to_type(value, col_def)
            values.append(converted_value)
            idx += 1

        values.append(row_id)
        sql = (
            f'UPDATE "{table["name"]}" SET {", ".join(set_parts)} '
            f'WHERE "{id_column}" = ${idx} RETURNING *'
        )

        async with self._db.acquire() as conn:
            record = await conn.fetchrow(sql, *values)

        if record is None:
            raise TableNotFoundError(
                f"Row with {id_column}={row_id} not found in table '{table['name']}'"
            )

        return dict(record)

    async def delete_row(self, table_name: str, row_id: Any, id_column: str) -> None:
        await self._ensure_metadata_table()
        table = await self.get_table(table_name)
        valid_columns = {col["name"] for col in table["schema"].get("columns", [])}
        if id_column not in valid_columns:
            raise TableColumnError(f"Invalid identifier column '{id_column}'")

        async with self._db.acquire() as conn:
            result = await conn.execute(
                f'DELETE FROM "{table["name"]}" WHERE "{id_column}" = $1',
                row_id,
            )

        if result.endswith("0"):
            raise TableNotFoundError(
                f"Row with {id_column}={row_id} not found in table '{table['name']}'"
            )

        await self._refresh_row_count(table["name"])

    async def add_column(self, table_name: str, column_definition: Dict[str, Any]) -> None:
        await self._ensure_metadata_table()
        table = await self.get_table(table_name)
        column_sql = self._build_column_definition(column_definition)
        column_name = column_definition.get("name")

        async with self._db.transaction() as conn:
            await conn.execute(f'ALTER TABLE "{table["name"]}" ADD COLUMN {column_sql}')

            updated_schema = dict(table["schema"])
            columns = list(updated_schema.get("columns", []))
            columns.append(column_definition)
            updated_schema["columns"] = columns

            await conn.execute(
                "UPDATE tables SET schema = $1::jsonb WHERE name = $2",
                json.dumps(updated_schema),
                table["name"],
            )

    async def delete_column(self, table_name: str, column_name: str) -> None:
        await self._ensure_metadata_table()
        table = await self.get_table(table_name)
        normalized = column_name.strip()
        columns = table["schema"].get("columns", [])
        if normalized not in {col["name"] for col in columns}:
            raise TableColumnError(f"Column '{normalized}' not found in table '{table['name']}'")

        primary_keys = [col["name"] for col in columns if col.get("primary_key")]
        if normalized in primary_keys:
            raise TableColumnError("Cannot remove primary key column")

        async with self._db.transaction() as conn:
            await conn.execute(f'ALTER TABLE "{table["name"]}" DROP COLUMN "{normalized}"')

            updated_columns = [col for col in columns if col["name"] != normalized]
            updated_schema = dict(table["schema"])
            updated_schema["columns"] = updated_columns

            await conn.execute(
                "UPDATE tables SET schema = $1::jsonb WHERE name = $2",
                json.dumps(updated_schema),
                table["name"],
            )

    async def update_column(self, table_name: str, column_name: str, updates: Dict[str, Any]) -> None:
        if not updates:
            raise TableValidationError("Column update payload cannot be empty")

        await self._ensure_metadata_table()
        table = await self.get_table(table_name)
        normalized = column_name.strip()
        columns = table["schema"].get("columns", [])
        column_lookup = {col["name"]: col for col in columns}

        if normalized not in column_lookup:
            raise TableColumnError(f"Column '{normalized}' not found in table '{table['name']}'")

        target_column = dict(column_lookup[normalized])
        statements: List[str] = []
        current_name = normalized

        new_name = updates.get("new_name")
        if new_name and new_name != normalized:
            validated_new_name = self._normalize_table_name(new_name)
            statements.append(
                f'ALTER TABLE "{table["name"]}" RENAME COLUMN "{current_name}" TO "{validated_new_name}"'
            )
            current_name = validated_new_name
            target_column["name"] = validated_new_name

        if "type" in updates and updates["type"]:
            statements.append(
                f'ALTER TABLE "{table["name"]}" ALTER COLUMN "{current_name}" TYPE {updates["type"]}'
            )
            target_column["type"] = updates["type"]

        if "nullable" in updates:
            if updates["nullable"]:
                statements.append(
                    f'ALTER TABLE "{table["name"]}" ALTER COLUMN "{current_name}" DROP NOT NULL'
                )
            else:
                statements.append(
                    f'ALTER TABLE "{table["name"]}" ALTER COLUMN "{current_name}" SET NOT NULL'
                )
            target_column["nullable"] = updates["nullable"]

        if "default" in updates:
            default_value = updates["default"]
            if default_value is None:
                statements.append(
                    f'ALTER TABLE "{table["name"]}" ALTER COLUMN "{current_name}" DROP DEFAULT'
                )
                target_column.pop("default", None)
            else:
                statements.append(
                    f'ALTER TABLE "{table["name"]}" ALTER COLUMN "{current_name}" SET DEFAULT {self._format_default(default_value)}'
                )
                target_column["default"] = default_value

        if not statements:
            return

        async with self._db.transaction() as conn:
            for statement in statements:
                await conn.execute(statement)

            updated_columns = []
            for col in columns:
                if col["name"] == column_name:
                    updated_columns.append(target_column)
                elif new_name and col["name"] == new_name:
                    # Already updated
                    continue
                else:
                    updated_columns.append(col)

            updated_schema = dict(table["schema"])
            updated_schema["columns"] = updated_columns

            await conn.execute(
                "UPDATE tables SET schema = $1::jsonb WHERE name = $2",
                json.dumps(updated_schema),
                table["name"],
            )

    async def update_table_metadata(
        self,
        table_name: str,
        *,
        new_name: Optional[str] = None,
        description: Optional[str] = None,
        public: Optional[bool] = None,
    ) -> Dict[str, Any]:
        await self._ensure_metadata_table()
        table = await self.get_table(table_name)
        target_name = self._normalize_table_name(new_name) if new_name else table["name"]

        async with self._db.transaction() as conn:
            if new_name and target_name != table["name"]:
                if await self._table_exists(target_name):
                    raise TableAlreadyExistsError(f"Table '{target_name}' already exists")
                await conn.execute(
                    f'ALTER TABLE "{table["name"]}" RENAME TO "{target_name}"'
                )

            await conn.execute(
                """
                UPDATE tables
                SET name = $1,
                    description = COALESCE($2, description),
                    public = COALESCE($3, public)
                WHERE name = $4
                """,
                target_name,
                description,
                public,
                table["name"],
            )

        return await self.get_table(target_name)

    async def _table_exists(self, table_name: str) -> bool:
        await self._ensure_metadata_table()
        async with self._db.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1)",
                table_name,
            )
        return bool(exists)

    def _normalize_table_definition(self, definition: Dict[str, Any]) -> Dict[str, Any]:
        if "name" not in definition:
            raise TableValidationError("Table definition requires a 'name' field")
        if "schema" not in definition:
            raise TableValidationError("Table definition requires a 'schema' field")

        name = self._normalize_table_name(definition["name"])
        schema = definition["schema"]

        if not isinstance(schema, dict):
            raise TableValidationError("Schema must be a dictionary")

        columns = schema.get("columns")
        if not columns or not isinstance(columns, list):
            raise TableValidationError("Schema must include a non-empty 'columns' list")

        seen_columns = set()
        for column in columns:
            if "name" not in column or "type" not in column:
                raise TableValidationError("Each column requires 'name' and 'type'")
            column_name = column["name"]
            if column_name in seen_columns:
                raise TableValidationError(f"Duplicate column '{column_name}' in schema")
            seen_columns.add(column_name)

        return {
            "name": name,
            "schema": schema,
            "public": bool(definition.get("public", False)),
            "description": definition.get("description"),
            "metadata": definition.get("metadata", {}),
        }

    def _normalize_table_name(self, name: str) -> str:
        if not isinstance(name, str) or not name:
            raise TableValidationError("Table name must be a non-empty string")
        trimmed = name.strip()
        if not TABLE_NAME_PATTERN.match(trimmed):
            raise TableValidationError(
                "Table names must start with a letter or underscore and contain only alphanumeric characters or underscores"
            )
        return trimmed

    def _build_create_statements(self, table_name: str, schema: Dict[str, Any]) -> Tuple[str, List[str]]:
        if schema is None:
            raise TableValidationError("Schema cannot be None")
        
        column_definitions = []
        primary_keys: List[str] = []

        for column in schema.get("columns", []):
            column_definitions.append(self._build_column_definition(column))
            if column.get("primary_key"):
                primary_keys.append(column["name"])

        create_sql = f'CREATE TABLE "{table_name}" ({", ".join(column_definitions)}'
        if primary_keys:
            pk_columns = ", ".join(f'"{col}"' for col in primary_keys)
            create_sql += f", PRIMARY KEY ({pk_columns})"
        create_sql += ")"

        index_statements: List[str] = []
        indexes = schema.get("indexes") or []
        for index in indexes:
            index_name = index.get("name") or f"idx_{table_name}_{'_'.join(index.get('columns', []))}"
            columns = index.get("columns") or []
            if not columns:
                continue
            unique = "UNIQUE " if index.get("unique") else ""
            column_sql = ", ".join(f'"{col}"' for col in columns)
            index_statements.append(
                f'CREATE {unique}INDEX IF NOT EXISTS "{index_name}" ON "{table_name}" ({column_sql})'
            )

        return create_sql, index_statements

    def _build_column_definition(self, column: Dict[str, Any]) -> str:
        name = column.get("name")
        if not name:
            raise TableValidationError("Column is missing required 'name'")
        col_type = column.get("type")
        if not col_type:
            raise TableValidationError(f"Column '{name}' is missing required 'type'")

        parts = [f'"{name}" {col_type}']
        if not column.get("nullable", True):
            parts.append("NOT NULL")
        if column.get("unique") and not column.get("primary_key"):
            parts.append("UNIQUE")
        default = column.get("default")
        
        # Auto-generate UUID for uuid type columns if no default is specified
        if col_type.lower() == "uuid" and default is None and column.get("primary_key"):
            parts.append("DEFAULT uuid_generate_v4()")
        elif default is not None:
            parts.append(f"DEFAULT {self._format_default(default)}")

        return " ".join(parts)

    def _format_default(self, default: Any) -> str:
        if isinstance(default, str):
            stripped = default.strip()
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(.*\)$", stripped):
                return stripped
            if stripped.startswith("'") and stripped.endswith("'"):
                return stripped
            return f"'{stripped}'"
        if isinstance(default, bool):
            return "TRUE" if default else "FALSE"
        if isinstance(default, (int, float)):
            return str(default)
        return json.dumps(default)

    def _convert_value_to_type(self, value: Any, column_def: Dict[str, Any]) -> Any:
        """Convert a value to the appropriate Python type based on the column definition."""
        if value is None:
            return None
        
        col_type = column_def.get("type", "").lower()
        
        # If value is already the correct type, return it
        if not isinstance(value, str):
            return value
        
        # Handle empty strings for nullable columns
        if value == "" and column_def.get("nullable", True):
            return None
        
        try:
            # Integer types
            if col_type in ("integer", "int", "int4", "smallint", "int2", "bigint", "int8", "serial", "serial4", "bigserial", "serial8", "smallserial", "serial2"):
                return int(value)
            
            # Floating point types
            if col_type in ("real", "float4", "double precision", "float8", "numeric", "decimal"):
                return float(value)
            
            # Boolean type
            if col_type in ("boolean", "bool"):
                if isinstance(value, bool):
                    return value
                lower_value = value.lower()
                if lower_value in ("true", "t", "yes", "y", "1"):
                    return True
                if lower_value in ("false", "f", "no", "n", "0"):
                    return False
                raise ValueError(f"Cannot convert '{value}' to boolean")
            
            # JSON/JSONB types - asyncpg expects JSON as a string
            if col_type in ("json", "jsonb"):
                if isinstance(value, str):
                    # Validate it's valid JSON by parsing and re-serializing
                    json.loads(value)  # Will raise JSONDecodeError if invalid
                    return value
                # If it's already a dict/list, convert to JSON string
                return json.dumps(value)
            
            # UUID type
            if col_type == "uuid":
                # Validate UUID format
                import uuid as uuid_lib
                uuid_lib.UUID(value)
                return value
            
            # Date type
            if col_type == "date":
                if isinstance(value, date):
                    return value
                # Try to parse ISO format date (YYYY-MM-DD)
                return datetime.strptime(value, "%Y-%m-%d").date()
            
            # Time types (with or without time zone)
            if col_type in ("time", "time without time zone", "timetz", "time with time zone"):
                if isinstance(value, time):
                    return value
                # Try to parse ISO format time (HH:MM:SS or HH:MM:SS.ffffff)
                parsed = datetime.strptime(value.split('+')[0].split('-')[0].strip(), "%H:%M:%S" if value.count(':') == 2 and '.' not in value else "%H:%M:%S.%f")
                return parsed.time()
            
            # Timestamp types (with or without time zone)
            if col_type in ("timestamp", "timestamp without time zone", "timestamptz", "timestamp with time zone"):
                if isinstance(value, datetime):
                    return value
                # Try to parse ISO format timestamp
                # Support formats: YYYY-MM-DD HH:MM:SS or YYYY-MM-DDTHH:MM:SS
                value_clean = value.replace('T', ' ').split('+')[0].split('-', 3)[-1] if value.count('-') > 2 else value.replace('T', ' ')
                try:
                    return datetime.fromisoformat(value)
                except:
                    # Fallback to manual parsing
                    if '.' in value_clean:
                        return datetime.strptime(value_clean.split('+')[0].split('Z')[0].strip(), "%Y-%m-%d %H:%M:%S.%f")
                    else:
                        return datetime.strptime(value_clean.split('+')[0].split('Z')[0].strip(), "%Y-%m-%d %H:%M:%S")
            
            # Interval type - asyncpg expects timedelta objects for interval columns
            if col_type in ("interval",):
                from datetime import timedelta
                import re
                if isinstance(value, timedelta):
                    return value
                # Parse common interval string formats to timedelta
                # Format: "N days", "N hours", "N minutes", "N seconds", "N weeks"
                value_str = str(value).strip().lower()
                match = re.match(r'^(\d+)\s*(day|days|hour|hours|minute|minutes|second|seconds|week|weeks)$', value_str)
                if match:
                    num = int(match.group(1))
                    unit = match.group(2)
                    if 'day' in unit:
                        return timedelta(days=num)
                    elif 'hour' in unit:
                        return timedelta(hours=num)
                    elif 'minute' in unit:
                        return timedelta(minutes=num)
                    elif 'second' in unit:
                        return timedelta(seconds=num)
                    elif 'week' in unit:
                        return timedelta(weeks=num)
                # For complex intervals, return as string and let PostgreSQL parse it with explicit cast
                return value
            
            # Money type - asyncpg expects string, numeric, or float
            if col_type == "money":
                from decimal import Decimal
                if isinstance(value, (int, float, Decimal)):
                    return value
                # Remove currency symbols and commas
                clean_value = value.replace('$', '').replace(',', '').strip()
                # Return as string - asyncpg will handle conversion to money type
                # This avoids potential precision issues with Decimal
                return clean_value
            
            # Binary data type (bytea) - expect hex or base64 encoded strings
            if col_type == "bytea":
                # Try to decode as hex first (prefixed with \x)
                if value.startswith('\\x'):
                    return bytes.fromhex(value[2:])
                # Try base64
                import base64
                try:
                    return base64.b64decode(value)
                except:
                    # If neither works, encode the string as UTF-8 bytes
                    return value.encode('utf-8')
            
            # Network address types
            if col_type in ("inet", "cidr"):
                # Validate IP address format (IPv4 or IPv6 with optional CIDR notation)
                import ipaddress
                # For inet: can be '192.168.1.1' or '192.168.1.1/24'
                # For cidr: must be network address like '192.168.1.0/24'
                ipaddress.ip_network(value, strict=False if col_type == "inet" else True)
                return value
            
            # MAC address types
            if col_type in ("macaddr", "macaddr8"):
                # Validate MAC address format and normalize
                # Accepted formats: 08:00:2b:01:02:03, 08-00-2b-01-02-03, etc.
                import re
                # Remove all separators and validate hex digits
                mac_clean = re.sub(r'[:\-\.]', '', value)
                expected_len = 12 if col_type == "macaddr" else 16
                if len(mac_clean) != expected_len or not all(c in '0123456789abcdefABCDEF' for c in mac_clean):
                    raise ValueError(f"Invalid MAC address format: {value}")
                return value
            
            # Bit string types
            if col_type in ("bit", "bit varying", "varbit"):
                # Expect binary string like '101010' or 'B101010'
                if value.startswith('B'):
                    value = value[1:]
                # Validate it's all 0s and 1s
                if not all(c in '01' for c in value):
                    raise ValueError(f"Bit string must contain only 0 and 1: {value}")
                return value
            
            # Array types - parse array notation like '{1,2,3}' or '["a","b","c"]'
            if col_type.endswith('[]') or col_type.startswith('_'):
                # PostgreSQL arrays can be in format: '{1,2,3}' or '{"a","b","c"}'
                # Extract the base type
                base_type = col_type.rstrip('[]').lstrip('_')
                
                # Try to parse JSON array first
                try:
                    arr = json.loads(value) if not value.startswith('{') else None
                    if arr is not None and isinstance(arr, list):
                        # Convert each element
                        return [self._convert_value_to_type(
                            item, 
                            {"type": base_type, "nullable": True, "name": "array_element"}
                        ) for item in arr]
                except:
                    pass
                
                # Try PostgreSQL array format: {1,2,3}
                if value.startswith('{') and value.endswith('}'):
                    # Parse PostgreSQL array notation
                    inner = value[1:-1]
                    if not inner:
                        return []
                    # Split by comma (basic parsing, doesn't handle nested arrays perfectly)
                    elements = [e.strip().strip('"') for e in inner.split(',')]
                    return [self._convert_value_to_type(
                        elem, 
                        {"type": base_type, "nullable": True, "name": "array_element"}
                    ) for elem in elements]
                
                # If it looks like a Python list string, eval it safely
                return json.loads(value) if '[' in value else [value]
            
            # Geometric types - use asyncpg's special type classes
            if col_type == "point":
                # Parse string like "(1.5,2.5)" or "1.5,2.5" into asyncpg.Point
                import asyncpg
                clean = value.strip().strip('()')
                parts = [p.strip() for p in clean.split(',')]
                if len(parts) != 2:
                    raise ValueError(f"Invalid point format: {value}. Expected (x,y)")
                return asyncpg.Point(float(parts[0]), float(parts[1]))
            
            if col_type == "circle":
                # Parse string like "<(0,0),5>" or "((0,0),5)" into asyncpg.Circle
                import asyncpg
                clean = value.strip().lstrip('<(').rstrip('>')
                # Split by last comma to separate center from radius
                if '),(' in clean:
                    raise ValueError(f"Invalid circle format: {value}. Expected <(x,y),r>")
                # Format: (x,y),r
                parts = clean.split('),(')
                if len(parts) == 2:
                    center_str = parts[0].strip('(')
                    radius_str = parts[1].strip(')')
                else:
                    # Try alternate format: x,y),r
                    match = value.strip().replace('<', '').replace('>', '').strip('()')
                    parts = match.rsplit(',', 1)
                    if len(parts) != 2:
                        raise ValueError(f"Invalid circle format: {value}. Expected <(x,y),r>")
                    center_str = parts[0].strip('()')
                    radius_str = parts[1].strip()
                
                center_parts = [p.strip() for p in center_str.split(',')]
                if len(center_parts) != 2:
                    raise ValueError(f"Invalid circle format: {value}. Expected <(x,y),r>")
                center = asyncpg.Point(float(center_parts[0]), float(center_parts[1]))
                return asyncpg.Circle(center, float(radius_str))
            
            if col_type == "box":
                # Parse string like "((1,1),(0,0))" or "(1,1),(0,0)" into asyncpg.Box
                import asyncpg
                clean = value.strip().strip('()')
                # Split into two points
                parts = clean.split('),(')
                if len(parts) != 2:
                    raise ValueError(f"Invalid box format: {value}. Expected ((x1,y1),(x2,y2))")
                p1_str = parts[0].strip('()')
                p2_str = parts[1].strip('()')
                p1_parts = [float(p.strip()) for p in p1_str.split(',')]
                p2_parts = [float(p.strip()) for p in p2_str.split(',')]
                if len(p1_parts) != 2 or len(p2_parts) != 2:
                    raise ValueError(f"Invalid box format: {value}. Expected ((x1,y1),(x2,y2))")
                # asyncpg.Box expects (high, low) where high and low are sequences
                return asyncpg.Box(p1_parts, p2_parts)
            
            if col_type == "lseg":
                # Parse string like "[(1,1),(0,0)]" or "((1,1),(0,0))" into asyncpg.LineSegment
                import asyncpg
                clean = value.strip().strip('[]()') 
                parts = clean.split('),(')
                if len(parts) != 2:
                    raise ValueError(f"Invalid line segment format: {value}. Expected [(x1,y1),(x2,y2)]")
                p1_str = parts[0].strip('()')
                p2_str = parts[1].strip('()')
                p1_parts = [float(p.strip()) for p in p1_str.split(',')]
                p2_parts = [float(p.strip()) for p in p2_str.split(',')]
                if len(p1_parts) != 2 or len(p2_parts) != 2:
                    raise ValueError(f"Invalid line segment format: {value}. Expected [(x1,y1),(x2,y2)]")
                return asyncpg.LineSegment(p1_parts, p2_parts)
            
            if col_type in ("line", "path", "polygon"):
                # For now, return as string - these are more complex to parse
                # asyncpg should handle string format for these types
                return str(value).strip()
            
            # Text types - char, varchar, text
            if col_type in ("character", "char", "character varying", "varchar", "text", "name"):
                return value
            
            # Other types - return as is and let PostgreSQL handle it
            return value
            
        except (ValueError, json.JSONDecodeError) as e:
            raise TableValidationError(
                f"Cannot convert value '{value}' to type '{col_type}' for column '{column_def.get('name')}': {str(e)}"
            )

    def _row_to_dict(self, row) -> Dict[str, Any]:
        data = dict(row)
        data["owner_id"] = str(data.get("owner_id")) if data.get("owner_id") is not None else None
        schema = data.get("schema")
        if isinstance(schema, str):
            data["schema"] = json.loads(schema)
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            data["metadata"] = json.loads(metadata)
        if data.get("created_at") is not None:
            data["created_at"] = data["created_at"].isoformat()
        if data.get("updated_at") is not None:
            data["updated_at"] = data["updated_at"].isoformat()
        return data

    async def _refresh_row_count(self, table_name: str) -> None:
        async with self._db.acquire() as conn:
            count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
        await self._set_row_count(table_name, count)

    async def _set_row_count(self, table_name: str, count: int) -> None:
        async with self._db.acquire() as conn:
            await conn.execute(
                "UPDATE tables SET row_count = $1, updated_at = NOW() WHERE name = $2",
                count,
                table_name,
            )

    async def _ensure_metadata_table(self) -> None:
        if self._metadata_initialized:
            return

        async with self._db.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tables (
                    name VARCHAR(255) PRIMARY KEY,
                    schema JSONB NOT NULL,
                    public BOOLEAN NOT NULL DEFAULT FALSE,
                    owner_id VARCHAR(36) NOT NULL,
                    description TEXT,
                    metadata JSONB,
                    row_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        self._metadata_initialized = True

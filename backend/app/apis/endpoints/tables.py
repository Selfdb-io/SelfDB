from typing import Any, List, Dict, Optional, Union, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, inspect
import logging
from pydantic import BaseModel, Field

from ...models.user import User
from ..deps import get_db, get_current_active_user, get_current_user_or_anon, ANON_USER_ROLE
from ...db.notify import emit_table_notification, ensure_table_trigger_exists

# Configure logging
logger = logging.getLogger(__name__)

# Define models for table creation
class ColumnDefinition(BaseModel):
    name: str
    type: str
    nullable: bool = True
    default: Optional[str] = None
    primary_key: bool = False
    description: Optional[str] = None
    is_foreign_key: bool = False
    references_table: Optional[str] = None
    references_column: Optional[str] = None

class TableCreate(BaseModel):
    name: str
    description: Optional[str] = None
    columns: List[ColumnDefinition]
    if_not_exists: bool = False

class TableUpdate(BaseModel):
    new_name: Optional[str] = None
    description: Optional[str] = None

# Column operations

class ColumnCreate(BaseModel):
    column_name: str
    data_type: str
    is_nullable: str = "YES"
    column_default: Optional[str] = None
    character_maximum_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    column_description: Optional[str] = None

class ColumnUpdate(BaseModel):
    data_type: Optional[str] = None
    is_nullable: Optional[str] = None
    column_default: Optional[str] = None
    character_maximum_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    column_description: Optional[str] = None

router = APIRouter()

@router.get("", summary="Get all tables")
async def get_tables(
    db: AsyncSession = Depends(get_db),
    current_user_or_anon: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
) -> List[Dict[str, Any]]:
    """
    Get a list of all tables in the database.
    This endpoint supports anonymous access with a valid ANON_KEY.
    """
    # Check if user is authenticated (either as a user or with anon key)
    if current_user_or_anon is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        # Query to get all tables
        query = """
        SELECT
            table_name,
            pg_catalog.obj_description(pgc.oid, 'pg_class') as table_description,
            pg_total_relation_size(quote_ident(table_name)) as table_size,
            (SELECT count(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
        FROM information_schema.tables t
        JOIN pg_catalog.pg_class pgc ON pgc.relname = t.table_name
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        result = await db.execute(text(query))
        tables = [
            {
                "name": row.table_name,
                "description": row.table_description,
                "size": row.table_size,
                "column_count": row.column_count
            }
            for row in result.fetchall()
        ]
        return tables
    except Exception as e:
        logger.error(f"Error getting tables: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{table_name}", summary="Get table details")
async def get_table_details(
    table_name: str,
    db: AsyncSession = Depends(get_db),
    current_user_or_anon: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
) -> Dict[str, Any]:
    """
    Get detailed information about a specific table.
    This endpoint supports anonymous access with a valid ANON_KEY.
    """
    # Check if user is authenticated (either as a user or with anon key)
    if current_user_or_anon is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        # Check if table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_name})
        exists = result.scalar()

        if not exists:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        # Get columns
        columns_query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            pg_catalog.col_description(
                (SELECT oid FROM pg_catalog.pg_class WHERE relname = :table_name),
                ordinal_position
            ) as column_description
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = :table_name
        ORDER BY ordinal_position;
        """
        result = await db.execute(text(columns_query), {"table_name": table_name})
        columns = [dict(row._mapping) for row in result.fetchall()]

        # Get primary key
        pk_query = """
        SELECT
            a.attname as column_name
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        JOIN pg_class c ON c.oid = i.indrelid
        WHERE c.relname = :table_name
        AND i.indisprimary;
        """
        result = await db.execute(text(pk_query), {"table_name": table_name})
        primary_keys = [row.column_name for row in result.fetchall()]

        # Get foreign keys
        fk_query = """
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = :table_name;
        """
        result = await db.execute(text(fk_query), {"table_name": table_name})
        foreign_keys = [dict(row._mapping) for row in result.fetchall()]

        # Get indexes
        indexes_query = """
        SELECT
            i.relname AS index_name,
            a.attname AS column_name,
            ix.indisunique AS is_unique,
            ix.indisprimary AS is_primary
        FROM
            pg_class t,
            pg_class i,
            pg_index ix,
            pg_attribute a
        WHERE
            t.oid = ix.indrelid
            AND i.oid = ix.indexrelid
            AND a.attrelid = t.oid
            AND a.attnum = ANY(ix.indkey)
            AND t.relkind = 'r'
            AND t.relname = :table_name
        ORDER BY
            i.relname;
        """
        result = await db.execute(text(indexes_query), {"table_name": table_name})
        indexes = [dict(row._mapping) for row in result.fetchall()]

        # Get table description
        desc_query = """
        SELECT pg_catalog.obj_description(pgc.oid, 'pg_class') as table_description
        FROM pg_catalog.pg_class pgc
        WHERE pgc.relname = :table_name;
        """
        result = await db.execute(text(desc_query), {"table_name": table_name})
        description = result.scalar() or ""

        # Get row count (approximate)
        count_query = f"SELECT count(*) FROM \"{table_name}\";"
        result = await db.execute(text(count_query))
        row_count = result.scalar()

        return {
            "name": table_name,
            "description": description,
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "row_count": row_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table details: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{table_name}/data", summary="Get table data")
async def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    order_by: Optional[str] = None,
    filter_column: Optional[str] = None,
    filter_value: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user_or_anon: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
) -> Dict[str, Any]:
    """
    Get data from a table with pagination and filtering.
    This endpoint supports anonymous access with a valid ANON_KEY.
    """
    # Check if user is authenticated (either as a user or with anon key)
    if current_user_or_anon is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        # Check if table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_name})
        exists = result.scalar()

        if not exists:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        # Build the query
        base_query = f'SELECT * FROM "{table_name}"'
        count_query = f'SELECT COUNT(*) FROM "{table_name}"'

        # Add filtering if specified
        where_clause = ""
        params = {}
        if filter_column and filter_value is not None:
            # Check if column exists
            column_check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = :table_name
                AND column_name = :column_name
            );
            """
            result = await db.execute(
                text(column_check_query),
                {"table_name": table_name, "column_name": filter_column}
            )
            column_exists = result.scalar()

            if not column_exists:
                raise HTTPException(status_code=400, detail=f"Column '{filter_column}' not found in table '{table_name}'")

            where_clause = f' WHERE "{filter_column}"::text ILIKE :filter_value'
            params["filter_value"] = f"%{filter_value}%"

        # Add ordering if specified
        order_clause = ""
        if order_by:
            # Parse order_by format: column_name:asc or column_name:desc
            parts = order_by.split(":")
            column = parts[0]
            direction = "ASC"
            if len(parts) > 1 and parts[1].upper() == "DESC":
                direction = "DESC"

            # Check if column exists
            column_check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = :table_name
                AND column_name = :column_name
            );
            """
            result = await db.execute(
                text(column_check_query),
                {"table_name": table_name, "column_name": column}
            )
            column_exists = result.scalar()

            if not column_exists:
                raise HTTPException(status_code=400, detail=f"Column '{column}' not found in table '{table_name}'")

            order_clause = f' ORDER BY "{column}" {direction}'

        # Add pagination
        offset = (page - 1) * page_size
        limit_clause = f" LIMIT {page_size} OFFSET {offset}"

        # Execute count query
        full_count_query = count_query + where_clause
        result = await db.execute(text(full_count_query), params)
        total_count = result.scalar()

        # Execute data query
        full_query = base_query + where_clause + order_clause + limit_clause
        result = await db.execute(text(full_query), params)
        rows = result.fetchall()

        # Convert rows to dictionaries
        data = [dict(row._mapping) for row in rows]

        # Get column information for metadata
        columns_query = """
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = :table_name
        ORDER BY ordinal_position;
        """
        result = await db.execute(text(columns_query), {"table_name": table_name})
        columns = [dict(row._mapping) for row in result.fetchall()]

        return {
            "data": data,
            "metadata": {
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size,
                "columns": columns
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table data: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/{table_name}/data", summary="Insert data into a table")
async def insert_table_data(
    table_name: str,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user_or_anon: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
) -> Dict[str, Any]:
    """
    Insert a new row into a table.
    This endpoint supports anonymous access with a valid ANON_KEY.
    """
    # Check if user is authenticated (either as a user or with anon key)
    if current_user_or_anon is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        # Check if table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_name})
        exists = result.scalar()

        if not exists:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        # Get columns to validate input
        columns_query = """
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = :table_name;
        """
        result = await db.execute(text(columns_query), {"table_name": table_name})
        columns = {row.column_name: row for row in result.fetchall()}

        # Validate input data
        for key in data:
            if key not in columns:
                raise HTTPException(status_code=400, detail=f"Column '{key}' does not exist in table '{table_name}'")

        # Build the insert query
        column_names = list(data.keys())
        placeholders = [f":{col}" for col in column_names]

        insert_query = f"""
        INSERT INTO "{table_name}" ({', '.join([f'"{col}"' for col in column_names])})
        VALUES ({', '.join(placeholders)})
        RETURNING *;
        """

        # Execute the query
        result = await db.execute(text(insert_query), data)
        inserted_row = result.fetchone()
        await db.commit()
        
        await emit_table_notification(db, table_name, "INSERT", dict(inserted_row._mapping))

        return dict(inserted_row._mapping)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error inserting data: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/{table_name}/data/{id}", summary="Update a row in a table")
async def update_table_data(
    table_name: str,
    id: str,
    data: Dict[str, Any],
    id_column: str = Query(..., description="The primary key column name"),
    db: AsyncSession = Depends(get_db),
    current_user_or_anon: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
) -> Dict[str, Any]:
    """
    Update a specific row in a table.
    This endpoint supports anonymous access with a valid ANON_KEY.
    """
    # Check if user is authenticated (either as a user or with anon key)
    if current_user_or_anon is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    """
    Update a specific row in a table.
    """
    try:
        # Check if table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_name})
        exists = result.scalar()

        if not exists:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        # Check if id_column exists
        column_check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = :table_name
            AND column_name = :column_name
        );
        """
        result = await db.execute(
            text(column_check_query),
            {"table_name": table_name, "column_name": id_column}
        )
        column_exists = result.scalar()

        if not column_exists:
            raise HTTPException(status_code=400, detail=f"Column '{id_column}' not found in table '{table_name}'")

        # Get columns to validate input
        columns_query = """
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = :table_name;
        """
        result = await db.execute(text(columns_query), {"table_name": table_name})
        columns = {row.column_name: row for row in result.fetchall()}

        # Validate input data
        for key in data:
            if key not in columns:
                raise HTTPException(status_code=400, detail=f"Column '{key}' does not exist in table '{table_name}'")

        # Check if row exists
        check_row_query = f"""
        SELECT EXISTS (
            SELECT FROM "{table_name}"
            WHERE "{id_column}" = :id
        );
        """
        result = await db.execute(text(check_row_query), {"id": id})
        row_exists = result.scalar()

        if not row_exists:
            raise HTTPException(status_code=404, detail=f"Row with {id_column}='{id}' not found in table '{table_name}'")

        # Build the update query
        set_clause = ", ".join([f'"{col}" = :{col}' for col in data.keys()])

        update_query = f"""
        UPDATE "{table_name}"
        SET {set_clause}
        WHERE "{id_column}" = :id
        RETURNING *;
        """

        # Execute the query
        params = {**data, "id": id}
        result = await db.execute(text(update_query), params)
        updated_row = result.fetchone()
        await db.commit()
        
        await emit_table_notification(
            db, 
            table_name, 
            "UPDATE", 
            dict(updated_row._mapping), 
            {"id": id, "id_column": id_column}
        )

        return dict(updated_row._mapping)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating data: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/{table_name}/data/{id}", summary="Delete a row from a table")
async def delete_table_data(
    table_name: str,
    id: str,
    id_column: str = Query(..., description="The primary key column name"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Delete a specific row from a table.
    """
    try:
        # Check if table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_name})
        exists = result.scalar()

        if not exists:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        # Check if id_column exists
        column_check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = :table_name
            AND column_name = :column_name
        );
        """
        result = await db.execute(
            text(column_check_query),
            {"table_name": table_name, "column_name": id_column}
        )
        column_exists = result.scalar()

        if not column_exists:
            raise HTTPException(status_code=400, detail=f"Column '{id_column}' not found in table '{table_name}'")

        # Check if row exists
        check_row_query = f"""
        SELECT EXISTS (
            SELECT FROM "{table_name}"
            WHERE "{id_column}" = :id
        );
        """
        result = await db.execute(text(check_row_query), {"id": id})
        row_exists = result.scalar()

        if not row_exists:
            raise HTTPException(status_code=404, detail=f"Row with {id_column}='{id}' not found in table '{table_name}'")

        # Build the delete query
        delete_query = f"""
        DELETE FROM "{table_name}"
        WHERE "{id_column}" = :id
        RETURNING *;
        """

        # Execute the query
        result = await db.execute(text(delete_query), {"id": id})
        deleted_row = result.fetchone()
        deleted_data = dict(deleted_row._mapping)
        await db.commit()
        
        await emit_table_notification(
            db, 
            table_name, 
            "DELETE", 
            None, 
            deleted_data
        )

        return {"message": f"Row with {id_column}='{id}' deleted successfully", "deleted_data": deleted_data}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting data: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{table_name}/sql", summary="Get SQL creation script for a table")
async def get_table_sql(
    table_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get the SQL script that can be used to recreate the table.
    """
    try:
        # Check if table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_name})
        exists = result.scalar()

        if not exists:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        # Get columns
        columns_query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = :table_name
        ORDER BY ordinal_position;
        """
        result = await db.execute(text(columns_query), {"table_name": table_name})
        columns = [dict(row._mapping) for row in result.fetchall()]

        # Get primary key
        pk_query = """
        SELECT
            a.attname as column_name
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        JOIN pg_class c ON c.oid = i.indrelid
        WHERE c.relname = :table_name
        AND i.indisprimary;
        """
        result = await db.execute(text(pk_query), {"table_name": table_name})
        primary_keys = [row.column_name for row in result.fetchall()]

        # Get foreign keys
        fk_query = """
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            tc.constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = :table_name;
        """
        result = await db.execute(text(fk_query), {"table_name": table_name})
        foreign_keys = [dict(row._mapping) for row in result.fetchall()]

        # Get indexes
        indexes_query = """
        SELECT
            i.relname AS index_name,
            array_agg(a.attname) AS column_names,
            ix.indisunique AS is_unique,
            ix.indisprimary AS is_primary
        FROM
            pg_class t,
            pg_class i,
            pg_index ix,
            pg_attribute a
        WHERE
            t.oid = ix.indrelid
            AND i.oid = ix.indexrelid
            AND a.attrelid = t.oid
            AND a.attnum = ANY(ix.indkey)
            AND t.relkind = 'r'
            AND t.relname = :table_name
        GROUP BY
            i.relname,
            ix.indisunique,
            ix.indisprimary
        ORDER BY
            i.relname;
        """
        result = await db.execute(text(indexes_query), {"table_name": table_name})
        indexes = [dict(row._mapping) for row in result.fetchall()]

        # Build CREATE TABLE statement
        column_definitions = []
        for column in columns:
            col_def = f'"{column["column_name"]}" {column["data_type"]}'

            # Add length for character types
            if column["character_maximum_length"] is not None:
                col_def = col_def.replace(column["data_type"], f"{column['data_type']}({column['character_maximum_length']})")

            # Add precision and scale for numeric types
            if column["numeric_precision"] is not None and column["numeric_scale"] is not None:
                if "numeric" in column["data_type"] or "decimal" in column["data_type"]:
                    col_def = col_def.replace(column["data_type"], f"{column['data_type']}({column['numeric_precision']},{column['numeric_scale']})")

            # Add NOT NULL constraint
            if column["is_nullable"] == "NO":
                col_def += " NOT NULL"

            # Add default value
            if column["column_default"] is not None:
                col_def += f" DEFAULT {column['column_default']}"

            column_definitions.append(col_def)

        # Add primary key constraint
        if primary_keys:
            pk_constraint = f"PRIMARY KEY ({', '.join([f'"{pk}"' for pk in primary_keys])})"
            column_definitions.append(pk_constraint)

        # Create the CREATE TABLE statement
        create_table_sql = f"""CREATE TABLE \"{table_name}\" (
    {',\n    '.join(column_definitions)}
);\n"""

        # Add foreign key constraints
        foreign_key_statements = []
        for fk in foreign_keys:
            fk_statement = f"""ALTER TABLE \"{table_name}\" ADD CONSTRAINT \"{fk['constraint_name']}\"
    FOREIGN KEY (\"{fk['column_name']}\") REFERENCES \"{fk['foreign_table_name']}\" (\"{fk['foreign_column_name']}\");"""
            foreign_key_statements.append(fk_statement)

        # Add indexes (excluding primary key indexes which are already handled)
        index_statements = []
        for idx in indexes:
            if not idx["is_primary"]:
                unique_clause = "UNIQUE " if idx["is_unique"] else ""
                columns_list = ", ".join([f'"{col}"' for col in idx["column_names"]])
                index_statement = f"CREATE {unique_clause}INDEX \"{idx['index_name']}\" ON \"{table_name}\" ({columns_list});"
                index_statements.append(index_statement)

        # Combine all SQL statements
        full_sql = create_table_sql
        if foreign_key_statements:
            full_sql += "\n\n-- Foreign Key Constraints\n" + "\n".join(foreign_key_statements)
        if index_statements:
            full_sql += "\n\n-- Indexes\n" + "\n".join(index_statements)

        return {
            "sql": full_sql
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating SQL for table: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def has_foreign_key_references(db: AsyncSession, table_name: str) -> bool:
    """
    Check if any tables have foreign key constraints referencing this table.
    """
    # Query to find foreign key constraints referencing the table
    query = """
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND ccu.table_name = :table_name
    );
    """
    result = await db.execute(text(query), {"table_name": table_name})
    return result.scalar()

@router.delete("/{table_name}", summary="Delete a table")
async def delete_table(
    table_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Delete a table from the database.
    Uses CASCADE option to delete the table and all dependent objects.
    """
    try:
        # Check if table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_name})
        exists = result.scalar()

        if not exists:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        await emit_table_notification(
            db, 
            table_name, 
            "DELETE", 
            {"message": f"Table '{table_name}' deleted"}
        )
        
        # Drop the table with CASCADE to handle dependencies
        drop_query = f"""
        DROP TABLE "{table_name}" CASCADE;
        """
        await db.execute(text(drop_query))
        await db.commit()

        return {"message": f"Table '{table_name}' deleted successfully"}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting table: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("", summary="Create a new table", status_code=201)
async def create_table(
    table_data: TableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Create a new database table.
    """
    try:
        # Check if table already exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_data.name})
        exists = result.scalar()

        if exists and not table_data.if_not_exists:
            raise HTTPException(status_code=400, detail=f"Table '{table_data.name}' already exists")
        elif exists and table_data.if_not_exists:
            return {"message": f"Table '{table_data.name}' already exists", "created": False}

        # Validate column names (no duplicates)
        column_names = [col.name for col in table_data.columns]
        if len(column_names) != len(set(column_names)):
            raise HTTPException(status_code=400, detail="Duplicate column names are not allowed")

        # Ensure at least one column is defined
        if not table_data.columns:
            raise HTTPException(status_code=400, detail="At least one column must be defined")

        # Build the CREATE TABLE query
        column_definitions = []
        primary_keys = []
        foreign_keys = []

        for column in table_data.columns:
            # Build column definition
            col_def = f'"{column.name}" {column.type}'

            if not column.nullable:
                col_def += " NOT NULL"

            if column.default is not None:
                col_def += f" DEFAULT {column.default}"

            if column.primary_key:
                primary_keys.append(column.name)

            # Handle foreign key constraints
            if column.is_foreign_key and column.references_table and column.references_column:
                # We'll add the foreign key constraint separately
                fk_constraint = f"FOREIGN KEY (\"{column.name}\") REFERENCES \"{column.references_table}\"(\"{column.references_column}\") ON DELETE CASCADE"
                foreign_keys.append(fk_constraint)

            column_definitions.append(col_def)

        # Add primary key constraint if specified
        if primary_keys:
            formatted_pks = [f'"{pk}"' for pk in primary_keys]
            pk_constraint = f"PRIMARY KEY ({', '.join(formatted_pks)})"
            column_definitions.append(pk_constraint)

        # Add foreign key constraints
        for fk in foreign_keys:
            column_definitions.append(fk)

        # Construct the final CREATE TABLE query
        if_not_exists_clause = "IF NOT EXISTS " if table_data.if_not_exists else ""
        create_table_query = f"""
        CREATE TABLE {if_not_exists_clause}"{table_data.name}" (
            {',\n            '.join(column_definitions)}
        );
        """

        # Execute the query
        await db.execute(text(create_table_query))

        # Add table description if provided
        if table_data.description:
            # PostgreSQL requires single quotes around the comment text, not parameter placeholders
            escaped_description = table_data.description.replace("'", "''")
            comment_query = f"""
            COMMENT ON TABLE "{table_data.name}" IS '{escaped_description}';
            """
            await db.execute(text(comment_query))

        # Add column descriptions if provided
        for column in table_data.columns:
            if column.description:
                # PostgreSQL requires single quotes around the comment text, not parameter placeholders
                escaped_description = column.description.replace("'", "''")
                col_comment_query = f"""
                COMMENT ON COLUMN "{table_data.name}"."{column.name}" IS '{escaped_description}';
                """
                await db.execute(text(col_comment_query))

        await db.commit()
        
        await ensure_table_trigger_exists(db, table_data.name)

        return {
            "message": f"Table '{table_data.name}' created successfully",
            "created": True,
            "name": table_data.name,
            "columns": [col.model_dump() for col in table_data.columns]
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating table: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/{table_name}/columns", summary="Add a column to a table")
async def add_column(
    table_name: str,
    column_data: ColumnCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Add a new column to an existing table."""
    try:
        # Check if table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_name})
        exists = result.scalar()

        if not exists:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        # Check if column already exists
        column_check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = :table_name
            AND column_name = :column_name
        );
        """
        result = await db.execute(
            text(column_check_query),
            {"table_name": table_name, "column_name": column_data.column_name}
        )
        column_exists = result.scalar()
        
        if column_exists:
            raise HTTPException(status_code=400, detail=f"Column '{column_data.column_name}' already exists in table '{table_name}'")
        
        # Build SQL for column creation
        column_type = column_data.data_type
        
        # Add length/precision for certain data types
        if column_data.character_maximum_length and column_data.data_type in ["VARCHAR", "CHAR"]:
            column_type = f"{column_data.data_type}({column_data.character_maximum_length})"
        elif column_data.numeric_precision and column_data.data_type in ["NUMERIC", "DECIMAL"]:
            scale = column_data.numeric_scale or 0
            column_type = f"{column_data.data_type}({column_data.numeric_precision}, {scale})"
        
        # Build nullable constraint
        nullable = "" if column_data.is_nullable == "YES" else "NOT NULL"
        
        # Build default value
        default_value = ""
        if column_data.column_default is not None:
            default_value = f"DEFAULT {column_data.column_default}"
        
        # Create ALTER TABLE query
        alter_query = f"""
        ALTER TABLE "{table_name}" 
        ADD COLUMN "{column_data.column_name}" {column_type} {nullable} {default_value};
        """
        
        # Execute ALTER TABLE query
        await db.execute(text(alter_query))
        
        # Add column comment if provided
        if column_data.column_description:
            # PostgreSQL requires single quotes around the comment text, not parameter placeholders
            escaped_description = column_data.column_description.replace("'", "''")
            comment_query = f"""
            COMMENT ON COLUMN "{table_name}"."{column_data.column_name}" IS '{escaped_description}';
            """
            await db.execute(text(comment_query))
        
        await db.commit()
        
        return {
            "message": f"Column '{column_data.column_name}' added to table '{table_name}'",
            "column_name": column_data.column_name,
            "data_type": column_data.data_type
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding column: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/{table_name}/columns/{column_name}", summary="Update a column in a table")
async def update_column(
    table_name: str,
    column_name: str,
    column_data: ColumnUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Update an existing column in a table."""
    try:
        # Check if table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_name})
        exists = result.scalar()

        if not exists:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        # Check if column exists
        column_check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = :table_name
            AND column_name = :column_name
        );
        """
        result = await db.execute(
            text(column_check_query),
            {"table_name": table_name, "column_name": column_name}
        )
        column_exists = result.scalar()
        
        if not column_exists:
            raise HTTPException(status_code=404, detail=f"Column '{column_name}' not found in table '{table_name}'")
        
        # Get current column details
        current_column_query = """
        SELECT
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = :table_name
        AND column_name = :column_name;
        """
        result = await db.execute(
            text(current_column_query),
            {"table_name": table_name, "column_name": column_name}
        )
        current_column = result.fetchone()
        
        # Start building ALTER TABLE statements
        alter_statements = []
        
        # Handle data type changes
        if column_data.data_type:
            column_type = column_data.data_type
            
            # Add length/precision for certain data types
            if column_data.character_maximum_length and column_data.data_type in ["VARCHAR", "CHAR"]:
                column_type = f"{column_data.data_type}({column_data.character_maximum_length})"
            elif column_data.numeric_precision and column_data.data_type in ["NUMERIC", "DECIMAL"]:
                scale = column_data.numeric_scale or 0
                column_type = f"{column_data.data_type}({column_data.numeric_precision}, {scale})"
            
            alter_statements.append(f'ALTER COLUMN "{column_name}" TYPE {column_type} USING "{column_name}"::{column_type}')
        
        # Handle nullable changes
        if column_data.is_nullable is not None:
            if column_data.is_nullable == "YES":
                alter_statements.append(f'ALTER COLUMN "{column_name}" DROP NOT NULL')
            else:
                alter_statements.append(f'ALTER COLUMN "{column_name}" SET NOT NULL')
        
        # Handle default value changes
        if column_data.column_default is not None:
            if column_data.column_default == "":
                alter_statements.append(f'ALTER COLUMN "{column_name}" DROP DEFAULT')
            else:
                alter_statements.append(f'ALTER COLUMN "{column_name}" SET DEFAULT {column_data.column_default}')
        
        # Execute ALTER TABLE statement if any changes
        if alter_statements:
            alter_query = f"""
            ALTER TABLE "{table_name}" 
            {', '.join(alter_statements)};
            """
            await db.execute(text(alter_query))
        
        # Update column comment if provided
        if column_data.column_description is not None:
            # PostgreSQL requires single quotes around the comment text, not parameter placeholders
            escaped_description = column_data.column_description.replace("'", "''")
            comment_query = f"""
            COMMENT ON COLUMN "{table_name}"."{column_name}" IS '{escaped_description}';
            """
            await db.execute(text(comment_query))
        
        await db.commit()
        
        return {
            "message": f"Column '{column_name}' updated in table '{table_name}'",
            "column_name": column_name
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating column: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/{table_name}/columns/{column_name}", summary="Delete a column from a table")
async def delete_column(
    table_name: str,
    column_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Delete a column from a table."""
    try:
        # Check if table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_name})
        exists = result.scalar()

        if not exists:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        # Check if column exists
        column_check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = :table_name
            AND column_name = :column_name
        );
        """
        result = await db.execute(
            text(column_check_query),
            {"table_name": table_name, "column_name": column_name}
        )
        column_exists = result.scalar()
        
        if not column_exists:
            raise HTTPException(status_code=404, detail=f"Column '{column_name}' not found in table '{table_name}'")
        
        # Check if column is a primary key
        pk_query = """
        SELECT EXISTS (
            SELECT FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            JOIN pg_class c ON c.oid = i.indrelid
            WHERE c.relname = :table_name
            AND a.attname = :column_name
            AND i.indisprimary
        );
        """
        result = await db.execute(text(pk_query), {"table_name": table_name, "column_name": column_name})
        is_primary_key = result.scalar()
        
        if is_primary_key:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete column '{column_name}' because it is part of the primary key"
            )
        
        # Create and execute DROP COLUMN statement
        drop_query = f"""
        ALTER TABLE "{table_name}" DROP COLUMN "{column_name}";
        """
        await db.execute(text(drop_query))
        
        await db.commit()
        
        return {
            "message": f"Column '{column_name}' deleted from table '{table_name}'",
            "column_name": column_name
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting column: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/{table_name}", summary="Update table name or description")
async def update_table(
    table_name: str,
    table_data: TableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Update a table's name and/or description."""
    try:
        # Check if table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
        """
        result = await db.execute(text(check_query), {"table_name": table_name})
        exists = result.scalar()

        if not exists:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        changes_made = False
        response_data = {"message": f"Table '{table_name}' updated successfully"}
        
        # Handle table renaming
        if table_data.new_name and table_data.new_name != table_name:
            # Check if the new name already exists
            new_name_check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = :new_name
            );
            """
            result = await db.execute(text(new_name_check_query), {"new_name": table_data.new_name})
            new_name_exists = result.scalar()
            
            if new_name_exists:
                raise HTTPException(status_code=400, detail=f"Table with name '{table_data.new_name}' already exists")
            
            # Rename the table
            rename_query = f"""
            ALTER TABLE "{table_name}" RENAME TO "{table_data.new_name}";
            """
            await db.execute(text(rename_query))
            changes_made = True
            response_data["old_name"] = table_name
            response_data["new_name"] = table_data.new_name
        
        # Target table name (either the original or the newly renamed one)
        target_table = table_data.new_name if table_data.new_name else table_name
        
        # Handle description update
        if table_data.description is not None:
            # PostgreSQL requires single quotes around the comment text
            escaped_description = table_data.description.replace("'", "''")
            comment_query = f"""
            COMMENT ON TABLE "{target_table}" IS '{escaped_description}';
            """
            await db.execute(text(comment_query))
            changes_made = True
            response_data["description"] = table_data.description
        
        if not changes_made:
            return {"message": "No changes were made to the table"}
        
        await db.commit()
        return response_data
    
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating table: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from ...models.user import User
from ..deps import get_db, get_current_active_user

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("", summary="Get database schema")
async def get_schema(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get complete database schema information.
    """
    try:
        # Get tables
        tables_query = """
        SELECT
            table_name,
            pg_catalog.obj_description(pgc.oid, 'pg_class') as table_description
        FROM information_schema.tables t
        JOIN pg_catalog.pg_class pgc ON pgc.relname = t.table_name
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        result = await db.execute(text(tables_query))
        tables = [dict(row._mapping) for row in result.fetchall()]

        # Get columns for each table
        for table in tables:
            columns_query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                pg_catalog.col_description(
                    (SELECT oid FROM pg_catalog.pg_class WHERE relname = :table_name),
                    ordinal_position
                ) as column_description
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = :table_name
            ORDER BY ordinal_position;
            """
            result = await db.execute(text(columns_query), {"table_name": table["table_name"]})
            table["columns"] = [dict(row._mapping) for row in result.fetchall()]

            # Get primary keys
            pk_query = """
            SELECT
                a.attname as column_name
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = quote_ident(:table_name)::regclass
            AND i.indisprimary;
            """
            result = await db.execute(text(pk_query), {"table_name": table["table_name"]})
            table["primary_keys"] = [row.column_name for row in result.fetchall()]

        # Get foreign keys
        fk_query = """
        SELECT
            tc.table_name,
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
        AND tc.table_schema = 'public';
        """
        result = await db.execute(text(fk_query))
        foreign_keys = [dict(row._mapping) for row in result.fetchall()]

        return {
            "tables": tables,
            "foreign_keys": foreign_keys
        }
    except Exception as e:
        logger.error(f"Error getting schema: {e}", exc_info=True)
        # Provide a more user-friendly error message
        error_message = str(e)
        if "quote_ident" in error_message:
            error_message = "Error accessing database schema. Please ensure the database is properly set up."
        raise HTTPException(status_code=500, detail=f"Database error: {error_message}")

@router.get("/visualization", summary="Get schema visualization data")
async def get_schema_visualization(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get schema data formatted for visualization.
    """
    try:
        # Get tables as nodes
        tables_query = """
        SELECT
            table_name as id,
            table_name as label,
            pg_catalog.obj_description(pgc.oid, 'pg_class') as description
        FROM information_schema.tables t
        JOIN pg_catalog.pg_class pgc ON pgc.relname = t.table_name
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        result = await db.execute(text(tables_query))
        nodes = [dict(row._mapping) for row in result.fetchall()]

        # Add column information to nodes
        for node in nodes:
            columns_query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                pg_catalog.col_description(
                    (SELECT oid FROM pg_catalog.pg_class WHERE relname = :table_name),
                    ordinal_position
                ) as column_description
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = :table_name
            ORDER BY ordinal_position;
            """
            result = await db.execute(text(columns_query), {"table_name": node["id"]})
            node["columns"] = [dict(row._mapping) for row in result.fetchall()]

            # Get primary keys
            pk_query = """
            SELECT
                a.attname as column_name
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = quote_ident(:table_name)::regclass
            AND i.indisprimary;
            """
            result = await db.execute(text(pk_query), {"table_name": node["id"]})
            primary_keys = [row.column_name for row in result.fetchall()]
            node["primary_keys"] = primary_keys

            # Mark primary key columns
            for column in node["columns"]:
                column["is_primary_key"] = column["column_name"] in primary_keys

        # Get foreign keys as edges
        edges_query = """
        SELECT
            tc.constraint_name as id,
            kcu.table_name as source,
            ccu.table_name as target,
            kcu.column_name as source_column,
            ccu.column_name as target_column
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public';
        """
        result = await db.execute(text(edges_query))
        edges = [dict(row._mapping) for row in result.fetchall()]

        # Format edges for visualization
        for edge in edges:
            edge["label"] = f"{edge['source_column']} → {edge['target_column']}"
            edge["source_handle"] = edge["source_column"]
            edge["target_handle"] = edge["target_column"]

        return {
            "nodes": nodes,
            "edges": edges
        }
    except Exception as e:
        logger.error(f"Error getting schema visualization: {e}", exc_info=True)
        # Provide a more user-friendly error message
        error_message = str(e)
        if "quote_ident" in error_message:
            error_message = "Error accessing database schema. Please ensure the database is properly set up."
        raise HTTPException(status_code=500, detail=f"Database error: {error_message}")

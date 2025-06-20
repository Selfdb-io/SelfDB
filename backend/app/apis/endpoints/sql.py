from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging
from datetime import datetime
import uuid

from ...models.user import User
from ..deps import get_db, get_current_active_user

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/query", summary="Execute SQL query")
async def execute_sql_query(
    query: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Execute a SQL query and return the results.
    Supports multiple SQL statements separated by semicolons.
    Handles dollar-quoted blocks (e.g., $$ ... $$) as a single statement.
    """
    try:
        # Split the query into multiple statements, preserving dollar-quoted blocks
        statements = []
        if "$$" in query:
            # Use a more sophisticated approach to split statements with dollar quotes
            current_statement = ""
            in_dollar_quotes = False
            for line in query.split("\n"):
                stripped_line = line.strip()

                # Check for dollar quote boundaries
                if "$$" in stripped_line:
                    # Count occurrences of $$ in this line
                    dollar_count = stripped_line.count("$$")
                    # If odd number of $$, toggle the in_dollar_quotes flag
                    if dollar_count % 2 == 1:
                        in_dollar_quotes = not in_dollar_quotes

                # Add the line to the current statement
                current_statement += line + "\n"

                # If we're not in dollar quotes and the line ends with a semicolon
                if not in_dollar_quotes and stripped_line.endswith(";"):
                    # We have a complete statement
                    statements.append(current_statement.strip())
                    current_statement = ""

            # Add any remaining statement
            if current_statement.strip():
                statements.append(current_statement.strip())
        else:
            # Use the simple split for queries without dollar quotes
            statements = [stmt.strip() for stmt in query.split(';') if stmt.strip()]

        if not statements:
            return {
                "success": False,
                "error": "No valid SQL statements found"
            }

        results = []
        total_execution_time = 0
        total_rows_affected = 0
        overall_is_read_only = True

        # Execute each statement
        for statement in statements:
            # Check if statement is read-only (SELECT)
            is_read_only = statement.strip().upper().startswith("SELECT")
            overall_is_read_only = overall_is_read_only and is_read_only

            # Execute the statement
            start_time = datetime.now()
            result = await db.execute(text(statement))
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            total_execution_time += execution_time

            # Process results based on statement type
            if is_read_only:
                rows = result.fetchall()

                # Get column names
                columns = []
                if rows and len(rows) > 0:
                    columns = list(rows[0]._mapping.keys())

                # Convert rows to list of dictionaries
                data = [dict(row._mapping) for row in rows]
                row_count = len(data)

                results.append({
                    "statement": statement,
                    "is_read_only": True,
                    "columns": columns,
                    "data": data,
                    "row_count": row_count,
                    "execution_time": execution_time
                })
            else:
                # For non-SELECT statements
                row_count = result.rowcount
                total_rows_affected += row_count

                results.append({
                    "statement": statement,
                    "is_read_only": False,
                    "row_count": row_count,
                    "execution_time": execution_time,
                    "message": f"Statement executed successfully. {row_count} rows affected."
                })

        # Commit changes if any non-read-only statements were executed
        if not overall_is_read_only:
            await db.commit()

        # Return combined results
        return {
            "success": True,
            "is_read_only": overall_is_read_only,
            "results": results,
            "total_execution_time": total_execution_time,
            "total_rows_affected": total_rows_affected
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Error executing SQL query: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/snippets", summary="Get saved SQL snippets")
async def get_sql_snippets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """
    Get all saved SQL snippets for the current user.
    """
    try:
        # Check if sql_snippets table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'sql_snippets'
        );
        """
        result = await db.execute(text(check_query))
        table_exists = result.scalar()

        # Create table if it doesn't exist
        if not table_exists:
            create_table_query = """
            CREATE TABLE sql_snippets (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                sql_code TEXT NOT NULL,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                is_shared BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            await db.execute(text(create_table_query))
            await db.commit()

        # Get snippets for the current user
        query = """
        SELECT
            id,
            name,
            description,
            sql_code,
            user_id,
            is_shared,
            created_at,
            updated_at
        FROM sql_snippets
        WHERE user_id = :user_id
        OR is_shared = TRUE
        ORDER BY created_at DESC;
        """
        result = await db.execute(text(query), {"user_id": str(current_user.id)})
        snippets = [dict(row._mapping) for row in result.fetchall()]

        return snippets
    except Exception as e:
        logger.error(f"Error getting SQL snippets: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/snippets", summary="Save a new SQL snippet")
async def save_sql_snippet(
    name: str = Body(...),
    sql_code: str = Body(...),
    description: Optional[str] = Body(None),
    is_shared: bool = Body(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Save a new SQL snippet.
    """
    try:
        # Check if sql_snippets table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'sql_snippets'
        );
        """
        result = await db.execute(text(check_query))
        table_exists = result.scalar()

        # Create table if it doesn't exist
        if not table_exists:
            create_table_query = """
            CREATE TABLE sql_snippets (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                sql_code TEXT NOT NULL,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                is_shared BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            await db.execute(text(create_table_query))
            await db.commit()

        # Insert the new snippet
        insert_query = """
        INSERT INTO sql_snippets (
            id,
            name,
            description,
            sql_code,
            user_id,
            is_shared
        )
        VALUES (
            :id,
            :name,
            :description,
            :sql_code,
            :user_id,
            :is_shared
        )
        RETURNING *;
        """

        snippet_id = str(uuid.uuid4())
        params = {
            "id": snippet_id,
            "name": name,
            "description": description,
            "sql_code": sql_code,
            "user_id": str(current_user.id),
            "is_shared": is_shared
        }

        result = await db.execute(text(insert_query), params)
        new_snippet = result.fetchone()
        await db.commit()

        return dict(new_snippet._mapping)
    except Exception as e:
        await db.rollback()
        logger.error(f"Error saving SQL snippet: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/snippets/{snippet_id}", summary="Update a SQL snippet")
async def update_sql_snippet(
    snippet_id: str,
    name: Optional[str] = Body(None),
    sql_code: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    is_shared: Optional[bool] = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Update an existing SQL snippet.
    """
    try:
        # Check if snippet exists and belongs to the user
        check_query = """
        SELECT EXISTS (
            SELECT FROM sql_snippets
            WHERE id = :snippet_id
            AND user_id = :user_id
        );
        """
        result = await db.execute(
            text(check_query),
            {"snippet_id": snippet_id, "user_id": str(current_user.id)}
        )
        snippet_exists = result.scalar()

        if not snippet_exists:
            raise HTTPException(status_code=404, detail="Snippet not found or you don't have permission to update it")

        # Build the update query
        update_parts = []
        params = {"snippet_id": snippet_id}

        if name is not None:
            update_parts.append("name = :name")
            params["name"] = name

        if sql_code is not None:
            update_parts.append("sql_code = :sql_code")
            params["sql_code"] = sql_code

        if description is not None:
            update_parts.append("description = :description")
            params["description"] = description

        if is_shared is not None:
            update_parts.append("is_shared = :is_shared")
            params["is_shared"] = is_shared

        update_parts.append("updated_at = NOW()")

        if not update_parts:
            return {"message": "No changes to update"}

        update_query = f"""
        UPDATE sql_snippets
        SET {", ".join(update_parts)}
        WHERE id = :snippet_id
        RETURNING *;
        """

        result = await db.execute(text(update_query), params)
        updated_snippet = result.fetchone()
        await db.commit()

        return dict(updated_snippet._mapping)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating SQL snippet: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/snippets/{snippet_id}", summary="Delete a SQL snippet")
async def delete_sql_snippet(
    snippet_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Delete a SQL snippet.
    """
    try:
        # Check if snippet exists and belongs to the user
        check_query = """
        SELECT EXISTS (
            SELECT FROM sql_snippets
            WHERE id = :snippet_id
            AND user_id = :user_id
        );
        """
        result = await db.execute(
            text(check_query),
            {"snippet_id": snippet_id, "user_id": str(current_user.id)}
        )
        snippet_exists = result.scalar()

        if not snippet_exists:
            raise HTTPException(status_code=404, detail="Snippet not found or you don't have permission to delete it")

        # Delete the snippet
        delete_query = """
        DELETE FROM sql_snippets
        WHERE id = :snippet_id
        RETURNING *;
        """

        result = await db.execute(text(delete_query), {"snippet_id": snippet_id})
        deleted_snippet = result.fetchone()
        await db.commit()

        return {"message": "Snippet deleted successfully", "deleted_snippet": dict(deleted_snippet._mapping)}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting SQL snippet: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/history", summary="Get query execution history")
async def get_query_history(
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get query execution history for the current user.
    """
    try:
        # Check if sql_history table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'sql_history'
        );
        """
        result = await db.execute(text(check_query))
        table_exists = result.scalar()

        # Create table if it doesn't exist
        if not table_exists:
            create_table_query = """
            CREATE TABLE sql_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                query TEXT NOT NULL,
                is_read_only BOOLEAN NOT NULL,
                execution_time FLOAT,
                row_count INTEGER,
                error TEXT,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            await db.execute(text(create_table_query))
            await db.commit()

        # Get total count
        count_query = """
        SELECT COUNT(*) FROM sql_history
        WHERE user_id = :user_id;
        """
        result = await db.execute(text(count_query), {"user_id": str(current_user.id)})
        total_count = result.scalar()

        # Calculate pagination
        offset = (page - 1) * page_size

        # Get history entries
        query = """
        SELECT
            id,
            query,
            is_read_only,
            execution_time,
            row_count,
            error,
            executed_at
        FROM sql_history
        WHERE user_id = :user_id
        ORDER BY executed_at DESC
        LIMIT :limit OFFSET :offset;
        """
        result = await db.execute(
            text(query),
            {"user_id": str(current_user.id), "limit": page_size, "offset": offset}
        )
        history = [dict(row._mapping) for row in result.fetchall()]

        return {
            "history": history,
            "metadata": {
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }
    except Exception as e:
        logger.error(f"Error getting query history: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/history", summary="Save query to history")
async def save_query_history(
    query: str = Body(...),
    is_read_only: bool = Body(...),
    execution_time: float = Body(...),
    row_count: int = Body(None),
    error: Optional[str] = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Save a query execution to history.
    """
    try:
        # Check if sql_history table exists
        check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'sql_history'
        );
        """
        result = await db.execute(text(check_query))
        table_exists = result.scalar()

        # Create table if it doesn't exist
        if not table_exists:
            create_table_query = """
            CREATE TABLE sql_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                query TEXT NOT NULL,
                is_read_only BOOLEAN NOT NULL,
                execution_time FLOAT,
                row_count INTEGER,
                error TEXT,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            await db.execute(text(create_table_query))
            await db.commit()

        # Insert the history entry
        insert_query = """
        INSERT INTO sql_history (
            id,
            query,
            is_read_only,
            execution_time,
            row_count,
            error,
            user_id
        )
        VALUES (
            :id,
            :query,
            :is_read_only,
            :execution_time,
            :row_count,
            :error,
            :user_id
        )
        RETURNING *;
        """

        history_id = str(uuid.uuid4())
        params = {
            "id": history_id,
            "query": query,
            "is_read_only": is_read_only,
            "execution_time": execution_time,
            "row_count": row_count,
            "error": error,
            "user_id": str(current_user.id)
        }

        result = await db.execute(text(insert_query), params)
        new_history = result.fetchone()
        await db.commit()

        return dict(new_history._mapping)
    except Exception as e:
        await db.rollback()
        logger.error(f"Error saving query history: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

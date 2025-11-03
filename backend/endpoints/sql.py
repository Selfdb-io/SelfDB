"""SQL execution endpoints for SelfDB."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from shared.services.sql_service import (
    SqlService,
    SqlExecutionResult,
    SqlSnippetCreate,
    SqlSnippet,
    SecurityError,
)
from shared.database.connection_manager import DatabaseConnectionManager
from shared.config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["sql"])


async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current authenticated user from request state."""
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return {
        "id": request.state.user_id,
        "role": getattr(request.state, "user_role", "USER"),
        "auth_method": getattr(request.state, "auth_method", "unknown"),
    }


async def get_current_admin_user(request: Request) -> Dict[str, Any]:
    """Get current admin user from request state."""
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    user_role = getattr(request.state, "user_role", "USER")
    if user_role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    logger.debug(
        "Current admin user resolved from request: id=%s role=%s auth_method=%s",
        getattr(request.state, "user_id", None),
        user_role,
        getattr(request.state, "auth_method", None),
    )
    return {
        "id": request.state.user_id,
        "role": user_role,
        "auth_method": getattr(request.state, "auth_method", "unknown"),
    }


# Initialize service (following tables.py pattern)
try:
    _config_manager = ConfigManager()
    _db_manager = DatabaseConnectionManager(_config_manager)
    sql_service = SqlService(_db_manager)
except Exception as exc:
    logger.warning("Failed to initialize SqlService: %s", exc)
    sql_service = None


# Pydantic models
class SqlQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100000)


class SqlHistorySaveRequest(BaseModel):
    query: str
    result: Dict[str, Any]


class SqlSnippetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sql_code: str = Field(..., min_length=1, max_length=100000)
    description: Optional[str] = None
    is_shared: bool = False


@router.post("/sql/query", response_model=SqlExecutionResult)
async def execute_query(
    request: SqlQueryRequest,
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
):
    """Execute a SQL query (ADMIN only for all queries)."""
    if not sql_service:
        raise HTTPException(status_code=503, detail="SQL service unavailable")

    try:
        result = await sql_service.execute_query(request.query, current_user["id"])
        return result
    except SecurityError as exc:
        logger.error("Security validation failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Query execution failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/sql/history", status_code=status.HTTP_201_CREATED)
async def save_query_history(
    request: SqlHistorySaveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Save query to history."""
    if not sql_service:
        raise HTTPException(status_code=503, detail="SQL service unavailable")

    try:
        # Convert dict result to SqlExecutionResult
        result = SqlExecutionResult(**request.result)
        await sql_service.save_query_history(request.query, result, current_user["id"])
        return {"message": "Query saved to history"}
    except Exception as exc:
        logger.error("Failed to save query history: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save history")


@router.get("/sql/history")
async def get_query_history(
    limit: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get query execution history."""
    if not sql_service:
        raise HTTPException(status_code=503, detail="SQL service unavailable")

    try:
        history = await sql_service.get_query_history(current_user["id"], limit)
        return {"history": history}
    except Exception as exc:
        logger.error("Failed to get query history: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


@router.get("/sql/snippets")
async def get_snippets(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get saved SQL snippets."""
    if not sql_service:
        raise HTTPException(status_code=503, detail="SQL service unavailable")

    try:
        snippets = await sql_service.get_snippets(current_user["id"])
        return snippets
    except Exception as exc:
        logger.error("Failed to get snippets: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve snippets")


@router.post("/sql/snippets", status_code=status.HTTP_201_CREATED)
async def create_snippet(
    snippet: SqlSnippetCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new SQL snippet."""
    if not sql_service:
        raise HTTPException(status_code=503, detail="SQL service unavailable")

    try:
        snippet_create = SqlSnippetCreate(
            name=snippet.name,
            sql_code=snippet.sql_code,
            description=snippet.description,
            is_shared=snippet.is_shared,
        )
        created_snippet = await sql_service.save_snippet(snippet_create, current_user["id"])
        return created_snippet
    except Exception as exc:
        logger.error("Failed to create snippet: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/sql/snippets/{snippet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_snippet(
    snippet_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a SQL snippet."""
    if not sql_service:
        raise HTTPException(status_code=503, detail="SQL service unavailable")

    try:
        await sql_service.delete_snippet(snippet_id, current_user["id"])
    except Exception as exc:
        logger.error("Failed to delete snippet: %s", exc)
        raise HTTPException(status_code=404, detail="Snippet not found or access denied")

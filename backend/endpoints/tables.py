"""FastAPI endpoints for dynamic table management."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field, ConfigDict

try:
    import asyncpg
except ImportError:
    asyncpg = None

from shared.config.config_manager import ConfigManager
from shared.database.connection_manager import DatabaseConnectionManager
from shared.services.table_crud_manager import (
    TableAlreadyExistsError,
    TableCRUDManager,
    TableColumnError,
    TableNotFoundError,
    TableValidationError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["tables"])

try:
    _config_manager = ConfigManager()
    _db_manager = DatabaseConnectionManager(_config_manager)
    table_crud_manager = TableCRUDManager(_db_manager)
except Exception as exc:  # pragma: no cover - initialization fallback for tests
    logger.warning("Failed to initialize TableCRUDManager: %s", exc)
    table_crud_manager = None


class TableSchemaModel(BaseModel):
    columns: List[Dict[str, Any]]
    indexes: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(protected_namespaces=())


class CreateTableRequest(BaseModel):
    name: str
    description: Optional[str] = None
    public: bool = False
    table_schema: TableSchemaModel = Field(alias="schema")
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(protected_namespaces=(), populate_by_name=True)


class UpdateTableRequest(BaseModel):
    new_name: Optional[str] = Field(default=None, alias="new_name")
    description: Optional[str] = None
    public: Optional[bool] = None

    model_config = ConfigDict(protected_namespaces=(), populate_by_name=True)


class ColumnDefinitionModel(BaseModel):
    name: str
    type: str
    nullable: Optional[bool] = True
    unique: Optional[bool] = False
    default: Optional[Any] = None
    primary_key: Optional[bool] = False

    model_config = ConfigDict(protected_namespaces=())


class UpdateColumnRequest(BaseModel):
    new_name: Optional[str] = None
    type: Optional[str] = None
    nullable: Optional[bool] = None
    default: Optional[Any] = None

    model_config = ConfigDict(protected_namespaces=())


class TableDataResponse(BaseModel):
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]


def _require_manager() -> TableCRUDManager:
    if table_crud_manager is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Table service unavailable")
    return table_crud_manager


async def get_current_user(request: Request) -> Dict[str, Any]:
    if not hasattr(request.state, "user_id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    logger.debug(
        "Current user resolved from request: id=%s role=%s auth_method=%s",
        getattr(request.state, "user_id", None),
        getattr(request.state, "user_role", None),
        getattr(request.state, "auth_method", None),
    )
    return {
        "user_id": request.state.user_id,
        "role": getattr(request.state, "user_role", "USER"),
        "auth_method": getattr(request.state, "auth_method", "unknown"),
    }


def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user.get("role", "").upper() != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


async def require_table_owner_or_admin(table_name: str, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Allow table owner or admin to perform operations on the table."""
    if user.get("role", "").upper() == "ADMIN":
        return user
    
    # Check if user owns the table
    manager = _require_manager()
    try:
        table = await manager.get_table(table_name)
        if table.get("owner_id") == user.get("user_id"):
            return user
    except Exception:
        pass  # Table not found or other error
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to modify this table")


def _handle_table_exception(error: Exception) -> None:
    if isinstance(error, TableAlreadyExistsError):
        logger.warning("Table already exists error: %s", error)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if isinstance(error, TableValidationError):
        logger.warning("Table validation error: %s", error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if isinstance(error, TableColumnError):
        logger.warning("Table column error: %s", error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if isinstance(error, TableNotFoundError):
        logger.warning("Table not found error: %s", error)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    
    # Handle database-specific errors
    if asyncpg and isinstance(error, asyncpg.exceptions.PostgresError):
        error_msg = str(error)
        logger.warning("Database error: %s", error_msg)
        # Extract meaningful error message from asyncpg exception
        if isinstance(error, asyncpg.exceptions.DataError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid data: {error_msg}") from error
        elif isinstance(error, asyncpg.exceptions.IntegrityConstraintViolationError):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Constraint violation: {error_msg}") from error
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database error: {error_msg}") from error
    
    logger.exception("Unexpected table operation failure")
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Table operation failed") from error


@router.get("/tables")
async def list_tables(current_user: Dict[str, Any] = Depends(get_current_user)):
    manager = _require_manager()
    try:
        tables = await manager.list_tables(owner_id=current_user["user_id"])
        return tables
    except Exception as exc:  # pragma: no cover - unexpected failure
        logger.exception("Failed to list tables")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list tables") from exc


@router.post("/tables", status_code=status.HTTP_201_CREATED)
async def create_table(
    request_body: CreateTableRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    manager = _require_manager()
    try:
        table_definition = request_body.model_dump(by_alias=True)
        result = await manager.create_table(owner_id=current_user["user_id"], table_definition=table_definition)
        return result
    except Exception as exc:
        _handle_table_exception(exc)


@router.get("/tables/{table_name}")
async def get_table_metadata(table_name: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    manager = _require_manager()
    try:
        table = await manager.get_table(table_name)
        return table
    except Exception as exc:
        _handle_table_exception(exc)


@router.put("/tables/{table_name}")
async def update_table(
    table_name: str,
    updates: UpdateTableRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    manager = _require_manager()
    try:
        updated = await manager.update_table_metadata(
            table_name,
            new_name=updates.new_name,
            description=updates.description,
            public=updates.public,
        )
        return updated
    except Exception as exc:
        _handle_table_exception(exc)


@router.delete("/tables/{table_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(table_name: str, _: Dict[str, Any] = Depends(require_admin)) -> Response:
    manager = _require_manager()
    try:
        await manager.delete_table(table_name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _handle_table_exception(exc)


@router.get("/tables/{table_name}/data", response_model=TableDataResponse)
async def get_table_data(
    table_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    order_by: Optional[str] = None,
    filter_column: Optional[str] = None,
    filter_value: Optional[str] = None,
):
    manager = _require_manager()
    try:
        result = await manager.get_table_data(
            table_name,
            page=page,
            page_size=page_size,
            order_by=order_by,
            filter_column=filter_column,
            filter_value=filter_value,
        )
        return result
    except Exception as exc:
        _handle_table_exception(exc)


@router.post("/tables/{table_name}/data")
async def insert_table_row(
    table_name: str,
    row: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    manager = _require_manager()
    try:
        return await manager.insert_row(table_name, row)
    except Exception as exc:
        _handle_table_exception(exc)


@router.put("/tables/{table_name}/data/{row_id}")
async def update_table_row(
    table_name: str,
    row_id: str,
    updates: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    id_column: str = Query("id"),
):
    manager = _require_manager()
    try:
        return await manager.update_row(table_name, row_id=row_id, id_column=id_column, updates=updates)
    except Exception as exc:
        _handle_table_exception(exc)


@router.delete("/tables/{table_name}/data/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table_row(
    table_name: str,
    row_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    id_column: str = Query("id"),
) -> Response:
    manager = _require_manager()
    try:
        await manager.delete_row(table_name, row_id=row_id, id_column=id_column)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _handle_table_exception(exc)


@router.get("/tables/{table_name}/sql")
async def get_table_sql(table_name: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    manager = _require_manager()
    try:
        sql_text = await manager.get_table_sql(table_name)
        return {"sql": sql_text}
    except Exception as exc:
        _handle_table_exception(exc)


@router.post("/tables/{table_name}/columns")
async def add_column(
    table_name: str,
    column: ColumnDefinitionModel,
    _: Dict[str, Any] = Depends(require_admin),
):
    manager = _require_manager()
    try:
        await manager.add_column(table_name, column.model_dump())
        return {"status": "column_added"}
    except Exception as exc:
        _handle_table_exception(exc)


@router.put("/tables/{table_name}/columns/{column_name}")
async def update_column_endpoint(
    table_name: str,
    column_name: str,
    updates: UpdateColumnRequest,
    _: Dict[str, Any] = Depends(require_admin),
):
    manager = _require_manager()
    try:
        await manager.update_column(table_name, column_name, updates.model_dump(exclude_unset=True))
        return {"status": "column_updated"}
    except Exception as exc:
        _handle_table_exception(exc)


@router.delete("/tables/{table_name}/columns/{column_name}", status_code=status.HTTP_200_OK)
async def delete_column_endpoint(
    table_name: str,
    column_name: str,
    _: Dict[str, Any] = Depends(require_admin),
):
    manager = _require_manager()
    try:
        await manager.delete_column(table_name, column_name)
        return {"status": "column_deleted"}
    except Exception as exc:
        _handle_table_exception(exc)

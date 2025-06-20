from typing import Any, List
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, status, Path, Response
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.encoders import jsonable_encoder

from ...schemas.function import (
    Function,
    FunctionCreate,
    FunctionUpdate,
    FunctionEnvVar,
    FunctionEnvVarBase,
    FunctionVersion,
)
from ...models.user import User
from ...crud.function import (
    get_function,
    get_functions_by_owner,
    create_function,
    update_function,
    delete_function,
    list_env_vars,
    create_env_var,
    update_env_var,
    delete_env_var,
    get_versions,
)
from ..deps import get_db, get_current_active_user
from ...db.notify import emit_table_notification

router = APIRouter()

# ---------------------------------------------------------
# Function CRUD Endpoints
# ---------------------------------------------------------

@router.get("", response_model=List[Function])
async def list_user_functions(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """List all functions owned by the authenticated user."""
    # TODO: support superuser listing all
    functions = await get_functions_by_owner(db, owner_id=current_user.id, skip=skip, limit=limit)
    return functions


@router.post("", response_model=Function, status_code=status.HTTP_201_CREATED)
async def create_user_function(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    obj_in: FunctionCreate,
) -> Any:
    """Create a new function."""
    fn = await create_function(db, owner_id=current_user.id, obj_in=obj_in)
    
    await emit_table_notification(
        db, 
        "functions", 
        "INSERT", 
        jsonable_encoder(fn)
    )
    
    return fn


@router.get("/{function_id}", response_model=Function)
async def read_function(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    function_id: UUID = Path(..., description="Function ID"),
) -> Any:
    fn = await get_function(db, function_id=function_id)
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")
    if fn.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return fn


@router.put("/{function_id}", response_model=Function)
async def update_user_function(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    function_id: UUID,
    obj_in: FunctionUpdate,
) -> Any:
    fn = await get_function(db, function_id=function_id)
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")
    if fn.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    fn = await update_function(db, function=fn, obj_in=obj_in, updated_by=current_user.id)
    
    await emit_table_notification(
        db, 
        "functions", 
        "UPDATE", 
        jsonable_encoder(fn)
    )
    
    return fn


@router.delete("/{function_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_function(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    function_id: UUID,
) -> None:
    fn = await get_function(db, function_id=function_id)
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")
    if fn.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    await emit_table_notification(
        db, 
        "functions", 
        "DELETE", 
        None, 
        jsonable_encoder(fn)
    )
    
    await delete_function(db, function=fn)


# ---------------------------------------------------------
# Function Versions Endpoints (read‑only)
# ---------------------------------------------------------

@router.get("/{function_id}/versions", response_model=List[FunctionVersion])
async def list_function_versions(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    function_id: UUID,
) -> Any:
    fn = await get_function(db, function_id=function_id)
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")
    if fn.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    versions = await get_versions(db, function_id=function_id)
    return versions


# ---------------------------------------------------------
# Environment Variables Endpoints
# ---------------------------------------------------------

@router.get("/{function_id}/env", response_model=List[FunctionEnvVar])
async def list_function_env_vars(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    function_id: UUID,
) -> Any:
    fn = await get_function(db, function_id=function_id)
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")
    if fn.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return await list_env_vars(db, function_id=function_id)


@router.post("/{function_id}/env", response_model=FunctionEnvVar, status_code=status.HTTP_201_CREATED)
async def create_function_env_var(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    function_id: UUID,
    var_in: FunctionEnvVarBase,
) -> Any:
    fn = await get_function(db, function_id=function_id)
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")
    if fn.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    env_var = await create_env_var(db, function_id=function_id, var_in=var_in)
    
    await emit_table_notification(
        db, 
        "function_env_vars", 
        "INSERT", 
        jsonable_encoder(env_var)
    )
    
    return env_var


@router.put("/{function_id}/env/{env_id}", response_model=FunctionEnvVar)
async def update_function_env_var(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    function_id: UUID,
    env_id: UUID,
    var_in: FunctionEnvVarBase,
) -> Any:
    fn = await get_function(db, function_id=function_id)
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")
    if fn.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Fetch env var
    env_vars = await list_env_vars(db, function_id=function_id)
    env_obj = next((v for v in env_vars if v.id == env_id), None)
    if not env_obj:
        raise HTTPException(status_code=404, detail="Environment variable not found")

    updated_env_var = await update_env_var(db, env_var=env_obj, var_in=var_in)
    
    await emit_table_notification(
        db, 
        "function_env_vars", 
        "UPDATE", 
        jsonable_encoder(updated_env_var)
    )
    
    return updated_env_var


@router.delete("/{function_id}/env/{env_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_function_env_var(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    function_id: UUID,
    env_id: UUID,
) -> None:
    fn = await get_function(db, function_id=function_id)
    if not fn:
        raise HTTPException(status_code=404, detail="Function not found")
    if fn.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    env_vars = await list_env_vars(db, function_id=function_id)
    env_obj = next((v for v in env_vars if v.id == env_id), None)
    if not env_obj:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    
    await emit_table_notification(
        db, 
        "function_env_vars", 
        "DELETE", 
        None, 
        jsonable_encoder(env_obj)
    )
    
    await delete_env_var(db, env_var=env_obj)


# ---------------------------------------------------------
# Code‑editor helper endpoints (lint, validate, types, templates)
# ---------------------------------------------------------

import asyncio
import json
import tempfile
import os
from pathlib import Path

# Path where we cache generated Deno types to avoid heavy regeneration
_DENO_TYPES_CACHE = Path("/tmp/deno_types.d.ts")


@router.post("/lint", response_model=List[dict])
async def lint_code_endpoint(*, code: str) -> Any:  # type: ignore[valid-type]
    """Run `deno lint` on provided code and return diagnostics."""
    # Write code to temp file
    with tempfile.NamedTemporaryFile("w+", suffix=".ts", delete=False) as temp:
        temp.write(code)
        temp_path = temp.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "deno", "lint", "--json", temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode not in (0, 1):  # 1 means lint errors were found
            raise HTTPException(status_code=500, detail=f"deno lint failed: {stderr.decode()}")

        try:
            diagnostics = json.loads(stdout or b"{}")
        except json.JSONDecodeError:
            diagnostics = {}
        return diagnostics.get("diagnostics", [])
    finally:
        os.unlink(temp_path)


@router.post("/validate", response_model=dict)
async def validate_code_endpoint(*, code: str) -> Any:  # type: ignore[valid-type]
    """Run `deno check` (TypeScript compiler) on provided code."""
    with tempfile.NamedTemporaryFile("w+", suffix=".ts", delete=False) as temp:
        temp.write(code)
        temp_path = temp.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "deno", "check", "--json", temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        valid = proc.returncode == 0
        errors = []
        if not valid:
            try:
                errors = json.loads(stderr or b"[]").get("errors", [])
            except json.JSONDecodeError:
                errors = [{"message": stderr.decode()}]
        return {"valid": valid, "errors": errors}
    finally:
        os.unlink(temp_path)


@router.get("/deno-types")
async def deno_types_endpoint() -> Any:
    """Return cached Deno type definitions (regenerated every 24h)."""
    if not _DENO_TYPES_CACHE.exists() or (os.stat(_DENO_TYPES_CACHE).st_mtime < (asyncio.get_event_loop().time() - 86400)):
        # Regenerate
        proc = await asyncio.create_subprocess_exec(
            "deno", "types",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Failed to get Deno types: {stderr.decode()}")
        _DENO_TYPES_CACHE.write_bytes(stdout)
    return _DENO_TYPES_CACHE.read_text()


_TEMPLATES = {
    "default": """// SelfDB Function Template
export default async function handler(req) {
  // This function can be called via HTTP, scheduled, or triggered by database events
  // You can implement your own scheduling logic or database event handling

  // Example: Access environment variables
  const dbUrl = Deno.env.get("DATABASE_URL");

  // Example: Return a response for HTTP requests
  if (req instanceof Request) {
    return new Response(JSON.stringify({message: 'Hello from SelfDB function!'}), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // For non-HTTP invocations (scheduled runs, etc.)
  console.log('Function executed at:', new Date().toISOString());
  return { success: true };
}"""
}


@router.get("/templates/{template_type}")
async def get_template_endpoint(template_type: str) -> Any:
    # Always return the default template regardless of the requested type
    # This simplifies the function model by removing trigger-specific templates
    return _TEMPLATES["default"]

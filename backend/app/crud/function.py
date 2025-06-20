from typing import List, Optional
from uuid import UUID
import json
import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from ..models.function import Function, FunctionVersion, FunctionEnvVar
from ..schemas.function import (
    FunctionCreate,
    FunctionUpdate,
    FunctionEnvVarBase,
)

FUNCTIONS_DIR = os.environ.get("FUNCTIONS_DIR", "/functions")


# ------------------------------------------------------------------
# Helper utilities
# ------------------------------------------------------------------

def _build_metadata(function: Function) -> str:  # Serialize as JSON string
    """Return a JSON string of non‑code metadata for version snapshot."""
    data = {
        "name": function.name or "",
        "description": function.description or "",
        "runtime": function.runtime.value if hasattr(function, 'runtime') and function.runtime and hasattr(function.runtime, 'value') else (function.runtime or ""),
        "is_active": function.is_active,
    }
    # Always return a valid JSON string
    return json.dumps(data)


def write_function_file(function_id, function_name, code):
    """Write function code to a file using only the function name.

    Args:
        function_id: The UUID of the function (not used in filename)
        function_name: The name of the function (used as the filename)
        code: The function code to write
    """
    os.makedirs(FUNCTIONS_DIR, exist_ok=True)

    # Clean the function name to ensure it's a valid filename
    # Replace spaces and special characters with hyphens
    clean_name = ''.join(c if c.isalnum() else '-' for c in function_name)
    clean_name = clean_name.lower()

    # Use just the name as the filename
    filename = f"{clean_name}.ts"

    # Check if file already exists with this name
    path = os.path.join(FUNCTIONS_DIR, filename)
    if os.path.exists(path):
        # If it exists, we need to make sure it's the same function
        # Otherwise, we'll need to add a suffix to avoid conflicts
        try:
            # Try to find any existing file for this function ID
            for existing_file in os.listdir(FUNCTIONS_DIR):
                if existing_file.endswith(".ts") and existing_file != filename:
                    # If we find an old file for this function with a different name, remove it
                    old_path = os.path.join(FUNCTIONS_DIR, existing_file)
                    os.remove(old_path)
                    print(f"Removed old function file: {existing_file}")
        except Exception as e:
            print(f"Error cleaning up old function files: {e}")

    # Write the new file
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)


# ------------------------------------------------------------------
# Functions CRUD
# ------------------------------------------------------------------

async def get_function(db: AsyncSession, *, function_id: UUID) -> Optional[Function]:
    result = await db.execute(select(Function).filter(Function.id == function_id))
    return result.scalars().first()


async def get_functions_by_owner(
    db: AsyncSession, *, owner_id: UUID, skip: int = 0, limit: int = 100
) -> List[Function]:
    result = await db.execute(
        select(Function)
        .filter(Function.owner_id == owner_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def create_function(
    db: AsyncSession, *, owner_id: UUID, obj_in: FunctionCreate
) -> Function:
    # First create the function entry without the large fields
    db_fn = Function(
        name=obj_in.name,
        description=obj_in.description,
        # Store a short placeholder for code initially
        code="# Code stored in file system",
        runtime=obj_in.runtime if hasattr(obj_in, "runtime") and obj_in.runtime else None,
        owner_id=owner_id,
    )
    db.add(db_fn)
    await db.flush()  # Assign PK so we can create version row

    # Write function code to file for Deno runtime
    write_function_file(db_fn.id, db_fn.name, obj_in.code)
    
    # Create version with shorter metadata
    metadata = json.dumps({
        "name": db_fn.name,
        "description": db_fn.description,
        "runtime": str(db_fn.runtime),
        "version": 1,
        "created_at": str(db_fn.created_at) if db_fn.created_at else None,
    })
    
    version = FunctionVersion(
        function_id=db_fn.id,
        version_number=1,
        # Store a placeholder for code in the version too
        code="# Code stored in file system",
        metadata_json=metadata,
        created_by=owner_id,
    )
    db.add(version)
    db_fn.version_id = version.id
    await db.commit()
    await db.refresh(db_fn)
    return db_fn


async def update_function(
    db: AsyncSession, *, function: Function, obj_in: FunctionUpdate, updated_by: UUID
) -> Function:
    update_data = obj_in.model_dump(exclude_unset=True)
    
    # Store the code separately if it's in the update data
    code_to_write = None
    if 'code' in update_data:
        code_to_write = update_data['code']
        # Replace with placeholder in the database
        update_data['code'] = "# Code stored in file system"
    
    # Apply updates to the function object
    for field, value in update_data.items():
        setattr(function, field, value)
    
    # Increment version
    function.version_number += 1
    
    # Create version with shorter metadata
    metadata = json.dumps({
        "name": function.name,
        "description": function.description,
        "runtime": str(function.runtime),
        "version": function.version_number,
        "updated_at": str(function.updated_at) if function.updated_at else None,
    })
    
    version = FunctionVersion(
        function_id=function.id,
        version_number=function.version_number,
        # Store a placeholder for code in the version
        code="# Code stored in file system",
        metadata_json=metadata,
        created_by=updated_by,
    )
    db.add(version)
    function.version_id = version.id
    
    await db.commit()
    await db.refresh(function)
    
    # Write updated function code to file for Deno runtime if it was updated
    if code_to_write:
        write_function_file(function.id, function.name, code_to_write)
    
    return function


async def delete_function(db: AsyncSession, *, function: Function) -> None:
    # Delete the function file if it exists
    try:
        # Clean the function name to ensure it matches the filename format
        clean_name = ''.join(c if c.isalnum() else '-' for c in function.name)
        clean_name = clean_name.lower()
        filename = f"{clean_name}.ts"

        # Check if the file exists
        file_path = os.path.join(FUNCTIONS_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted function file: {filename}")
    except Exception as e:
        print(f"Error deleting function file: {e}")

    # Delete from database
    await db.delete(function)
    await db.commit()


# ------------------------------------------------------------------
# Version helpers
# ------------------------------------------------------------------

async def get_versions(db: AsyncSession, *, function_id: UUID) -> List[FunctionVersion]:
    result = await db.execute(
        select(FunctionVersion).filter(FunctionVersion.function_id == function_id).order_by(FunctionVersion.version_number.desc())
    )
    return result.scalars().all()


# ------------------------------------------------------------------
# Environment variables helpers
# ------------------------------------------------------------------

async def list_env_vars(db: AsyncSession, *, function_id: UUID) -> List[FunctionEnvVar]:
    result = await db.execute(select(FunctionEnvVar).filter(FunctionEnvVar.function_id == function_id))
    return result.scalars().all()


async def create_env_var(
    db: AsyncSession, *, function_id: UUID, var_in: FunctionEnvVarBase
) -> FunctionEnvVar:
    db_var = FunctionEnvVar(function_id=function_id, **var_in.model_dump())
    db.add(db_var)
    await db.commit()
    await db.refresh(db_var)
    return db_var


async def update_env_var(
    db: AsyncSession, *, env_var: FunctionEnvVar, var_in: FunctionEnvVarBase
) -> FunctionEnvVar:
    for field, value in var_in.model_dump(exclude_unset=True).items():
        setattr(env_var, field, value)
    await db.commit()
    await db.refresh(env_var)
    return env_var


async def delete_env_var(db: AsyncSession, *, env_var: FunctionEnvVar) -> None:
    await db.delete(env_var)
    await db.commit()
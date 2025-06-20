from typing import Any, List

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.encoders import jsonable_encoder

from ...schemas.user import User, UserCreate, UserUpdate, PasswordChange, AnonKeyResponse
from ...crud.user import get_user, get_users, create_user, update_user, delete_user, get_user_by_email, change_user_password, count_regular_users
from ..deps import get_db, get_current_active_user, get_current_active_superuser
from app.core.config import settings
from ...db.notify import emit_table_notification

router = APIRouter()

@router.get("/me", response_model=User)
async def read_user_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.put("/me", response_model=User)
async def update_user_me(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update own user.
    """
    user = await update_user(db, user_id=current_user.id, user_in=user_in)
    
    await emit_table_notification(
        db, 
        "users", 
        "UPDATE", 
        jsonable_encoder(user)
    )
    
    return user

@router.put("/me/password", response_model=bool)
async def change_password(
    *,
    db: AsyncSession = Depends(get_db),
    password_in: PasswordChange,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Change current user password.
    """
    success = await change_user_password(
        db=db, 
        user=current_user,
        current_password=password_in.current_password,
        new_password=password_in.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )
    
    return True

@router.get("/", response_model=List[User])
async def read_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Retrieve users. Requires superuser privileges.
    """
    users = await get_users(db, skip=skip, limit=limit)
    return users

@router.get("/list", response_model=List[User])
async def read_all_active_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve list of users, excluding superusers. Requires standard user login.
    (For messaging app, etc.)

    Note: This retrieves non-superuser users.
    Consider adding further filtering logic here later if needed (e.g., only contacts,
    exclude self, filter by activity, etc.) based on app requirements.
    """
    _ = current_user # Indicate usage for linters
    all_users = await get_users(db, skip=skip, limit=limit)
    # Filter out superusers
    non_superusers = [user for user in all_users if not user.is_superuser]
    return non_superusers

@router.get("/count", response_model=int)
async def get_regular_users_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get the total count of regular users (excluding superusers).
    This endpoint is used for dashboard statistics.
    """
    _ = current_user  # Indicate usage for linters
    count = await count_regular_users(db)
    return count

@router.get("/{user_id}", response_model=User)
async def read_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a specific user by id.
    """
    user = await get_user(db, user_id=user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return user

@router.post("", response_model=User)
async def create_user_admin(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Create new user. Only for superusers.
    """
    user = await get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = await create_user(db, user_in=user_in)
    
    await emit_table_notification(
        db, 
        "users", 
        "INSERT", 
        jsonable_encoder(user)
    )
    
    return user

@router.put("/{user_id}", response_model=User)
async def update_user_admin(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: str,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Update a user. Only for superusers.
    """
    user = await get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    user = await update_user(db, user_id=user_id, user_in=user_in)
    
    await emit_table_notification(
        db, 
        "users", 
        "UPDATE", 
        jsonable_encoder(user)
    )
    
    return user

@router.delete("/{user_id}", response_model=bool)
async def delete_user_admin(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: str,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Delete a user. Only for superusers.
    """
    user = await get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    
    await emit_table_notification(
        db, 
        "users", 
        "DELETE", 
        None, 
        jsonable_encoder(user)
    )
    
    result = await delete_user(db, user_id=user_id)
    return result

@router.get("/me/anon-key", response_model=AnonKeyResponse)
async def read_current_user_anon_key(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve the global Anonymous Access Key (ANON_KEY).
    Requires user authentication.

    Warning: Exposing this key in the frontend might have security implications
    as it's a single key for all anonymous access to public resources.
    """
    anon_key = settings.ANON_KEY
    if not anon_key:
        # Optionally handle the case where ANON_KEY is not set in the environment
        # Depending on requirements, you could return None, an empty string,
        # or raise an error if it's expected to always be present.
        # For now, returning None or empty string seems reasonable.
        anon_key = None # Or ""

    return {"anon_key": anon_key}

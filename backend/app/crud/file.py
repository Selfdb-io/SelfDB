from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
import uuid

from ..models.file import File
from ..schemas.file import FileCreate, FileUpdate

async def get_file(db: AsyncSession, file_id: uuid.UUID) -> Optional[File]:
    """
    Get a file by ID.
    """
    result = await db.execute(select(File).filter(File.id == file_id))
    return result.scalars().first()

async def get_files_by_owner(
    db: AsyncSession, owner_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> List[File]:
    """
    Get files by owner ID with pagination.
    """
    result = await db.execute(
        select(File)
        .filter(File.owner_id == owner_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_files_by_bucket(
    db: AsyncSession, bucket_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> List[File]:
    """
    Get files by bucket ID with pagination.
    """
    result = await db.execute(
        select(File)
        .filter(File.bucket_id == bucket_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_file(db: AsyncSession, file_in: FileCreate) -> File:
    """
    Create a new file record.
    """
    db_file = File(
        filename=file_in.filename,
        object_name=file_in.object_name,
        bucket_name=file_in.bucket_name,
        content_type=file_in.content_type,
        size=file_in.size,
        owner_id=file_in.owner_id,
        bucket_id=file_in.bucket_id,
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    return db_file

async def update_file(
    db: AsyncSession, file_id: uuid.UUID, file_in: FileUpdate
) -> Optional[File]:
    """
    Update a file record.
    """
    file = await get_file(db, file_id)
    if not file:
        return None

    update_data = file_in.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(file, field, value)

    await db.commit()
    await db.refresh(file)
    return file

async def delete_file(db: AsyncSession, file_id: uuid.UUID) -> bool:
    """
    Delete a file record.
    """
    file = await get_file(db, file_id)
    if not file:
        return False

    await db.delete(file)
    await db.commit()
    return True

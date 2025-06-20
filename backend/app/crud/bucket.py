from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import uuid
import re

from ..models.bucket import Bucket
from ..models.file import File
from ..schemas.bucket import BucketCreate, BucketUpdate

def slugify(text: str) -> str:
    """
    Convert a string to a slug format (lowercase, no special chars, hyphens instead of spaces).
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces with hyphens
    text = text.replace(" ", "-")
    # Remove special characters
    text = re.sub(r'[^a-z0-9\-]', '', text)
    # Remove multiple hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text

async def get_bucket(db: AsyncSession, bucket_id: uuid.UUID) -> Optional[Bucket]:
    """
    Get a bucket by ID.
    """
    result = await db.execute(select(Bucket).filter(Bucket.id == bucket_id))
    return result.scalars().first()

async def get_bucket_by_minio_name(db: AsyncSession, minio_bucket_name: str) -> Optional[Bucket]:
    """
    Get a bucket by MinIO bucket name.
    """
    result = await db.execute(select(Bucket).filter(Bucket.minio_bucket_name == minio_bucket_name))
    return result.scalars().first()

async def get_buckets_by_owner(
    db: AsyncSession, owner_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> List[Bucket]:
    """
    Get buckets by owner ID with pagination.
    """
    result = await db.execute(
        select(Bucket)
        .filter(Bucket.owner_id == owner_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_public_buckets(
    db: AsyncSession, exclude_owner_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100
) -> List[Bucket]:
    """
    Get public buckets with pagination, optionally excluding buckets owned by a specific user.
    """
    query = select(Bucket).filter(Bucket.is_public == True)

    # Exclude buckets owned by the specified user if provided
    if exclude_owner_id:
        query = query.filter(Bucket.owner_id != exclude_owner_id)

    result = await db.execute(
        query
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_all_buckets(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[Bucket]:
    """
    Get all buckets with pagination.
    This is used for authenticated users who should see all buckets.
    """
    result = await db.execute(
        select(Bucket)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_bucket_stats(db: AsyncSession, bucket_id: uuid.UUID) -> dict:
    """
    Get statistics for a bucket (file count and total size).
    """
    # Query to get file count and total size
    query = select(
        func.count(File.id).label("file_count"),
        func.coalesce(func.sum(File.size), 0).label("total_size")
    ).filter(File.bucket_id == bucket_id)

    result = await db.execute(query)
    stats = result.first()

    return {
        "file_count": stats.file_count if stats else 0,
        "total_size": stats.total_size if stats else 0
    }

async def create_bucket(
    db: AsyncSession, bucket_in: BucketCreate, owner_id: uuid.UUID
) -> Bucket:
    """
    Create a new bucket record.
    """
    # Validate bucket name (only allow alphanumeric, hyphens, and underscores)
    slug = slugify(bucket_in.name)
    if not re.match(r'^[a-z0-9\-]+$', slug):
        raise ValueError("Bucket name must contain only letters, numbers, and hyphens")

    # Use the slugified name directly as the bucket name for storage service
    # This ensures consistent naming between database and storage service
    storage_bucket_name = slug

    # Check if a bucket with this name already exists
    existing_bucket = await db.execute(
        select(Bucket).filter(Bucket.name == bucket_in.name)
    )
    if existing_bucket.scalars().first():
        raise ValueError(f"A bucket with the name '{bucket_in.name}' already exists")

    # Check if a bucket with this storage bucket name already exists
    existing_storage = await db.execute(
        select(Bucket).filter(Bucket.minio_bucket_name == storage_bucket_name)
    )
    if existing_storage.scalars().first():
        raise ValueError(f"A bucket with the storage name '{storage_bucket_name}' already exists")

    db_bucket = Bucket(
        name=bucket_in.name,
        description=bucket_in.description,
        minio_bucket_name=storage_bucket_name,  # Keep using this field for compatibility
        is_public=bucket_in.is_public,
        owner_id=owner_id,
    )
    db.add(db_bucket)
    await db.commit()
    await db.refresh(db_bucket)
    return db_bucket

async def update_bucket(
    db: AsyncSession, bucket_id: uuid.UUID, bucket_in: BucketUpdate
) -> Optional[Bucket]:
    """
    Update a bucket record.
    """
    bucket = await get_bucket(db, bucket_id)
    if not bucket:
        return None

    update_data = bucket_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(bucket, field, value)

    await db.commit()
    await db.refresh(bucket)
    return bucket

async def delete_bucket(db: AsyncSession, bucket_id: uuid.UUID) -> bool:
    """
    Delete a bucket record.
    """
    bucket = await get_bucket(db, bucket_id)
    if not bucket:
        return False

    await db.delete(bucket)
    await db.commit()
    return True

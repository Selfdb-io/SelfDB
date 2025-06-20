import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.core.config import settings
from app.models.temp_user import TempUser
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_first_superuser():
    """
    Create a superuser if it doesn't exist.
    This is useful for initial setup.
    """
    # Get admin credentials from environment variables or use defaults
    admin_email = getattr(settings, 'DEFAULT_ADMIN_EMAIL', 'admin@example.com')
    admin_password = getattr(settings, 'DEFAULT_ADMIN_PASSWORD', 'adminpassword')

    logger.info(f"Using admin email: {admin_email}")

    async with AsyncSessionLocal() as db:
        # Check if superuser already exists
        result = await db.execute(select(TempUser).filter(TempUser.email == admin_email))
        user = result.scalars().first()

        if not user:
            # Create new user
            hashed_password = get_password_hash(admin_password)
            new_user = TempUser(
                email=admin_email,
                hashed_password=hashed_password,
                is_superuser=True,
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            logger.info(f"Superuser created: {new_user.email}")
        else:
            logger.info(f"Superuser already exists: {user.email}")

async def main():
    logger.info("Creating initial data")
    await create_first_superuser()
    logger.info("Initial data created")

if __name__ == "__main__":
    asyncio.run(main())

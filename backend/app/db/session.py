from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from ..core.config import settings # Import settings instance

# Create an asynchronous engine instance
# Uses the DATABASE_URL from the settings
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True, # Checks connection validity before use
    echo=False # Set to True to log SQL queries (useful for debugging)
)

# Create a session factory bound to the engine
# expire_on_commit=False prevents attributes from expiring after commit in async context
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

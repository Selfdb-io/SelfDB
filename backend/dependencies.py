"""
Dependency injection for SelfDB backend services.

This module provides dependency injection patterns for:
- Database connections
- Authentication services
- User store implementations
- Configuration management
"""

from typing import Optional, Protocol
from shared.auth.auth_endpoints import AuthEndpoints
from shared.auth.jwt_service import JWTService
from shared.auth.user_store import UserStoreInterface
from shared.auth.database_user_store import DatabaseUserStore
from shared.config.config_manager import ConfigManager
from shared.database.connection_manager import DatabaseConnectionManager
import logging
import os

logger = logging.getLogger(__name__)

# Use the actual UserStoreInterface for type safety
UserStoreProtocol = UserStoreInterface

class AuthServiceProtocol(Protocol):
    """Protocol for authentication operations."""

    async def register(self, user_data: dict): ...
    async def login(self, email: str, password: str): ...
    async def refresh_token(self, refresh_token: str): ...
    async def logout(self, access_token: str, refresh_token: str): ...
    async def get_current_user(self, token: str): ...

# Dependency providers
def get_config_manager() -> ConfigManager:
    """Get configuration manager instance."""
    return ConfigManager()

def get_database_connection_manager() -> DatabaseConnectionManager:
    """Get database connection manager instance."""
    config = get_config_manager()
    return DatabaseConnectionManager(config)

def get_jwt_service() -> JWTService:
    """Get JWT service instance."""
    config = get_config_manager()
    return JWTService(
        secret_key=os.getenv("JWT_SECRET_KEY", "dev-secret-key"),
        algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        refresh_token_expire_hours=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_HOURS", "168")),
        issuer=os.getenv("JWT_ISSUER", "selfdb")
    )

def get_auth_endpoints(
    jwt_service: Optional[JWTService] = None,
    user_store: Optional[UserStoreProtocol] = None
) -> AuthEndpoints:
    """
    Get AuthEndpoints instance with dependencies.

    Args:
        jwt_service: JWT service for token operations
        user_store: User store for user data operations

    Returns:
        AuthEndpoints instance with injected dependencies
    """
    if jwt_service is None:
        jwt_service = get_jwt_service()

    # Get API key from config
    config = get_config_manager()
    api_key = config.get_api_key()

    # Use the real database user store
    if user_store is None:
        db_manager = get_database_connection_manager()
        user_store = DatabaseUserStore(db_manager)

    return AuthEndpoints(
        api_key=api_key,
        jwt_service=jwt_service,
        user_store=user_store
    )

# FastAPI dependency functions for HTTP endpoints
async def get_auth_service() -> AuthServiceProtocol:
    """
    FastAPI dependency for authentication service.

    Returns AuthEndpoints instance for HTTP endpoints.
    """
    return get_auth_endpoints()

async def get_user_store() -> UserStoreProtocol:
    """
    FastAPI dependency for user store.

    Returns DatabaseUserStore instance for HTTP endpoints.
    """
    db_manager = get_database_connection_manager()
    return DatabaseUserStore(db_manager)

# Health check dependencies
async def get_service_health() -> dict:
    """Get health status of all dependencies."""
    health_status = {
        "config_manager": "healthy",
        "jwt_service": "healthy",
        "auth_endpoints": "healthy",
        "database_connection": "healthy",
        "user_store": "healthy"
    }

    try:
        config = get_config_manager()
        config.get_api_key()  # Test config access
    except Exception as e:
        health_status["config_manager"] = f"unhealthy: {str(e)}"
        logger.error(f"Config manager health check failed: {e}")

    try:
        jwt_service = get_jwt_service()
        # Test JWT service by generating a test token
        test_payload = {"test": "data", "exp": 1234567890}
        jwt_service.generate_access_token(test_payload)
    except Exception as e:
        health_status["jwt_service"] = f"unhealthy: {str(e)}"
        logger.error(f"JWT service health check failed: {e}")

    try:
        auth_endpoints = get_auth_endpoints()
        # AuthEndpoints doesn't need specific health checks for now
    except Exception as e:
        health_status["auth_endpoints"] = f"unhealthy: {str(e)}"
        logger.error(f"Auth endpoints health check failed: {e}")

    return health_status
"""
Database package for SelfDB.

Provides database connection management, pooling, and transaction support.
"""

from .connection_manager import (
    DatabaseConnectionManager,
    DatabaseConnectionError,
    HealthCheckError
)

__all__ = [
    'DatabaseConnectionManager',
    'DatabaseConnectionError',
    'HealthCheckError'
]
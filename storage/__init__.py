"""
Storage Package

This package provides a complete storage service implementation for SelfDB.
The storage service is internal-only and handles bucket and file operations
with proper authentication integration and health monitoring.

Main Classes:
    Storage: Complete storage service with all functionality
    StorageBase: Base class with initialization and utilities
    
Mixins:
    BucketOperationsMixin: Bucket CRUD operations
    FileOperationsMixin: File upload/download/metadata/listing
    FileManagementMixin: File delete/copy/move operations
    AuthIntegrationMixin: Authentication middleware integration
    HealthCheckMixin: Health monitoring and status checks
"""

from .storage import Storage
from .base import StorageBase
from .bucket_operations import BucketOperationsMixin
from .file_operations import FileOperationsMixin
from .file_management import FileManagementMixin
from .auth_integration import AuthIntegrationMixin
from .health_check import HealthCheckMixin

__all__ = [
    "Storage",
    "StorageBase",
    "BucketOperationsMixin",
    "FileOperationsMixin", 
    "FileManagementMixin",
    "AuthIntegrationMixin",
    "HealthCheckMixin"
]

__version__ = "1.0.0"
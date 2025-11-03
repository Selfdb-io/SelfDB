"""
Backup Configuration Manager

Handles backup configuration from environment variables.
"""

import os
from typing import Optional


class BackupConfig:
    """Manages backup system configuration."""
    
    VALID_STORAGE_TYPES = ['local', 's3', 'gcs', 'azure']
    VALID_COMPRESSIONS = ['gzip', 'bzip2', 'xz', 'none']
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        self.storage_type = os.getenv('BACKUP_STORAGE_TYPE', 'local')
        self.local_path = os.getenv('BACKUP_LOCAL_PATH', '/tmp/selfdb_backups')
        self.compression = os.getenv('BACKUP_COMPRESSION', 'gzip')
        self.encryption = os.getenv('BACKUP_ENCRYPTION', 'false').lower() == 'true'
        
        # Parse retention days
        retention_str = os.getenv('BACKUP_RETENTION_DAYS', '30')
        try:
            self.retention_days = int(retention_str)
        except ValueError:
            raise ValueError(f"Invalid BACKUP_RETENTION_DAYS value: {retention_str}")
    
    def validate(self):
        """Validate the configuration."""
        if self.storage_type not in self.VALID_STORAGE_TYPES:
            raise ValueError(f"Invalid storage type: {self.storage_type}")
        
        if self.compression not in self.VALID_COMPRESSIONS:
            raise ValueError(f"Invalid compression type: {self.compression}")
        
        if self.retention_days <= 0:
            raise ValueError(f"Retention days must be positive: {self.retention_days}")
"""
Storage Backends for Backup System

Provides local filesystem storage for backups.
"""

import os
from pathlib import Path
from typing import List


class LocalStorageBackend:
    """Local filesystem storage backend for backups."""
    
    def __init__(self, base_path: str):
        """Initialize local storage backend."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def prepare_backup_location(self, volume_name: str, timestamp: str) -> str:
        """Prepare backup directory structure."""
        backup_dir = self.base_path / volume_name / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        return str(backup_dir)
    
    def store_backup(self, volume_name: str, timestamp: str, backup_data: bytes) -> str:
        """Store backup data to filesystem."""
        backup_dir = self.base_path / volume_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_file = backup_dir / f"{timestamp}.tar.gz"
        with open(backup_file, 'wb') as f:
            f.write(backup_data)
        
        return str(backup_file)
    
    def list_backups(self, volume_name: str) -> List[str]:
        """List available backups for a volume."""
        volume_dir = self.base_path / volume_name
        if not volume_dir.exists():
            return []
        
        backups = []
        for item in volume_dir.iterdir():
            if item.is_dir():
                backups.append(item.name)
        
        return sorted(backups)
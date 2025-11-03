"""
Backup Metadata Manager

Tracks backup metadata, checksums, and catalog information.
"""

import json
import hashlib
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional


class MetadataManager:
    """Manages backup metadata and tracking."""
    
    def __init__(self, metadata_path: str):
        """Initialize metadata manager."""
        self.metadata_path = Path(metadata_path)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        
        self.catalog_file = self.metadata_path / 'backup_catalog.json'
        self._load_catalog()
    
    def _load_catalog(self):
        """Load existing backup catalog or create new one."""
        if self.catalog_file.exists():
            with open(self.catalog_file, 'r') as f:
                self.catalog = json.load(f)
        else:
            self.catalog = {'backups': []}
    
    def _save_catalog(self):
        """Save backup catalog to disk."""
        with open(self.catalog_file, 'w') as f:
            json.dump(self.catalog, f, indent=2)
    
    def create_backup_record(self, backup_info: Dict[str, Any]) -> str:
        """Create a new backup record and return its ID."""
        record_id = str(uuid.uuid4())
        
        record = {
            'id': record_id,
            **backup_info
        }
        
        self.catalog['backups'].append(record)
        self._save_catalog()
        
        return record_id
    
    def get_backup_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a backup record by ID."""
        for record in self.catalog['backups']:
            if record['id'] == record_id:
                return record
        return None
    
    def list_records_for_volume(self, volume_name: str) -> List[Dict[str, Any]]:
        """List all backup records for a specific volume."""
        return [
            record for record in self.catalog['backups']
            if record.get('volume_name') == volume_name
        ]
    
    def calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum for a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
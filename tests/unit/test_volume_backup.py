"""
Unit tests for Docker Volume Backup System - Phase 1.4

Tests for Docker volume discovery, backup creation, storage, metadata tracking,
restore capabilities, scheduling, and retention policies using TDD principles.
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Import the modules we're testing
from shared.backup.volume_manager import VolumeManager
from shared.backup.backup_config import BackupConfig
from shared.backup.storage_backend import LocalStorageBackend
from shared.backup.metadata_manager import MetadataManager


class TestVolumeDiscovery:
    """Test Docker volume discovery and enumeration."""
    
    def test_volume_manager_initialization(self):
        """Test VolumeManager initializes with proper dependencies."""
        mock_docker_client = Mock()
        volume_manager = VolumeManager(docker_client=mock_docker_client)
        assert volume_manager.docker_client == mock_docker_client
    
    def test_list_docker_volumes(self):
        """Test listing all Docker volumes on the system."""
        # Mock Docker client for testing
        mock_docker_client = Mock()
        mock_volumes = Mock()
        mock_docker_client.volumes = mock_volumes
        
        # Mock volume data with proper name attribute
        mock_volume_1 = Mock()
        mock_volume_1.name = 'selfdb_postgres_data'
        mock_volume_1.attrs = {'Driver': 'local', 'Mountpoint': '/var/lib/docker/volumes/selfdb_postgres_data'}
        
        mock_volume_2 = Mock()
        mock_volume_2.name = 'selfdb_storage_data' 
        mock_volume_2.attrs = {'Driver': 'local', 'Mountpoint': '/var/lib/docker/volumes/selfdb_storage_data'}
        
        mock_volume_3 = Mock()
        mock_volume_3.name = 'test_volume'
        mock_volume_3.attrs = {'Driver': 'local', 'Mountpoint': '/var/lib/docker/volumes/test_volume'}
        
        mock_volume_data = [mock_volume_1, mock_volume_2, mock_volume_3]
        mock_volumes.list.return_value = mock_volume_data
        
        volume_manager = VolumeManager(docker_client=mock_docker_client)
        volumes = volume_manager.list_volumes()
        
        assert len(volumes) == 3
        assert any(vol['name'] == 'selfdb_postgres_data' for vol in volumes)
        assert any(vol['name'] == 'selfdb_storage_data' for vol in volumes)
    
    def test_filter_volumes_by_prefix(self):
        """Test filtering volumes by project prefix."""
        mock_docker_client = Mock()
        mock_volumes = Mock()
        mock_docker_client.volumes = mock_volumes
        
        # Mock volume data with proper name attribute
        mock_volume_1 = Mock()
        mock_volume_1.name = 'selfdb_postgres_data'
        mock_volume_1.attrs = {'Driver': 'local'}
        
        mock_volume_2 = Mock()
        mock_volume_2.name = 'selfdb_storage_data'
        mock_volume_2.attrs = {'Driver': 'local'}
        
        mock_volume_3 = Mock()
        mock_volume_3.name = 'other_project_data'
        mock_volume_3.attrs = {'Driver': 'local'}
        
        mock_volume_data = [mock_volume_1, mock_volume_2, mock_volume_3]
        mock_volumes.list.return_value = mock_volume_data
        
        volume_manager = VolumeManager(docker_client=mock_docker_client)
        selfdb_volumes = volume_manager.list_volumes(prefix='selfdb')
        
        assert len(selfdb_volumes) == 2
        assert all('selfdb' in vol['name'] for vol in selfdb_volumes)
    
    def test_get_volume_metadata(self):
        """Test retrieving detailed metadata for a specific volume."""
        mock_docker_client = Mock()
        mock_volume = Mock()
        mock_volume.attrs = {
            'Name': 'selfdb_postgres_data',
            'Driver': 'local',
            'Mountpoint': '/var/lib/docker/volumes/selfdb_postgres_data/_data',
            'CreatedAt': '2023-01-01T00:00:00Z',
            'Labels': {'com.docker.compose.project': 'selfdb'},
            'Options': {},
            'Scope': 'local'
        }
        mock_docker_client.volumes.get.return_value = mock_volume
        
        volume_manager = VolumeManager(docker_client=mock_docker_client)
        metadata = volume_manager.get_volume_metadata('selfdb_postgres_data')
        
        assert metadata['name'] == 'selfdb_postgres_data'
        assert metadata['driver'] == 'local'
        assert metadata['mountpoint'] == '/var/lib/docker/volumes/selfdb_postgres_data/_data'
        assert 'created_at' in metadata
        assert 'labels' in metadata


class TestBackupConfiguration:
    """Test backup configuration management."""
    
    def test_backup_config_initialization(self):
        """Test BackupConfig loads configuration from environment."""
        config = BackupConfig()
        assert config.storage_type == 'local'
        assert config.compression == 'gzip'
        assert config.retention_days == 30
    
    def test_backup_config_from_env_vars(self):
        """Test loading backup configuration from environment variables."""
        env_vars = {
            'BACKUP_STORAGE_TYPE': 'local',
            'BACKUP_LOCAL_PATH': '/tmp/selfdb_backups',
            'BACKUP_COMPRESSION': 'gzip',
            'BACKUP_ENCRYPTION': 'false',
            'BACKUP_RETENTION_DAYS': '30'
        }
        
        with patch.dict(os.environ, env_vars):
            config = BackupConfig()
            
            assert config.storage_type == 'local'
            assert config.local_path == '/tmp/selfdb_backups'
            assert config.compression == 'gzip'
            assert config.encryption is False
            assert config.retention_days == 30
    
    def test_backup_config_validation_invalid_retention(self):
        """Test backup configuration validation with invalid retention days."""
        invalid_env_vars = {
            'BACKUP_RETENTION_DAYS': 'not_a_number'
        }
        
        with patch.dict(os.environ, invalid_env_vars):
            with pytest.raises(ValueError, match="Invalid BACKUP_RETENTION_DAYS value"):
                config = BackupConfig()
    
    def test_backup_config_validation_invalid_storage_type(self):
        """Test backup configuration validation with invalid storage type."""
        env_vars = {
            'BACKUP_STORAGE_TYPE': 'invalid_type'
        }
        
        with patch.dict(os.environ, env_vars):
            config = BackupConfig()
            with pytest.raises(ValueError, match="Invalid storage type"):
                config.validate()
    
    def test_backup_config_validation_invalid_compression(self):
        """Test backup configuration validation with invalid compression type."""
        env_vars = {
            'BACKUP_COMPRESSION': 'invalid_compression'
        }
        
        with patch.dict(os.environ, env_vars):
            config = BackupConfig()
            with pytest.raises(ValueError, match="Invalid compression type"):
                config.validate()
    
    def test_backup_config_validation_negative_retention(self):
        """Test backup configuration validation with negative retention days."""
        env_vars = {
            'BACKUP_RETENTION_DAYS': '-5'
        }
        
        with patch.dict(os.environ, env_vars):
            config = BackupConfig()
            with pytest.raises(ValueError, match="Retention days must be positive"):
                config.validate()
    
    def test_backup_config_validation_zero_retention(self):
        """Test backup configuration validation with zero retention days."""
        env_vars = {
            'BACKUP_RETENTION_DAYS': '0'
        }
        
        with patch.dict(os.environ, env_vars):
            config = BackupConfig()
            with pytest.raises(ValueError, match="Retention days must be positive"):
                config.validate()


class TestLocalStorageBackend:
    """Test local filesystem storage backend."""
    
    def test_local_storage_initialization(self):
        """Test LocalStorageBackend initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalStorageBackend(base_path=temp_dir)
            assert storage.base_path == Path(temp_dir)
    
    def test_create_backup_directory_structure(self):
        """Test creating backup directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalStorageBackend(base_path=temp_dir)
            backup_path = storage.prepare_backup_location('selfdb_postgres_data', '2023-01-01T00:00:00Z')
            
            expected_path = Path(temp_dir) / 'selfdb_postgres_data' / '2023-01-01T00:00:00Z'
            assert backup_path == str(expected_path)
            assert expected_path.exists()
    
    def test_store_backup_file(self):
        """Test storing a backup file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_data = b"test backup data"
            
            storage = LocalStorageBackend(base_path=temp_dir)
            backup_path = storage.store_backup('selfdb_postgres_data', '2023-01-01', test_data)
            
            assert Path(backup_path).exists()
            with open(backup_path, 'rb') as f:
                assert f.read() == test_data
    
    def test_list_backups(self):
        """Test listing available backups for a volume."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some mock backup directories
            volume_dir = Path(temp_dir) / 'selfdb_postgres_data'
            (volume_dir / '2023-01-01T00:00:00Z').mkdir(parents=True)
            (volume_dir / '2023-01-02T00:00:00Z').mkdir(parents=True)
            
            storage = LocalStorageBackend(base_path=temp_dir)
            backups = storage.list_backups('selfdb_postgres_data')
            
            assert len(backups) == 2
            assert '2023-01-01T00:00:00Z' in backups
            assert '2023-01-02T00:00:00Z' in backups


class TestMetadataManager:
    """Test backup metadata tracking."""
    
    def test_metadata_manager_initialization(self):
        """Test MetadataManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_manager = MetadataManager(metadata_path=temp_dir)
            assert metadata_manager.metadata_path == Path(temp_dir)
    
    def test_create_backup_record(self):
        """Test creating a backup metadata record."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_info = {
                'volume_name': 'selfdb_postgres_data',
                'timestamp': '2023-01-01T00:00:00Z',
                'size': 1024,
                'compression': 'gzip',
                'checksum': 'abc123'
            }
            
            metadata_manager = MetadataManager(metadata_path=temp_dir)
            record_id = metadata_manager.create_backup_record(backup_info)
            
            assert record_id is not None
            # Verify the record was created
            record = metadata_manager.get_backup_record(record_id)
            assert record['volume_name'] == 'selfdb_postgres_data'
            assert record['timestamp'] == '2023-01-01T00:00:00Z'
    
    def test_list_backup_records_for_volume(self):
        """Test listing backup records for a specific volume."""
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_manager = MetadataManager(metadata_path=temp_dir)
            
            # Create multiple backup records
            metadata_manager.create_backup_record({
                'volume_name': 'selfdb_postgres_data',
                'timestamp': '2023-01-01T00:00:00Z'
            })
            metadata_manager.create_backup_record({
                'volume_name': 'selfdb_postgres_data',
                'timestamp': '2023-01-02T00:00:00Z'
            })
            metadata_manager.create_backup_record({
                'volume_name': 'other_volume',
                'timestamp': '2023-01-01T00:00:00Z'
            })
            
            postgres_records = metadata_manager.list_records_for_volume('selfdb_postgres_data')
            assert len(postgres_records) == 2
    
    def test_calculate_and_store_checksum(self):
        """Test calculating and storing backup checksums."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / 'test_backup.tar.gz'
            test_data = b"test backup content for checksum"
            test_file.write_bytes(test_data)
            
            metadata_manager = MetadataManager(metadata_path=temp_dir)
            checksum = metadata_manager.calculate_checksum(str(test_file))
            
            assert checksum is not None
            assert len(checksum) > 0
            # Verify checksum is consistent
            checksum2 = metadata_manager.calculate_checksum(str(test_file))
            assert checksum == checksum2
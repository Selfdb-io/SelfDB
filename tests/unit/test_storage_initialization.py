"""
Unit tests for storage service initialization and configuration.

Tests storage service initialization, configuration, and basic setup.
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Optional, Dict, Any


class TestStorageInitialization:
    """Test suite for storage service initialization and configuration."""
    
    @pytest.fixture
    def config_manager(self):
        """Mock ConfigManager for testing."""
        manager = Mock()
        manager.get_port.return_value = 8001
        manager.get_setting.return_value = "test_value"
        return manager
    
    @pytest.fixture
    def auth_middleware(self):
        """Mock authentication middleware."""
        return Mock()
    
    def test_storage_initialization(self, config_manager, auth_middleware):
        """Test Storage initialization with required dependencies."""
        from storage.storage import Storage
        
        service = Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware,
            storage_backend="minio",
            enable_streaming=True
        )
        
        assert service.config_manager == config_manager
        assert service.auth_middleware == auth_middleware
        assert service.storage_backend == "minio"
        assert service.enable_streaming is True
        assert service.is_internal_only() is True  # Must be internal-only by design
    
    def test_storage_default_configuration(self, config_manager, auth_middleware):
        """Test Storage with default configuration values."""
        from storage.storage import Storage
        
        service = Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
        
        # Verify defaults
        assert service.storage_backend == "minio"  # Default backend
        assert service.enable_streaming is True   # Default streaming enabled
        assert service.is_internal_only() is True      # Always internal-only
        assert service.get_port() == 8001               # Port comes from config_manager
    
    def test_storage_missing_config_manager_raises_error(self, auth_middleware):
        """Test that missing ConfigManager raises initialization error."""
        from storage.storage import Storage
        
        with pytest.raises(ValueError, match="ConfigManager must be provided"):
            Storage(
                config_manager=None,
                auth_middleware=auth_middleware
            )
    
    def test_storage_missing_auth_middleware_raises_error(self, config_manager):
        """Test that missing authentication middleware raises error."""
        from storage.storage import Storage
        
        with pytest.raises(ValueError, match="Authentication middleware must be provided"):
            Storage(
                config_manager=config_manager,
                auth_middleware=None
            )
    
    def test_storage_invalid_backend_raises_error(self, config_manager, auth_middleware):
        """Test that invalid storage backend raises error."""
        from storage.storage import Storage
        
        with pytest.raises(ValueError, match="Unsupported storage backend"):
            Storage(
                config_manager=config_manager,
                auth_middleware=auth_middleware,
                storage_backend="invalid_backend"
            )
    
    def test_storage_get_port_from_config(self, config_manager, auth_middleware):
        """Test that storage service gets port from ConfigManager."""
        from storage.storage import Storage
        
        # Configure mock to return specific port
        config_manager.get_port.return_value = 8003
        
        service = Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
        
        port = service.get_port()
        
        assert port == 8003
        config_manager.get_port.assert_called_once()
    
    def test_storage_get_configuration_settings(self, config_manager, auth_middleware):
        """Test that storage service can retrieve configuration settings."""
        from storage.storage import Storage
        
        service = Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
        
        config = service.get_configuration()
        
        assert config["storage_backend"] == "minio"
        assert config["streaming_enabled"] is True
        assert config["internal_only"] is True
        assert "port" in config
    
    def test_storage_supported_backends_list(self, config_manager, auth_middleware):
        """Test getting list of supported storage backends."""
        from storage.storage import Storage
        
        service = Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
        
        supported_backends = service.SUPPORTED_BACKENDS
        
        expected_backends = ["minio", "local", "s3"]
        assert all(backend in supported_backends for backend in expected_backends)
        assert len(supported_backends) >= 3
    
    def test_storage_service_info(self, config_manager, auth_middleware):
        """Test getting comprehensive service information."""
        from storage.storage import Storage
        
        service = Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
        
        service_info = service.get_service_info()
        
        assert service_info["name"] == "SelfDB Storage Service"
        assert service_info["version"] == "1.0.0"
        assert service_info["internal_only"] is True
        assert "capabilities" in service_info
        assert "bucket_management" in service_info["capabilities"]
        assert "file_upload_download" in service_info["capabilities"]
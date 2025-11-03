"""
Unit tests for storage service internal-only network access validation.

Tests network access validation, CORS handling, and internal service resolution.
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Optional, Dict, Any


class TestStorageNetworkAccess:
    """Test suite for internal-only network access validation."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        # Mock different ports for different services
        def mock_get_setting(service):
            port_map = {
                "backend_port": 8000,
                "functions_port": 8002,
                "auth_port": 8001,
                "storage_port": 8003
            }
            return port_map.get(service, 8003)
        
        config_manager.get_port.return_value = 8003
        config_manager.get_setting.side_effect = mock_get_setting
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
    
    def test_storage_is_internal_only_by_design(self, storage):
        """Test that storage service is always internal-only."""
        assert storage.is_internal_only() is True
        assert storage.has_external_endpoint() is False
    
    def test_storage_get_allowed_internal_services(self, storage):
        """Test that storage service returns allowed internal services."""
        allowed_services = storage.get_allowed_internal_services()
        
        expected_services = ["backend", "functions", "docker_network"]
        
        for service in expected_services:
            assert service in allowed_services
    
    def test_storage_validates_internal_network_access(self, storage):
        """Test that storage service validates internal network access."""
        # Test internal IP addresses (Docker networks and localhost only for storage service)
        internal_addresses = [
            "127.0.0.1",      # localhost
            "::1",            # localhost IPv6
            "172.18.0.1",     # Docker network
            "172.17.0.1"      # Docker bridge
        ]
        
        for address in internal_addresses:
            is_internal = storage.validate_internal_network_access(address)
            assert is_internal is True, f"Address {address} should be considered internal"
    
    def test_storage_blocks_external_network_access(self, storage):
        """Test that storage service blocks external network access."""
        # Test external IP addresses (including private networks that aren't Docker)
        external_addresses = [
            "8.8.8.8",        # Google DNS
            "1.1.1.1",        # Cloudflare DNS
            "203.0.113.1",    # Test external IP
            "10.0.0.1",       # Private class A (not allowed for storage)
            "192.168.1.1"     # Private class C (not allowed for storage)
        ]
        
        for address in external_addresses:
            is_internal = storage.validate_internal_network_access(address)
            assert is_internal is False, f"Address {address} should be considered external"
    
    def test_storage_validates_cors_for_internal_only(self, storage):
        """Test CORS validation specifically for internal-only access."""
        # Internal origins should be allowed (storage service is very restrictive)
        internal_origins = [
            "http://backend",
            "http://functions",
            None  # No origin header for service-to-service
        ]
        
        for origin in internal_origins:
            cors_valid = storage.validate_cors_for_internal_only(origin)
            assert cors_valid is True, f"Origin {origin} should be allowed for internal service"
        
        # External origins should be blocked (including localhost for storage service)
        external_origins = [
            "http://localhost",
            "https://localhost", 
            "http://127.0.0.1",
            "http://example.com",
            "https://external-site.com",
            "http://192.168.1.100:8001"
        ]
        
        for origin in external_origins:
            cors_valid = storage.validate_cors_for_internal_only(origin)
            assert cors_valid is False, f"Origin {origin} should be blocked for internal-only service"
    
    def test_storage_internal_services_discovery(self, storage):
        """Test that storage service can discover internal services."""
        service_discovery = storage.get_internal_services_discovery()
        
        # Should contain at least the core services
        expected_services = ["backend", "functions", "auth", "storage"]
        
        for service in expected_services:
            assert service in service_discovery
            # Should be in format "service:port"
            service_address = service_discovery[service]
            assert ":" in service_address
            assert service in service_address
    
    def test_storage_configuration_includes_network_settings(self, storage):
        """Test that configuration includes network access settings."""
        config = storage.get_configuration()
        
        assert config["internal_only"] is True
        assert "port" in config
        assert "supported_backends" in config
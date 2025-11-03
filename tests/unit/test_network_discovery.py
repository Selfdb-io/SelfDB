"""
Test suite for Network Discovery & Container Communication System - Phase 1.2

This test suite defines the behavior for SelfDB's network discovery and container 
communication system, addressing the core issue that frontend hardcodes localhost URLs 
causing cross-device access failures.

Tests define requirements before implementation (TDD Red-Green-Refactor).
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path

# Import the network discovery system (will fail initially - that's expected!)
from shared.network.network_discovery import NetworkDiscovery, NetworkDiscoveryError
from shared.network.service_resolver import ServiceResolver
from shared.network.proxy_config import ProxyConfigGenerator
from shared.network.network_validator import NetworkValidator


class TestServiceNameResolution:
    """Test Docker container service name resolution"""
    
    def test_resolve_service_with_compose_project_name(self):
        """Test that service resolution considers COMPOSE_PROJECT_NAME"""
        # GIVEN: Environment with specific COMPOSE_PROJECT_NAME
        env_vars = {
            'COMPOSE_PROJECT_NAME': 'selfdb_dev',
            'DOCKER_ENV': 'true'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # WHEN: NetworkDiscovery resolves service names
            network_discovery = NetworkDiscovery()
            
            # THEN: Service names include project prefix
            assert network_discovery.resolve_service_name('postgres') == 'selfdb_dev_postgres'
            assert network_discovery.resolve_service_name('backend') == 'selfdb_dev_backend'
            assert network_discovery.resolve_service_name('storage') == 'selfdb_dev_storage'
    
    def test_resolve_service_without_compose_project_name(self):
        """Test fallback when COMPOSE_PROJECT_NAME is not set"""
        # GIVEN: Environment without COMPOSE_PROJECT_NAME
        with patch.dict(os.environ, {}, clear=True):
            # WHEN: NetworkDiscovery resolves service names
            network_discovery = NetworkDiscovery()
            
            # THEN: Service names use default 'selfdb' prefix
            assert network_discovery.resolve_service_name('postgres') == 'selfdb_postgres'
            assert network_discovery.resolve_service_name('backend') == 'selfdb_backend'
    
    def test_resolve_service_in_development_mode(self):
        """Test that development mode uses localhost"""
        # GIVEN: Development environment (non-Docker)
        with patch.dict(os.environ, {'DOCKER_ENV': 'false'}, clear=True):
            # WHEN: NetworkDiscovery resolves service names
            network_discovery = NetworkDiscovery()
            
            # THEN: Service names remain as-is for localhost usage
            assert network_discovery.resolve_service_name('postgres') == 'postgres'
            assert network_discovery.resolve_service_name('backend') == 'backend'
    
    def test_get_internal_service_url_docker_environment(self):
        """Test internal service URL generation in Docker environment"""
        # GIVEN: Docker environment configuration
        env_vars = {
            'DOCKER_ENV': 'true',
            'COMPOSE_PROJECT_NAME': 'selfdb_staging'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            network_discovery = NetworkDiscovery()
            
            # WHEN: Getting internal service URLs
            backend_url = network_discovery.get_internal_service_url('backend', 8000)
            postgres_url = network_discovery.get_internal_service_url('postgres', 5432)
            
            # THEN: URLs use Docker service names with project prefix
            assert backend_url == 'http://selfdb_staging_backend:8000'
            assert postgres_url == 'postgresql://selfdb_staging_postgres:5432'
    
    def test_get_external_service_url_for_client_access(self):
        """Test external service URL generation for client/browser access"""
        # GIVEN: Configuration with specific ports
        env_vars = {
            'API_PORT': '8001',
            'FRONTEND_PORT': '3001'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            network_discovery = NetworkDiscovery()
            
            # WHEN: Getting external service URLs
            backend_url = network_discovery.get_external_service_url('backend')
            frontend_url = network_discovery.get_external_service_url('frontend')
            
            # THEN: URLs use configured external ports for client access
            assert backend_url == 'http://localhost:8001'
            assert frontend_url == 'http://localhost:3001'


class TestCrossEnvironmentCompatibility:
    """Test service discovery across dev/staging/prod environments"""
    
    def test_dev_environment_service_discovery(self):
        """Test service discovery in development environment"""
        # GIVEN: Development environment configuration
        env_vars = {
            'ENV': 'dev',
            'COMPOSE_PROJECT_NAME': 'selfdb_dev',
            'DOCKER_ENV': 'true'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            network_discovery = NetworkDiscovery()
            
            # WHEN: Discovering services in dev environment
            services = network_discovery.discover_available_services()
            
            # THEN: All expected services are discovered with dev prefix
            expected_services = ['postgres', 'backend', 'storage', 'frontend', 'deno-runtime']
            for service in expected_services:
                assert f'selfdb_dev_{service}' in services
    
    def test_staging_environment_service_discovery(self):
        """Test service discovery in staging environment"""
        # GIVEN: Staging environment configuration
        env_vars = {
            'ENV': 'staging',
            'COMPOSE_PROJECT_NAME': 'selfdb_staging',
            'DOCKER_ENV': 'true'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            network_discovery = NetworkDiscovery()
            
            # WHEN: Discovering services in staging environment
            services = network_discovery.discover_available_services()
            
            # THEN: Services use staging prefix
            assert 'selfdb_staging_postgres' in services
            assert 'selfdb_staging_backend' in services
    
    def test_production_environment_service_discovery(self):
        """Test service discovery in production environment"""
        # GIVEN: Production environment configuration
        env_vars = {
            'ENV': 'prod',
            'COMPOSE_PROJECT_NAME': 'selfdb_prod',
            'DOCKER_ENV': 'true'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            network_discovery = NetworkDiscovery()
            
            # WHEN: Discovering services in production environment
            services = network_discovery.discover_available_services()
            
            # THEN: Services use production prefix
            assert 'selfdb_prod_postgres' in services
            assert 'selfdb_prod_backend' in services


class TestNetworkReachabilityTesting:
    """Test network connectivity and reachability validation"""
    
    def test_check_service_reachability_success(self):
        """Test successful service reachability check"""
        # GIVEN: NetworkValidator with mocked successful connection
        with patch('socket.create_connection') as mock_connection:
            mock_connection.return_value = MagicMock()
            validator = NetworkValidator()
            
            # WHEN: Checking if service is reachable
            is_reachable = validator.check_service_reachability('backend', 8000)
            
            # THEN: Service is reported as reachable
            assert is_reachable is True
            mock_connection.assert_called_once_with(('backend', 8000), timeout=5)
    
    def test_check_service_reachability_failure(self):
        """Test failed service reachability check"""
        # GIVEN: NetworkValidator with mocked failed connection
        with patch('socket.create_connection') as mock_connection:
            mock_connection.side_effect = ConnectionError("Connection refused")
            validator = NetworkValidator()
            
            # WHEN: Checking if service is reachable
            is_reachable = validator.check_service_reachability('backend', 8000)
            
            # THEN: Service is reported as not reachable
            assert is_reachable is False
    
    def test_validate_all_services_connectivity(self):
        """Test validation of connectivity to all required services"""
        # GIVEN: NetworkValidator and service configuration
        env_vars = {
            'DOCKER_ENV': 'true',
            'COMPOSE_PROJECT_NAME': 'selfdb_test'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('socket.create_connection') as mock_connection:
                mock_connection.return_value = MagicMock()
                validator = NetworkValidator()
                
                # WHEN: Validating connectivity to all services
                results = validator.validate_all_services_connectivity()
                
                # THEN: All services are validated
                expected_services = ['postgres', 'backend', 'storage', 'deno-runtime']
                for service in expected_services:
                    assert service in results
                    assert results[service] is True
    
    def test_network_health_check_with_failures(self):
        """Test network health check identifies failing services"""
        # GIVEN: NetworkValidator with some services failing
        def mock_connection_side_effect(address, timeout=None):
            host, port = address
            if 'postgres' in host:
                raise ConnectionError("Connection refused")
            return MagicMock()
        
        with patch('socket.create_connection') as mock_connection:
            mock_connection.side_effect = mock_connection_side_effect
            validator = NetworkValidator()
            
            # WHEN: Running network health check
            health_status = validator.network_health_check()
            
            # THEN: Failed services are identified
            assert health_status['status'] == 'degraded'
            assert 'postgres' in health_status['failed_services']
            assert len(health_status['healthy_services']) > 0


class TestDynamicURLGeneration:
    """Test dynamic URL generation based on request context"""
    
    def test_generate_frontend_api_urls_for_internal_requests(self):
        """Test API URL generation for internal container requests"""
        # GIVEN: ServiceResolver configured for internal requests
        env_vars = {
            'DOCKER_ENV': 'true',
            'COMPOSE_PROJECT_NAME': 'selfdb_app'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            resolver = ServiceResolver()
            
            # WHEN: Generating API URLs for internal use
            api_config = resolver.generate_api_urls(context='internal')
            
            # THEN: URLs use Docker service names
            assert api_config['backend_url'] == 'http://selfdb_app_backend:8000'
            assert api_config['storage_url'] == 'http://selfdb_app_storage:8001'
            assert api_config['functions_url'] == 'http://selfdb_app_deno-runtime:8090'
    
    def test_generate_frontend_api_urls_for_external_requests(self):
        """Test API URL generation for external browser requests"""
        # GIVEN: ServiceResolver configured for external requests
        env_vars = {
            'API_PORT': '8000',
            'STORAGE_PORT': '8001',
            'DENO_PORT': '8090'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            resolver = ServiceResolver()
            
            # WHEN: Generating API URLs for external use
            api_config = resolver.generate_api_urls(context='external')
            
            # THEN: URLs use localhost with configured ports
            assert api_config['backend_url'] == 'http://localhost:8000'
            assert api_config['storage_url'] == 'http://localhost:8001'
            assert api_config['functions_url'] == 'http://localhost:8090'
    
    def test_generate_urls_with_custom_host(self):
        """Test URL generation with custom host (for remote/mobile access)"""
        # GIVEN: ServiceResolver with custom host configuration
        resolver = ServiceResolver()
        
        # WHEN: Generating URLs with custom host
        api_config = resolver.generate_api_urls(
            context='external', 
            host='192.168.1.100'
        )
        
        # THEN: URLs use the specified host
        assert api_config['backend_url'] == 'http://192.168.1.100:8000'
        assert api_config['storage_url'] == 'http://192.168.1.100:8001'
        assert api_config['functions_url'] == 'http://192.168.1.100:8090'
    
    def test_context_aware_url_resolution(self):
        """Test that URL resolution adapts to request context"""
        # GIVEN: ServiceResolver with context detection
        resolver = ServiceResolver()
        
        # Mock request context detection
        with patch.object(resolver, '_detect_request_context') as mock_detect:
            mock_detect.return_value = 'mobile_browser'
            
            # WHEN: Resolving URLs with context detection
            urls = resolver.resolve_urls_for_client()
            
            # THEN: URLs are optimized for mobile browser context
            assert 'localhost' in urls['backend_url']  # Should use external URLs


class TestProxyMiddlewareConfiguration:
    """Test frontend proxy middleware for internal service routing"""
    
    def test_generate_proxy_config_for_development(self):
        """Test proxy configuration generation for development environment"""
        # GIVEN: ProxyConfigGenerator in development mode
        env_vars = {
            'NODE_ENV': 'development',
            'API_PORT': '8000',
            'STORAGE_PORT': '8001'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            generator = ProxyConfigGenerator()
            
            # WHEN: Generating proxy configuration
            proxy_config = generator.generate_proxy_config()
            
            # THEN: Proxy routes to localhost services
            assert '/api' in proxy_config
            assert proxy_config['/api']['target'] == 'http://localhost:8000'
            assert '/storage' in proxy_config
            assert proxy_config['/storage']['target'] == 'http://localhost:8001'
    
    def test_generate_proxy_config_for_docker_environment(self):
        """Test proxy configuration for Docker container environment"""
        # GIVEN: ProxyConfigGenerator in Docker environment
        env_vars = {
            'DOCKER_ENV': 'true',
            'COMPOSE_PROJECT_NAME': 'selfdb_docker'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            generator = ProxyConfigGenerator()
            
            # WHEN: Generating proxy configuration
            proxy_config = generator.generate_proxy_config()
            
            # THEN: Proxy routes to Docker service names
            assert proxy_config['/api']['target'] == 'http://selfdb_docker_backend:8000'
            assert proxy_config['/storage']['target'] == 'http://selfdb_docker_storage:8001'
    
    def test_generate_webpack_proxy_configuration(self):
        """Test Webpack development server proxy configuration"""
        # GIVEN: ProxyConfigGenerator for Webpack
        generator = ProxyConfigGenerator()
        
        # WHEN: Generating Webpack proxy configuration
        webpack_config = generator.generate_webpack_proxy_config()
        
        # THEN: Configuration is in Webpack format
        assert 'proxy' in webpack_config
        proxy_rules = webpack_config['proxy']
        
        # Check API proxy rule
        api_rule = next(rule for rule in proxy_rules if rule['context'] == ['/api/**'])
        assert 'target' in api_rule
        assert 'changeOrigin' in api_rule
        assert api_rule['changeOrigin'] is True
    
    def test_generate_nginx_proxy_configuration(self):
        """Test Nginx proxy configuration generation"""
        # GIVEN: ProxyConfigGenerator for Nginx
        generator = ProxyConfigGenerator()
        
        # WHEN: Generating Nginx proxy configuration
        nginx_config = generator.generate_nginx_proxy_config()
        
        # THEN: Configuration includes proxy_pass directives
        assert 'location /api' in nginx_config
        assert 'proxy_pass' in nginx_config
        assert 'location /storage' in nginx_config


class TestNetworkSecurityBoundaries:
    """Test network isolation and security boundary validation"""
    
    def test_validate_network_isolation_between_environments(self):
        """Test that different environments are properly isolated"""
        # GIVEN: NetworkValidator with environment isolation checks
        validator = NetworkValidator()
        
        # WHEN: Validating network isolation
        isolation_status = validator.validate_network_isolation()
        
        # THEN: Network isolation is properly configured
        assert isolation_status['isolated'] is True
        assert 'selfdb_network' in isolation_status['networks']
        assert isolation_status['external_access_controlled'] is True
    
    def test_validate_service_access_permissions(self):
        """Test validation of service-to-service access permissions"""
        # GIVEN: NetworkValidator with access control rules
        validator = NetworkValidator()
        
        # WHEN: Validating service access permissions
        permissions = validator.validate_service_permissions()
        
        # THEN: Only authorized service communications are allowed
        assert permissions['backend_to_postgres'] is True
        assert permissions['backend_to_storage'] is True
        assert permissions['frontend_to_backend'] is True
        # External access should be controlled
        assert permissions['external_to_postgres'] is False
    
    def test_detect_security_vulnerabilities(self):
        """Test detection of network security vulnerabilities"""
        # GIVEN: NetworkValidator with security scanning
        validator = NetworkValidator()
        
        # WHEN: Scanning for security vulnerabilities
        vulnerabilities = validator.scan_network_security()
        
        # THEN: Security assessment is provided
        assert 'open_ports' in vulnerabilities
        assert 'exposed_services' in vulnerabilities
        assert 'network_policies' in vulnerabilities
        assert vulnerabilities['risk_level'] in ['low', 'medium', 'high']


class TestDockerNetworkConnectivity:
    """Test Docker network connectivity and container discovery"""
    
    def test_discover_containers_on_selfdb_network(self):
        """Test discovery of containers on the selfdb_network"""
        # GIVEN: NetworkDiscovery with Docker API access
        with patch('docker.from_env') as mock_docker:
            # Mock Docker client and containers
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            # Mock container list
            mock_postgres = MagicMock()
            mock_postgres.name = 'selfdb_postgres'
            mock_postgres.attrs = {'NetworkSettings': {'Networks': {'selfdb_network': {}}}}
            
            mock_backend = MagicMock()
            mock_backend.name = 'selfdb_backend' 
            mock_backend.attrs = {'NetworkSettings': {'Networks': {'selfdb_network': {}}}}
            
            mock_containers = [mock_postgres, mock_backend]
            mock_client.containers.list.return_value = mock_containers
            
            network_discovery = NetworkDiscovery()
            
            # WHEN: Discovering containers on network
            containers = network_discovery.discover_containers_on_network('selfdb_network')
            
            # THEN: All containers on the network are discovered
            assert len(containers) == 2
            container_names = [c.name for c in containers]
            assert 'selfdb_postgres' in container_names
            assert 'selfdb_backend' in container_names
    
    def test_get_container_network_info(self):
        """Test retrieval of container network information"""
        # GIVEN: NetworkDiscovery with container network details
        with patch('docker.from_env') as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            # Mock container with network info
            mock_container = MagicMock()
            mock_container.attrs = {
                'NetworkSettings': {
                    'Networks': {
                        'selfdb_network': {
                            'IPAddress': '172.20.0.2',
                            'Aliases': ['postgres', 'selfdb_postgres']
                        }
                    }
                }
            }
            mock_client.containers.get.return_value = mock_container
            
            network_discovery = NetworkDiscovery()
            
            # WHEN: Getting container network info
            network_info = network_discovery.get_container_network_info('selfdb_postgres')
            
            # THEN: Network information is correctly extracted
            assert network_info['ip_address'] == '172.20.0.2'
            assert 'postgres' in network_info['aliases']
            assert 'selfdb_postgres' in network_info['aliases']
    
    def test_docker_network_health_monitoring(self):
        """Test monitoring of Docker network health"""
        # GIVEN: NetworkValidator with Docker network monitoring
        validator = NetworkValidator()
        
        # WHEN: Monitoring Docker network health
        with patch.object(validator, '_check_docker_network_status') as mock_check:
            mock_check.return_value = {
                'network_exists': True,
                'containers_connected': 5,
                'network_driver': 'bridge'
            }
            
            health_status = validator.monitor_docker_network_health()
            
            # THEN: Network health status is comprehensive
            assert health_status['network_operational'] is True
            assert health_status['containers_connected'] == 5
            assert 'bridge' in health_status['network_config']['driver']


class TestNetworkDiscoveryIntegration:
    """Integration tests for the complete Network Discovery system"""
    
    def test_full_service_discovery_workflow(self):
        """Test complete workflow from service discovery to URL generation"""
        # GIVEN: Complete network discovery configuration
        env_vars = {
            'DOCKER_ENV': 'true',
            'COMPOSE_PROJECT_NAME': 'selfdb_integration',
            'API_PORT': '8000',
            'STORAGE_PORT': '8001'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # WHEN: Running full service discovery workflow
            network_discovery = NetworkDiscovery()
            resolver = ServiceResolver()
            
            # Discover services
            services = network_discovery.discover_available_services()
            
            # Generate URLs for different contexts
            internal_urls = resolver.generate_api_urls(context='internal')
            external_urls = resolver.generate_api_urls(context='external')
            
            # THEN: Complete workflow produces expected results
            assert 'selfdb_integration_backend' in services
            assert internal_urls['backend_url'] == 'http://selfdb_integration_backend:8000'
            assert external_urls['backend_url'] == 'http://localhost:8000'
    
    def test_cross_device_access_configuration(self):
        """Test configuration for cross-device access (mobile/remote)"""
        # GIVEN: Configuration for cross-device access
        resolver = ServiceResolver()
        generator = ProxyConfigGenerator()
        
        # WHEN: Generating configuration for cross-device access
        mobile_urls = resolver.generate_api_urls(
            context='external', 
            host='192.168.1.50'  # Local network IP
        )
        proxy_config = generator.generate_proxy_config()
        
        # THEN: Configuration supports cross-device access
        assert '192.168.1.50' in mobile_urls['backend_url']
        assert 'target' in proxy_config['/api']
        # Proxy should handle CORS and routing properly
        assert proxy_config['/api'].get('changeOrigin', False) is True
    
    def test_environment_migration_compatibility(self):
        """Test compatibility when migrating between environments"""
        # GIVEN: NetworkDiscovery that handles environment transitions
        environments = [
            {'ENV': 'dev', 'COMPOSE_PROJECT_NAME': 'selfdb_dev'},
            {'ENV': 'staging', 'COMPOSE_PROJECT_NAME': 'selfdb_staging'},
            {'ENV': 'prod', 'COMPOSE_PROJECT_NAME': 'selfdb_prod'}
        ]
        
        for env_config in environments:
            with patch.dict(os.environ, env_config, clear=True):
                # WHEN: Initializing NetworkDiscovery in each environment
                network_discovery = NetworkDiscovery()
                
                # THEN: Service discovery adapts to environment
                postgres_name = network_discovery.resolve_service_name('postgres')
                expected_name = f"{env_config['COMPOSE_PROJECT_NAME']}_postgres"
                assert postgres_name == expected_name


class TestNetworkDiscoveryEdgeCases:
    """Test edge cases and error handling in NetworkDiscovery"""
    
    def test_get_internal_service_url_non_docker_postgres(self):
        """Test internal service URL for postgres in non-Docker environment (lines 70-71)"""
        # GIVEN: Non-Docker environment configuration
        env_vars = {
            'DOCKER_ENV': 'false',
            'COMPOSE_PROJECT_NAME': 'selfdb_test'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            network_discovery = NetworkDiscovery()
            
            # WHEN: Getting internal postgres URL in non-Docker
            postgres_url = network_discovery.get_internal_service_url('postgres', 5432)
            
            # THEN: URL uses localhost for non-Docker postgres (line 71)
            assert postgres_url == 'postgresql://localhost:5432'
    
    def test_get_internal_service_url_non_docker_other_services(self):
        """Test internal service URL for non-postgres services in non-Docker (lines 72-73)"""
        # GIVEN: Non-Docker environment configuration
        env_vars = {
            'DOCKER_ENV': 'false',
            'COMPOSE_PROJECT_NAME': 'selfdb_test'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            network_discovery = NetworkDiscovery()
            
            # WHEN: Getting internal URLs for other services in non-Docker
            backend_url = network_discovery.get_internal_service_url('backend', 8000)
            storage_url = network_discovery.get_internal_service_url('storage', 8001)
            
            # THEN: URLs use localhost for non-Docker services (line 73)
            assert backend_url == 'http://localhost:8000'
            assert storage_url == 'http://localhost:8001'
    
    def test_discover_available_services_non_docker(self):
        """Test service discovery in non-Docker environment (line 100)"""
        # GIVEN: Non-Docker environment configuration
        env_vars = {
            'DOCKER_ENV': 'false'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            network_discovery = NetworkDiscovery()
            
            # WHEN: Discovering services in non-Docker environment
            services = network_discovery.discover_available_services()
            
            # THEN: Services are returned without prefixes (line 100)
            expected_services = ['postgres', 'backend', 'storage', 'frontend', 'deno-runtime']
            assert services == expected_services
    
    def test_discover_containers_on_network_exception_handling(self):
        """Test exception handling in discover_containers_on_network (lines 124-126)"""
        # GIVEN: NetworkDiscovery with Docker API that raises exception
        with patch('docker.from_env') as mock_docker:
            # Mock Docker client to raise exception
            mock_docker.side_effect = Exception("Docker not available")
            
            network_discovery = NetworkDiscovery()
            
            # WHEN: Trying to discover containers when Docker fails
            containers = network_discovery.discover_containers_on_network('selfdb_network')
            
            # THEN: Empty list is returned on exception (line 126)
            assert containers == []
    
    def test_discover_containers_on_network_container_list_exception(self):
        """Test exception handling when listing containers fails (lines 124-126)"""
        # GIVEN: NetworkDiscovery with Docker client that fails on list()
        with patch('docker.from_env') as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            # Make containers.list() raise exception
            mock_client.containers.list.side_effect = Exception("Failed to list containers")
            
            network_discovery = NetworkDiscovery()
            
            # WHEN: Trying to discover containers when list fails
            containers = network_discovery.discover_containers_on_network('selfdb_network')
            
            # THEN: Empty list is returned on exception (lines 124-126)
            assert containers == []
    
    def test_get_container_network_info_exception_handling(self):
        """Test exception handling in get_container_network_info (lines 153-154)"""
        # GIVEN: NetworkDiscovery with Docker API that raises exception
        with patch('docker.from_env') as mock_docker:
            # Mock Docker client to raise exception
            mock_docker.side_effect = Exception("Docker not available")
            
            network_discovery = NetworkDiscovery()
            
            # WHEN: Trying to get container network info when Docker fails
            network_info = network_discovery.get_container_network_info('test_container')
            
            # THEN: Default network info is returned (line 154)
            assert network_info == {'ip_address': None, 'aliases': []}
    
    def test_get_container_network_info_container_not_found(self):
        """Test exception handling when container not found (lines 153-154)"""
        # GIVEN: NetworkDiscovery with Docker client that can't find container
        with patch('docker.from_env') as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            # Make containers.get() raise exception for container not found
            mock_client.containers.get.side_effect = Exception("Container not found")
            
            network_discovery = NetworkDiscovery()
            
            # WHEN: Trying to get network info for non-existent container
            network_info = network_discovery.get_container_network_info('nonexistent_container')
            
            # THEN: Default network info is returned (lines 153-154)
            assert network_info == {'ip_address': None, 'aliases': []}
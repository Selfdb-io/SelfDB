"""
Test suite for Configuration Management System - Phase 1.1

This test suite defines the behavior for SelfDB's configuration management system,
addressing the core issue that only 2/5 services currently have configurable ports.

Tests define requirements before implementation (TDD Red-Green-Refactor).
"""
import pytest
import os
import tempfile
from unittest.mock import patch, mock_open
from pathlib import Path

# Import the configuration system (will fail initially - that's expected!)
from shared.config.config_manager import ConfigManager, ConfigValidationError


class TestPortConfiguration:
    """Test port configuration from environment variables for all services"""
    
    def test_all_service_ports_configurable_from_env(self):
        """Test that all 5 services can have their ports configured via environment variables"""
        # GIVEN: Environment variables for all service ports
        env_vars = {
            'POSTGRES_PORT': '5433',
            'STORAGE_PORT': '8002', 
            'API_PORT': '8001',
            'FRONTEND_PORT': '3001',
            'DENO_PORT': '8091'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            # WHEN: ConfigManager loads configuration
            config = ConfigManager()
            
            # THEN: All ports are configurable and loaded correctly
            assert config.get_port('postgres') == 5433
            assert config.get_port('storage') == 8002
            assert config.get_port('backend') == 8001
            assert config.get_port('frontend') == 3001
            assert config.get_port('deno-runtime') == 8091
    
    def test_missing_env_vars_raises_validation_error(self):
        """Test that missing required environment variables raise ConfigValidationError"""
        # GIVEN: No port environment variables in environment or files
        with patch.dict(os.environ, {}, clear=True):
            with patch('shared.config.config_manager.ConfigManager._load_env_files'):
                # WHEN: ConfigManager attempts to load configuration with no env files
                # THEN: ConfigValidationError is raised for missing required vars
                with pytest.raises(ConfigValidationError) as exc_info:
                    ConfigManager()
                
                assert "Required environment variable" in str(exc_info.value)
    
    def test_partial_port_configuration_raises_error(self):
        """Test that partial port configuration raises ConfigValidationError"""
        # GIVEN: Only some ports configured (missing required ones)
        env_vars = {
            'POSTGRES_PORT': '5433',
            'FRONTEND_PORT': '3001'
            # Missing STORAGE_PORT, API_PORT, DENO_PORT
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('shared.config.config_manager.ConfigManager._load_env_files'):
                # WHEN: ConfigManager attempts to load configuration
                # THEN: ConfigValidationError is raised for missing ports
                with pytest.raises(ConfigValidationError) as exc_info:
                    ConfigManager()
                
                assert "Required environment variable" in str(exc_info.value)


class TestMultiInstanceDeployment:
    """Test multi-instance deployment without port conflicts"""
    
    def test_port_range_allocation_for_multiple_instances(self):
        """Test that different instances can be allocated different port ranges"""
        # GIVEN: Environment configuration for instance 1
        instance1_env = {
            'INSTANCE_ID': '1',
            'PORT_RANGE_START': '8000'
        }
        
        with patch.dict(os.environ, instance1_env, clear=True):
            # WHEN: ConfigManager allocates ports for instance 1
            config1 = ConfigManager()
            
            # THEN: Instance 1 gets ports starting from 8000
            assert config1.get_port('backend') == 8000
            assert config1.get_port('storage') == 8001
            assert config1.get_port('deno-runtime') == 8002
        
        # GIVEN: Environment configuration for instance 2  
        instance2_env = {
            'INSTANCE_ID': '2',
            'PORT_RANGE_START': '9000'
        }
        
        with patch.dict(os.environ, instance2_env, clear=True):
            # WHEN: ConfigManager allocates ports for instance 2
            config2 = ConfigManager()
            
            # THEN: Instance 2 gets ports starting from 9000
            assert config2.get_port('backend') == 9000
            assert config2.get_port('storage') == 9001
            assert config2.get_port('deno-runtime') == 9002
    
    def test_compose_project_name_affects_service_naming(self):
        """Test that COMPOSE_PROJECT_NAME affects service naming for multi-instance"""
        # GIVEN: Different project names
        project1_env = {'COMPOSE_PROJECT_NAME': 'selfdb_dev'}
        project2_env = {'COMPOSE_PROJECT_NAME': 'selfdb_staging'}
        
        with patch.dict(os.environ, project1_env, clear=True):
            config1 = ConfigManager()
            # THEN: Service names include project prefix
            assert config1.get_service_name('postgres') == 'selfdb_dev_postgres'
        
        with patch.dict(os.environ, project2_env, clear=True):
            config2 = ConfigManager()
            assert config2.get_service_name('postgres') == 'selfdb_staging_postgres'


class TestEnvironmentFileLoading:
    """Test environment-based configuration loading with precedence"""
    
    def test_env_file_precedence_prod_over_staging_over_dev(self):
        """Test that .env.prod > .env.staging > .env.dev > .env in precedence"""
        # GIVEN: Multiple environment files with different values
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test environment files with all required ports and PgBouncer config
            env_files = {
                '.env': 'API_PORT=8000\nFRONTEND_PORT=3000\nPOSTGRES_PORT=5432\nSTORAGE_PORT=8001\nDENO_PORT=8090\nPGBOUNCER_PORT=6432\nPGBOUNCER_MAX_CLIENT_CONN=5000\nPGBOUNCER_DEFAULT_POOL_SIZE=50\nPGBOUNCER_RESERVE_POOL_SIZE=10\nPGBOUNCER_SERVER_LIFETIME=3600\nPGBOUNCER_SERVER_IDLE_TIMEOUT=600\nPGBOUNCER_QUERY_WAIT_TIMEOUT=30\nPGBOUNCER_CLIENT_IDLE_TIMEOUT=600',
                '.env.dev': 'API_PORT=8001\nFRONTEND_PORT=3001\nPOSTGRES_PORT=5433\nSTORAGE_PORT=8002\nDENO_PORT=8091\nPGBOUNCER_PORT=6432\nPGBOUNCER_MAX_CLIENT_CONN=5000\nPGBOUNCER_DEFAULT_POOL_SIZE=50\nPGBOUNCER_RESERVE_POOL_SIZE=10\nPGBOUNCER_SERVER_LIFETIME=3600\nPGBOUNCER_SERVER_IDLE_TIMEOUT=600\nPGBOUNCER_QUERY_WAIT_TIMEOUT=30\nPGBOUNCER_CLIENT_IDLE_TIMEOUT=600',
                '.env.staging': 'API_PORT=8002\nFRONTEND_PORT=3002\nPOSTGRES_PORT=5434\nSTORAGE_PORT=8003\nDENO_PORT=8092\nPGBOUNCER_PORT=6433\nPGBOUNCER_MAX_CLIENT_CONN=5000\nPGBOUNCER_DEFAULT_POOL_SIZE=50\nPGBOUNCER_RESERVE_POOL_SIZE=10\nPGBOUNCER_SERVER_LIFETIME=3600\nPGBOUNCER_SERVER_IDLE_TIMEOUT=600\nPGBOUNCER_QUERY_WAIT_TIMEOUT=30\nPGBOUNCER_CLIENT_IDLE_TIMEOUT=600',
                '.env.prod': 'API_PORT=8003\nFRONTEND_PORT=3003\nPOSTGRES_PORT=5435\nSTORAGE_PORT=8004\nDENO_PORT=8093\nPGBOUNCER_PORT=6434\nPGBOUNCER_MAX_CLIENT_CONN=5000\nPGBOUNCER_DEFAULT_POOL_SIZE=50\nPGBOUNCER_RESERVE_POOL_SIZE=10\nPGBOUNCER_SERVER_LIFETIME=3600\nPGBOUNCER_SERVER_IDLE_TIMEOUT=600\nPGBOUNCER_QUERY_WAIT_TIMEOUT=30\nPGBOUNCER_CLIENT_IDLE_TIMEOUT=600'
            }
            
            for filename, content in env_files.items():
                Path(temp_dir, filename).write_text(content)
            
            # WHEN: ConfigManager loads configuration in production environment
            with patch.dict(os.environ, {'ENV': 'prod'}, clear=True):
                config = ConfigManager(config_dir=temp_dir)
                
                # THEN: Production values take precedence
                assert config.get_port('backend') == 8003
                assert config.get_port('frontend') == 3003
                assert config.get_port('postgres') == 5435
                assert config.get_port('storage') == 8004
                assert config.get_port('deno-runtime') == 8093
    
    def test_fallback_to_lower_precedence_files(self):
        """Test fallback when higher precedence files don't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # GIVEN: Only dev and base env files exist with all required ports and PgBouncer config
            env_files = {
                '.env': 'API_PORT=8000\nFRONTEND_PORT=3000\nPOSTGRES_PORT=5432\nSTORAGE_PORT=8001\nDENO_PORT=8090\nPGBOUNCER_PORT=6432\nPGBOUNCER_MAX_CLIENT_CONN=5000\nPGBOUNCER_DEFAULT_POOL_SIZE=50\nPGBOUNCER_RESERVE_POOL_SIZE=10\nPGBOUNCER_SERVER_LIFETIME=3600\nPGBOUNCER_SERVER_IDLE_TIMEOUT=600\nPGBOUNCER_QUERY_WAIT_TIMEOUT=30\nPGBOUNCER_CLIENT_IDLE_TIMEOUT=600',
                '.env.dev': 'API_PORT=8001\nFRONTEND_PORT=3001\nPOSTGRES_PORT=5433\nSTORAGE_PORT=8002\nDENO_PORT=8091\nPGBOUNCER_PORT=6432\nPGBOUNCER_MAX_CLIENT_CONN=5000\nPGBOUNCER_DEFAULT_POOL_SIZE=50\nPGBOUNCER_RESERVE_POOL_SIZE=10\nPGBOUNCER_SERVER_LIFETIME=3600\nPGBOUNCER_SERVER_IDLE_TIMEOUT=600\nPGBOUNCER_QUERY_WAIT_TIMEOUT=30\nPGBOUNCER_CLIENT_IDLE_TIMEOUT=600'
            }
            
            for filename, content in env_files.items():
                Path(temp_dir, filename).write_text(content)
            
            # WHEN: ConfigManager loads in staging (but .env.staging doesn't exist)
            with patch.dict(os.environ, {'ENV': 'staging'}, clear=True):
                config = ConfigManager(config_dir=temp_dir)
                
                # THEN: Falls back to .env.dev, then .env
                assert config.get_port('backend') == 8001
                assert config.get_port('frontend') == 3001
                assert config.get_port('postgres') == 5433
                assert config.get_port('storage') == 8002
                assert config.get_port('deno-runtime') == 8091


class TestServiceDiscovery:
    """Test Docker Compose service name resolution"""
    
    def test_service_url_generation_with_docker_names(self):
        """Test that service URLs use Docker Compose service names instead of localhost"""
        # GIVEN: Configuration for Docker environment
        with patch.dict(os.environ, {'DOCKER_ENV': 'true'}, clear=True):
            config = ConfigManager()
            
            # WHEN: Generating service URLs
            backend_url = config.get_service_url('backend')
            storage_url = config.get_service_url('storage')
            postgres_url = config.get_service_url('postgres')
            
            # THEN: URLs use Docker service names, not localhost
            assert backend_url == 'http://backend:8000'
            assert storage_url == 'http://storage:8001'  
            assert postgres_url == 'postgresql://postgres:5432'
    
    def test_localhost_urls_for_development(self):
        """Test that localhost URLs are used in development mode"""
        # GIVEN: Development environment configuration
        with patch.dict(os.environ, {'DOCKER_ENV': 'false'}, clear=True):
            config = ConfigManager()
            
            # WHEN: Generating service URLs
            backend_url = config.get_service_url('backend')
            storage_url = config.get_service_url('storage')
            
            # THEN: URLs use localhost for development
            assert backend_url == 'http://localhost:8000'
            assert storage_url == 'http://localhost:8001'


class TestConfigurationValidation:
    """Test configuration validation and error reporting"""
    
    def test_invalid_port_numbers_raise_validation_error(self):
        """Test that invalid port numbers raise ConfigValidationError"""
        # GIVEN: Invalid port numbers in environment
        invalid_ports = [
            ('POSTGRES_PORT', '-1'),     # Negative
            ('API_PORT', '0'),           # Zero
            ('FRONTEND_PORT', '65536'),  # Too high
            ('STORAGE_PORT', 'abc'),     # Non-numeric
        ]
        
        for env_var, invalid_value in invalid_ports:
            with patch.dict(os.environ, {env_var: invalid_value}, clear=True):
                # WHEN: ConfigManager attempts to load configuration
                # THEN: ConfigValidationError is raised with helpful message
                with pytest.raises(ConfigValidationError) as exc_info:
                    ConfigManager()
                
                assert env_var.lower().replace('_port', '') in str(exc_info.value)
                assert invalid_value in str(exc_info.value)
    
    def test_missing_required_database_credentials_raise_error(self):
        """Test that missing database credentials raise validation error"""
        # GIVEN: Missing required database environment variables
        with patch.dict(os.environ, {}, clear=True):
            # WHEN: ConfigManager attempts to load configuration
            # THEN: ConfigValidationError is raised for missing credentials
            with pytest.raises(ConfigValidationError) as exc_info:
                ConfigManager(validate_database=True)
            
            error_message = str(exc_info.value)
            assert 'POSTGRES_DB' in error_message
            assert 'POSTGRES_USER' in error_message
            assert 'POSTGRES_PASSWORD' in error_message
    
    def test_port_conflict_detection(self):
        """Test detection of port conflicts in configuration"""
        # GIVEN: Configuration with port conflicts
        conflicting_env = {
            'API_PORT': '8000',
            'STORAGE_PORT': '8000',  # Same port!
        }
        
        with patch.dict(os.environ, conflicting_env, clear=True):
            # WHEN: ConfigManager validates configuration
            # THEN: ConfigValidationError is raised for port conflict
            with pytest.raises(ConfigValidationError) as exc_info:
                ConfigManager(check_port_conflicts=True)
            
            assert 'port conflict' in str(exc_info.value).lower()
            assert '8000' in str(exc_info.value)
    
    def test_helpful_error_messages_for_common_mistakes(self):
        """Test that error messages provide helpful guidance for common mistakes"""
        # GIVEN: Common configuration mistakes
        with patch.dict(os.environ, {'API_PORT': 'eight_thousand'}, clear=True):
            # WHEN: ConfigManager validates configuration
            with pytest.raises(ConfigValidationError) as exc_info:
                ConfigManager()
            
            # THEN: Error message is helpful and specific
            error_message = str(exc_info.value)
            assert 'API_PORT' in error_message
            assert 'must be a number' in error_message.lower()
            assert 'eight_thousand' in error_message


class TestConfigManagerIntegration:
    """Integration tests for the complete ConfigManager"""
    
    def test_docker_compose_template_generation(self):
        """Test generation of docker-compose.yml with configurable ports"""
        # GIVEN: Custom port configuration
        env_vars = {
            'POSTGRES_PORT': '5433',
            'STORAGE_PORT': '8002',
            'API_PORT': '8001', 
            'FRONTEND_PORT': '3001',
            'DENO_PORT': '8091'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = ConfigManager()
            
            # WHEN: Generating Docker Compose configuration
            compose_config = config.generate_docker_compose_config()
            
            # THEN: All services use configured ports
            assert compose_config['services']['postgres']['ports'][0] == '5433:5432'
            assert compose_config['services']['storage']['ports'][0] == '8002:8001'
            assert compose_config['services']['backend']['ports'][0] == '8001:8000'
            assert compose_config['services']['frontend']['ports'][0] == '3001:80'
            assert compose_config['services']['deno-runtime']['ports'][0] == '8091:8090'
    
    def test_environment_template_generation(self):
        """Test generation of .env template files with all required variables"""
        # GIVEN: ConfigManager instance
        config = ConfigManager()
        
        # WHEN: Generating environment template
        env_template = config.generate_env_template()
        
        # THEN: Template contains all port configurations with defaults
        expected_vars = [
            'POSTGRES_PORT=5432',
            'STORAGE_PORT=8001', 
            'API_PORT=8000',
            'FRONTEND_PORT=3000',
            'DENO_PORT=8090'
        ]
        
        for expected_var in expected_vars:
            assert expected_var in env_template


class TestConfigManagerAPIKey:
    """Test API key configuration management"""
    
    def test_get_api_key_from_environment(self):
        """Test that API key is loaded from environment variable"""
        # GIVEN: API key in environment
        env_vars = {'API_KEY': 'test-api-key-12345'}
        
        with patch.dict(os.environ, env_vars, clear=True):
            # WHEN: ConfigManager loads configuration
            config = ConfigManager()
            
            # THEN: API key is available
            assert config.get_api_key() == 'test-api-key-12345'
    
    def test_get_api_key_missing_raises_error(self):
        """Test that missing API key raises ConfigValidationError"""
        # GIVEN: No API key in environment or files
        env_vars = {
            'POSTGRES_PORT': '5432',
            'STORAGE_PORT': '8001',
            'API_PORT': '8000',
            'FRONTEND_PORT': '3000',
            'DENO_PORT': '8090',
            'PGBOUNCER_PORT': '6432'
            # Missing API_KEY
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with patch('shared.config.config_manager.ConfigManager._load_env_files'):
                # WHEN: ConfigManager attempts to get API key
                config = ConfigManager()
                
                # THEN: ConfigValidationError is raised
                with pytest.raises(ConfigValidationError) as exc_info:
                    config.get_api_key()
                
                assert "API_KEY is required" in str(exc_info.value)
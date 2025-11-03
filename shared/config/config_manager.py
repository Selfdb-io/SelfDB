"""
Configuration Manager for SelfDB - Phase 1.1

Handles port configuration, multi-instance deployment, environment file loading,
service discovery, and configuration validation.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
import re


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigManager:
    """
    Central configuration management for SelfDB.
    
    Provides:
    - Port configuration from environment variables
    - Multi-instance deployment support  
    - Environment file loading with precedence
    - Docker Compose service discovery
    - Configuration validation
    """
    
    # Default port mappings for all services
    DEFAULT_PORTS = {
        'postgres': 5432,
        'pgbouncer': 6432,
        'storage': 8001,
        'backend': 8000,
        'frontend': 3000,
        'deno-runtime': 8090
    }

    # Environment variable mappings
    PORT_ENV_VARS = {
        'postgres': 'POSTGRES_PORT',
        'pgbouncer': 'PGBOUNCER_PORT',
        'storage': 'STORAGE_PORT',
        'backend': 'API_PORT',
        'frontend': 'FRONTEND_PORT',
        'deno-runtime': 'DENO_PORT'
    }
    
    def __init__(
        self,
        config_dir: Optional[str] = None,
        validate_database: bool = False,
        check_port_conflicts: bool = False
    ):
        """
        Initialize ConfigManager.
        
        Args:
            config_dir: Directory containing environment files
            validate_database: Whether to validate database credentials
            check_port_conflicts: Whether to check for port conflicts
        """
        self.config_dir = Path(config_dir) if config_dir else Path.cwd()
        self.validate_database = validate_database
        self.check_port_conflicts = check_port_conflicts
        
        # Initialize internal state
        self._env_vars = {}
        
        # Load configuration
        self._load_env_files()
        self._load_ports()
        
        # Perform validation
        if validate_database:
            self._validate_database_config()
        if check_port_conflicts:
            self._validate_port_conflicts()
    
    def _load_env_files(self):
        """Load environment files with precedence: .env.prod > .env.staging > .env.dev > .env"""
        env = os.getenv('ENV', 'dev')
        
        # Define file precedence (load in order, higher precedence files override lower)
        env_files = ['.env']
        if env in ['dev', 'staging', 'prod']:
            env_files.append('.env.dev')
        if env in ['staging', 'prod']:
            env_files.append('.env.staging')
        if env == 'prod':
            env_files.append('.env.prod')
        
        # Load files in order (higher precedence files will override)
        for env_file in env_files:
            env_path = self.config_dir / env_file
            if env_path.exists():
                self._load_env_file(env_path)
    
    def _load_env_file(self, env_path: Path):
        """Load a single environment file into our internal env_vars dict."""
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Store in our internal dict (later files override earlier)
                        self._env_vars[key] = value
        except Exception:
            # Silently ignore file read errors for now
            pass
    
    def _load_ports(self):
        """Load port configuration from environment variables."""
        self._ports = {}
        
        # Check for instance-based port allocation
        instance_id = os.getenv('INSTANCE_ID')
        port_range_start = os.getenv('PORT_RANGE_START')
        
        if instance_id and port_range_start:
            self._load_instance_ports(int(port_range_start))
        else:
            self._load_standard_ports()
    
    def _load_standard_ports(self):
        """Load standard port configuration."""
        for service, env_var in self.PORT_ENV_VARS.items():
            # Check os.environ first (highest precedence), then file-loaded env_vars
            env_value = os.getenv(env_var) or self._env_vars.get(env_var)
            if env_value:
                try:
                    port = int(env_value)
                    self._validate_port(port, service, env_var, env_value)
                    self._ports[service] = port
                except ValueError:
                    # Extract service name from env_var for error message  
                    service_name = env_var.lower().replace('_port', '')
                    raise ConfigValidationError(
                        f"Invalid {env_var}: '{env_value}' - {service_name} port must be a number between 1 and 65535"
                    )
            else:
                raise ConfigValidationError(
                    f"Required environment variable {env_var} is not configured"
                )
    
    def _load_instance_ports(self, start_port: int):
        """Load instance-based port allocation."""
        # Allocate ports for backend services in sequence
        backend_services = ['backend', 'storage', 'deno-runtime']
        for i, service in enumerate(backend_services):
            self._ports[service] = start_port + i
        
        # Use env vars for postgres and frontend (no fallbacks)
        postgres_port = os.getenv('POSTGRES_PORT') or self._env_vars.get('POSTGRES_PORT')
        frontend_port = os.getenv('FRONTEND_PORT') or self._env_vars.get('FRONTEND_PORT')
        
        if not postgres_port:
            raise ConfigValidationError("Required environment variable POSTGRES_PORT is not configured")
        if not frontend_port:
            raise ConfigValidationError("Required environment variable FRONTEND_PORT is not configured")
            
        try:
            self._ports['postgres'] = int(postgres_port)
            self._ports['frontend'] = int(frontend_port)
        except ValueError:
            raise ConfigValidationError("POSTGRES_PORT and FRONTEND_PORT must be valid integers")
    
    def _validate_port(self, port: int, service: str, env_var: str, original_value: str):
        """Validate a port number."""
        if not (1 <= port <= 65535):
            # Extract service name from env_var for error message
            service_name = env_var.lower().replace('_port', '')
            raise ConfigValidationError(
                f"Invalid {env_var}: '{original_value}' - {service_name} port must be between 1 and 65535"
            )
    
    def _validate_database_config(self):
        """Validate database configuration."""
        required_vars = ['POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ConfigValidationError(
                f"Missing required database configuration: {', '.join(missing_vars)}"
            )
    
    def _validate_port_conflicts(self):
        """Check for port conflicts."""
        ports_used = {}
        for service, port in self._ports.items():
            if port in ports_used:
                raise ConfigValidationError(
                    f"Port conflict: {service} and {ports_used[port]} both trying to use port {port}"
                )
            ports_used[port] = service
    
    def get_port(self, service: str) -> int:
        """Get the configured port for a service."""
        if service not in self._ports:
            raise ValueError(f"Unknown service: {service}")
        return self._ports[service]
    
    def get_service_name(self, service: str) -> str:
        """Get the service name with project prefix if configured."""
        project_name = os.getenv('COMPOSE_PROJECT_NAME', 'selfdb')
        return f"{project_name}_{service}"
    
    def get_service_url(self, service: str) -> str:
        """Get the service URL for Docker or development environment."""
        port = self.get_port(service)
        is_docker = os.getenv('DOCKER_ENV', 'false').lower() == 'true'
        
        if is_docker:
            # Use Docker service names
            if service == 'postgres':
                return f"postgresql://{service}:{port}"
            else:
                return f"http://{service}:{port}"
        else:
            # Use localhost for development
            if service == 'postgres':
                return f"postgresql://localhost:{port}"
            else:
                return f"http://localhost:{port}"
    
    def get_api_key(self) -> str:
        """Get the configured API key from environment."""
        # Check os.environ first (highest precedence), then file-loaded env_vars
        api_key = os.getenv('API_KEY') or self._env_vars.get('API_KEY')
        if not api_key:
            raise ConfigValidationError("API_KEY is required but not configured")
        return api_key

    def get_jwt_secret(self) -> str:
        """Get the configured JWT secret key from environment."""
        # Check os.environ first (highest precedence), then file-loaded env_vars
        jwt_secret = os.getenv('JWT_SECRET_KEY') or self._env_vars.get('JWT_SECRET_KEY')
        if not jwt_secret:
            raise ConfigValidationError("JWT_SECRET_KEY is required but not configured")
        return jwt_secret
    
    def generate_docker_compose_config(self) -> Dict[str, Any]:
        """Generate Docker Compose configuration with configured ports."""
        # Internal container ports (what the services listen on inside containers)
        internal_ports = {
            'postgres': 5432,
            'pgbouncer': 6432,
            'storage': 8001,
            'backend': 8000,
            'frontend': 80,
            'deno-runtime': 8090
        }
        
        services = {}
        for service in self._ports:
            external_port = self._ports[service]
            internal_port = internal_ports[service]
            
            services[service] = {
                'ports': [f"{external_port}:{internal_port}"]
            }
        
        return {'services': services}
    
    def generate_env_template(self) -> str:
        """Generate environment template with all port configurations."""
        template_lines = []
        
        # Add port configurations
        for service, env_var in self.PORT_ENV_VARS.items():
            default_port = self.DEFAULT_PORTS[service]
            template_lines.append(f"{env_var}={default_port}")
        
        return '\n'.join(template_lines)
    
    @property
    def postgres_port(self) -> int:
        """Get PostgreSQL port."""
        return self.get_port('postgres')

    @property
    def pgbouncer_port(self) -> int:
        """Get PgBouncer port."""
        return self.get_port('pgbouncer')

    @property
    def postgres_host(self) -> str:
        """Get PostgreSQL host."""
        is_docker = os.getenv('DOCKER_ENV', 'false').lower() == 'true'
        host = "postgres" if is_docker else os.getenv('POSTGRES_HOST')
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"DOCKER_ENV={os.getenv('DOCKER_ENV')}, is_docker={is_docker}, host={host}")
        logger.debug(f"POSTGRES_HOST env var: {os.getenv('POSTGRES_HOST')}")
        return host

    @property
    def pgbouncer_host(self) -> str:
        """Get PgBouncer host."""
        is_docker = os.getenv('DOCKER_ENV', 'false').lower() == 'true'
        return "pgbouncer" if is_docker else os.getenv('PGBOUNCER_HOST', 'localhost')
    
    @property
    def postgres_db(self) -> str:
        """Get PostgreSQL database name."""
        return os.getenv('POSTGRES_DB', 'selfdb')
    
    @property
    def postgres_user(self) -> str:
        """Get PostgreSQL user."""
        return os.getenv('POSTGRES_USER', 'postgres')
    
    @property
    def postgres_password(self) -> str:
        """Get PostgreSQL password."""
        return os.getenv('POSTGRES_PASSWORD', 'postgres')

    def get_database_url(self, use_pgbouncer: bool = False) -> str:
        """Get database URL with optional PgBouncer support."""
        if use_pgbouncer:
            host = self.pgbouncer_host
            port = self.pgbouncer_port
        else:
            host = self.postgres_host
            port = self.postgres_port

        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{host}:{port}/{self.postgres_db}"

    def get_pgbouncer_database_url(self) -> str:
        """Get database URL using PgBouncer."""
        return self.get_database_url(use_pgbouncer=True)

    def get_direct_postgres_url(self) -> str:
        """Get direct PostgreSQL URL (bypass PgBouncer for LISTEN/NOTIFY)."""
        host = self.postgres_host
        port = 5432  # Use direct PostgreSQL port, not PgBouncer
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{host}:{port}/{self.postgres_db}"

    @property
    def pgbouncer_max_client_conn(self) -> int:
        """Get PgBouncer max client connections."""
        return int(os.getenv('PGBOUNCER_MAX_CLIENT_CONN', '5000'))

    @property
    def pgbouncer_default_pool_size(self) -> int:
        """Get PgBouncer default pool size."""
        return int(os.getenv('PGBOUNCER_DEFAULT_POOL_SIZE', '50'))

    @property
    def pgbouncer_reserve_pool_size(self) -> int:
        """Get PgBouncer reserve pool size."""
        return int(os.getenv('PGBOUNCER_RESERVE_POOL_SIZE', '10'))

    @property
    def pgbouncer_server_lifetime(self) -> int:
        """Get PgBouncer server lifetime."""
        return int(os.getenv('PGBOUNCER_SERVER_LIFETIME', '3600'))

    @property
    def pgbouncer_server_idle_timeout(self) -> int:
        """Get PgBouncer server idle timeout."""
        return int(os.getenv('PGBOUNCER_SERVER_IDLE_TIMEOUT', '600'))

    @property
    def pgbouncer_query_wait_timeout(self) -> int:
        """Get PgBouncer query wait timeout."""
        return int(os.getenv('PGBOUNCER_QUERY_WAIT_TIMEOUT', '30'))

    @property
    def pgbouncer_client_idle_timeout(self) -> int:
        """Get PgBouncer client idle timeout."""
        return int(os.getenv('PGBOUNCER_CLIENT_IDLE_TIMEOUT', '600'))
    
    @property
    def is_docker_environment(self) -> bool:
        """Check if running in Docker environment."""
        return os.getenv('DOCKER_ENV', 'false').lower() == 'true'
    
    @property
    def compose_project_name(self) -> str:
        """Get Docker Compose project name."""
        return os.getenv('COMPOSE_PROJECT_NAME', 'selfdb')

    @property
    def admin_email(self) -> str:
        """Get the configured admin email from environment."""
        # Check os.environ first (highest precedence), then file-loaded env_vars
        admin_email = os.getenv('ADMIN_EMAIL') or self._env_vars.get('ADMIN_EMAIL')
        if not admin_email:
            raise ConfigValidationError("ADMIN_EMAIL is required but not configured")
        return admin_email

    @property
    def admin_password(self) -> str:
        """Get the configured admin password from environment."""
        # Check os.environ first (highest precedence), then file-loaded env_vars
        admin_password = os.getenv('ADMIN_PASSWORD') or self._env_vars.get('ADMIN_PASSWORD')
        if not admin_password:
            raise ConfigValidationError("ADMIN_PASSWORD is required but not configured")
        return admin_password

    @property
    def admin_first_name(self) -> str:
        """Get the configured admin first name from environment."""
        # Check os.environ first (highest precedence), then file-loaded env_vars
        admin_first_name = os.getenv('ADMIN_FIRST_NAME') or self._env_vars.get('ADMIN_FIRST_NAME')
        if not admin_first_name:
            raise ConfigValidationError("ADMIN_FIRST_NAME is required but not configured")
        return admin_first_name

    @property
    def admin_last_name(self) -> str:
        """Get the configured admin last name from environment."""
        # Check os.environ first (highest precedence), then file-loaded env_vars
        admin_last_name = os.getenv('ADMIN_LAST_NAME') or self._env_vars.get('ADMIN_LAST_NAME')
        if not admin_last_name:
            raise ConfigValidationError("ADMIN_LAST_NAME is required but not configured")
        return admin_last_name
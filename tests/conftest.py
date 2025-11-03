"""
Centralized test configuration and fixtures for SelfDB TDD rebuild.

This module provides shared test fixtures that:
1. Load configuration from .env.dev file
2. Provide consistent mocking for unit tests
3. Manage shared containers for integration tests
4. Centralize all test environment setup
"""

import pytest
import pytest_asyncio
import os
import sys
import asyncio
import importlib
from unittest.mock import Mock, AsyncMock
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import logging
from fastapi.testclient import TestClient

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Python path for backend imports
# This allows backend code to use relative imports (Docker style) while tests run locally
_project_root = Path(__file__).resolve().parent.parent

# Add Docker-style module paths to sys.path so tests import the same way containers do
_docker_paths = [
    _project_root,
    _project_root / "backend",
    _project_root / "shared",
    _project_root / "storage",
    _project_root / "functions",
]

def _ensure_path(path: Path, position: Optional[int] = None) -> None:
    """Insert a path into sys.path at a specific position, maintaining order."""
    path_str = str(path)
    if not path.exists():
        return

    if path_str in sys.path:
        sys.path.remove(path_str)

    if position is not None and position < len(sys.path):
        sys.path.insert(position, path_str)
    else:
        sys.path.append(path_str)

# Maintain precedence: project root first, backend second, others afterwards
for index, path in enumerate(_docker_paths):
    if index < 2:
        _ensure_path(path, index)
    else:
        _ensure_path(path)


def _load_backend_app():
    """Import or reload backend FastAPI application respecting current env."""
    modules_to_refresh = (
        "backend.middleware.auth",
        "backend.main",
    )

    for module_name in modules_to_refresh:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)

    from backend.main import app

    return app


@pytest.fixture
def api_client(test_environment):
    """FastAPI TestClient that mirrors container import paths."""
    app = _load_backend_app()

    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
def setup_test_imports():
    """
    Session-scoped fixture that ensures Python imports are set up correctly for tests.
    
    This fixture ensures that:
    1. Backend code can use relative imports (Docker style: 'from endpoints.files import ...')
    2. Tests can import backend modules ('from backend.main import app')
    3. Both work because backend directory is added to sys.path
    
    This fixture runs automatically for all tests.
    """
    # The setup is done at module level (sys.path modification above)
    # This fixture exists for documentation and potential future cleanup
    yield
    # No cleanup needed - sys.path modifications persist for the test session


def load_dev_environment():
    """Load development environment variables from .env.dev file."""
    env_path = Path(__file__).parent.parent / '.env.dev'

    if not env_path.exists():
        raise FileNotFoundError(f"Development environment file not found: {env_path}")

    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


@pytest.fixture(scope="session")
def dev_environment():
    """Session-scoped fixture providing development environment variables."""
    return load_dev_environment()


@pytest.fixture(scope="session")
def test_environment(dev_environment):
    """Session-scoped fixture that sets up the test environment."""
    # Store original environment
    original_env = dict(os.environ)

    # Update with dev environment - ensure all variables are set
    os.environ.update(dev_environment)
    
    # Explicitly set critical variables for backend application
    os.environ['API_KEY'] = dev_environment.get('API_KEY', 'dev_api_key_not_for_production')
    os.environ['JWT_SECRET_KEY'] = dev_environment.get('JWT_SECRET_KEY', 'dev_jwt_secret_not_for_production')
    os.environ['POSTGRES_HOST'] = 'postgres'  # Use Docker service name
    os.environ['POSTGRES_PORT'] = '5432'
    os.environ['POSTGRES_DB'] = dev_environment.get('POSTGRES_DB', 'selfdb_dev')
    os.environ['POSTGRES_USER'] = dev_environment.get('POSTGRES_USER', 'selfdb_dev_user')
    os.environ['POSTGRES_PASSWORD'] = dev_environment.get('POSTGRES_PASSWORD', 'dev_password_123')
    os.environ['DOCKER_ENV'] = 'true'  # Enable Docker environment detection

    yield dev_environment

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_config_manager(test_environment):
    """
    Mock ConfigManager configured with development environment values.

    This fixture provides a mock ConfigManager that returns values
    consistent with the .env.dev configuration file.
    """
    config = Mock()

    # Port configurations from .env.dev
    config.get_port.side_effect = lambda service: {
        'postgres': int(test_environment.get('POSTGRES_PORT', '5432')),
        'storage': int(test_environment.get('STORAGE_PORT', '8001')),
        'backend': int(test_environment.get('API_PORT', '8000')),
        'frontend': int(test_environment.get('FRONTEND_PORT', '3000')),
        'deno-runtime': int(test_environment.get('DENO_PORT', '8090')),
    }.get(service, 8080)

    # Database configuration
    config.postgres_port = int(test_environment.get('POSTGRES_PORT', '5432'))
    config.postgres_host = test_environment.get('POSTGRES_HOST', 'localhost')
    config.postgres_db = test_environment.get('POSTGRES_DB', 'selfdb_dev')
    config.postgres_user = test_environment.get('POSTGRES_USER', 'selfdb_dev_user')
    config.postgres_password = test_environment.get('POSTGRES_PASSWORD', 'dev_password_123')

    # API configuration
    config.get_api_key.return_value = test_environment.get('API_KEY', 'dev_api_key_not_for_production')
    config.api_key = test_environment.get('API_KEY', 'dev_api_key_not_for_production')

    # JWT configuration
    config.jwt_secret = test_environment.get('JWT_SECRET_KEY', 'dev_jwt_secret_not_for_production')
    config.jwt_algorithm = test_environment.get('JWT_ALGORITHM', 'HS256')
    config.jwt_expiration_hours = int(test_environment.get('JWT_EXPIRATION_HOURS', '72'))

    # Environment settings
    config.is_docker_environment = test_environment.get('DOCKER_ENV', 'false').lower() == 'true'
    config.debug = test_environment.get('DEBUG', 'true').lower() == 'true'
    config.log_level = test_environment.get('LOG_LEVEL', 'DEBUG')
    config.environment = test_environment.get('ENV', 'dev')

    # Service URLs
    config.get_service_url.side_effect = lambda service: {
        'backend': f"http://localhost:{test_environment.get('API_PORT', '8000')}",
        'storage': f"http://localhost:{test_environment.get('STORAGE_PORT', '8001')}",
        'postgres': f"postgresql://localhost:{test_environment.get('POSTGRES_PORT', '5432')}",
    }.get(service, 'http://localhost:8080')

    # Admin configuration
    config.admin_email = test_environment.get('ADMIN_EMAIL', 'admin@selfdb.dev')
    config.admin_password = test_environment.get('ADMIN_PASSWORD', 'dev_admin_password_123')

    # Network configuration
    config.docker_network = test_environment.get('DOCKER_NETWORK', 'selfdb_dev_network')
    config.allowed_cors = test_environment.get('ALLOWED_CORS', 'http://localhost:3000,http://localhost:8000')

    return config


@pytest.fixture(scope="session")
def dev_config_manager(test_environment):
    """
    Real ConfigManager instance loaded with development environment.

    This fixture provides an actual ConfigManager instance for integration tests
    that need real configuration management.
    """
    try:
        from shared.config.config_manager import ConfigManager
        return ConfigManager()
    except ImportError:
        # Fallback to mock if ConfigManager doesn't exist yet
        logger.warning("ConfigManager not available, falling back to mock")
        return mock_config_manager(test_environment)


@pytest.fixture(scope="session")
def test_api_key(test_environment):
    """Test API key from development environment."""
    return test_environment.get('API_KEY', 'dev_api_key_not_for_production')


@pytest.fixture(scope="session")
def test_jwt_config(test_environment):
    """JWT configuration from development environment."""
    return {
        'secret_key': test_environment.get('JWT_SECRET_KEY', 'dev_jwt_secret_not_for_production'),
        'algorithm': test_environment.get('JWT_ALGORITHM', 'HS256'),
        'access_token_expire_minutes': 30,
        'refresh_token_expire_hours': int(test_environment.get('JWT_EXPIRATION_HOURS', '72')),
        'issuer': 'selfdb-test'
    }


@pytest.fixture(scope="session")
def test_database_config(test_environment):
    """Database configuration from development environment."""
    return {
        'host': test_environment.get('POSTGRES_HOST', 'localhost'),
        'port': int(test_environment.get('POSTGRES_PORT', '5432')),
        'database': test_environment.get('POSTGRES_DB', 'selfdb_dev'),
        'username': test_environment.get('POSTGRES_USER', 'selfdb_dev_user'),
        'password': test_environment.get('POSTGRES_PASSWORD', 'dev_password_123')
    }


@pytest.fixture(scope="session")
def test_service_ports(test_environment):
    """Service port configurations from development environment."""
    return {
        'postgres': int(test_environment.get('POSTGRES_PORT', '5432')),
        'storage': int(test_environment.get('STORAGE_PORT', '8001')),
        'backend': int(test_environment.get('API_PORT', '8000')),
        'frontend': int(test_environment.get('FRONTEND_PORT', '3000')),
        'deno': int(test_environment.get('DENO_PORT', '8090'))
    }


# Integration test fixtures for Docker containers

@pytest.fixture(scope="session")
def docker_manager():
    """Session-scoped Docker test manager for integration tests."""
    try:
        from shared.testing.docker_manager import DockerTestManager
        manager = DockerTestManager()
        yield manager
        # Cleanup after all tests
        manager.cleanup_all()
    except ImportError:
        logger.warning("DockerTestManager not available, skipping Docker fixtures")
        yield None


@pytest.fixture(scope="session")
def postgres_container(docker_manager, test_database_config, dev_environment):
    """
    Session-scoped PostgreSQL container for integration tests.

    This fixture first checks if development containers are running and uses them,
    otherwise creates a new test container.
    """
    import docker
    
    try:
        # Check if development PostgreSQL container is running
        docker_client = docker.from_env()
        dev_containers = docker_client.containers.list(filters={"name": "selfdb-dev-postgres"})
        
        if dev_containers:
            # Use the running development container
            dev_container = dev_containers[0]
            logger.info(f"Using running development PostgreSQL container: {dev_container.name}")
            
            # Use development database configuration
            container_config = {
                'host': 'localhost',
                'port': 5432,  # Development container uses standard port
                'database': dev_environment.get('POSTGRES_DB', 'selfdb_dev'),
                'username': dev_environment.get('POSTGRES_USER', 'selfdb_dev_user'),
                'password': dev_environment.get('POSTGRES_PASSWORD', 'dev_password_123')
            }
            
            yield dev_container, container_config
            return
            
    except Exception as e:
        logger.warning(f"Could not check for development containers: {e}")
    
    # Fallback to creating a test container
    if not docker_manager:
        pytest.skip("Docker manager not available and no dev containers found")

    container_config = {
        'image': 'postgres:17',
        'environment': {
            'POSTGRES_DB': test_database_config['database'],
            'POSTGRES_USER': test_database_config['username'],
            'POSTGRES_PASSWORD': test_database_config['password']
        },
        'port_mapping': {'5432/tcp': None},  # Auto-assign port
        'healthcheck': {
            'test': ['CMD-SHELL', f"pg_isready -U {test_database_config['username']} -d {test_database_config['database']}"],
            'interval': 1000000000,  # 1s in nanoseconds
            'timeout': 5000000000,   # 5s in nanoseconds
            'retries': 10
        }
    }

    container = docker_manager.create_test_container(
        name='test_postgres_shared',
        config=container_config
    )

    # Wait for container to be healthy
    is_healthy = docker_manager.wait_for_health(
        container_name='test_postgres_shared',
        timeout=60
    )

    if not is_healthy:
        pytest.fail("PostgreSQL container failed to start")

    # Get the mapped port
    container.reload()
    host_port = container.ports['5432/tcp'][0]['HostPort']

    # Update database config with actual container port
    test_container_config = dict(test_database_config)
    test_container_config['port'] = int(host_port)
    test_container_config['host'] = 'localhost'

    yield container, test_container_config


@pytest.fixture
def test_database_manager(postgres_container):
    """
    Database connection manager configured for the test PostgreSQL container.
    Each test gets its own database manager instance but uses the shared container.
    """
    container, db_config = postgres_container

    try:
        from shared.database.connection_manager import DatabaseConnectionManager

        # Create a mock config manager for integration tests
        # Use PgBouncer configuration pointing to the test PostgreSQL container
        config = Mock()
        config.pgbouncer_host = db_config['host']
        config.pgbouncer_port = db_config['port']
        config.postgres_host = db_config['host']
        config.postgres_port = db_config['port']
        config.postgres_db = db_config['database']
        config.postgres_user = db_config['username']
        config.postgres_password = db_config['password']
        config.is_docker_environment = False  # Direct connection for tests via PgBouncer config

        db_manager = DatabaseConnectionManager(config)
        return db_manager

    except ImportError:
        logger.warning("DatabaseConnectionManager not available")
        return None


# Authentication and authorization fixtures

@pytest.fixture
def mock_user_store():
    """Mock user store for unit testing."""
    from unittest.mock import AsyncMock

    user_store = AsyncMock()

    # Mock user data
    mock_user = Mock()
    mock_user.id = "user_123"
    mock_user.email = "test@example.com"
    mock_user.first_name = "Test"
    mock_user.last_name = "User"
    mock_user.role = "USER"
    mock_user.is_active = True
    mock_user.created_at = "2024-01-01T00:00:00Z"
    mock_user.updated_at = "2024-01-01T00:00:00Z"
    mock_user.last_login_at = None

    mock_admin = Mock()
    mock_admin.id = "admin_456"
    mock_admin.email = "admin@example.com"
    mock_admin.first_name = "Admin"
    mock_admin.last_name = "User"
    mock_admin.role = "ADMIN"
    mock_admin.is_active = True
    mock_admin.created_at = "2024-01-01T00:00:00Z"
    mock_admin.updated_at = "2024-01-01T00:00:00Z"
    mock_admin.last_login_at = None

    # Configure mock methods
    user_store.get_user_by_email.side_effect = lambda email: {
        "test@example.com": mock_user,
        "admin@example.com": mock_admin
    }.get(email)

    user_store.get_user_by_id.side_effect = lambda user_id: {
        "user_123": mock_user,
        "admin_456": mock_admin
    }.get(user_id)

    user_store.create_user.return_value = mock_user
    user_store.update_user.return_value = mock_user
    user_store.delete_user.return_value = True
    user_store.list_users.return_value = [mock_user, mock_admin]
    user_store.update_user_last_login.return_value = None
    user_store.is_email_available.return_value = True
    user_store.count_users.return_value = 2

    return user_store


@pytest.fixture
def test_database_user_store(test_database_manager):
    """Real database user store for integration testing."""
    if not test_database_manager:
        pytest.skip("Database manager not available for user store testing")

    try:
        from shared.auth.database_user_store import DatabaseUserStore
        return DatabaseUserStore(test_database_manager)
    except ImportError:
        pytest.skip("DatabaseUserStore not available")


@pytest.fixture
def mock_auth_middleware(test_api_key):
    """Mock authentication middleware for testing."""
    middleware = Mock()

    async def validate_api_key(api_key):
        if api_key == test_api_key:
            return {
                "valid": True,
                "user_id": "test_user_123",
                "permissions": ["storage:read", "storage:write", "admin:read"],
                "rate_limit": {
                    "requests_per_minute": 1000,
                    "current_usage": 45
                }
            }
        else:
            return {
                "valid": False,
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "API key is invalid or expired"
                }
            }

    async def check_permission(user_id, resource, action):
        # Simple permission model for testing
        permissions = {
            "test_user_123": {
                "bucket:test_bucket": ["read", "write"],
                "file:test_file": ["read"],
                "admin:*": ["read"]
            }
        }

        user_perms = permissions.get(user_id, {})
        resource_perms = user_perms.get(resource, [])

        if action in resource_perms or "*" in resource_perms:
            return {
                "allowed": True,
                "user_id": user_id,
                "resource": resource,
                "action": action
            }
        else:
            return {
                "allowed": False,
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": f"User {user_id} does not have {action} permission for {resource}"
                }
            }

    middleware.validate_api_key = AsyncMock(side_effect=validate_api_key)
    middleware.check_permission = AsyncMock(side_effect=check_permission)

    return middleware


@pytest.fixture
def mock_jwt_service():
    """Mock JWT service for testing."""
    from unittest.mock import Mock
    from shared.auth.jwt_service import JWTService

    jwt_service = Mock(spec=JWTService)

    # Mock token generation
    jwt_service.generate_access_token.return_value = "mock_access_token_123"
    jwt_service.generate_refresh_token.return_value = "mock_refresh_token_456"

    # Mock token validation
    jwt_service.validate_access_token.return_value = {
        "user_id": "user_123",
        "email": "test@example.com",
        "role": "USER",
        "is_active": True,
        "exp": 1234567890
    }
    jwt_service.validate_refresh_token.return_value = {
        "user_id": "user_123",
        "email": "test@example.com",
        "role": "USER",
        "is_active": True,
        "exp": 1234567890
    }

    # Mock token blacklisting
    jwt_service.blacklist_token.return_value = None
    jwt_service.is_token_blacklisted.return_value = False

    return jwt_service


@pytest.fixture
def test_jwt_token():
    """Sample JWT token for testing."""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoidXNlcl8xMjMiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJyb2xlIjoiVVNFUiIsImlzX2FjdGl2ZSI6dHJ1ZSwiaWF0IjoxNjM4MzQ1NjAwLCJleHAiOjE2MzgzNDkyMDB9.mock_signature"


@pytest.fixture
def test_admin_jwt_token():
    """Sample admin JWT token for testing."""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYWRtaW5fNDU2IiwiZW1haWwiOiJhZG1pbkBleGFtcGxlLmNvbSIsInJvbGUiOiJBRE1JTiIsImlzX2FjdGl2ZSI6dHJ1ZSwiaWF0IjoxNjM4MzQ1NjAwLCJleHAiOjE2MzgzNDkyMDB9.mock_admin_signature"


# Request/Response fixtures

@pytest.fixture
def mock_request():
    """Mock HTTP request for middleware testing."""
    request = Mock()
    request.headers = {}
    request.url = Mock()
    request.url.path = "/api/v1/test"
    request.query_params = {}
    request.state = Mock()
    return request


@pytest.fixture
def mock_call_next():
    """Mock call_next function for middleware testing."""
    async def call_next(request):
        response = Mock()
        response.status_code = 200
        response.body = b'{"message": "success"}'
        response.headers = {}
        return response
    return call_next


# Utility fixtures

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": "user_123",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "role": "USER",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "last_login_at": None
    }


@pytest.fixture
def sample_admin_data():
    """Sample admin user data for testing."""
    return {
        "id": "admin_456",
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User",
        "role": "ADMIN",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "last_login_at": None
    }


@pytest.fixture
def sample_user_registration_data():
    """Sample user registration data for testing."""
    return {
        "email": "newuser@example.com",
        "password": "TestPassword123",
        "first_name": "New",
        "last_name": "User"
    }


@pytest.fixture
def sample_user_login_data():
    """Sample user login data for testing."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123"
    }


@pytest.fixture
def sample_bucket_data():
    """Sample bucket data for testing."""
    import uuid
    return {
        "bucket_id": str(uuid.uuid4()),
        "name": "test-bucket",
        "public": False,
        "owner_id": "user_123",
        "description": "Test bucket for unit testing"
    }


@pytest.fixture
def sample_file_data():
    """Sample file data for testing."""
    import uuid
    return {
        "id": str(uuid.uuid4()),
        "name": "test-file.txt",
        "mime_type": "text/plain",
        "size": 1024,
        "bucket_id": "bucket_123",
        "metadata": {"author": "Test User"}
    }


# Pytest configuration

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "docker: mark test as requiring Docker")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add integration marker for tests in integration directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add docker marker for tests that use docker fixtures
        if "docker" in str(item.fspath) or "container" in str(item.fspath):
            item.add_marker(pytest.mark.docker)


# Concurrent function execution fixtures

@pytest.fixture(scope="session")
def mock_database_manager():
    """Session-scoped mock database manager for concurrent function tests."""
    mock_db = AsyncMock()
    mock_db.save_function = AsyncMock()
    mock_db.get_function_by_id = AsyncMock()
    mock_db.update_function = AsyncMock()
    mock_db.save_execution_environment = AsyncMock()
    mock_db.get_execution_environment = AsyncMock()
    mock_db.save_resource_usage = AsyncMock()
    mock_db.save_execution_metrics = AsyncMock()
    mock_db.get_concurrent_execution_stats = AsyncMock(return_value={
        "active_executions": 0,
        "max_concurrent": 10,
        "average_execution_time": 150
    })
    return mock_db

@pytest.fixture(scope="session")
def execution_environment(mock_database_manager):
    """Session-scoped function execution environment."""
    from shared.services.function_execution_environment import FunctionExecutionEnvironment
    return FunctionExecutionEnvironment(
        database_manager=mock_database_manager,
        enable_isolation=True,
        max_memory_mb=1024,
        max_cpu_cores=4.0
    )

@pytest.fixture(scope="session")
def concurrent_manager(mock_database_manager, execution_environment):
    """Session-scoped concurrent function manager."""
    from shared.services.function_concurrent_manager import ConcurrentFunctionManager, IsolationLevel
    return ConcurrentFunctionManager(
        database_manager=mock_database_manager,
        execution_environment=execution_environment,
        max_concurrent_executions=10,
        resource_pool_size=8,
        enable_resource_monitoring=True,
        isolation_level=IsolationLevel.PROCESS
    )

@pytest.fixture(scope="session")
def sample_concurrent_functions():
    """Session-scoped sample functions for concurrent testing."""
    import uuid
    from shared.models.function import Function
    
    functions = []
    
    # CPU-intensive function
    cpu_function = Function(
        id=uuid.uuid4(),
        name="cpu-intensive",
        code='''
        export default async function(request) {
            const start = Date.now();
            let result = 0;
            
            // Simulate CPU work
            for (let i = 0; i < 100000; i++) {
                result += Math.sqrt(i);
            }
            
            return {
                type: "cpu-intensive",
                result: result,
                duration: Date.now() - start,
                timestamp: new Date().toISOString()
            };
        }
        ''',
        runtime="deno_typescript",
        owner_id=uuid.uuid4(),
        is_active=True
    )
    functions.append(cpu_function)
    
    # I/O-bound function (simulated)
    io_function = Function(
        id=uuid.uuid4(),
        name="io-bound",
        code='''
        export default async function(request) {
            const start = Date.now();
            
            // Simulate async I/O work
            await new Promise(resolve => setTimeout(resolve, 100));
            
            return {
                type: "io-bound",
                request_id: request.id || "unknown",
                duration: Date.now() - start,
                timestamp: new Date().toISOString()
            };
        }
        ''',
        runtime="deno_typescript", 
        owner_id=uuid.uuid4(),
        is_active=True
    )
    functions.append(io_function)
    
    # Memory-intensive function
    memory_function = Function(
        id=uuid.uuid4(),
        name="memory-intensive",
        code='''
        export default async function(request) {
            const start = Date.now();
            
            // Allocate memory
            const largeArray = new Array(50000).fill(0).map((_, i) => ({
                id: i,
                data: `item-${i}`,
                timestamp: Date.now()
            }));
            
            return {
                type: "memory-intensive",
                items_created: largeArray.length,
                duration: Date.now() - start,
                timestamp: new Date().toISOString()
            };
        }
        ''',
        runtime="deno_typescript",
        owner_id=uuid.uuid4(), 
        is_active=True
    )
    functions.append(memory_function)
    
    return functions

# Cleanup fixtures

# HTTP client fixture for integration tests

@pytest_asyncio.fixture
async def client():
    """Async HTTP client for integration testing."""
    try:
        from httpx import AsyncClient, Timeout

        # Create a basic async client for testing with longer timeouts for database operations
        timeout = Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        async with AsyncClient(base_url="http://localhost:8000", timeout=timeout) as test_client:
            yield test_client
    except ImportError:
        pytest.skip("httpx not available for integration testing")


@pytest.fixture(scope="session")
def cleanup_database_manager(dev_config_manager):
    """
    Database connection manager configured for cleanup operations using PgBouncer.

    This fixture provides a database manager that uses PgBouncer connections
    for cleanup operations, ensuring we use the same connection infrastructure
    as production code.
    """
    try:
        from shared.database.connection_manager import DatabaseConnectionManager
        from unittest.mock import Mock

        # Create a modified config for cleanup that uses localhost for PgBouncer
        # since tests run on host machine and can't resolve Docker service names
        cleanup_config = Mock()
        cleanup_config.pgbouncer_host = 'localhost'
        cleanup_config.pgbouncer_port = dev_config_manager.pgbouncer_port
        cleanup_config.postgres_db = dev_config_manager.postgres_db
        cleanup_config.postgres_user = dev_config_manager.postgres_user
        cleanup_config.postgres_password = dev_config_manager.postgres_password
        cleanup_config.is_docker_environment = False  # Force non-docker for cleanup

        # Copy other necessary attributes
        for attr in dir(dev_config_manager):
            if not attr.startswith('_') and not hasattr(cleanup_config, attr):
                try:
                    setattr(cleanup_config, attr, getattr(dev_config_manager, attr))
                except:
                    pass  # Skip attributes that can't be copied

        db_manager = DatabaseConnectionManager(cleanup_config)
        return db_manager

    except ImportError:
        logger.warning("DatabaseConnectionManager not available for cleanup")
        return None


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_resources(cleanup_database_manager):
    """Cleanup any test resources after the test session."""
    yield

    if not cleanup_database_manager:
        logger.warning("No database manager available for cleanup")
        return

    logger.info("Starting test resource cleanup...")

    try:
        import asyncio

        asyncio.run(_perform_cleanup(cleanup_database_manager))
        _cleanup_storage_buckets()

    except Exception as e:
        logger.error(f"Error during test resource cleanup: {e}")
        import traceback
        logger.error(f"Cleanup traceback: {traceback.format_exc()}")


async def _perform_cleanup(db_manager):
    """Perform actual cleanup operations."""
    try:
        # Helper function to check if table exists
        async def table_exists(table_name):
            try:
                async with db_manager.acquire() as conn:
                    result = await conn.fetchval(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
                        table_name
                    )
                    return result
            except Exception:
                return False

        # Clean up test users (but preserve admin user)
        if await table_exists('users'):
            async with db_manager.acquire() as conn:
                cleanup_users_sql = """
                DELETE FROM users
                WHERE email != 'admin@example.com'
                AND (email LIKE 'test_%@example.com'
                     OR email LIKE 'integration_%@example.com'
                     OR email LIKE '%_test_%@example.com'
                     OR email LIKE '%_integration_%@example.com')
                """
                await conn.execute(cleanup_users_sql)
                logger.info("Cleaned up test users")

        # Clean up test functions
        if await table_exists('functions'):
            async with db_manager.acquire() as conn:
                cleanup_functions_sql = """
                DELETE FROM functions
                WHERE name LIKE 'test-%'
                OR name LIKE 'integration-%'
                OR name LIKE '%-test'
                OR name LIKE '%-integration'
                """
                await conn.execute(cleanup_functions_sql)
                logger.info("Cleaned up test functions")

        # Clean up test webhooks
        if await table_exists('webhooks'):
            async with db_manager.acquire() as conn:
                cleanup_webhooks_sql = """
                DELETE FROM webhooks
                WHERE source_url LIKE '%test%'
                OR source_url LIKE '%integration%'
                OR name LIKE 'test-%'
                OR name LIKE 'integration-%'
                """
                await conn.execute(cleanup_webhooks_sql)
                logger.info("Cleaned up test webhooks")

        # Clean up test webhook audit logs (only if webhooks table exists)
        if await table_exists('webhook_audit') and await table_exists('webhooks'):
            async with db_manager.acquire() as conn:
                cleanup_webhook_audit_sql = """
                DELETE FROM webhook_audit
                WHERE webhook_id IN (
                    SELECT id FROM webhooks WHERE source_url LIKE '%test%' OR source_url LIKE '%integration%'
                )
                """
                await conn.execute(cleanup_webhook_audit_sql)
                logger.info("Cleaned up test webhook audit logs")

        # Clean up test buckets (but preserve system buckets)
        if await table_exists('buckets'):
            async with db_manager.acquire() as conn:
                cleanup_buckets_sql = """
                DELETE FROM buckets
                WHERE name LIKE 'test-%'
                OR name LIKE 'integration-%'
                OR name NOT IN ('default', 'system', 'public')
                """
                await conn.execute(cleanup_buckets_sql)
                logger.info("Cleaned up test buckets")

        # Clean up test files
        if await table_exists('files'):
            async with db_manager.acquire() as conn:
                cleanup_files_sql = """
                DELETE FROM files
                WHERE bucket_id IN (
                    SELECT id FROM buckets WHERE name LIKE 'test-%' OR name LIKE 'integration-%'
                )
                """
                await conn.execute(cleanup_files_sql)
                logger.info("Cleaned up test files")

        # Clean up function executions
        if await table_exists('function_executions'):
            async with db_manager.acquire() as conn:
                cleanup_executions_sql = """
                DELETE FROM function_executions
                WHERE function_id IN (
                    SELECT id FROM functions WHERE name LIKE 'test-%' OR name LIKE 'integration-%'
                )
                """
                await conn.execute(cleanup_executions_sql)
                logger.info("Cleaned up test function executions")

        logger.info("Test resource cleanup completed successfully")

    except Exception as e:
        logger.error(f"Error during cleanup operations: {e}")
        # Continue with other cleanup operations even if one fails
        raise  # Re-raise to ensure cleanup errors are visible


def _cleanup_storage_buckets():
    """Remove test buckets from the storage container's filesystem."""
    try:
        import docker

        client = docker.from_env()
        containers = client.containers.list(filters={"name": "storage"})
        if not containers:
            logger.info("No storage container found for cleanup")
            return

        container = containers[0]
        # List top-level entries under /app/data
        result = container.exec_run("sh -lc 'ls -1 /app/data 2>/dev/null || true'")
        output = getattr(result, "output", b"") or (result[1] if isinstance(result, tuple) and len(result) > 1 else b"")
        names = [line.strip() for line in output.decode().splitlines() if line.strip()]

        patterns = ("test-", "integration-", "it-")
        to_delete = [n for n in names if n == "test-bucket" or any(n.startswith(p) for p in patterns)]

        for name in to_delete:
            # Safety: restrict deletion strictly to known test prefixes
            cmd = f"sh -lc 'rm -rf -- /app/data/{name}'"
            container.exec_run(cmd)
            logger.info(f"Deleted storage bucket directory: {name}")
    except Exception as e:
        logger.warning(f"Storage cleanup skipped/failed: {e}")


# Mock database fixtures for unit tests

# Unit test fixtures for mocked database operations

class MockTransactionContext:
    """Mock async context manager for database transactions."""
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockAcquireContext:
    """Mock async context manager for database connections."""
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_db_connection():
    """Mock database connection with async methods."""
    connection = AsyncMock()
    connection.fetchrow = AsyncMock()
    connection.execute = AsyncMock()
    connection.fetch = AsyncMock()
    return connection


@pytest.fixture
def mock_db_transaction(mock_db_connection):
    """Mock database transaction context manager."""
    return MockTransactionContext(mock_db_connection)


@pytest.fixture
def mock_database_manager(mock_db_connection, mock_db_transaction):
    """Mock database manager with acquire and transaction methods."""
    manager = Mock()
    manager.acquire.return_value = MockAcquireContext(mock_db_connection)
    manager.transaction.return_value = mock_db_transaction
    return manager
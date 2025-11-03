"""
Unit tests for internal-only storage service.

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
        assert service.internal_only is True  # Must be internal-only by design
    
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
        assert service.internal_only is True      # Always internal-only
        assert service.port is None               # Port comes from config_manager
    
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
        config_manager.get_port.return_value = 8001
        
        service = Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
        
        port = service.get_service_port()
        
        assert port == 8001
        config_manager.get_port.assert_called_once_with("storage")
    
    def test_storage_get_configuration_settings(self, config_manager, auth_middleware):
        """Test that storage service can retrieve configuration settings."""
        from storage.storage import Storage
        
        # Mock configuration values
        config_manager.get_setting.side_effect = lambda key, default=None: {
            "MINIO_ENDPOINT": "minio:9000",
            "MINIO_ACCESS_KEY": "minioaccess",
            "MINIO_SECRET_KEY": "miniosecret",
            "MINIO_SECURE": False
        }.get(key, default)
        
        service = Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
        
        config = service.get_storage_configuration()
        
        assert config["endpoint"] == "minio:9000"
        assert config["access_key"] == "minioaccess"
        assert config["secret_key"] == "miniosecret"
        assert config["secure"] is False
    
    def test_storage_supported_backends_list(self, config_manager, auth_middleware):
        """Test getting list of supported storage backends."""
        from storage.storage import Storage
        
        service = Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
        
        supported_backends = service.get_supported_backends()
        
        expected_backends = ["minio", "local", "s3"]
        assert all(backend in supported_backends for backend in expected_backends)
        assert len(supported_backends) >= 3
    
    def test_storage_health_status_initialization(self, config_manager, auth_middleware):
        """Test that storage service initializes with healthy status."""
        from storage.storage import Storage
        
        service = Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
        
        health_status = service.get_health_status()
        
        assert health_status["status"] == "initializing"
        assert health_status["storage_backend"] == "minio"
        assert health_status["internal_only"] is True
        assert "startup_time" in health_status
        assert "version" in health_status


class TestStorageNetworkAccess:
    """Test suite for internal-only network access validation."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        # Mock different ports for different services
        def mock_get_port(service):
            port_map = {
                "storage": 8001,
                "backend": 8000,
                "functions": 8090,
                "postgres": 5432
            }
            return port_map.get(service, 8001)
        
        config_manager.get_port.side_effect = mock_get_port
        config_manager.get_setting.return_value = "test_value"
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
    
    def test_storage_is_internal_only_by_design(self, storage):
        """Test that storage service is always internal-only."""
        assert storage.internal_only is True
        
        # Cannot be overridden
        storage.internal_only = False
        assert storage.internal_only is True  # Should remain True
    
    def test_storage_has_no_external_endpoint(self, storage):
        """Test that storage service has no external endpoint configuration."""
        network_config = storage.get_network_configuration()
        
        assert network_config["internal_only"] is True
        assert network_config["external_access"] is False
        assert "external_endpoint" not in network_config
        assert "public_url" not in network_config
    
    def test_storage_validates_internal_network_access(self, storage):
        """Test that storage service validates internal network access."""
        # Should allow internal network access
        internal_request = {
            "source_ip": "172.18.0.1",  # Docker internal network
            "headers": {"host": "storage:8001"},
            "origin": "backend"
        }
        
        access_result = storage.validate_network_access(internal_request)
        
        assert access_result["allowed"] is True
        assert access_result["access_type"] == "internal"
        assert access_result["source"] == "docker_network"
    
    def test_storage_blocks_external_network_access(self, storage):
        """Test that storage service blocks external network access."""
        # Should block external network access
        external_request = {
            "source_ip": "192.168.1.100",  # External network
            "headers": {"host": "localhost:8001"},
            "origin": "external"
        }
        
        access_result = storage.validate_network_access(external_request)
        
        assert access_result["allowed"] is False
        assert access_result["access_type"] == "external"
        assert access_result["error"]["code"] == "EXTERNAL_ACCESS_DENIED"
        assert "internal-only" in access_result["error"]["message"].lower()
    
    def test_storage_validates_allowed_internal_sources(self, storage):
        """Test that storage service validates allowed internal sources."""
        allowed_sources = storage.get_allowed_internal_sources()
        
        expected_sources = [
            "backend",       # Backend service
            "functions",     # Functions runtime
            "docker_network" # Docker internal network
        ]
        
        for source in expected_sources:
            assert source in allowed_sources
        
        # External sources should not be allowed
        assert "frontend" not in allowed_sources  # Frontend should proxy through backend
        assert "public" not in allowed_sources
        assert "internet" not in allowed_sources
    
    def test_storage_docker_network_detection(self, storage):
        """Test Docker network detection for internal access."""
        # Test various Docker network scenarios
        docker_scenarios = [
            {
                "ip": "172.18.0.2",
                "host": "backend",
                "expected": True
            },
            {
                "ip": "172.19.0.3", 
                "host": "functions",
                "expected": True
            },
            {
                "ip": "10.0.0.1",
                "host": "gateway",
                "expected": False  # Not a known Docker network
            }
        ]
        
        for scenario in docker_scenarios:
            request = {
                "source_ip": scenario["ip"],
                "headers": {"host": f"{scenario['host']}:8001"}
            }
            
            is_docker = storage.is_docker_internal_network(request)
            assert is_docker == scenario["expected"]
    
    def test_storage_service_name_resolution(self, storage):
        """Test that storage service resolves internal service names."""
        service_resolution = storage.resolve_internal_services()
        
        expected_services = {
            "backend": "backend:8000",
            "functions": "functions:8090",
            "postgres": "postgres:5432"
        }
        
        for service_name, expected_address in expected_services.items():
            assert service_name in service_resolution
            # Should resolve to internal Docker service names, not localhost
            resolved = service_resolution[service_name]
            assert "localhost" not in resolved
            assert service_name in resolved
    
    def test_storage_cors_validation_for_internal_only(self, storage):
        """Test CORS validation specifically for internal-only access."""
        # Internal origins should be allowed
        internal_origins = [
            "http://backend:8000",
            "http://functions:8090",
            None  # No origin header for service-to-service
        ]
        
        for origin in internal_origins:
            cors_result = storage.validate_cors_origin(origin)
            assert cors_result["allowed"] is True
        
        # External origins should be blocked
        external_origins = [
            "http://localhost:3000",
            "https://external-site.com",
            "http://192.168.1.100:8001"
        ]
        
        for origin in external_origins:
            cors_result = storage.validate_cors_origin(origin)
            assert cors_result["allowed"] is False
            assert "internal-only" in cors_result["error"]["message"].lower()


class TestStorageBucketOperations:
    """Test suite for bucket creation and validation."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        # Mock different ports for different services
        def mock_get_port(service):
            port_map = {
                "storage": 8001,
                "backend": 8000,
                "functions": 8090,
                "postgres": 5432
            }
            return port_map.get(service, 8001)
        
        config_manager.get_port.side_effect = mock_get_port
        config_manager.get_setting.return_value = "test_value"
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
    
    @pytest.mark.asyncio
    async def test_bucket_creation_with_valid_data(self, storage):
        """Test creating bucket with valid data."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_data = {
            "bucket_id": "test-bucket-123",
            "name": "test-bucket",
            "public": False,
            "owner_id": user_uuid
        }
        
        # Mock the underlying storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.create_bucket = AsyncMock(return_value={"success": True})
        
        result = await storage.create_bucket(bucket_data, user_id=user_uuid)
        
        # Debug if test fails
        if not result["success"]:
            print(f"Failed result: {result}")
        
        assert result["success"] is True
        assert "id" in result["bucket"]  # Bucket model uses "id" not "bucket_id"
        assert result["bucket"]["name"] == "test-bucket"
        assert result["bucket"]["public"] is False
        assert result["bucket"]["owner_id"] == user_uuid
        assert "created_at" in result["bucket"]
    
    @pytest.mark.asyncio
    async def test_bucket_creation_missing_required_fields(self, storage):
        """Test bucket creation fails with missing required fields."""
        incomplete_bucket_data = {
            "name": "test-bucket"
            # Missing bucket_id, public, owner_id
        }
        
        result = await storage.create_bucket(incomplete_bucket_data, user_id="user_456")
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "required" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_bucket_creation_invalid_bucket_name(self, storage):
        """Test bucket creation fails with invalid bucket name."""
        invalid_bucket_data = {
            "bucket_id": "test-bucket-123",
            "name": "Invalid Bucket Name!@#",  # Invalid characters
            "public": False,
            "owner_id": "user_456"
        }
        
        result = await storage.create_bucket(invalid_bucket_data, user_id="user_456")
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_BUCKET_NAME"
        assert "invalid characters" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_bucket_creation_duplicate_name_for_user(self, storage):
        """Test bucket creation fails with duplicate name for same user."""
        bucket_data = {
            "bucket_id": "test-bucket-123",
            "name": "existing-bucket",
            "public": False,
            "owner_id": "user_456"
        }
        
        # Mock storage backend to simulate existing bucket
        storage._storage_backend = Mock()
        storage._storage_backend.create_bucket = AsyncMock(
            side_effect=Exception("Bucket already exists")
        )
        storage._storage_backend.bucket_exists = AsyncMock(return_value=True)
        
        result = await storage.create_bucket(bucket_data, user_id="user_456")
        
        assert result["success"] is False
        assert result["error"]["code"] == "BUCKET_ALREADY_EXISTS"
    
    @pytest.mark.asyncio
    async def test_bucket_creation_validates_owner_permission(self, storage):
        """Test bucket creation validates owner permission."""
        bucket_data = {
            "bucket_id": "test-bucket-123", 
            "name": "test-bucket",
            "public": False,
            "owner_id": "user_456"
        }
        
        # Try to create bucket as different user
        result = await storage.create_bucket(bucket_data, user_id="different_user_789")
        
        assert result["success"] is False
        assert result["error"]["code"] == "PERMISSION_DENIED"
        assert "own" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_bucket_creation_generates_minio_name(self, storage):
        """Test bucket creation generates MinIO-compatible internal name."""
        bucket_data = {
            "bucket_id": "test-bucket-123",
            "name": "my-test-bucket",  # URL-safe name
            "public": True,
            "owner_id": "user_456"
        }
        
        storage._storage_backend = Mock()
        storage._storage_backend.create_bucket = AsyncMock(return_value={"success": True})
        
        result = await storage.create_bucket(bucket_data, user_id="user_456")
        
        assert result["success"] is True
        # Should generate internal bucket name
        assert "internal_bucket_name" in result["bucket"]
        internal_name = result["bucket"]["internal_bucket_name"] 
        assert internal_name.islower()  # Internal names must be lowercase
        assert " " not in internal_name  # No spaces allowed
        assert internal_name.startswith("selfdb-")  # Our prefix
    
    @pytest.mark.asyncio
    async def test_bucket_creation_sets_default_metadata(self, storage):
        """Test bucket creation sets default metadata."""
        bucket_data = {
            "bucket_id": "test-bucket-123",
            "name": "test-bucket", 
            "public": False,
            "owner_id": "user_456"
        }
        
        storage._storage_backend = Mock()
        storage._storage_backend.create_bucket = AsyncMock(return_value={"success": True})
        
        result = await storage.create_bucket(bucket_data, user_id="user_456")
        
        assert result["success"] is True
        bucket = result["bucket"]
        
        # Check default metadata
        assert "created_at" in bucket
        assert "updated_at" in bucket
        assert bucket["file_count"] == 0
        assert bucket["total_size_bytes"] == 0
        assert bucket["version"] == "1.0"
    
    @pytest.mark.asyncio
    async def test_bucket_creation_with_optional_description(self, storage):
        """Test bucket creation with optional description."""
        bucket_data = {
            "bucket_id": "test-bucket-123",
            "name": "test-bucket",
            "public": False,
            "owner_id": "user_456",
            "description": "This is a test bucket for unit testing"
        }
        
        storage._storage_backend = Mock()
        storage._storage_backend.create_bucket = AsyncMock(return_value={"success": True})
        
        result = await storage.create_bucket(bucket_data, user_id="user_456")
        
        assert result["success"] is True
        assert result["bucket"]["description"] == "This is a test bucket for unit testing"
    
    @pytest.mark.asyncio
    async def test_bucket_creation_storage_backend_failure(self, storage):
        """Test bucket creation handles storage backend failure."""
        bucket_data = {
            "bucket_id": "test-bucket-123",
            "name": "test-bucket",
            "public": False,
            "owner_id": "user_456"
        }
        
        # Mock storage backend failure
        storage._storage_backend = Mock()
        storage._storage_backend.create_bucket = AsyncMock(
            side_effect=Exception("MinIO connection error")
        )
        
        result = await storage.create_bucket(bucket_data, user_id="user_456")
        
        assert result["success"] is False
        assert result["error"]["code"] == "STORAGE_BACKEND_ERROR"
        assert "storage" in result["error"]["message"].lower()


class TestStorageBucketListing:
    """Test suite for bucket listing with pagination."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        # Mock different ports for different services
        def mock_get_port(service):
            port_map = {
                "storage": 8001,
                "backend": 8000,
                "functions": 8090,
                "postgres": 5432
            }
            return port_map.get(service, 8001)
        
        config_manager.get_port.side_effect = mock_get_port
        config_manager.get_setting.return_value = "test_value"
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
    
    @pytest.mark.asyncio
    async def test_list_buckets_with_default_pagination(self, storage):
        """Test listing buckets with default pagination parameters."""
        import uuid
        user_uuid = str(uuid.uuid4())
        
        # Mock bucket data from storage backend
        mock_buckets = [
            {
                "id": str(uuid.uuid4()),
                "name": "bucket-1",
                "owner_id": user_uuid,
                "public": False,
                "created_at": "2025-01-01T10:00:00Z",
                "file_count": 5,
                "total_size_bytes": 1024
            },
            {
                "id": str(uuid.uuid4()),
                "name": "bucket-2", 
                "owner_id": user_uuid,
                "public": True,
                "created_at": "2025-01-01T11:00:00Z",
                "file_count": 10,
                "total_size_bytes": 2048
            }
        ]
        
        # Mock storage backend list method
        storage._storage_backend = Mock()
        storage._storage_backend.list_buckets = AsyncMock(return_value={
            "buckets": mock_buckets,
            "total": 2,
            "has_more": False
        })
        
        result = await storage.list_buckets(user_id=user_uuid)
        
        assert result["success"] is True
        assert len(result["buckets"]) == 2
        assert result["pagination"]["limit"] == 50  # Default limit
        assert result["pagination"]["offset"] == 0   # Default offset
        assert result["pagination"]["total"] == 2
        assert result["pagination"]["has_more"] is False
        
        # Verify bucket data structure
        bucket = result["buckets"][0]
        assert "id" in bucket
        assert "name" in bucket
        assert "owner_id" in bucket
        assert "public" in bucket
        assert "created_at" in bucket
        assert "file_count" in bucket
        assert "total_size_bytes" in bucket
    
    @pytest.mark.asyncio
    async def test_list_buckets_with_custom_pagination(self, storage):
        """Test listing buckets with custom pagination parameters."""
        import uuid
        user_uuid = str(uuid.uuid4())
        
        # Mock storage backend with pagination
        storage._storage_backend = Mock()
        storage._storage_backend.list_buckets = AsyncMock(return_value={
            "buckets": [],
            "total": 25,
            "has_more": True
        })
        
        result = await storage.list_buckets(
            user_id=user_uuid,
            limit=10,
            offset=15,
            sort="name:asc"
        )
        
        assert result["success"] is True
        assert result["pagination"]["limit"] == 10
        assert result["pagination"]["offset"] == 15
        assert result["pagination"]["total"] == 25
        assert result["pagination"]["has_more"] is True
        assert result["pagination"]["sort"] == "name:asc"
        
        # Verify backend was called with correct parameters
        storage._storage_backend.list_buckets.assert_called_once_with(
            user_id=user_uuid,
            limit=10,
            offset=15,
            sort="name:asc",
            filters={}
        )
    
    @pytest.mark.asyncio
    async def test_list_buckets_validates_pagination_limits(self, storage):
        """Test bucket listing validates pagination limits."""
        import uuid
        user_uuid = str(uuid.uuid4())
        
        # Test limit too large
        result = await storage.list_buckets(
            user_id=user_uuid,
            limit=1001  # Over max limit of 1000
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_PAGINATION"
        assert "limit" in result["error"]["message"].lower()
        
        # Test negative offset
        result = await storage.list_buckets(
            user_id=user_uuid,
            limit=50,
            offset=-1
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_PAGINATION"
        assert "offset" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_list_buckets_with_filtering(self, storage):
        """Test listing buckets with filtering options."""
        import uuid
        user_uuid = str(uuid.uuid4())
        
        storage._storage_backend = Mock()
        storage._storage_backend.list_buckets = AsyncMock(return_value={
            "buckets": [],
            "total": 0,
            "has_more": False
        })
        
        filters = {
            "public": True,
            "name_prefix": "prod-"
        }
        
        result = await storage.list_buckets(
            user_id=user_uuid,
            filters=filters
        )
        
        assert result["success"] is True
        
        # Verify filters were passed to backend
        storage._storage_backend.list_buckets.assert_called_once_with(
            user_id=user_uuid,
            limit=50,
            offset=0,
            sort="created_at:desc",
            filters=filters
        )
    
    @pytest.mark.asyncio
    async def test_list_buckets_validates_sort_options(self, storage):
        """Test bucket listing validates sort options."""
        import uuid
        user_uuid = str(uuid.uuid4())
        
        # Test invalid sort field
        result = await storage.list_buckets(
            user_id=user_uuid,
            sort="invalid_field:asc"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_SORT"
        assert "invalid_field" in result["error"]["message"]
        
        # Test invalid sort direction
        result = await storage.list_buckets(
            user_id=user_uuid,
            sort="name:invalid"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_SORT"
        assert "direction" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_list_buckets_valid_sort_options(self, storage):
        """Test bucket listing accepts valid sort options."""
        import uuid
        user_uuid = str(uuid.uuid4())
        
        storage._storage_backend = Mock()
        storage._storage_backend.list_buckets = AsyncMock(return_value={
            "buckets": [],
            "total": 0,
            "has_more": False
        })
        
        valid_sorts = [
            "name:asc",
            "name:desc", 
            "created_at:asc",
            "created_at:desc",
            "updated_at:asc",
            "updated_at:desc",
            "file_count:asc",
            "file_count:desc",
            "total_size:asc",
            "total_size:desc"
        ]
        
        for sort_option in valid_sorts:
            result = await storage.list_buckets(
                user_id=user_uuid,
                sort=sort_option
            )
            assert result["success"] is True, f"Failed for sort: {sort_option}"
    
    @pytest.mark.asyncio
    async def test_list_buckets_empty_result(self, storage):
        """Test listing buckets when no buckets exist."""
        import uuid
        user_uuid = str(uuid.uuid4())
        
        storage._storage_backend = Mock()
        storage._storage_backend.list_buckets = AsyncMock(return_value={
            "buckets": [],
            "total": 0,
            "has_more": False
        })
        
        result = await storage.list_buckets(user_id=user_uuid)
        
        assert result["success"] is True
        assert len(result["buckets"]) == 0
        assert result["pagination"]["total"] == 0
        assert result["pagination"]["has_more"] is False
    
    @pytest.mark.asyncio
    async def test_list_buckets_storage_backend_error(self, storage):
        """Test listing buckets handles storage backend errors."""
        import uuid
        user_uuid = str(uuid.uuid4())
        
        storage._storage_backend = Mock()
        storage._storage_backend.list_buckets = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        
        result = await storage.list_buckets(user_id=user_uuid)
        
        assert result["success"] is False
        assert result["error"]["code"] == "STORAGE_BACKEND_ERROR"
        assert "database" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_list_buckets_includes_minio_names(self, storage):
        """Test listing buckets includes MinIO internal names."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        mock_buckets = [
            {
                "id": bucket_uuid,
                "name": "my-bucket",
                "owner_id": user_uuid,
                "public": False,
                "created_at": "2025-01-01T10:00:00Z",
                "file_count": 0,
                "total_size_bytes": 0
            }
        ]
        
        storage._storage_backend = Mock()
        storage._storage_backend.list_buckets = AsyncMock(return_value={
            "buckets": mock_buckets,
            "total": 1,
            "has_more": False
        })
        
        result = await storage.list_buckets(user_id=user_uuid)
        
        assert result["success"] is True
        bucket = result["buckets"][0]
        assert "internal_bucket_name" in bucket
        
        # Internal name should follow our naming convention
        internal_name = bucket["internal_bucket_name"]
        assert internal_name.startswith("selfdb-")
        assert bucket_uuid in internal_name
        assert "my-bucket" in internal_name


class TestStorageBucketCrudOperations:
    """Test storage service bucket CRUD operations (get, update, delete)."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        config_manager.get_port.return_value = 8001
        config_manager.get_setting.return_value = "test_value"
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware,
            storage_backend="minio",
            enable_streaming=True
        )
    
    @pytest.mark.asyncio
    async def test_get_bucket_success(self, storage):
        """Test getting a bucket by ID."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        expected_bucket = {
            "id": bucket_uuid,
            "name": "test-bucket",
            "owner_id": user_uuid,
            "public": False,
            "description": "Test bucket",
            "metadata": {"key": "value"},
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-01T10:00:00Z",
            "file_count": 5,
            "total_size_bytes": 1024
        }
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.get_bucket = AsyncMock(return_value={
            "success": True,
            "bucket": expected_bucket
        })
        
        result = await storage.get_bucket(bucket_id=bucket_uuid, user_id=user_uuid)
        
        assert result["success"] is True
        assert result["bucket"]["id"] == bucket_uuid
        assert result["bucket"]["name"] == "test-bucket"
        assert result["bucket"]["owner_id"] == user_uuid
        assert "internal_bucket_name" in result["bucket"]
        
        # Verify internal bucket name is added
        internal_name = result["bucket"]["internal_bucket_name"]
        assert internal_name.startswith("selfdb-")
        assert bucket_uuid in internal_name
        assert "test-bucket" in internal_name
        
        # Verify backend was called correctly
        storage._storage_backend.get_bucket.assert_called_once_with(
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
    
    @pytest.mark.asyncio
    async def test_get_bucket_not_found(self, storage):
        """Test getting a non-existent bucket."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Mock storage backend to return not found
        storage._storage_backend = Mock()
        storage._storage_backend.get_bucket = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "BUCKET_NOT_FOUND",
                "message": "Bucket not found"
            }
        })
        
        result = await storage.get_bucket(bucket_id=bucket_uuid, user_id=user_uuid)
        
        assert result["success"] is False
        assert result["error"]["code"] == "BUCKET_NOT_FOUND"
        assert "not found" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_get_bucket_permission_denied(self, storage):
        """Test getting a bucket with no permission."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Mock storage backend to return permission denied
        storage._storage_backend = Mock()
        storage._storage_backend.get_bucket = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "Access denied to bucket"
            }
        })
        
        result = await storage.get_bucket(bucket_id=bucket_uuid, user_id=user_uuid)
        
        assert result["success"] is False
        assert result["error"]["code"] == "PERMISSION_DENIED"
        assert "denied" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_update_bucket_success(self, storage):
        """Test updating a bucket."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        update_data = {
            "name": "updated-bucket",
            "description": "Updated description",
            "public": True,
            "metadata": {"updated": "true"}
        }
        
        updated_bucket = {
            "id": bucket_uuid,
            "name": "updated-bucket",
            "owner_id": user_uuid,
            "public": True,
            "description": "Updated description",
            "metadata": {"updated": "true"},
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-01T11:00:00Z",
            "file_count": 5,
            "total_size_bytes": 1024
        }
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.update_bucket = AsyncMock(return_value={
            "success": True,
            "bucket": updated_bucket
        })
        
        result = await storage.update_bucket(
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            update_data=update_data
        )
        
        assert result["success"] is True
        assert result["bucket"]["name"] == "updated-bucket"
        assert result["bucket"]["public"] is True
        assert result["bucket"]["description"] == "Updated description"
        assert "internal_bucket_name" in result["bucket"]
        
        # Verify backend was called correctly
        storage._storage_backend.update_bucket.assert_called_once_with(
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            update_data=update_data
        )
    
    @pytest.mark.asyncio
    async def test_update_bucket_validates_name(self, storage):
        """Test bucket update validates bucket name."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        update_data = {
            "name": "invalid bucket name!"  # Contains invalid characters
        }
        
        result = await storage.update_bucket(
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            update_data=update_data
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_BUCKET_NAME"
        assert "invalid characters" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_update_bucket_not_found(self, storage):
        """Test updating a non-existent bucket."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        update_data = {"description": "New description"}
        
        # Mock storage backend to return not found
        storage._storage_backend = Mock()
        storage._storage_backend.update_bucket = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "BUCKET_NOT_FOUND",
                "message": "Bucket not found"
            }
        })
        
        result = await storage.update_bucket(
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            update_data=update_data
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "BUCKET_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_delete_bucket_success(self, storage):
        """Test deleting a bucket."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.delete_bucket = AsyncMock(return_value={
            "success": True,
            "message": "Bucket deleted successfully"
        })
        
        result = await storage.delete_bucket(bucket_id=bucket_uuid, user_id=user_uuid)
        
        assert result["success"] is True
        assert "deleted" in result["message"].lower()
        
        # Verify backend was called correctly
        storage._storage_backend.delete_bucket.assert_called_once_with(
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
    
    @pytest.mark.asyncio
    async def test_delete_bucket_not_empty(self, storage):
        """Test deleting a bucket that contains files."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Mock storage backend to return bucket not empty error
        storage._storage_backend = Mock()
        storage._storage_backend.delete_bucket = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "BUCKET_NOT_EMPTY",
                "message": "Cannot delete bucket with files. Delete all files first."
            }
        })
        
        result = await storage.delete_bucket(bucket_id=bucket_uuid, user_id=user_uuid)
        
        assert result["success"] is False
        assert result["error"]["code"] == "BUCKET_NOT_EMPTY"
        assert "files" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_delete_bucket_not_found(self, storage):
        """Test deleting a non-existent bucket."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Mock storage backend to return not found
        storage._storage_backend = Mock()
        storage._storage_backend.delete_bucket = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "BUCKET_NOT_FOUND",
                "message": "Bucket not found"
            }
        })
        
        result = await storage.delete_bucket(bucket_id=bucket_uuid, user_id=user_uuid)
        
        assert result["success"] is False
        assert result["error"]["code"] == "BUCKET_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_delete_bucket_permission_denied(self, storage):
        """Test deleting a bucket without permission."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Mock storage backend to return permission denied
        storage._storage_backend = Mock()
        storage._storage_backend.delete_bucket = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "Access denied to bucket"
            }
        })
        
        result = await storage.delete_bucket(bucket_id=bucket_uuid, user_id=user_uuid)
        
        assert result["success"] is False
        assert result["error"]["code"] == "PERMISSION_DENIED"
    
    @pytest.mark.asyncio
    async def test_bucket_operations_storage_backend_error(self, storage):
        """Test bucket operations handle storage backend errors."""
        import uuid
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Mock storage backend to raise exception
        storage._storage_backend = Mock()
        storage._storage_backend.get_bucket = AsyncMock(side_effect=Exception("Backend error"))
        
        result = await storage.get_bucket(bucket_id=bucket_uuid, user_id=user_uuid)
        
        assert result["success"] is False
        assert result["error"]["code"] == "STORAGE_BACKEND_ERROR"
        assert "backend error" in result["error"]["message"].lower()


class TestStorageFileUpload:
    """Test storage service file upload with streaming support."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        config_manager.get_port.return_value = 8001
        config_manager.get_setting.return_value = "test_value"
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware,
            storage_backend="minio",
            enable_streaming=True
        )
    
    @pytest.mark.asyncio
    async def test_upload_file_success(self, storage):
        """Test successful file upload with streaming."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Create mock file data
        file_data = b"Hello, World! This is test file content."
        file_stream = io.BytesIO(file_data)
        
        upload_data = {
            "id": file_uuid,
            "bucket_id": bucket_uuid,
            "name": "test-file.txt",
            "mime_type": "text/plain",
            "size": len(file_data)
        }
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.upload_file = AsyncMock(return_value={
            "success": True,
            "file": {
                "id": file_uuid,
                "name": "test-file.txt",
                "bucket_id": bucket_uuid,
                "mime_type": "text/plain",
                "size": len(file_data),
                "upload_complete": True,
                "created_at": "2025-01-01T10:00:00Z"
            }
        })
        
        result = await storage.upload_file(
            file_stream=file_stream,
            upload_data=upload_data,
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["file"]["id"] == file_uuid
        assert result["file"]["name"] == "test-file.txt" 
        assert result["file"]["bucket_id"] == bucket_uuid
        assert result["file"]["mime_type"] == "text/plain"
        assert result["file"]["size"] == len(file_data)
        assert result["file"]["upload_complete"] is True
        
        # Verify backend was called correctly
        storage._storage_backend.upload_file.assert_called_once_with(
            file_stream=file_stream,
            upload_data=upload_data,
            user_id=user_uuid
        )
    
    @pytest.mark.asyncio
    async def test_upload_file_with_streaming_enabled(self, storage):
        """Test file upload with streaming I/O enabled."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Large file for streaming test
        large_data = b"X" * (5 * 1024 * 1024)  # 5MB file
        file_stream = io.BytesIO(large_data)
        
        upload_data = {
            "id": str(uuid.uuid4()),
            "bucket_id": bucket_uuid,
            "name": "large-file.dat",
            "mime_type": "application/octet-stream",
            "size": len(large_data)
        }
        
        # Mock storage backend with streaming support
        storage._storage_backend = Mock()
        storage._storage_backend.upload_file = AsyncMock(return_value={
            "success": True,
            "streaming_enabled": True,
            "chunks_processed": 5,
            "file": {
                "id": upload_data["id"],
                "name": upload_data["name"],
                "size": len(large_data)
            }
        })
        
        result = await storage.upload_file(
            file_stream=file_stream,
            upload_data=upload_data,
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["streaming_enabled"] is True
        assert "chunks_processed" in result
        
        # Verify streaming was used for large file
        call_args = storage._storage_backend.upload_file.call_args
        assert call_args[1]["file_stream"] == file_stream
        assert call_args[1]["upload_data"]["size"] > 1024 * 1024  # > 1MB
    
    @pytest.mark.asyncio
    async def test_upload_file_validates_required_fields(self, storage):
        """Test file upload validates required fields."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        file_stream = io.BytesIO(b"test")
        
        # Missing required fields
        incomplete_data = {
            "name": "test.txt"
            # Missing: id, bucket_id, mime_type, size
        }
        
        result = await storage.upload_file(
            file_stream=file_stream,
            upload_data=incomplete_data,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "required" in result["error"]["message"].lower()
        assert "missing_fields" in result["error"]
        
        # Check specific missing fields
        missing_fields = result["error"]["missing_fields"]
        expected_missing = ["id", "bucket_id", "mime_type", "size"]
        for field in expected_missing:
            assert field in missing_fields
    
    
    @pytest.mark.asyncio
    async def test_upload_file_validates_filename(self, storage):
        """Test file upload validates filename safety."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_stream = io.BytesIO(b"test")
        
        # Invalid filename with path traversal
        upload_data = {
            "id": str(uuid.uuid4()),
            "bucket_id": bucket_uuid,
            "name": "../../../etc/passwd",  # Path traversal attempt
            "mime_type": "text/plain",
            "size": 4
        }
        
        result = await storage.upload_file(
            file_stream=file_stream,
            upload_data=upload_data,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_FILENAME"
        assert "unsafe" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_upload_file_validates_content_type(self, storage):
        """Test file upload validates content type."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_stream = io.BytesIO(b"test")
        
        # Empty content type
        upload_data = {
            "id": str(uuid.uuid4()),
            "bucket_id": bucket_uuid,
            "name": "test.txt",
            "mime_type": "",  # Empty mime type
            "size": 4
        }
        
        result = await storage.upload_file(
            file_stream=file_stream,
            upload_data=upload_data,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_MIME_TYPE"
        assert "mime type" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_upload_file_bucket_not_found(self, storage):
        """Test file upload when bucket doesn't exist."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        nonexistent_bucket = str(uuid.uuid4())
        file_stream = io.BytesIO(b"test")
        
        upload_data = {
            "id": str(uuid.uuid4()),
            "bucket_id": nonexistent_bucket,
            "name": "test.txt",
            "mime_type": "text/plain",
            "size": 4
        }
        
        # Mock storage backend to return bucket not found
        storage._storage_backend = Mock()
        storage._storage_backend.upload_file = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "BUCKET_NOT_FOUND",
                "message": "Bucket not found"
            }
        })
        
        result = await storage.upload_file(
            file_stream=file_stream,
            upload_data=upload_data,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "BUCKET_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_upload_file_permission_denied(self, storage):
        """Test file upload with insufficient permissions."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_stream = io.BytesIO(b"test")
        
        upload_data = {
            "id": str(uuid.uuid4()),
            "bucket_id": bucket_uuid,
            "name": "test.txt",
            "mime_type": "text/plain",
            "size": 4
        }
        
        # Mock storage backend to return permission denied
        storage._storage_backend = Mock()
        storage._storage_backend.upload_file = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "User does not have upload permission to this bucket"
            }
        })
        
        result = await storage.upload_file(
            file_stream=file_stream,
            upload_data=upload_data,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "PERMISSION_DENIED"
        assert "permission" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_upload_file_storage_backend_error(self, storage):
        """Test file upload handles storage backend errors."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_stream = io.BytesIO(b"test")
        
        upload_data = {
            "id": str(uuid.uuid4()),
            "bucket_id": bucket_uuid,
            "name": "test.txt",
            "mime_type": "text/plain",
            "size": 4
        }
        
        # Mock storage backend to raise exception
        storage._storage_backend = Mock()
        storage._storage_backend.upload_file = AsyncMock(
            side_effect=Exception("Storage connection failed")
        )
        
        result = await storage.upload_file(
            file_stream=file_stream,
            upload_data=upload_data,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "STORAGE_BACKEND_ERROR"
        assert "storage" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_upload_file_with_metadata(self, storage):
        """Test file upload with custom metadata."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_stream = io.BytesIO(b"test content")
        
        upload_data = {
            "id": str(uuid.uuid4()),
            "bucket_id": bucket_uuid,
            "name": "document.pdf",
            "mime_type": "application/pdf",
            "size": 12,
            "metadata": {
                "author": "John Doe",
                "document_type": "invoice",
                "category": "business"
            }
        }
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.upload_file = AsyncMock(return_value={
            "success": True,
            "file": {
                "id": upload_data["id"],
                "name": upload_data["name"],
                "metadata": upload_data["metadata"]
            }
        })
        
        result = await storage.upload_file(
            file_stream=file_stream,
            upload_data=upload_data,
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["file"]["metadata"]["author"] == "John Doe"
        assert result["file"]["metadata"]["document_type"] == "invoice"
        assert result["file"]["metadata"]["category"] == "business"


class TestStorageFileDownload:
    """Test storage service file download with streaming support."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        config_manager.get_port.return_value = 8001
        config_manager.get_setting.return_value = "test_value"
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware,
            storage_backend="minio",
            enable_streaming=True
        )
    
    @pytest.mark.asyncio
    async def test_download_file_success(self, storage):
        """Test successful file download with streaming."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock file content
        file_content = b"Hello, World! This is the downloaded file content."
        file_stream = io.BytesIO(file_content)
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.download_file = AsyncMock(return_value={
            "success": True,
            "file_stream": file_stream,
            "file": {
                "id": file_uuid,
                "name": "downloaded-file.txt",
                "bucket_id": bucket_uuid,
                "mime_type": "text/plain",
                "size": len(file_content),
                "created_at": "2025-01-01T10:00:00Z"
            }
        })
        
        result = await storage.download_file(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["file"]["id"] == file_uuid
        assert result["file"]["name"] == "downloaded-file.txt"
        assert result["file"]["bucket_id"] == bucket_uuid
        assert result["file"]["mime_type"] == "text/plain"
        assert result["file"]["size"] == len(file_content)
        
        # Verify file stream content
        assert "file_stream" in result
        downloaded_content = result["file_stream"].read()
        assert downloaded_content == file_content
        
        # Verify backend was called correctly with additional parameters
        storage._storage_backend.download_file.assert_called_once_with(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            range_start=None,
            range_end=None,
            if_none_match=None
        )
    
    @pytest.mark.asyncio
    async def test_download_file_with_streaming_enabled(self, storage):
        """Test file download with streaming I/O for large files."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Large file content for streaming test
        large_content = b"X" * (10 * 1024 * 1024)  # 10MB file
        file_stream = io.BytesIO(large_content)
        
        # Mock storage backend with streaming support
        storage._storage_backend = Mock()
        storage._storage_backend.download_file = AsyncMock(return_value={
            "success": True,
            "file_stream": file_stream,
            "streaming_enabled": True,
            "chunk_size": 1024 * 1024,  # 1MB chunks
            "file": {
                "id": file_uuid,
                "name": "large-file.dat",
                "size": len(large_content)
            }
        })
        
        result = await storage.download_file(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["streaming_enabled"] is True
        assert "chunk_size" in result
        assert result["file"]["size"] == len(large_content)
        
        # Verify large file stream
        assert "file_stream" in result
        assert result["file_stream"].getvalue() == large_content
    
    @pytest.mark.asyncio
    async def test_download_file_not_found(self, storage):
        """Test downloading a non-existent file."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        nonexistent_file = str(uuid.uuid4())
        
        # Mock storage backend to return file not found
        storage._storage_backend = Mock()
        storage._storage_backend.download_file = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "FILE_NOT_FOUND",
                "message": "File not found"
            }
        })
        
        result = await storage.download_file(
            file_id=nonexistent_file,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "FILE_NOT_FOUND"
        assert "not found" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_download_file_bucket_not_found(self, storage):
        """Test downloading file from non-existent bucket."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        nonexistent_bucket = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock storage backend to return bucket not found
        storage._storage_backend = Mock()
        storage._storage_backend.download_file = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "BUCKET_NOT_FOUND",
                "message": "Bucket not found"
            }
        })
        
        result = await storage.download_file(
            file_id=file_uuid,
            bucket_id=nonexistent_bucket,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "BUCKET_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_download_file_permission_denied(self, storage):
        """Test file download with insufficient permissions."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock storage backend to return permission denied
        storage._storage_backend = Mock()
        storage._storage_backend.download_file = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "User does not have download permission for this file"
            }
        })
        
        result = await storage.download_file(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "PERMISSION_DENIED"
        assert "permission" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_download_file_validates_parameters(self, storage):
        """Test file download validates required parameters."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        
        # Test missing file_id
        result = await storage.download_file(
            file_id="",  # Empty file_id
            bucket_id=str(uuid.uuid4()),
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "file id" in result["error"]["message"].lower()
        
        # Test missing bucket_id
        result = await storage.download_file(
            file_id=str(uuid.uuid4()),
            bucket_id="",  # Empty bucket_id
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "bucket id" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_download_file_storage_backend_error(self, storage):
        """Test file download handles storage backend errors."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock storage backend to raise exception
        storage._storage_backend = Mock()
        storage._storage_backend.download_file = AsyncMock(
            side_effect=Exception("Storage connection failed")
        )
        
        result = await storage.download_file(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "STORAGE_BACKEND_ERROR"
        assert "storage" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_download_file_with_range_request(self, storage):
        """Test file download with HTTP range request for partial content."""
        import uuid
        import io
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Full file content
        full_content = b"0123456789" * 100  # 1000 bytes
        # Partial content (bytes 100-199)
        partial_content = full_content[100:200]
        partial_stream = io.BytesIO(partial_content)
        
        # Mock storage backend with range support
        storage._storage_backend = Mock()
        storage._storage_backend.download_file = AsyncMock(return_value={
            "success": True,
            "file_stream": partial_stream,
            "range_request": True,
            "content_range": "bytes 100-199/1000",
            "file": {
                "id": file_uuid,
                "name": "range-test.dat",
                "size": 1000  # Full file size
            }
        })
        
        result = await storage.download_file(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            range_header="bytes=100-199"
        )
        
        assert result["success"] is True
        assert result["range_request"] is True
        assert result["content_range"] == "bytes 100-199/1000"
        
        # Verify partial content
        downloaded_content = result["file_stream"].read()
        assert downloaded_content == partial_content
        assert len(downloaded_content) == 100
        
        # Verify backend was called with range parameters
        storage._storage_backend.download_file.assert_called_once_with(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            range_start=100,
            range_end=199,
            if_none_match=None
        )
    
    @pytest.mark.asyncio
    async def test_download_file_with_etag_conditional(self, storage):
        """Test file download with ETag conditional requests."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock storage backend for not modified response
        storage._storage_backend = Mock()
        storage._storage_backend.download_file = AsyncMock(return_value={
            "success": True,
            "not_modified": True,
            "etag": "\"abc123def456\"",
            "file": {
                "id": file_uuid,
                "name": "cached-file.jpg"
            }
        })
        
        result = await storage.download_file(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            if_none_match="\"abc123def456\""
        )
        
        assert result["success"] is True
        assert result["not_modified"] is True
        assert result["etag"] == "\"abc123def456\""
        assert "file_stream" not in result  # No content for 304 Not Modified
        
        # Verify backend was called with conditional parameters
        storage._storage_backend.download_file.assert_called_once_with(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            range_start=None,
            range_end=None,
            if_none_match="\"abc123def456\""
        )


class TestStorageFileMetadata:
    """Test suite for storage service file metadata operations (HEAD requests)."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        config_manager.get_port.return_value = 8003
        config_manager.get_setting.return_value = "test_value"
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware,
            storage_backend="minio",
            enable_streaming=True
        )
    
    @pytest.mark.asyncio
    async def test_get_file_metadata_success(self, storage):
        """Test successful file metadata retrieval."""
        import uuid
        from datetime import datetime, timezone
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # File metadata
        created_at = datetime.now(timezone.utc)
        updated_at = created_at
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.get_file_metadata = AsyncMock(return_value={
            "success": True,
            "metadata": {
                "id": file_uuid,
                "name": "metadata-test.pdf",
                "bucket_id": bucket_uuid,
                "size": 2048576,  # 2MB
                "mime_type": "application/pdf",
                "etag": "\"d41d8cd98f00b204e9800998ecf8427e\"",
                "created_at": created_at.isoformat(),
                "updated_at": updated_at.isoformat(),
                "version": "1.0",
                "metadata": {
                    "author": "Test User",
                    "title": "Test Document"
                }
            }
        })
        
        result = await storage.get_file_metadata(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["metadata"]["id"] == file_uuid
        assert result["metadata"]["name"] == "metadata-test.pdf"
        assert result["metadata"]["bucket_id"] == bucket_uuid
        assert result["metadata"]["size"] == 2048576
        assert result["metadata"]["mime_type"] == "application/pdf"
        assert "etag" in result["metadata"]
        assert "created_at" in result["metadata"]
        assert "updated_at" in result["metadata"]
        
        # Verify backend was called correctly
        storage._storage_backend.get_file_metadata.assert_called_once_with(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            if_modified_since=None
        )
    
    @pytest.mark.asyncio
    async def test_get_file_metadata_not_found(self, storage):
        """Test metadata retrieval for non-existent file."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        nonexistent_file = str(uuid.uuid4())
        
        # Mock storage backend to return file not found
        storage._storage_backend = Mock()
        storage._storage_backend.get_file_metadata = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "FILE_NOT_FOUND",
                "message": "File not found"
            }
        })
        
        result = await storage.get_file_metadata(
            file_id=nonexistent_file,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "FILE_NOT_FOUND"
        assert "not found" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_get_file_metadata_bucket_not_found(self, storage):
        """Test metadata retrieval from non-existent bucket."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        nonexistent_bucket = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock storage backend to return bucket not found
        storage._storage_backend = Mock()
        storage._storage_backend.get_file_metadata = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "BUCKET_NOT_FOUND",
                "message": "Bucket not found"
            }
        })
        
        result = await storage.get_file_metadata(
            file_id=file_uuid,
            bucket_id=nonexistent_bucket,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "BUCKET_NOT_FOUND"
        assert "bucket" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_get_file_metadata_permission_denied(self, storage):
        """Test metadata retrieval with insufficient permissions."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock storage backend to return permission denied
        storage._storage_backend = Mock()
        storage._storage_backend.get_file_metadata = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "User does not have read permission for this file"
            }
        })
        
        result = await storage.get_file_metadata(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "PERMISSION_DENIED"
        assert "permission" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_get_file_metadata_validates_parameters(self, storage):
        """Test file metadata validates required parameters."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        
        # Test missing file_id
        result = await storage.get_file_metadata(
            file_id="",  # Empty file_id
            bucket_id=str(uuid.uuid4()),
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "file id" in result["error"]["message"].lower()
        
        # Test missing bucket_id
        result = await storage.get_file_metadata(
            file_id=str(uuid.uuid4()),
            bucket_id="",  # Empty bucket_id
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "bucket id" in result["error"]["message"].lower()
        
        # Test missing user_id
        result = await storage.get_file_metadata(
            file_id=str(uuid.uuid4()),
            bucket_id=str(uuid.uuid4()),
            user_id=""  # Empty user_id
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "user id" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_get_file_metadata_storage_backend_error(self, storage):
        """Test file metadata handles storage backend errors."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock storage backend to raise exception
        storage._storage_backend = Mock()
        storage._storage_backend.get_file_metadata = AsyncMock(
            side_effect=Exception("Metadata service unavailable")
        )
        
        result = await storage.get_file_metadata(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "STORAGE_BACKEND_ERROR"
        assert "storage" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_get_file_metadata_with_conditional_request(self, storage):
        """Test file metadata with If-Modified-Since conditional request."""
        import uuid
        from datetime import datetime, timezone
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Last modified time for conditional request
        if_modified_since = datetime.now(timezone.utc).isoformat()
        
        # Mock storage backend for not modified response
        storage._storage_backend = Mock()
        storage._storage_backend.get_file_metadata = AsyncMock(return_value={
            "success": True,
            "not_modified": True,
            "last_modified": if_modified_since,
            "file": {
                "id": file_uuid,
                "name": "unchanged-file.txt"
            }
        })
        
        result = await storage.get_file_metadata(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            if_modified_since=if_modified_since
        )
        
        assert result["success"] is True
        assert result["not_modified"] is True
        assert result["last_modified"] == if_modified_since
        assert "metadata" not in result  # No full metadata for 304 Not Modified
        
        # Verify backend was called with conditional parameter
        storage._storage_backend.get_file_metadata.assert_called_once_with(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            if_modified_since=if_modified_since
        )
    
    @pytest.mark.asyncio
    async def test_get_file_metadata_with_custom_metadata(self, storage):
        """Test file metadata with custom user-defined metadata fields."""
        import uuid
        from datetime import datetime, timezone
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Custom metadata
        custom_metadata = {
            "department": "Engineering",
            "project": "SelfDB TDD",
            "classification": "Internal",
            "tags": ["storage", "files", "metadata"]
        }
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.get_file_metadata = AsyncMock(return_value={
            "success": True,
            "metadata": {
                "id": file_uuid,
                "name": "project-doc.docx",
                "bucket_id": bucket_uuid,
                "size": 524288,  # 512KB
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "etag": "\"custom-etag-with-metadata\"",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0",
                "metadata": custom_metadata
            }
        })
        
        result = await storage.get_file_metadata(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["metadata"]["metadata"] == custom_metadata
        assert result["metadata"]["metadata"]["department"] == "Engineering"
        assert result["metadata"]["metadata"]["project"] == "SelfDB TDD"
        assert isinstance(result["metadata"]["metadata"]["tags"], list)
        assert len(result["metadata"]["metadata"]["tags"]) == 3


class TestStorageFileListing:
    """Test suite for storage service file listing with pagination and filtering."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        config_manager.get_port.return_value = 8003
        config_manager.get_setting.return_value = "test_value"
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware,
            storage_backend="minio",
            enable_streaming=True
        )
    
    @pytest.mark.asyncio
    async def test_list_files_success_with_pagination(self, storage):
        """Test successful file listing with pagination."""
        import uuid
        from datetime import datetime, timezone
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Sample files for pagination test
        files = [
            {
                "id": str(uuid.uuid4()),
                "name": f"file-{i:03d}.txt",
                "bucket_id": bucket_uuid,
                "size": 1024 * (i + 1),  # Different sizes
                "mime_type": "text/plain",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0",
                "etag": f'"etag-file-{i}"'
            }
            for i in range(15)  # 15 files total
        ]
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.list_files = AsyncMock(return_value={
            "success": True,
            "files": files[:10],  # First 10 files (limit=10, offset=0)
            "pagination": {
                "limit": 10,
                "offset": 0,
                "total": 15,
                "has_more": True,
                "sort": "name:asc"
            }
        })
        
        result = await storage.list_files(
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            limit=10,
            offset=0,
            sort="name:asc"
        )
        
        assert result["success"] is True
        assert len(result["files"]) == 10
        assert result["pagination"]["total"] == 15
        assert result["pagination"]["has_more"] is True
        assert result["pagination"]["limit"] == 10
        assert result["pagination"]["offset"] == 0
        assert result["pagination"]["sort"] == "name:asc"
        
        # Verify files are in correct format
        for file in result["files"]:
            assert "id" in file
            assert "name" in file
            assert "bucket_id" in file
            assert "size" in file
            assert "mime_type" in file
            assert "etag" in file
        
        # Verify backend was called correctly
        storage._storage_backend.list_files.assert_called_once_with(
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            limit=10,
            offset=0,
            sort="name:asc",
            filters={}
        )
    
    @pytest.mark.asyncio
    async def test_list_files_with_filters(self, storage):
        """Test file listing with various filters."""
        import uuid
        from datetime import datetime, timezone
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Filtered files (only PDFs)
        pdf_files = [
            {
                "id": str(uuid.uuid4()),
                "name": "document-001.pdf",
                "bucket_id": bucket_uuid,
                "size": 2048576,  # 2MB
                "mime_type": "application/pdf",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0",
                "etag": '"pdf-etag-1"'
            },
            {
                "id": str(uuid.uuid4()),
                "name": "report-002.pdf",
                "bucket_id": bucket_uuid,
                "size": 1048576,  # 1MB
                "mime_type": "application/pdf",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0",
                "etag": '"pdf-etag-2"'
            }
        ]
        
        filters = {
            "mime_type": "application/pdf",
            "size_min": 1000000,  # 1MB minimum
            "name_contains": ".pdf"
        }
        
        # Mock storage backend with filtered results
        storage._storage_backend = Mock()
        storage._storage_backend.list_files = AsyncMock(return_value={
            "success": True,
            "files": pdf_files,
            "pagination": {
                "limit": 50,
                "offset": 0,
                "total": 2,
                "has_more": False,
                "sort": "size:desc"
            }
        })
        
        result = await storage.list_files(
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            limit=50,
            offset=0,
            sort="size:desc",
            filters=filters
        )
        
        assert result["success"] is True
        assert len(result["files"]) == 2
        assert result["pagination"]["total"] == 2
        assert result["pagination"]["has_more"] is False
        
        # Verify all files match filters
        for file in result["files"]:
            assert file["mime_type"] == "application/pdf"
            assert file["size"] >= 1000000
            assert ".pdf" in file["name"]
        
        # Verify backend was called with filters
        storage._storage_backend.list_files.assert_called_once_with(
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            limit=50,
            offset=0,
            sort="size:desc",
            filters=filters
        )
    
    @pytest.mark.asyncio
    async def test_list_files_empty_bucket(self, storage):
        """Test listing files in empty bucket."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Mock storage backend with empty results
        storage._storage_backend = Mock()
        storage._storage_backend.list_files = AsyncMock(return_value={
            "success": True,
            "files": [],
            "pagination": {
                "limit": 50,
                "offset": 0,
                "total": 0,
                "has_more": False,
                "sort": "created_at:desc"
            }
        })
        
        result = await storage.list_files(
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert len(result["files"]) == 0
        assert result["pagination"]["total"] == 0
        assert result["pagination"]["has_more"] is False
    
    @pytest.mark.asyncio
    async def test_list_files_bucket_not_found(self, storage):
        """Test listing files from non-existent bucket."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        nonexistent_bucket = str(uuid.uuid4())
        
        # Mock storage backend to return bucket not found
        storage._storage_backend = Mock()
        storage._storage_backend.list_files = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "BUCKET_NOT_FOUND",
                "message": "Bucket not found"
            }
        })
        
        result = await storage.list_files(
            bucket_id=nonexistent_bucket,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "BUCKET_NOT_FOUND"
        assert "bucket" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_list_files_permission_denied(self, storage):
        """Test listing files with insufficient permissions."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Mock storage backend to return permission denied
        storage._storage_backend = Mock()
        storage._storage_backend.list_files = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "User does not have list permission for this bucket"
            }
        })
        
        result = await storage.list_files(
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "PERMISSION_DENIED"
        assert "permission" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_list_files_validates_parameters(self, storage):
        """Test file listing validates parameters."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        
        # Test missing bucket_id
        result = await storage.list_files(
            bucket_id="",  # Empty bucket_id
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "bucket id" in result["error"]["message"].lower()
        
        # Test missing user_id
        result = await storage.list_files(
            bucket_id=str(uuid.uuid4()),
            user_id=""  # Empty user_id
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "user id" in result["error"]["message"].lower()
        
        # Test invalid limit
        result = await storage.list_files(
            bucket_id=str(uuid.uuid4()),
            user_id=user_uuid,
            limit=0  # Invalid limit
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_PAGINATION"
        assert "limit" in result["error"]["message"].lower()
        
        # Test invalid offset
        result = await storage.list_files(
            bucket_id=str(uuid.uuid4()),
            user_id=user_uuid,
            offset=-1  # Invalid offset
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_PAGINATION"
        assert "offset" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_list_files_validates_sort_parameter(self, storage):
        """Test file listing validates sort parameter format."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Test invalid sort format
        result = await storage.list_files(
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            sort="name"  # Missing ":asc" or ":desc"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_SORT_FORMAT"
        assert "field:order" in result["error"]["message"]
        
        # Test invalid sort field
        result = await storage.list_files(
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            sort="invalid_field:asc"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_SORT"
        assert "invalid sort field" in result["error"]["message"].lower()
        
        # Test invalid sort order
        result = await storage.list_files(
            bucket_id=bucket_uuid,
            user_id=user_uuid,
            sort="name:invalid"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_SORT"
        assert "Must be 'asc' or 'desc'" in result["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_list_files_storage_backend_error(self, storage):
        """Test file listing handles storage backend errors."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Mock storage backend to raise exception
        storage._storage_backend = Mock()
        storage._storage_backend.list_files = AsyncMock(
            side_effect=Exception("File service unavailable")
        )
        
        result = await storage.list_files(
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "STORAGE_BACKEND_ERROR"
        assert "storage" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_list_files_with_multiple_sort_options(self, storage):
        """Test file listing with different sort options."""
        import uuid
        from datetime import datetime, timezone
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Files sorted by created_at:desc
        sorted_files = [
            {
                "id": str(uuid.uuid4()),
                "name": "newest-file.txt",
                "bucket_id": bucket_uuid,
                "size": 1024,
                "mime_type": "text/plain",
                "created_at": "2024-03-15T12:00:00Z",
                "updated_at": "2024-03-15T12:00:00Z",
                "version": "1.0"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "older-file.txt", 
                "bucket_id": bucket_uuid,
                "size": 2048,
                "mime_type": "text/plain",
                "created_at": "2024-03-14T12:00:00Z",
                "updated_at": "2024-03-14T12:00:00Z",
                "version": "1.0"
            }
        ]
        
        # Test different sort options
        sort_options = [
            "name:asc",
            "name:desc", 
            "size:asc",
            "size:desc",
            "created_at:asc",
            "created_at:desc",
            "updated_at:asc",
            "updated_at:desc"
        ]
        
        for sort_option in sort_options:
            # Mock storage backend for each sort option
            storage._storage_backend = Mock()
            storage._storage_backend.list_files = AsyncMock(return_value={
                "success": True,
                "files": sorted_files,
                "pagination": {
                    "limit": 50,
                    "offset": 0,
                    "total": 2,
                    "has_more": False,
                    "sort": sort_option
                }
            })
            
            result = await storage.list_files(
                bucket_id=bucket_uuid,
                user_id=user_uuid,
                sort=sort_option
            )
            
            assert result["success"] is True
            assert result["pagination"]["sort"] == sort_option
            
            # Verify backend was called with correct sort
            storage._storage_backend.list_files.assert_called_with(
                bucket_id=bucket_uuid,
                user_id=user_uuid,
                limit=50,
                offset=0,
                sort=sort_option,
                filters={}
            )


class TestStorageFileOperations:
    """Test suite for storage service file operations (delete, copy, move)."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        config_manager.get_port.return_value = 8003
        config_manager.get_setting.return_value = "test_value"
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware,
            storage_backend="minio",
            enable_streaming=True
        )
    
    # Delete File Tests
    
    @pytest.mark.asyncio
    async def test_delete_file_success(self, storage):
        """Test successful file deletion."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.delete_file = AsyncMock(return_value={
            "success": True,
            "deleted_file": {
                "id": file_uuid,
                "name": "deleted-file.txt",
                "bucket_id": bucket_uuid,
                "size": 1024,
                "deleted_at": "2024-03-15T12:00:00Z"
            }
        })
        
        result = await storage.delete_file(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["deleted_file"]["id"] == file_uuid
        assert result["deleted_file"]["name"] == "deleted-file.txt"
        assert result["deleted_file"]["bucket_id"] == bucket_uuid
        assert "deleted_at" in result["deleted_file"]
        
        # Verify backend was called correctly
        storage._storage_backend.delete_file.assert_called_once_with(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
    
    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, storage):
        """Test deleting a non-existent file."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        nonexistent_file = str(uuid.uuid4())
        
        # Mock storage backend to return file not found
        storage._storage_backend = Mock()
        storage._storage_backend.delete_file = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "FILE_NOT_FOUND",
                "message": "File not found"
            }
        })
        
        result = await storage.delete_file(
            file_id=nonexistent_file,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "FILE_NOT_FOUND"
        assert "not found" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_delete_file_permission_denied(self, storage):
        """Test deleting file with insufficient permissions."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock storage backend to return permission denied
        storage._storage_backend = Mock()
        storage._storage_backend.delete_file = AsyncMock(return_value={
            "success": False,
            "error": {
                "code": "PERMISSION_DENIED",
                "message": "User does not have delete permission for this file"
            }
        })
        
        result = await storage.delete_file(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "PERMISSION_DENIED"
        assert "permission" in result["error"]["message"].lower()
    
    # Copy File Tests
    
    @pytest.mark.asyncio
    async def test_copy_file_success(self, storage):
        """Test successful file copying."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        source_bucket = str(uuid.uuid4())
        dest_bucket = str(uuid.uuid4())
        source_file = str(uuid.uuid4())
        dest_file = str(uuid.uuid4())
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.copy_file = AsyncMock(return_value={
            "success": True,
            "source_file": {
                "id": source_file,
                "name": "original-file.pdf",
                "bucket_id": source_bucket
            },
            "copied_file": {
                "id": dest_file,
                "name": "copied-file.pdf",
                "bucket_id": dest_bucket,
                "size": 2048576,  # 2MB
                "mime_type": "application/pdf",
                "copied_at": "2024-03-15T12:00:00Z"
            }
        })
        
        result = await storage.copy_file(
            source_file_id=source_file,
            source_bucket_id=source_bucket,
            dest_bucket_id=dest_bucket,
            dest_file_name="copied-file.pdf",
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["source_file"]["id"] == source_file
        assert result["copied_file"]["id"] == dest_file
        assert result["copied_file"]["name"] == "copied-file.pdf"
        assert result["copied_file"]["bucket_id"] == dest_bucket
        assert "copied_at" in result["copied_file"]
        
        # Verify backend was called correctly
        storage._storage_backend.copy_file.assert_called_once_with(
            source_file_id=source_file,
            source_bucket_id=source_bucket,
            dest_bucket_id=dest_bucket,
            dest_file_name="copied-file.pdf",
            user_id=user_uuid
        )
    
    @pytest.mark.asyncio
    async def test_copy_file_cross_bucket(self, storage):
        """Test copying file between different buckets."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        source_bucket = str(uuid.uuid4())
        dest_bucket = str(uuid.uuid4())  # Different bucket
        source_file = str(uuid.uuid4())
        dest_file = str(uuid.uuid4())
        
        # Mock storage backend for cross-bucket copy
        storage._storage_backend = Mock()
        storage._storage_backend.copy_file = AsyncMock(return_value={
            "success": True,
            "source_file": {
                "id": source_file,
                "name": "source-doc.docx",
                "bucket_id": source_bucket
            },
            "copied_file": {
                "id": dest_file,
                "name": "destination-doc.docx",
                "bucket_id": dest_bucket,
                "size": 1048576,  # 1MB
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "cross_bucket_copy": True,
                "copied_at": "2024-03-15T12:00:00Z"
            }
        })
        
        result = await storage.copy_file(
            source_file_id=source_file,
            source_bucket_id=source_bucket,
            dest_bucket_id=dest_bucket,
            dest_file_name="destination-doc.docx",
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["source_file"]["bucket_id"] == source_bucket
        assert result["copied_file"]["bucket_id"] == dest_bucket
        assert result["copied_file"]["cross_bucket_copy"] is True
    
    # Move File Tests
    
    @pytest.mark.asyncio
    async def test_move_file_success(self, storage):
        """Test successful file moving."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        source_bucket = str(uuid.uuid4())
        dest_bucket = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.move_file = AsyncMock(return_value={
            "success": True,
            "moved_file": {
                "id": file_uuid,
                "name": "moved-image.png",
                "old_bucket_id": source_bucket,
                "new_bucket_id": dest_bucket,
                "size": 524288,  # 512KB
                "mime_type": "image/png",
                "moved_at": "2024-03-15T12:00:00Z"
            }
        })
        
        result = await storage.move_file(
            file_id=file_uuid,
            source_bucket_id=source_bucket,
            dest_bucket_id=dest_bucket,
            new_file_name="moved-image.png",
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["moved_file"]["id"] == file_uuid
        assert result["moved_file"]["name"] == "moved-image.png"
        assert result["moved_file"]["old_bucket_id"] == source_bucket
        assert result["moved_file"]["new_bucket_id"] == dest_bucket
        assert "moved_at" in result["moved_file"]
        
        # Verify backend was called correctly
        storage._storage_backend.move_file.assert_called_once_with(
            file_id=file_uuid,
            source_bucket_id=source_bucket,
            dest_bucket_id=dest_bucket,
            new_file_name="moved-image.png",
            user_id=user_uuid
        )
    
    @pytest.mark.asyncio
    async def test_move_file_same_bucket_rename(self, storage):
        """Test moving (renaming) file within the same bucket."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Mock storage backend for rename within same bucket
        storage._storage_backend = Mock()
        storage._storage_backend.move_file = AsyncMock(return_value={
            "success": True,
            "moved_file": {
                "id": file_uuid,
                "old_name": "old-filename.txt",
                "name": "new-filename.txt",
                "old_bucket_id": bucket_uuid,
                "new_bucket_id": bucket_uuid,
                "size": 2048,
                "mime_type": "text/plain",
                "renamed_in_place": True,
                "moved_at": "2024-03-15T12:00:00Z"
            }
        })
        
        result = await storage.move_file(
            file_id=file_uuid,
            source_bucket_id=bucket_uuid,
            dest_bucket_id=bucket_uuid,  # Same bucket
            new_file_name="new-filename.txt",
            user_id=user_uuid
        )
        
        assert result["success"] is True
        assert result["moved_file"]["old_bucket_id"] == bucket_uuid
        assert result["moved_file"]["new_bucket_id"] == bucket_uuid
        assert result["moved_file"]["renamed_in_place"] is True
        assert result["moved_file"]["old_name"] == "old-filename.txt"
        assert result["moved_file"]["name"] == "new-filename.txt"
    
    # Parameter Validation Tests
    
    @pytest.mark.asyncio
    async def test_file_operations_validate_parameters(self, storage):
        """Test file operations validate required parameters."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        
        # Test delete with empty file_id
        result = await storage.delete_file(
            file_id="",  # Empty file_id
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "file id" in result["error"]["message"].lower()
        
        # Test copy with empty source_file_id
        result = await storage.copy_file(
            source_file_id="",  # Empty source_file_id
            source_bucket_id=bucket_uuid,
            dest_bucket_id=bucket_uuid,
            dest_file_name="copy.txt",
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "source file id" in result["error"]["message"].lower()
        
        # Test move with empty dest_bucket_id
        result = await storage.move_file(
            file_id=str(uuid.uuid4()),
            source_bucket_id=bucket_uuid,
            dest_bucket_id="",  # Empty dest_bucket_id
            new_file_name="moved.txt",
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "destination bucket id" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_file_operations_validate_filenames(self, storage):
        """Test file operations validate filename safety."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        source_bucket = str(uuid.uuid4())
        dest_bucket = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Test copy with unsafe filename
        unsafe_filename = "../../../etc/passwd"
        
        result = await storage.copy_file(
            source_file_id=file_uuid,
            source_bucket_id=source_bucket,
            dest_bucket_id=dest_bucket,
            dest_file_name=unsafe_filename,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_FILENAME"
        assert "unsafe characters" in result["error"]["message"].lower()
        
        # Test move with unsafe filename
        result = await storage.move_file(
            file_id=file_uuid,
            source_bucket_id=source_bucket,
            dest_bucket_id=dest_bucket,
            new_file_name=unsafe_filename,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_FILENAME"
        assert "unsafe characters" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_file_operations_storage_backend_errors(self, storage):
        """Test file operations handle storage backend errors."""
        import uuid
        
        user_uuid = str(uuid.uuid4())
        bucket_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        # Test delete with backend error
        storage._storage_backend = Mock()
        storage._storage_backend.delete_file = AsyncMock(
            side_effect=Exception("Storage backend error")
        )
        
        result = await storage.delete_file(
            file_id=file_uuid,
            bucket_id=bucket_uuid,
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "STORAGE_BACKEND_ERROR"
        assert "storage" in result["error"]["message"].lower()
        
        # Test copy with backend error
        storage._storage_backend.copy_file = AsyncMock(
            side_effect=Exception("Copy operation failed")
        )
        
        result = await storage.copy_file(
            source_file_id=file_uuid,
            source_bucket_id=bucket_uuid,
            dest_bucket_id=bucket_uuid,
            dest_file_name="copy.txt",
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "STORAGE_BACKEND_ERROR"
        assert "storage" in result["error"]["message"].lower()
        
        # Test move with backend error
        storage._storage_backend.move_file = AsyncMock(
            side_effect=Exception("Move operation failed")
        )
        
        result = await storage.move_file(
            file_id=file_uuid,
            source_bucket_id=bucket_uuid,
            dest_bucket_id=bucket_uuid,
            new_file_name="moved.txt",
            user_id=user_uuid
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "STORAGE_BACKEND_ERROR"
        assert "storage" in result["error"]["message"].lower()


class TestStorageAuthIntegration:
    """Test suite for storage service authentication integration."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        config_manager.get_port.return_value = 8003
        config_manager.get_setting.return_value = "test_value"
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware,
            storage_backend="minio",
            enable_streaming=True
        )
    
    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, storage):
        """Test successful API key validation."""
        
        api_key = "sk-selfdb-test-key-12345"
        user_id = "test-user-123"
        
        # Mock auth middleware
        storage.auth_middleware.validate_api_key = AsyncMock(return_value={
            "valid": True,
            "user_id": user_id,
            "permissions": ["storage:read", "storage:write"],
            "rate_limit": {
                "requests_per_minute": 1000,
                "current_usage": 45
            }
        })
        
        result = await storage.validate_api_key(api_key)
        
        assert result["valid"] is True
        assert result["user_id"] == user_id
        assert "storage:read" in result["permissions"]
        assert "storage:write" in result["permissions"]
        assert "rate_limit" in result
        
        # Verify auth middleware was called
        storage.auth_middleware.validate_api_key.assert_called_once_with(api_key)
    
    @pytest.mark.asyncio
    async def test_validate_api_key_invalid(self, storage):
        """Test invalid API key validation."""
        
        invalid_api_key = "invalid-key-123"
        
        # Mock auth middleware to return invalid
        storage.auth_middleware.validate_api_key = AsyncMock(return_value={
            "valid": False,
            "error": {
                "code": "INVALID_API_KEY",
                "message": "API key is invalid or expired"
            }
        })
        
        result = await storage.validate_api_key(invalid_api_key)
        
        assert result["valid"] is False
        assert result["error"]["code"] == "INVALID_API_KEY"
        assert "invalid" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_validate_api_key_rate_limited(self, storage):
        """Test API key validation with rate limiting."""
        
        api_key = "sk-selfdb-rate-limited-key"
        
        # Mock auth middleware to return rate limit exceeded
        storage.auth_middleware.validate_api_key = AsyncMock(return_value={
            "valid": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded. Try again later.",
                "retry_after": 60
            }
        })
        
        result = await storage.validate_api_key(api_key)
        
        assert result["valid"] is False
        assert result["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "rate limit" in result["error"]["message"].lower()
        assert result["error"]["retry_after"] == 60
    
    @pytest.mark.asyncio
    async def test_check_permission_success(self, storage):
        """Test successful permission check."""
        
        user_id = "test-user-456"
        resource = "bucket:test-bucket-123"
        action = "read"
        
        # Mock auth middleware
        storage.auth_middleware.check_permission = AsyncMock(return_value={
            "allowed": True,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "scope": "bucket"
        })
        
        result = await storage.check_permission(user_id, resource, action)
        
        assert result["allowed"] is True
        assert result["user_id"] == user_id
        assert result["resource"] == resource
        assert result["action"] == action
        assert result["scope"] == "bucket"
        
        # Verify auth middleware was called
        storage.auth_middleware.check_permission.assert_called_once_with(
            user_id, resource, action
        )
    
    @pytest.mark.asyncio
    async def test_check_permission_denied(self, storage):
        """Test permission denied."""
        
        user_id = "test-user-789"
        resource = "bucket:restricted-bucket"
        action = "delete"
        
        # Mock auth middleware to deny permission
        storage.auth_middleware.check_permission = AsyncMock(return_value={
            "allowed": False,
            "error": {
                "code": "PERMISSION_DENIED",
                "message": f"User {user_id} does not have {action} permission for {resource}"
            }
        })
        
        result = await storage.check_permission(user_id, resource, action)
        
        assert result["allowed"] is False
        assert result["error"]["code"] == "PERMISSION_DENIED"
        assert user_id in result["error"]["message"]
        assert action in result["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_validate_bucket_access(self, storage):
        """Test bucket access validation."""
        import uuid
        
        user_id = str(uuid.uuid4())
        bucket_id = str(uuid.uuid4())
        action = "write"
        
        # Mock auth middleware
        storage.auth_middleware.validate_bucket_access = AsyncMock(return_value={
            "allowed": True,
            "user_id": user_id,
            "bucket_id": bucket_id,
            "action": action,
            "bucket_permissions": ["read", "write"],
            "is_owner": False
        })
        
        result = await storage.validate_bucket_access(user_id, bucket_id, action)
        
        assert result["allowed"] is True
        assert result["user_id"] == user_id
        assert result["bucket_id"] == bucket_id
        assert result["action"] == action
        assert "read" in result["bucket_permissions"]
        assert "write" in result["bucket_permissions"]
        assert result["is_owner"] is False
        
        # Verify auth middleware was called
        storage.auth_middleware.validate_bucket_access.assert_called_once_with(
            user_id, bucket_id, action
        )
    
    @pytest.mark.asyncio
    async def test_validate_file_access(self, storage):
        """Test file access validation."""
        import uuid
        
        user_id = str(uuid.uuid4())
        file_id = str(uuid.uuid4())
        bucket_id = str(uuid.uuid4())
        action = "read"
        
        # Mock auth middleware
        storage.auth_middleware.validate_file_access = AsyncMock(return_value={
            "allowed": True,
            "user_id": user_id,
            "file_id": file_id,
            "bucket_id": bucket_id,
            "action": action,
            "file_permissions": ["read"],
            "inherited_from_bucket": True
        })
        
        result = await storage.validate_file_access(user_id, file_id, bucket_id, action)
        
        assert result["allowed"] is True
        assert result["user_id"] == user_id
        assert result["file_id"] == file_id
        assert result["bucket_id"] == bucket_id
        assert result["action"] == action
        assert "read" in result["file_permissions"]
        assert result["inherited_from_bucket"] is True
        
        # Verify auth middleware was called
        storage.auth_middleware.validate_file_access.assert_called_once_with(
            user_id, file_id, bucket_id, action
        )
    
    @pytest.mark.asyncio
    async def test_get_user_info(self, storage):
        """Test getting user information."""
        import uuid
        from datetime import datetime, timezone
        
        user_id = str(uuid.uuid4())
        
        # Mock auth middleware
        storage.auth_middleware.get_user_info = AsyncMock(return_value={
            "user_id": user_id,
            "email": "test@example.com",
            "name": "Test User",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "permissions": ["storage:read", "storage:write", "storage:delete"],
            "storage_quota": {
                "total_bytes": 10737418240,  # 10GB
                "used_bytes": 1073741824,    # 1GB
                "available_bytes": 9663676416 # 9GB
            },
            "active": True
        })
        
        result = await storage.get_user_info(user_id)
        
        assert result["user_id"] == user_id
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert result["active"] is True
        assert "storage:read" in result["permissions"]
        assert "storage_quota" in result
        assert result["storage_quota"]["total_bytes"] == 10737418240
        
        # Verify auth middleware was called
        storage.auth_middleware.get_user_info.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_auth_middleware_error_handling(self, storage):
        """Test auth middleware error handling."""
        
        api_key = "test-key-error"
        
        # Mock auth middleware to raise exception
        storage.auth_middleware.validate_api_key = AsyncMock(
            side_effect=Exception("Auth service unavailable")
        )
        
        result = await storage.validate_api_key(api_key)
        
        assert result["valid"] is False
        assert result["error"]["code"] == "AUTH_SERVICE_ERROR"
        assert "auth service" in result["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_integrated_file_upload_with_auth(self, storage):
        """Test file upload with authentication integration."""
        import uuid
        import io
        
        user_id = str(uuid.uuid4())
        bucket_id = str(uuid.uuid4())
        file_id = str(uuid.uuid4())
        
        # Mock auth middleware for validation
        storage.auth_middleware.validate_bucket_access = AsyncMock(return_value={
            "allowed": True,
            "user_id": user_id,
            "bucket_id": bucket_id,
            "action": "write"
        })
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.upload_file = AsyncMock(return_value={
            "success": True,
            "file": {
                "id": file_id,
                "name": "auth-test.txt",
                "bucket_id": bucket_id,
                "size": 1024,
                "mime_type": "text/plain"
            }
        })
        
        # File data
        file_content = b"Test file with authentication"
        file_stream = io.BytesIO(file_content)
        upload_data = {
            "id": file_id,
            "bucket_id": bucket_id,
            "name": "auth-test.txt",
            "mime_type": "text/plain",
            "size": len(file_content)
        }
        
        # Test upload with auth validation
        auth_result = await storage.validate_bucket_access(user_id, bucket_id, "write")
        assert auth_result["allowed"] is True
        
        result = await storage.upload_file(
            file_stream=file_stream,
            upload_data=upload_data,
            user_id=user_id
        )
        
        assert result["success"] is True
        assert result["file"]["id"] == file_id
        assert result["file"]["bucket_id"] == bucket_id
    
    @pytest.mark.asyncio
    async def test_integrated_bucket_operations_with_auth(self, storage):
        """Test bucket operations with authentication integration."""
        import uuid
        
        user_id = str(uuid.uuid4())
        bucket_id = str(uuid.uuid4())
        
        # Mock auth middleware for bucket creation permission
        storage.auth_middleware.check_permission = AsyncMock(return_value={
            "allowed": True,
            "action": "create",
            "resource": "bucket",
            "user_id": user_id
        })
        
        # Mock storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.create_bucket = AsyncMock(return_value={
            "success": True,
            "bucket": {
                "id": bucket_id,
                "name": "auth-test-bucket",
                "owner_id": user_id,
                "public": False
            }
        })
        
        # Test bucket creation with auth
        auth_result = await storage.check_permission(user_id, "bucket", "create")
        assert auth_result["allowed"] is True
        
        bucket_data = {
            "bucket_id": bucket_id,
            "name": "auth-test-bucket",
            "owner_id": user_id,
            "public": False
        }
        
        result = await storage.create_bucket(bucket_data, user_id)
        
        assert result["success"] is True
        assert "id" in result["bucket"]  # Bucket gets its own generated ID
        assert result["bucket"]["name"] == "auth-test-bucket"
        assert result["bucket"]["owner_id"] == user_id


class TestStorageHealthCheck:
    """Test suite for storage service health check functionality."""
    
    @pytest.fixture
    def storage(self):
        """Storage instance for testing."""
        from storage.storage import Storage
        
        config_manager = Mock()
        config_manager.get_port.return_value = 8003
        config_manager.get_setting.return_value = "test_value"
        
        auth_middleware = Mock()
        
        return Storage(
            config_manager=config_manager,
            auth_middleware=auth_middleware,
            storage_backend="minio",
            enable_streaming=True
        )
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, storage):
        """Test successful health check."""
        from datetime import datetime, timezone
        
        # Mock storage backend health
        storage._storage_backend = Mock()
        storage._storage_backend.get_health = AsyncMock(return_value={
            "status": "healthy",
            "backend_type": "minio",
            "connected": True,
            "response_time_ms": 12,
            "available_space_gb": 500,
            "used_space_gb": 50
        })
        
        # Mock auth middleware health
        storage.auth_middleware.get_health = AsyncMock(return_value={
            "status": "healthy",
            "service": "auth",
            "connected": True,
            "response_time_ms": 8
        })
        
        result = await storage.get_health()
        
        assert result["status"] == "healthy"
        assert result["service"] == "storage"
        assert result["version"] == "1.0.0"
        assert result["storage_backend"] == "minio"
        assert result["internal_only"] is True
        assert result["streaming_enabled"] is True
        assert "startup_time" in result
        assert "uptime_seconds" in result
        
        # Check dependencies
        assert "dependencies" in result
        assert result["dependencies"]["storage_backend"]["status"] == "healthy"
        assert result["dependencies"]["auth_middleware"]["status"] == "healthy"
        
        # Verify backend was called
        storage._storage_backend.get_health.assert_called_once()
        storage.auth_middleware.get_health.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_storage_backend_unhealthy(self, storage):
        """Test health check with unhealthy storage backend."""
        
        # Mock unhealthy storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.get_health = AsyncMock(return_value={
            "status": "unhealthy",
            "backend_type": "minio",
            "connected": False,
            "error": "Connection timeout",
            "response_time_ms": None
        })
        
        # Mock healthy auth middleware
        storage.auth_middleware.get_health = AsyncMock(return_value={
            "status": "healthy",
            "service": "auth",
            "connected": True,
            "response_time_ms": 8
        })
        
        result = await storage.get_health()
        
        assert result["status"] == "degraded"
        assert result["service"] == "storage"
        assert "dependencies" in result
        assert result["dependencies"]["storage_backend"]["status"] == "unhealthy"
        assert result["dependencies"]["storage_backend"]["error"] == "Connection timeout"
        assert result["dependencies"]["auth_middleware"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_auth_middleware_unhealthy(self, storage):
        """Test health check with unhealthy auth middleware."""
        
        # Mock healthy storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.get_health = AsyncMock(return_value={
            "status": "healthy",
            "backend_type": "minio",
            "connected": True,
            "response_time_ms": 10
        })
        
        # Mock unhealthy auth middleware
        storage.auth_middleware.get_health = AsyncMock(return_value={
            "status": "unhealthy",
            "service": "auth",
            "connected": False,
            "error": "Database connection failed"
        })
        
        result = await storage.get_health()
        
        assert result["status"] == "degraded"
        assert result["service"] == "storage"
        assert result["dependencies"]["storage_backend"]["status"] == "healthy"
        assert result["dependencies"]["auth_middleware"]["status"] == "unhealthy"
        assert result["dependencies"]["auth_middleware"]["error"] == "Database connection failed"
    
    @pytest.mark.asyncio
    async def test_health_check_both_dependencies_unhealthy(self, storage):
        """Test health check with both dependencies unhealthy."""
        
        # Mock unhealthy storage backend
        storage._storage_backend = Mock()
        storage._storage_backend.get_health = AsyncMock(return_value={
            "status": "unhealthy",
            "backend_type": "minio",
            "connected": False,
            "error": "Service unavailable"
        })
        
        # Mock unhealthy auth middleware
        storage.auth_middleware.get_health = AsyncMock(return_value={
            "status": "unhealthy",
            "service": "auth",
            "connected": False,
            "error": "Service down"
        })
        
        result = await storage.get_health()
        
        assert result["status"] == "unhealthy"
        assert result["service"] == "storage"
        assert result["dependencies"]["storage_backend"]["status"] == "unhealthy"
        assert result["dependencies"]["auth_middleware"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_check_with_metrics(self, storage):
        """Test health check includes performance metrics."""
        
        # Mock storage backend with metrics
        storage._storage_backend = Mock()
        storage._storage_backend.get_health = AsyncMock(return_value={
            "status": "healthy",
            "backend_type": "minio",
            "connected": True,
            "response_time_ms": 15,
            "metrics": {
                "requests_per_second": 125.6,
                "error_rate_percent": 0.1,
                "available_space_gb": 750,
                "used_space_gb": 250,
                "active_connections": 12
            }
        })
        
        # Mock auth middleware with metrics
        storage.auth_middleware.get_health = AsyncMock(return_value={
            "status": "healthy",
            "service": "auth",
            "connected": True,
            "response_time_ms": 5,
            "metrics": {
                "active_sessions": 45,
                "requests_per_minute": 2400
            }
        })
        
        result = await storage.get_health()
        
        assert result["status"] == "healthy"
        assert "metrics" in result
        assert result["metrics"]["total_requests"] >= 0  # Can be 0 for new instances
        assert result["metrics"]["error_count"] >= 0
        assert "dependencies" in result
        assert "metrics" in result["dependencies"]["storage_backend"]
        assert "metrics" in result["dependencies"]["auth_middleware"]
        assert result["dependencies"]["storage_backend"]["metrics"]["available_space_gb"] == 750
    
    @pytest.mark.asyncio
    async def test_health_check_dependency_errors(self, storage):
        """Test health check handles dependency errors."""
        
        # Mock storage backend that raises exception
        storage._storage_backend = Mock()
        storage._storage_backend.get_health = AsyncMock(
            side_effect=Exception("Storage backend connection failed")
        )
        
        # Mock auth middleware that raises exception  
        storage.auth_middleware.get_health = AsyncMock(
            side_effect=Exception("Auth service timeout")
        )
        
        result = await storage.get_health()
        
        assert result["status"] == "unhealthy"
        assert result["service"] == "storage"
        assert "dependencies" in result
        
        # Check storage backend error handling
        assert result["dependencies"]["storage_backend"]["status"] == "error"
        assert "storage backend connection failed" in result["dependencies"]["storage_backend"]["error"].lower()
        
        # Check auth middleware error handling
        assert result["dependencies"]["auth_middleware"]["status"] == "error"
        assert "auth service timeout" in result["dependencies"]["auth_middleware"]["error"].lower()
    
    @pytest.mark.asyncio
    async def test_health_check_without_dependencies(self, storage):
        """Test health check when dependencies don't support health checks."""
        
        # Remove health check methods from dependencies
        # Remove storage backend entirely to simulate no backend
        if hasattr(storage, '_storage_backend'):
            delattr(storage, '_storage_backend')
        
        # Create new auth middleware without get_health method
        storage.auth_middleware = Mock()
        # Ensure no get_health method exists
        if hasattr(storage.auth_middleware, 'get_health'):
            delattr(storage.auth_middleware, 'get_health')
        
        result = await storage.get_health()
        
        assert result["status"] == "healthy"  # Service itself is healthy when deps are unknown
        assert result["service"] == "storage"
        assert "dependencies" in result
        
        # Dependencies should show as unknown/not-implemented
        assert result["dependencies"]["storage_backend"]["status"] == "unknown"
        assert result["dependencies"]["auth_middleware"]["status"] == "unknown"
    
    @pytest.mark.asyncio
    async def test_health_check_includes_configuration(self, storage):
        """Test health check includes service configuration."""
        
        # Mock healthy dependencies
        storage._storage_backend = Mock()
        storage._storage_backend.get_health = AsyncMock(return_value={
            "status": "healthy",
            "backend_type": "minio"
        })
        
        storage.auth_middleware.get_health = AsyncMock(return_value={
            "status": "healthy",
            "service": "auth"
        })
        
        result = await storage.get_health()
        
        assert result["status"] == "healthy"
        assert "configuration" in result
        assert result["configuration"]["storage_backend"] == "minio"
        assert result["configuration"]["internal_only"] is True
        assert result["configuration"]["streaming_enabled"] is True
        assert result["configuration"]["port"] == 8003
        assert "allowed_internal_services" in result["configuration"]
        assert result["configuration"]["allowed_internal_services"] == ["backend", "functions", "docker_network"]
    
    @pytest.mark.asyncio
    async def test_health_check_detailed_response(self, storage):
        """Test detailed health check response format."""
        
        # Mock detailed backend response
        storage._storage_backend = Mock()
        storage._storage_backend.get_health = AsyncMock(return_value={
            "status": "healthy",
            "backend_type": "minio",
            "connected": True,
            "response_time_ms": 8,
            "version": "2023.10.7",
            "cluster_info": {
                "nodes": 3,
                "online_nodes": 3
            }
        })
        
        # Mock detailed auth response
        storage.auth_middleware.get_health = AsyncMock(return_value={
            "status": "healthy",
            "service": "auth",
            "connected": True,
            "response_time_ms": 4,
            "database_status": "connected",
            "cache_status": "healthy"
        })
        
        result = await storage.get_health(detailed=True)
        
        assert result["status"] == "healthy"
        assert result["service"] == "storage"
        assert "detailed" in result
        assert result["detailed"] is True
        
        # Check detailed dependency information
        storage_dep = result["dependencies"]["storage_backend"]
        assert storage_dep["version"] == "2023.10.7"
        assert storage_dep["cluster_info"]["nodes"] == 3
        
        auth_dep = result["dependencies"]["auth_middleware"]
        assert auth_dep["database_status"] == "connected"
        assert auth_dep["cache_status"] == "healthy"
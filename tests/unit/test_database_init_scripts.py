"""
Database Init Scripts Tests
RED Phase: Write failing tests first for database initialization system
"""
import pytest
import asyncio
import os
import tempfile
import shutil
from pathlib import Path


class TestDatabaseInitScripts:
    """Test database initialization scripts following TDD methodology."""

    def test_init_script_files_exist(self):
        """Test that init script files exist."""
        init_dir = Path("database/init")
        assert init_dir.exists(), "Database init directory should exist"

        tables_file = init_dir / "01_create_tables.sql"
        indexes_file = init_dir / "02_create_indexes.sql"

        assert tables_file.exists(), "Tables init script should exist"
        assert indexes_file.exists(), "Indexes init script should exist"

    def test_init_script_has_all_tables(self):
        """Test that init script creates all 17 required tables."""
        tables_file = Path("database/init/01_create_tables.sql")
        content = tables_file.read_text()

        # Check for all required tables
        required_tables = [
            "users", "buckets", "files", "functions", "tables",
            "webhooks", "function_executions", "webhook_deliveries", "function_logs",
            "migrations", "data_records", "system_states", "active_executions",
            "resource_pool_states", "audit_logs", "performance_metrics",
            "system_checkpoints"
        ]

        for table in required_tables:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in content, f"Table {table} should be created"

    def test_init_script_creates_indexes(self):
        """Test that init script creates all required indexes."""
        indexes_file = Path("database/init/02_create_indexes.sql")
        content = indexes_file.read_text()

        # Check for key indexes
        required_indexes = [
            "idx_buckets_owner_id", "idx_files_bucket_id", "idx_files_owner_id",
            "idx_functions_owner_id", "idx_users_email", "idx_users_role"
        ]

        for index in required_indexes:
            assert f"CREATE INDEX IF NOT EXISTS {index}" in content, f"Index {index} should be created"

    def test_init_script_is_idempotent(self):
        """Test that init script can be run multiple times safely."""
        tables_file = Path("database/init/01_create_tables.sql")
        content = tables_file.read_text()

        # All table creations should use IF NOT EXISTS
        assert "CREATE TABLE IF NOT EXISTS" in content, "Tables should be created with IF NOT EXISTS"

    # Admin user creation is now handled by the backend application, not SQL scripts
    # This test has been removed as the SQL script is no longer needed


# Admin user creation is now handled by the backend application, not SQL scripts
# The TestAdminUserCreation class has been removed as it tested the deprecated SQL script approach


class TestMigrationSystem:
    """Test migration system following TDD methodology."""

    def test_migration_manager_exists(self):
        """Test that migration manager exists."""
        migration_file = Path("shared/database/migration_manager.py")
        assert migration_file.exists(), "Migration manager file should exist"

        content = migration_file.read_text()
        assert "MigrationManager" in content, "MigrationManager class should be defined"
        assert "async def run_pending_migrations" in content, "Should have run_pending_migrations method"
        assert "async def rollback_migration" in content, "Should have rollback_migration method"

    def test_migration_files_exist(self):
        """Test that migration files exist."""
        migrations_dir = Path("database/migrations")
        assert migrations_dir.exists(), "Migrations directory should exist"

        migration_files = list(migrations_dir.glob("*.sql"))
        assert len(migration_files) >= 4, "Should have at least 4 migration files"

        # Check for specific migration files
        expected_migrations = [
            "001_initial_schema.sql",
            "002_audit_tables.sql",
            "003_system_tables.sql",
            "004_create_indexes.sql"
        ]

        for migration in expected_migrations:
            migration_file = migrations_dir / migration
            assert migration_file.exists(), f"Migration file {migration} should exist"

    def test_migration_manager_has_proper_methods(self):
        """Test that migration manager has proper methods."""
        migration_file = Path("shared/database/migration_manager.py")
        content = migration_file.read_text()

        required_methods = [
            ("initialize_migrations_table", "async"),
            ("get_applied_migrations", "async"),
            ("get_available_migrations", "def"),
            ("apply_migration", "async"),
            ("run_pending_migrations", "async"),
            ("rollback_migration", "async"),
            ("get_migration_status", "async")
        ]

        for method, method_type in required_methods:
            if method_type == "async":
                assert f"async def {method}" in content, f"Method {method} should be async"
            else:
                assert f"def {method}" in content, f"Method {method} should be defined"

    def test_migration_cli_exists(self):
        """Test that migration CLI tool exists."""
        cli_file = Path("scripts/migrate.py")
        assert cli_file.exists(), "Migration CLI file should exist"
        assert os.access(cli_file, os.X_OK), "Migration CLI should be executable"

        content = cli_file.read_text()
        assert "MigrationManager" in content, "CLI should use MigrationManager"
        assert "argparse" in content, "CLI should use argparse for command line parsing"

    def test_migration_system_has_error_handling(self):
        """Test that migration system has proper error handling."""
        migration_file = Path("shared/database/migration_manager.py")
        content = migration_file.read_text()

        assert "try:" in content, "Migration system should have try-catch blocks"
        assert "except" in content, "Migration system should have exception handling"
        assert "logger.error" in content, "Migration system should log errors"


@pytest.mark.integration
class TestDatabaseInitIntegration:
    """Integration tests for database initialization system."""

    def test_docker_config_has_init_scripts_mounted(self):
        """Test that Docker configuration mounts init scripts."""
        docker_file = Path("docker-compose.template.yml")
        content = docker_file.read_text()

        assert "./database/init:/docker-entrypoint-initdb.d" in content, \
               "Docker config should mount init scripts"
        assert "ADMIN_EMAIL" in content, "Docker config should have admin email env var"
        assert "ADMIN_PASSWORD" in content, "Docker config should have admin password env var"

    def test_docker_config_has_environment_variable_support(self):
        """Test that Docker configuration supports environment variables for admin creation."""
        docker_file = Path("docker-compose.template.yml")
        content = docker_file.read_text()

        assert "ADMIN_EMAIL" in content, "Docker config should support ADMIN_EMAIL environment variable"
        assert "ADMIN_PASSWORD" in content, "Docker config should support ADMIN_PASSWORD environment variable"
        assert "ADMIN_FIRST_NAME" in content, "Docker config should support ADMIN_FIRST_NAME environment variable"
        assert "ADMIN_LAST_NAME" in content, "Docker config should support ADMIN_LAST_NAME environment variable"

    def test_migration_script_is_executable(self):
        """Test that migration CLI script is executable."""
        cli_file = Path("scripts/migrate.py")
        assert cli_file.exists(), "Migration CLI file should exist"
        assert os.access(cli_file, os.X_OK), "Migration CLI should be executable"

    def test_all_required_files_exist(self):
        """Test that all required files for database initialization exist."""
        required_files = [
            "database/init/01_create_tables.sql",
            "database/init/02_create_indexes.sql",
            "database/migrations/001_initial_schema.sql",
            "database/migrations/002_audit_tables.sql",
            "database/migrations/003_system_tables.sql",
            "database/migrations/004_create_indexes.sql",
            "shared/database/migration_manager.py",
            "scripts/migrate.py"
        ]

        for file_path in required_files:
            file_obj = Path(file_path)
            assert file_obj.exists(), f"Required file {file_path} should exist"

    def test_docker_config_has_proper_environment_vars(self):
        """Test that Docker configuration has proper environment variables."""
        docker_file = Path("docker-compose.template.yml")
        content = docker_file.read_text()

        required_env_vars = [
            "ADMIN_FIRST_NAME", "ADMIN_LAST_NAME", "DATABASE_URL"
        ]

        for env_var in required_env_vars:
            assert env_var in content, f"Environment variable {env_var} should be in Docker config"
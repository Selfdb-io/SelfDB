"""
SelfDB Migration Manager
Handles database migrations with version control and rollback capabilities.
Follows TDD methodology with comprehensive error handling.
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging


class MigrationManager:
    """Manages database migrations with proper version control."""

    def __init__(self, database_url: str = ""):
        self.database_url = database_url or os.getenv('DATABASE_URL', '')
        self.migrations_dir = Path(__file__).parent.parent.parent / "database" / "migrations"
        self.logger = logging.getLogger(__name__)

    def validate_environment(self) -> bool:
        """Validate that required environment variables are set."""
        if not self.database_url:
            self.logger.error("DATABASE_URL environment variable is required")
            return False
        return True

    async def initialize_migrations_table(self, conn: asyncpg.Connection) -> bool:
        """Create the migrations table if it doesn't exist."""
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    version INTEGER NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum VARCHAR(64)
                )
            """)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create migrations table: {e}")
            return False

    async def get_applied_migrations(self, conn: asyncpg.Connection) -> List[int]:
        """Get list of already applied migration versions."""
        try:
            rows = await conn.fetch(
                "SELECT version FROM migrations ORDER BY version"
            )
            return [row['version'] for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get applied migrations: {e}")
            return []

    def get_available_migrations(self) -> List[Tuple[int, str, Path]]:
        """Get list of available migration files."""
        migrations = []

        if not self.migrations_dir.exists():
            return migrations

        for file_path in self.migrations_dir.glob("*.sql"):
            if file_path.name.startswith((".", "__")):
                continue

            # Extract version number from filename (e.g., 001_initial_schema.sql)
            try:
                version_str = file_path.name.split('_')[0]
                version = int(version_str)
                name = file_path.stem.replace(f"{version_str}_", "")
                migrations.append((version, name, file_path))
            except (ValueError, IndexError):
                self.logger.warning(f"Invalid migration filename format: {file_path.name}")
                continue

        return sorted(migrations, key=lambda x: x[0])

    async def apply_migration(self, conn: asyncpg.Connection, version: int, name: str, file_path: Path) -> bool:
        """Apply a single migration."""
        try:
            # Read migration SQL
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            if not sql_content.strip():
                self.logger.warning(f"Migration {version} ({name}) is empty, skipping")
                return True

            # Start transaction
            async with conn.transaction():
                # Execute migration
                await conn.execute(sql_content)

                # Record migration
                await conn.execute(
                    """
                    INSERT INTO migrations (version, name, applied_at)
                    VALUES ($1, $2, $3)
                    """,
                    version, name, datetime.now()
                )

            self.logger.info(f"✅ Applied migration {version}: {name}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to apply migration {version} ({name}): {e}")
            return False

    async def run_pending_migrations(self) -> bool:
        """Run all pending migrations."""
        if not self.validate_environment():
            return False

        try:
            # Connect to database
            conn = await asyncpg.connect(self.database_url)

            try:
                # Initialize migrations table
                if not await self.initialize_migrations_table(conn):
                    return False

                # Get applied and available migrations
                applied_versions = await self.get_applied_migrations(conn)
                available_migrations = self.get_available_migrations()

                self.logger.info(f"Found {len(applied_versions)} applied migrations")
                self.logger.info(f"Found {len(available_migrations)} available migrations")

                # Apply pending migrations
                success_count = 0
                for version, name, file_path in available_migrations:
                    if version not in applied_versions:
                        self.logger.info(f"Applying migration {version}: {name}")
                        if await self.apply_migration(conn, version, name, file_path):
                            success_count += 1
                        else:
                            return False
                    else:
                        self.logger.debug(f"Migration {version} already applied, skipping")

                self.logger.info(f"✅ Successfully applied {success_count} migrations")
                return True

            finally:
                await conn.close()

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return False

    async def rollback_migration(self, target_version: int) -> bool:
        """Rollback migrations to a specific version."""
        if not self.validate_environment():
            return False

        try:
            conn = await asyncpg.connect(self.database_url)

            try:
                applied_versions = await self.get_applied_migrations(conn)
                available_migrations = self.get_available_migrations()

                # Get migrations to rollback
                versions_to_rollback = [v for v in applied_versions if v > target_version]

                if not versions_to_rollback:
                    self.logger.info("No migrations to rollback")
                    return True

                # Rollback in reverse order
                for version in sorted(versions_to_rollback, reverse=True):
                    # Find the migration file
                    migration_info = next((m for m in available_migrations if m[0] == version), None)
                    if not migration_info:
                        self.logger.error(f"Cannot find migration file for version {version}")
                        return False

                    _, name, file_path = migration_info

                    # Look for rollback file (e.g., 001_initial_schema_rollback.sql)
                    rollback_file = file_path.with_name(f"{file_path.stem}_rollback.sql")

                    if rollback_file.exists():
                        self.logger.info(f"Rolling back migration {version}: {name}")

                        # Read rollback SQL
                        with open(rollback_file, 'r', encoding='utf-8') as f:
                            rollback_sql = f.read()

                        async with conn.transaction():
                            # Execute rollback
                            await conn.execute(rollback_sql)

                            # Remove migration record
                            await conn.execute(
                                "DELETE FROM migrations WHERE version = $1",
                                version
                            )

                        self.logger.info(f"✅ Rolled back migration {version}: {name}")
                    else:
                        self.logger.warning(f"No rollback file found for migration {version}: {name}")

                return True

            finally:
                await conn.close()

        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False

    async def get_migration_status(self) -> Dict:
        """Get current migration status."""
        if not self.validate_environment():
            return {}

        try:
            conn = await asyncpg.connect(self.database_url)

            try:
                applied_versions = await self.get_applied_migrations(conn)
                available_migrations = self.get_available_migrations()

                pending = [m for m in available_migrations if m[0] not in applied_versions]

                return {
                    'applied_count': len(applied_versions),
                    'available_count': len(available_migrations),
                    'pending_count': len(pending),
                    'applied_versions': applied_versions,
                    'pending_migrations': [(v, n) for v, n, _ in pending]
                }

            finally:
                await conn.close()

        except Exception as e:
            self.logger.error(f"Failed to get migration status: {e}")
            return {}


async def main():
    """Command-line interface for migration manager."""
    import argparse

    parser = argparse.ArgumentParser(description="SelfDB Migration Manager")
    parser.add_argument('command', choices=['up', 'status', 'rollback'],
                       help='Migration command to execute')
    parser.add_argument('--target', type=int, help='Target version for rollback')
    parser.add_argument('--database-url', help='Database URL (overrides DATABASE_URL env var)')

    args = parser.parse_args()

    # Initialize migration manager
    manager = MigrationManager(args.database_url)

    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    if args.command == 'up':
        success = await manager.run_pending_migrations()
        sys.exit(0 if success else 1)

    elif args.command == 'status':
        status = await manager.get_migration_status()
        print(f"Applied migrations: {status.get('applied_count', 0)}")
        print(f"Available migrations: {status.get('available_count', 0)}")
        print(f"Pending migrations: {status.get('pending_count', 0)}")

        if status.get('pending_migrations'):
            print("\nPending migrations:")
            for version, name in status['pending_migrations']:
                print(f"  {version}: {name}")

    elif args.command == 'rollback':
        if not args.target:
            print("ERROR: --target version is required for rollback")
            sys.exit(1)

        success = await manager.rollback_migration(args.target)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
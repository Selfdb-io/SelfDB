#!/usr/bin/env python3
"""
SelfDB Migration CLI Tool
Command-line interface for running database migrations.
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database.migration_manager import MigrationManager


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SelfDB Migration CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s up                          # Run pending migrations
  %(prog)s status                      # Show migration status
  %(prog)s rollback --target 2         # Rollback to version 2
  %(prog)s up --database-url "..."     # Use custom database URL
        """
    )

    parser.add_argument(
        'command',
        choices=['up', 'status', 'rollback', 'init'],
        help='Migration command to execute'
    )

    parser.add_argument(
        '--target',
        type=int,
        help='Target version for rollback'
    )

    parser.add_argument(
        '--database-url',
        help='Database URL (overrides DATABASE_URL env var)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set up logging
    import logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize migration manager
    manager = MigrationManager(args.database_url)

    # Execute command
    if args.command == 'up':
        success = asyncio.run(manager.run_pending_migrations())
        sys.exit(0 if success else 1)

    elif args.command == 'status':
        status = asyncio.run(manager.get_migration_status())

        print("\n📊 Migration Status")
        print("==================")
        print(f"Applied migrations: {status.get('applied_count', 0)}")
        print(f"Available migrations: {status.get('available_count', 0)}")
        print(f"Pending migrations: {status.get('pending_count', 0)}")

        if status.get('pending_migrations'):
            print("\n⏳ Pending migrations:")
            for version, name in status['pending_migrations']:
                print(f"  {version}: {name}")

        print("\n✅ All migrations are up to date!" if not status.get('pending_migrations') else "")

    elif args.command == 'rollback':
        if not args.target:
            print("❌ Error: --target version is required for rollback")
            parser.print_help()
            sys.exit(1)

        success = asyncio.run(manager.rollback_migration(args.target))
        sys.exit(0 if success else 1)

    elif args.command == 'init':
        print("🔧 Initializing migration system...")

        if not manager.database_url:
            print("❌ Error: DATABASE_URL environment variable is required")
            sys.exit(1)

        success = asyncio.run(manager.initialize_migrations_table(
            asyncio.run(asyncpg.connect(manager.database_url))
        ))

        if success:
            print("✅ Migration system initialized successfully")
            sys.exit(0)
        else:
            print("❌ Failed to initialize migration system")
            sys.exit(1)


if __name__ == "__main__":
    main()
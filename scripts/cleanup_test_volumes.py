#!/usr/bin/env python3
"""
Utility script to clean up test Docker volumes and containers.
Run this if tests were interrupted and left orphaned resources.

Usage:
    python scripts/cleanup_test_volumes.py [--dry-run]
"""

import sys
import argparse
try:
    import docker
except ImportError:
    print("Docker package not installed. Run: pip install docker")
    sys.exit(1)


def cleanup_test_resources(dry_run=False):
    """Clean up all test-related Docker resources."""
    client = docker.from_env()
    
    # Test patterns to identify test resources
    test_patterns = [
        'test_', 'selfdb_test', 'selfdb_integration', 
        'postgres_function_test', 'postgres_test'
    ]
    
    print("🧹 Starting Docker test resource cleanup...")
    
    # Clean up containers first
    print("\n📦 Cleaning up test containers...")
    containers_removed = 0
    try:
        all_containers = client.containers.list(all=True)
        for container in all_containers:
            if any(pattern in container.name for pattern in test_patterns):
                if dry_run:
                    print(f"  [DRY RUN] Would remove container: {container.name}")
                else:
                    try:
                        print(f"  Removing container: {container.name}")
                        container.stop(timeout=5)
                        container.remove(force=True, v=True)  # v=True removes anonymous volumes
                        containers_removed += 1
                    except Exception as e:
                        print(f"    ⚠️  Failed to remove {container.name}: {e}")
    except Exception as e:
        print(f"  ❌ Error listing containers: {e}")
    
    # Clean up named volumes
    print("\n💾 Cleaning up test volumes...")
    volumes_removed = 0
    try:
        all_volumes = client.volumes.list()
        for volume in all_volumes:
            if any(pattern in volume.name for pattern in test_patterns):
                if dry_run:
                    print(f"  [DRY RUN] Would remove volume: {volume.name}")
                else:
                    try:
                        print(f"  Removing volume: {volume.name}")
                        volume.remove(force=True)
                        volumes_removed += 1
                    except Exception as e:
                        print(f"    ⚠️  Failed to remove {volume.name}: {e}")
    except Exception as e:
        print(f"  ❌ Error listing volumes: {e}")
    
    # Clean up networks
    print("\n🌐 Cleaning up test networks...")
    networks_removed = 0
    try:
        all_networks = client.networks.list()
        for network in all_networks:
            if any(pattern in network.name for pattern in test_patterns):
                if dry_run:
                    print(f"  [DRY RUN] Would remove network: {network.name}")
                else:
                    try:
                        print(f"  Removing network: {network.name}")
                        network.remove()
                        networks_removed += 1
                    except Exception as e:
                        print(f"    ⚠️  Failed to remove {network.name}: {e}")
    except Exception as e:
        print(f"  ❌ Error listing networks: {e}")
    
    # Summary
    print("\n✅ Cleanup complete!")
    if dry_run:
        print("  This was a dry run - no resources were actually removed.")
        print("  Run without --dry-run to actually clean up resources.")
    else:
        print(f"  Containers removed: {containers_removed}")
        print(f"  Volumes removed: {volumes_removed}")
        print(f"  Networks removed: {networks_removed}")
    
    # Show disk usage recovery estimate
    if not dry_run and volumes_removed > 0:
        print("\n💡 Tip: Run 'docker system df' to see recovered disk space.")


def main():
    parser = argparse.ArgumentParser(
        description="Clean up Docker test resources (containers, volumes, networks)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned up without actually removing anything"
    )
    args = parser.parse_args()
    
    try:
        cleanup_test_resources(dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
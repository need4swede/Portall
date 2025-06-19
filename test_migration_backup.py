#!/usr/bin/env python3
"""
Test script to demonstrate the new single backup migration strategy.

This script shows the difference between the old and new backup strategies.
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from utils.database import db
from utils.database.migrations import MigrationManager

def test_backup_strategies():
    """Test both backup strategies to show the difference."""

    print("🧪 Testing Migration Backup Strategies")
    print("=" * 50)

    with app.app_context():
        migration_manager = MigrationManager(app, db)

        # Get current status
        status = migration_manager.get_migration_status()

        print(f"\n📊 Current Migration Status:")
        print(f"  Applied migrations: {len(status['applied_migrations'])}")
        print(f"  Pending migrations: {len(status['pending_migrations'])}")
        print(f"  Total backups: {status['backup_info']['backup_count']}")

        if status['pending_migrations']:
            print(f"\n⏳ Pending migrations to run:")
            for migration in status['pending_migrations']:
                print(f"    • {migration}")

            print(f"\n💡 With SINGLE backup strategy:")
            print(f"    ✅ Will create 1 backup: portall_backup_migration_batch_YYYYMMDD_HHMMSS.db")
            print(f"    ✅ All {len(status['pending_migrations'])} migrations will use this same backup for rollback")

            print(f"\n💡 With INDIVIDUAL backup strategy (legacy):")
            print(f"    ⚠️  Would create {len(status['pending_migrations'])} backups:")
            for migration in status['pending_migrations']:
                print(f"       • portall_backup_before_{migration}_YYYYMMDD_HHMMSS.db")
        else:
            print(f"\n✅ All migrations are up to date!")
            print(f"   No backups would be created during migration run.")

        print(f"\n🎯 Benefits of Single Backup Strategy:")
        print(f"   • Reduced storage usage")
        print(f"   • Faster migration process")
        print(f"   • Cleaner backup directory")
        print(f"   • Same safety level")

        print(f"\n📝 Usage Examples:")
        print(f"   # Use single backup (default)")
        print(f"   python3 manage_migrations.py migrate")
        print(f"   python3 manage_migrations.py migrate --backup-strategy single")
        print(f"   ")
        print(f"   # Use individual backups (legacy)")
        print(f"   python3 manage_migrations.py migrate --backup-strategy individual")

if __name__ == '__main__':
    test_backup_strategies()

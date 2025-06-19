#!/usr/bin/env python3
"""
Migration Management CLI for Portall

This script provides a command-line interface for managing database migrations,
backups, and system maintenance tasks.

Usage:
    python3 manage_migrations.py [command] [options]

Commands:
    status      - Show migration and backup status
    migrate     - Run pending migrations
    backup      - Create a manual backup
    restore     - Restore from a backup
    list-backups - List available backups
    cleanup     - Clean up old backups
    help        - Show this help message

Examples:
    python3 manage_migrations.py status
    python3 manage_migrations.py migrate
    python3 manage_migrations.py migrate --backup-strategy single
    python3 manage_migrations.py migrate --backup-strategy individual
    python3 manage_migrations.py backup --reason "before_upgrade"
    python3 manage_migrations.py restore --backup "portall_backup_migration_20231218_143022.db"
    python3 manage_migrations.py cleanup --keep 5
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from utils.database import db
from utils.database.migrations import MigrationManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def format_size(size_bytes):
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f}{size_names[i]}"

def show_status(migration_manager):
    """Show current migration and backup status."""
    print("🔍 Portall Migration & Backup Status")
    print("=" * 50)

    status = migration_manager.get_migration_status()

    # Show applied migrations
    print(f"\n✅ Applied Migrations ({len(status['applied_migrations'])})")
    if status['applied_migrations']:
        for migration in status['applied_migrations']:
            print(f"  • {migration['name']} (applied: {migration['applied_at']})")
    else:
        print("  No migrations applied yet")

    # Show pending migrations
    print(f"\n⏳ Pending Migrations ({len(status['pending_migrations'])})")
    if status['pending_migrations']:
        for migration in status['pending_migrations']:
            print(f"  • {migration}")
    else:
        print("  All migrations up to date")

    # Show backup information
    backup_info = status['backup_info']
    print(f"\n💾 Backup Information")
    print(f"  Backup Directory: {backup_info['backup_dir'] or 'Not configured'}")
    print(f"  Total Backups: {backup_info['backup_count']}")

    if backup_info['latest_backup']:
        backup_path = os.path.join(backup_info['backup_dir'], backup_info['latest_backup'])
        if os.path.exists(backup_path):
            size = os.path.getsize(backup_path)
            mtime = datetime.fromtimestamp(os.path.getmtime(backup_path))
            print(f"  Latest Backup: {backup_info['latest_backup']}")
            print(f"  Size: {format_size(size)}")
            print(f"  Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

    # Show database information
    database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if database_url.startswith('sqlite:///'):
        db_path = database_url.replace('sqlite:///', '')
        if not db_path.startswith('/'):
            db_path = os.path.join('/app', db_path)

        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            mtime = datetime.fromtimestamp(os.path.getmtime(db_path))
            print(f"\n🗄️  Database Information")
            print(f"  Path: {db_path}")
            print(f"  Size: {format_size(size)}")
            print(f"  Last Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

def run_migrations(migration_manager, single_backup=True):
    """Run pending migrations."""
    backup_strategy = "single backup" if single_backup else "individual backups"
    print(f"🔄 Running Migrations (strategy: {backup_strategy})")
    print("=" * 50)

    try:
        success = migration_manager.run_standalone_migrations(single_backup=single_backup)
        if success:
            print("✅ All migrations completed successfully!")
        else:
            print("❌ Some migrations failed. Check logs for details.")
            return False
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

    return True

def create_backup(migration_manager, reason="manual"):
    """Create a manual backup."""
    print(f"💾 Creating Backup (reason: {reason})")
    print("=" * 40)

    backup_path = migration_manager._create_backup(reason)
    if backup_path:
        size = os.path.getsize(backup_path)
        print(f"✅ Backup created successfully!")
        print(f"  Path: {backup_path}")
        print(f"  Size: {format_size(size)}")
        return True
    else:
        print("❌ Backup creation failed. Check logs for details.")
        return False

def list_backups(migration_manager):
    """List all available backups."""
    print("📋 Available Backups")
    print("=" * 30)

    if not migration_manager.backup_dir or not os.path.exists(migration_manager.backup_dir):
        print("No backup directory found.")
        return

    backup_files = []
    for filename in os.listdir(migration_manager.backup_dir):
        if filename.startswith('portall_backup_') and filename.endswith('.db'):
            filepath = os.path.join(migration_manager.backup_dir, filename)
            size = os.path.getsize(filepath)
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            backup_files.append((filename, size, mtime))

    if not backup_files:
        print("No backups found.")
        return

    # Sort by modification time (newest first)
    backup_files.sort(key=lambda x: x[2], reverse=True)

    print(f"Found {len(backup_files)} backup(s):\n")
    for filename, size, mtime in backup_files:
        print(f"📁 {filename}")
        print(f"   Size: {format_size(size)}")
        print(f"   Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

def restore_backup(migration_manager, backup_name):
    """Restore from a specific backup."""
    print(f"🔄 Restoring from Backup: {backup_name}")
    print("=" * 50)

    if not migration_manager.backup_dir:
        print("❌ Backup directory not configured.")
        return False

    backup_path = os.path.join(migration_manager.backup_dir, backup_name)

    if not os.path.exists(backup_path):
        print(f"❌ Backup file not found: {backup_path}")
        return False

    # Confirm the restore operation
    print(f"⚠️  WARNING: This will replace your current database!")
    print(f"   Current database will be lost.")
    print(f"   Backup to restore: {backup_name}")

    confirm = input("\nAre you sure you want to continue? (yes/no): ").lower().strip()
    if confirm not in ['yes', 'y']:
        print("❌ Restore operation cancelled.")
        return False

    success = migration_manager._restore_from_backup(backup_path)
    if success:
        print("✅ Database restored successfully!")
        return True
    else:
        print("❌ Restore operation failed. Check logs for details.")
        return False

def cleanup_backups(migration_manager, keep_count=10):
    """Clean up old backups."""
    print(f"🧹 Cleaning up old backups (keeping {keep_count} most recent)")
    print("=" * 60)

    migration_manager._cleanup_old_backups(keep_count)
    print("✅ Cleanup completed!")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Portall Migration Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'command',
        choices=['status', 'migrate', 'backup', 'restore', 'list-backups', 'cleanup', 'help'],
        help='Command to execute'
    )

    parser.add_argument(
        '--reason',
        default='manual',
        help='Reason for backup (used in filename)'
    )

    parser.add_argument(
        '--backup',
        help='Backup filename to restore from'
    )

    parser.add_argument(
        '--keep',
        type=int,
        default=10,
        help='Number of backups to keep during cleanup'
    )

    parser.add_argument(
        '--backup-strategy',
        choices=['single', 'individual'],
        default='single',
        help='Backup strategy for migrations: "single" creates one backup before all migrations, "individual" creates backup before each migration (default: single)'
    )

    args = parser.parse_args()

    if args.command == 'help':
        parser.print_help()
        return

    # Initialize the migration manager
    try:
        with app.app_context():
            migration_manager = MigrationManager(app, db)

            if args.command == 'status':
                show_status(migration_manager)

            elif args.command == 'migrate':
                single_backup = args.backup_strategy == 'single'
                run_migrations(migration_manager, single_backup)

            elif args.command == 'backup':
                create_backup(migration_manager, args.reason)

            elif args.command == 'restore':
                if not args.backup:
                    print("❌ Error: --backup parameter is required for restore command")
                    print("   Use 'list-backups' to see available backups")
                    sys.exit(1)
                restore_backup(migration_manager, args.backup)

            elif args.command == 'list-backups':
                list_backups(migration_manager)

            elif args.command == 'cleanup':
                cleanup_backups(migration_manager, args.keep)

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

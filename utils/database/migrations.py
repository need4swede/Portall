# utils/database/migrations.py

import os
import shutil
import logging
from datetime import datetime
from flask import current_app
from flask_migrate import Migrate, upgrade, stamp, current
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from alembic.util import CommandError

# Import the standalone migration scripts
import migration
import migration_immutable
import migration_settings
import migration_tags
import migration_auto_execute

# Setup logging
logger = logging.getLogger(__name__)

class MigrationManager:
    """
    Enhanced migration manager with auto-backup functionality and version tracking.

    Features:
    - Automatic database backup before migrations
    - Version tracking and rollback capabilities
    - Safe migration execution with error recovery
    - Comprehensive logging and error handling
    """
    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.migrate = Migrate(app, db)
        self.backup_dir = None
        self.current_backup = None

        # Validate database setup before proceeding
        self._validate_database_setup()

        # Setup backup directory
        self._setup_backup_directory()

        # Track migration versions in the database
        self._ensure_version_table_exists()

    def _validate_database_setup(self):
        """
        Validates that the database directory exists and is writable.
        """
        database_url = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')

        if database_url.startswith('sqlite:///'):
            db_path = database_url.replace('sqlite:///', '')
            if not db_path.startswith('/'):
                # Relative path, make it absolute
                db_path = os.path.join('/app', db_path)

            db_dir = os.path.dirname(db_path)

            # Check if directory exists
            if not os.path.exists(db_dir):
                logger.error(f"Database directory {db_dir} does not exist")
                raise FileNotFoundError(f"Database directory {db_dir} does not exist")

            # Check if directory is writable
            if not os.access(db_dir, os.W_OK):
                logger.error(f"Database directory {db_dir} is not writable")
                logger.error(f"Current user: {os.getuid()}:{os.getgid()}")
                logger.error(f"Directory permissions: {oct(os.stat(db_dir).st_mode)[-3:]}")
                logger.error(f"Directory owner: {os.stat(db_dir).st_uid}:{os.stat(db_dir).st_gid}")

                raise PermissionError(
                    f"Cannot write to database directory {db_dir}. "
                    f"Please ensure the directory has proper permissions.\n"
                    f"Fix: chmod 777 {db_dir} or chown {os.getuid()}:{os.getgid()} {db_dir}"
                )

            logger.info(f"Database directory validation passed: {db_dir}")

    def _ensure_version_table_exists(self):
        """
        Ensures the migration_versions table exists to track custom migrations.
        """
        with self.app.app_context():
            try:
                with self.db.engine.connect() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS migration_versions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            migration_name VARCHAR(100) UNIQUE NOT NULL,
                            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    conn.commit()
                logger.info("Migration versions table verified/created.")
            except OperationalError as e:
                if "unable to open database file" in str(e):
                    logger.error("Failed to open database file. This is likely a permission issue.")
                    logger.error("Please check that the database directory has proper permissions.")
                    raise PermissionError(
                        "Unable to open database file. This is typically caused by incorrect "
                        "file permissions on the database directory."
                    ) from e
                else:
                    logger.error(f"Database error creating migration versions table: {e}")
                    raise
            except Exception as e:
                logger.error(f"Error creating migration versions table: {e}")
                raise

    def _is_migration_applied(self, migration_name):
        """
        Checks if a specific migration has been applied.

        Args:
            migration_name (str): The name of the migration to check.

        Returns:
            bool: True if the migration has been applied, False otherwise.
        """
        with self.app.app_context():
            try:
                with self.db.engine.connect() as conn:
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM migration_versions WHERE migration_name = :name"
                    ), {"name": migration_name})
                    count = result.scalar()
                    return count > 0
            except Exception as e:
                logger.error(f"Error checking migration status: {e}")
                return False

    def _record_migration(self, migration_name):
        """
        Records that a migration has been applied.

        Args:
            migration_name (str): The name of the migration to record.
        """
        with self.app.app_context():
            try:
                with self.db.engine.connect() as conn:
                    conn.execute(text(
                        "INSERT INTO migration_versions (migration_name) VALUES (:name)"
                    ), {"name": migration_name})
                    conn.commit()
                logger.info(f"Recorded migration: {migration_name}")
            except Exception as e:
                logger.error(f"Error recording migration: {e}")

    def _setup_backup_directory(self):
        """
        Sets up the backup directory for database backups.
        """
        try:
            # Get database path
            database_url = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if database_url.startswith('sqlite:///'):
                db_path = database_url.replace('sqlite:///', '')
                if not db_path.startswith('/'):
                    db_path = os.path.join('/app', db_path)

                db_dir = os.path.dirname(db_path)
                self.backup_dir = os.path.join(db_dir, 'backups')

                # Create backup directory if it doesn't exist
                os.makedirs(self.backup_dir, exist_ok=True)
                logger.info(f"Backup directory ready: {self.backup_dir}")
            else:
                logger.warning("Non-SQLite database detected. Backup functionality may be limited.")
                self.backup_dir = None
        except Exception as e:
            logger.error(f"Error setting up backup directory: {e}")
            self.backup_dir = None

    def _create_backup(self, backup_reason="migration"):
        """
        Creates a backup of the current database.

        Args:
            backup_reason (str): Reason for the backup (for naming).

        Returns:
            str: Path to the backup file, or None if backup failed.
        """
        if not self.backup_dir:
            logger.warning("Backup directory not available. Skipping backup.")
            return None

        try:
            database_url = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if not database_url.startswith('sqlite:///'):
                logger.warning("Non-SQLite database. Backup not supported.")
                return None

            db_path = database_url.replace('sqlite:///', '')
            if not db_path.startswith('/'):
                db_path = os.path.join('/app', db_path)

            if not os.path.exists(db_path):
                logger.info("Database file doesn't exist yet. No backup needed.")
                return None

            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"portall_backup_{backup_reason}_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            # Copy database file
            shutil.copy2(db_path, backup_path)

            # Verify backup
            if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                logger.info(f"✅ Database backup created: {backup_filename}")
                self.current_backup = backup_path

                # Clean up old backups (keep last 10)
                self._cleanup_old_backups()

                return backup_path
            else:
                logger.error("Backup verification failed.")
                return None

        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            return None

    def _cleanup_old_backups(self, keep_count=10):
        """
        Removes old backup files, keeping only the most recent ones.

        Args:
            keep_count (int): Number of backups to keep.
        """
        try:
            if not self.backup_dir or not os.path.exists(self.backup_dir):
                return

            # Get all backup files
            backup_files = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('portall_backup_') and filename.endswith('.db'):
                    filepath = os.path.join(self.backup_dir, filename)
                    backup_files.append((filepath, os.path.getmtime(filepath)))

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)

            # Remove old backups
            removed_count = 0
            for filepath, _ in backup_files[keep_count:]:
                try:
                    os.remove(filepath)
                    removed_count += 1
                except Exception as e:
                    logger.warning(f"Could not remove old backup {filepath}: {e}")

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old backup(s)")

        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")

    def _restore_from_backup(self, backup_path):
        """
        Restores database from a backup file.

        Args:
            backup_path (str): Path to the backup file.

        Returns:
            bool: True if restore was successful, False otherwise.
        """
        try:
            database_url = self.app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if not database_url.startswith('sqlite:///'):
                logger.error("Restore only supported for SQLite databases.")
                return False

            db_path = database_url.replace('sqlite:///', '')
            if not db_path.startswith('/'):
                db_path = os.path.join('/app', db_path)

            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False

            # Close any existing database connections
            self.db.engine.dispose()

            # Restore from backup
            shutil.copy2(backup_path, db_path)

            logger.info(f"✅ Database restored from backup: {os.path.basename(backup_path)}")
            return True

        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return False

    def _run_migration_safely(self, migration_name, migration_func):
        """
        Runs a migration with automatic backup and rollback on failure.

        Args:
            migration_name (str): Name of the migration.
            migration_func (callable): Function to execute the migration.

        Returns:
            bool: True if migration was successful, False otherwise.
        """
        logger.info(f"🔄 Starting migration: {migration_name}")

        # Create backup before migration
        backup_path = self._create_backup(f"before_{migration_name}")

        try:
            # Run the migration
            success = migration_func()

            if success:
                self._record_migration(migration_name)
                logger.info(f"✅ Migration completed successfully: {migration_name}")
                return True
            else:
                logger.error(f"❌ Migration failed: {migration_name}")

                # Attempt to restore from backup
                if backup_path and self._restore_from_backup(backup_path):
                    logger.info("🔄 Database restored from backup after migration failure")
                else:
                    logger.error("⚠️  Could not restore from backup. Manual intervention may be required.")

                return False

        except Exception as e:
            logger.error(f"❌ Migration error: {migration_name} - {e}")

            # Attempt to restore from backup
            if backup_path and self._restore_from_backup(backup_path):
                logger.info("🔄 Database restored from backup after migration error")
            else:
                logger.error("⚠️  Could not restore from backup. Manual intervention may be required.")

            return False

    def get_migration_status(self):
        """
        Gets the current migration status.

        Returns:
            dict: Migration status information.
        """
        status = {
            'applied_migrations': [],
            'pending_migrations': [],
            'backup_info': {
                'backup_dir': self.backup_dir,
                'backup_count': 0,
                'latest_backup': None
            }
        }

        # Get applied migrations
        with self.app.app_context():
            try:
                with self.db.engine.connect() as conn:
                    result = conn.execute(text(
                        "SELECT migration_name, applied_at FROM migration_versions ORDER BY applied_at"
                    ))
                    for row in result:
                        status['applied_migrations'].append({
                            'name': row[0],
                            'applied_at': row[1]
                        })
            except Exception as e:
                logger.error(f"Error getting migration status: {e}")

        # Check for pending migrations
        all_migrations = [
            "add_source_column",
            "add_is_immutable_column",
            "add_required_settings",
            "add_tagging_system",
            "add_auto_execute_column"
        ]

        applied_names = [m['name'] for m in status['applied_migrations']]
        status['pending_migrations'] = [m for m in all_migrations if m not in applied_names]

        # Get backup info
        if self.backup_dir and os.path.exists(self.backup_dir):
            backup_files = [f for f in os.listdir(self.backup_dir)
                          if f.startswith('portall_backup_') and f.endswith('.db')]
            status['backup_info']['backup_count'] = len(backup_files)

            if backup_files:
                # Get latest backup
                latest_backup = max(backup_files, key=lambda f: os.path.getmtime(
                    os.path.join(self.backup_dir, f)))
                status['backup_info']['latest_backup'] = latest_backup

        return status

    def run_standalone_migrations(self):
        """
        Runs all standalone migration scripts that haven't been applied yet.
        Uses safe migration execution with automatic backup and rollback.
        """
        migrations_to_run = [
            ("add_source_column", migration.run_migration),
            ("add_is_immutable_column", migration_immutable.run_migration),
            ("add_required_settings", migration_settings.run_migration),
            ("add_tagging_system", migration_tags.run_migration),
            ("add_auto_execute_column", migration_auto_execute.run_migration)
        ]

        for migration_name, migration_func in migrations_to_run:
            if not self._is_migration_applied(migration_name):
                success = self._run_migration_safely(migration_name, migration_func)
                if not success:
                    logger.error(f"Migration {migration_name} failed. Stopping migration process.")
                    return False
            else:
                logger.info(f"Migration {migration_name} already applied. Skipping.")

        return True

    def run_migrations(self):
        """
        Runs all migrations, including both Flask-Migrate migrations and standalone scripts.
        """
        with self.app.app_context():
            # Check if migrations folder exists
            migrations_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'migrations')
            migrations_exist = os.path.exists(migrations_folder)

            try:
                # Try to access the database
                self.db.engine.connect()
                logger.info("Existing database found.")

                if migrations_exist:
                    logger.info("Migrations folder found. Checking for pending migrations...")
                    try:
                        # Get current migration version
                        current_version = current(directory=migrations_folder)

                        # Try to upgrade
                        upgrade(directory=migrations_folder)
                        new_version = current(directory=migrations_folder)

                        if new_version != current_version:
                            logger.info("Database updated successfully.")
                        else:
                            logger.info("Database is up-to-date. No migration needed.")
                    except CommandError as e:
                        if "Target database is not up to date" in str(e):
                            logger.warning("Database schema has changed. Applying migrations...")
                            upgrade(directory=migrations_folder)
                            logger.info("Migrations applied successfully.")
                        else:
                            raise
                else:
                    logger.info("No migrations folder found. Ensuring all tables exist...")
                    self.db.create_all()
                    logger.info("Database tables verified/created.")

            except OperationalError as e:
                if "unable to open database file" in str(e):
                    logger.error("Unable to open database file. This is likely a permission issue.")
                    logger.error("Please ensure the database directory has proper permissions:")
                    logger.error("  mkdir -p ./instance")
                    logger.error("  chmod 777 ./instance")
                    raise PermissionError(
                        "Unable to open database file. Please ensure the database directory "
                        "has proper permissions by running: chmod 777 ./instance"
                    ) from e
                else:
                    logger.info("No existing database found. Creating new database and tables...")
                    # If the database doesn't exist, create it and all tables
                    self.db.create_all()
                    if migrations_exist:
                        # If migrations exist, stamp the database
                        stamp(directory=migrations_folder)
                        logger.info("New database created, all tables created, and stamped with latest migration version.")
                    else:
                        logger.info("New database and all tables created. No migrations to apply.")

            # Run standalone migrations after Flask-Migrate migrations
            self.run_standalone_migrations()

            logger.info("All migrations completed successfully.")

def init_migrations(app, db):
    """
    Initialize the migration manager and run all migrations.

    Args:
        app (Flask): The Flask application instance.
        db (SQLAlchemy): The SQLAlchemy database instance.

    Returns:
        MigrationManager: The initialized migration manager.
    """
    try:
        migration_manager = MigrationManager(app, db)
        migration_manager.run_migrations()
        return migration_manager
    except PermissionError as e:
        logger.error(f"Permission error during database initialization: {e}")
        logger.error("This is typically caused by incorrect file permissions on the database directory.")
        logger.error("Please ensure your docker-compose.yml includes proper volume permissions.")
        raise
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        raise

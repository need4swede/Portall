# utils/database/migrations.py

import os
import logging
from flask import current_app
from flask_migrate import Migrate, upgrade, stamp, current
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from alembic.util import CommandError

# Import the standalone migration scripts
import migration
import migration_immutable
import migration_settings

# Setup logging
logger = logging.getLogger(__name__)

class MigrationManager:
    """
    Manages database migrations, including both Flask-Migrate migrations
    and standalone migration scripts.
    """
    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.migrate = Migrate(app, db)

        # Validate database setup before proceeding
        self._validate_database_setup()

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

    def run_standalone_migrations(self):
        """
        Runs all standalone migration scripts that haven't been applied yet.
        """
        # Run source column migration if not already applied
        if not self._is_migration_applied("add_source_column"):
            logger.info("Running migration to add source column...")
            try:
                success = migration.run_migration()
                if success:
                    self._record_migration("add_source_column")
                    logger.info("Source column migration completed successfully.")
                else:
                    logger.error("Source column migration failed.")
            except Exception as e:
                logger.error(f"Error during source column migration: {e}")
        else:
            logger.info("Source column migration already applied. Skipping.")

        # Run is_immutable column migration if not already applied
        if not self._is_migration_applied("add_is_immutable_column"):
            logger.info("Running migration to add is_immutable column...")
            try:
                success = migration_immutable.run_migration()
                if success:
                    self._record_migration("add_is_immutable_column")
                    logger.info("Is_immutable column migration completed successfully.")
                else:
                    logger.error("Is_immutable column migration failed.")
            except Exception as e:
                logger.error(f"Error during is_immutable column migration: {e}")
        else:
            logger.info("Is_immutable column migration already applied. Skipping.")

        # Run settings migration if not already applied
        if not self._is_migration_applied("add_required_settings"):
            logger.info("Running migration to add required settings...")
            try:
                success = migration_settings.run_migration()
                if success:
                    self._record_migration("add_required_settings")
                    logger.info("Settings migration completed successfully.")
                else:
                    logger.error("Settings migration failed.")
            except Exception as e:
                logger.error(f"Error during settings migration: {e}")
        else:
            logger.info("Settings migration already applied. Skipping.")

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

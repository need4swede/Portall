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
        
        # Track migration versions in the database
        self._ensure_version_table_exists()
    
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
            except Exception as e:
                logger.error(f"Error creating migration versions table: {e}")
    
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
            except OperationalError:
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
    migration_manager = MigrationManager(app, db)
    migration_manager.run_migrations()
    return migration_manager

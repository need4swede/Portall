# migration_auto_execute.py

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Setup logging
logger = logging.getLogger(__name__)

def run_migration():
    """
    Add auto_execute column to tagging_rule table.

    Returns:
        bool: True if migration was successful, False otherwise.
    """
    try:
        # Get database URL from environment or use default
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/portall.db')

        # Create engine
        engine = create_engine(database_url)

        with engine.connect() as conn:
            # Check if the auto_execute column already exists
            try:
                result = conn.execute(text("PRAGMA table_info(tagging_rule)"))
                columns = [row[1] for row in result.fetchall()]

                if 'auto_execute' in columns:
                    logger.info("auto_execute column already exists in tagging_rule table. Skipping migration.")
                    return True

            except OperationalError as e:
                # Table might not exist yet
                logger.warning(f"Could not check existing columns: {e}")
                # Continue with migration attempt

            # Add the auto_execute column with default value False
            try:
                conn.execute(text("ALTER TABLE tagging_rule ADD COLUMN auto_execute BOOLEAN DEFAULT 0"))
                conn.commit()
                logger.info("Successfully added auto_execute column to tagging_rule table.")

                # Update all existing rules to have auto_execute = False (explicit)
                conn.execute(text("UPDATE tagging_rule SET auto_execute = 0 WHERE auto_execute IS NULL"))
                conn.commit()
                logger.info("Set auto_execute = False for all existing tagging rules.")

                return True

            except OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.info("auto_execute column already exists. Migration not needed.")
                    return True
                else:
                    logger.error(f"Error adding auto_execute column: {e}")
                    return False

    except Exception as e:
        logger.error(f"Error during auto_execute migration: {e}")
        return False

if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO)

    success = run_migration()
    if success:
        print("Auto-execute migration completed successfully.")
    else:
        print("Auto-execute migration failed.")
        exit(1)

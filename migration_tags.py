# migration_tags.py

import os
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """
    Migration to add tagging system tables.

    This migration adds:
    - tag table for storing tags
    - port_tag table for many-to-many relationship between ports and tags
    - tagging_rule table for automated tagging rules
    - rule_execution_log table for logging rule executions

    Returns:
        bool: True if migration was successful, False otherwise.
    """
    try:
        # Get database URL from environment or use default
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/portall.db')

        # Create engine
        engine = create_engine(database_url)

        # Check if tables already exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        tables_to_create = ['tag', 'port_tag', 'tagging_rule', 'rule_execution_log']
        tables_needed = [table for table in tables_to_create if table not in existing_tables]

        if not tables_needed:
            logger.info("All tagging tables already exist. Migration not needed.")
            return True

        logger.info(f"Creating tagging tables: {tables_needed}")

        with engine.connect() as conn:
            # Create tag table
            if 'tag' in tables_needed:
                logger.info("Creating tag table...")
                conn.execute(text("""
                    CREATE TABLE tag (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        color VARCHAR(7) NOT NULL DEFAULT '#007bff',
                        description VARCHAR(200),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                logger.info("Tag table created successfully.")

            # Create port_tag association table
            if 'port_tag' in tables_needed:
                logger.info("Creating port_tag table...")
                conn.execute(text("""
                    CREATE TABLE port_tag (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        port_id INTEGER NOT NULL,
                        tag_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (port_id) REFERENCES port (id) ON DELETE CASCADE,
                        FOREIGN KEY (tag_id) REFERENCES tag (id) ON DELETE CASCADE,
                        UNIQUE (port_id, tag_id)
                    )
                """))
                logger.info("Port_tag table created successfully.")

            # Create tagging_rule table
            if 'tagging_rule' in tables_needed:
                logger.info("Creating tagging_rule table...")
                conn.execute(text("""
                    CREATE TABLE tagging_rule (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(100) NOT NULL,
                        description VARCHAR(500),
                        enabled BOOLEAN NOT NULL DEFAULT 1,
                        auto_execute BOOLEAN NOT NULL DEFAULT 0,
                        priority INTEGER NOT NULL DEFAULT 0,
                        conditions TEXT NOT NULL,
                        actions TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_executed TIMESTAMP,
                        execution_count INTEGER NOT NULL DEFAULT 0,
                        ports_affected INTEGER NOT NULL DEFAULT 0
                    )
                """))
                logger.info("Tagging_rule table created successfully.")

            # Create rule_execution_log table
            if 'rule_execution_log' in tables_needed:
                logger.info("Creating rule_execution_log table...")
                conn.execute(text("""
                    CREATE TABLE rule_execution_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rule_id INTEGER NOT NULL,
                        port_id INTEGER NOT NULL,
                        action_type VARCHAR(20) NOT NULL,
                        tag_id INTEGER NOT NULL,
                        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN NOT NULL DEFAULT 1,
                        error_message VARCHAR(500),
                        FOREIGN KEY (rule_id) REFERENCES tagging_rule (id) ON DELETE CASCADE,
                        FOREIGN KEY (port_id) REFERENCES port (id) ON DELETE CASCADE,
                        FOREIGN KEY (tag_id) REFERENCES tag (id) ON DELETE CASCADE
                    )
                """))
                logger.info("Rule_execution_log table created successfully.")

            # Create indexes for better performance
            logger.info("Creating indexes...")

            # Indexes for port_tag table
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_port_tag_port_id ON port_tag (port_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_port_tag_tag_id ON port_tag (tag_id)"))

            # Indexes for tagging_rule table
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tagging_rule_enabled ON tagging_rule (enabled)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tagging_rule_priority ON tagging_rule (priority)"))

            # Indexes for rule_execution_log table
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rule_execution_log_rule_id ON rule_execution_log (rule_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rule_execution_log_port_id ON rule_execution_log (port_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rule_execution_log_executed_at ON rule_execution_log (executed_at)"))

            # Commit all changes
            conn.commit()
            logger.info("All indexes created successfully.")

        logger.info("Tagging system migration completed successfully.")
        return True

    except OperationalError as e:
        if "unable to open database file" in str(e):
            logger.error("Unable to open database file. This is likely a permission issue.")
            logger.error("Please ensure the database directory has proper permissions.")
            return False
        else:
            logger.error(f"Database error during tagging migration: {e}")
            return False
    except Exception as e:
        logger.error(f"Error during tagging migration: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        logger.info("Migration completed successfully.")
    else:
        logger.error("Migration failed.")
        exit(1)

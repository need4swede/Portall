# migration_immutable.py

import os
import sys
from flask import Flask
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Create a minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/portall.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

def run_migration():
    """Run the migration to add the is_immutable column to the Port table."""
    print("Starting migration for is_immutable column...")

    # Create a database engine
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

    try:
        # Check if the column already exists
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(port)"))
            columns = [row[1] for row in result]

            if 'is_immutable' not in columns:
                print("Adding 'is_immutable' column to Port table...")
                conn.execute(text("ALTER TABLE port ADD COLUMN is_immutable BOOLEAN DEFAULT 0"))
                print("Column added successfully.")

                # Update existing records based on source
                print("Updating existing records...")

                # Set Docker-imported ports as immutable
                conn.execute(text("UPDATE port SET is_immutable = 1 WHERE source IN ('docker', 'portainer', 'dockage', 'komodo')"))

                # Also update based on description patterns for backward compatibility
                conn.execute(text("UPDATE port SET is_immutable = 1 WHERE description LIKE 'Docker (%' OR description LIKE 'Portainer (%' OR description LIKE 'Dockage (%' OR description LIKE 'Komodo (%'"))
                conn.execute(text("UPDATE port SET is_immutable = 1 WHERE description LIKE '[D] %' OR description LIKE '[P] %'"))

                print("Existing records updated successfully.")
            else:
                print("'is_immutable' column already exists. Skipping migration.")

    except OperationalError as e:
        print(f"Error during migration: {e}")
        return False

    print("Migration completed successfully.")
    return True

if __name__ == "__main__":
    run_migration()

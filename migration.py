# migration.py

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
    """Run the migration to add the source column to the Port table."""
    print("Starting migration...")

    # Create a database engine
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

    try:
        # Check if the column already exists
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(port)"))
            columns = [row[1] for row in result]

            if 'source' not in columns:
                print("Adding 'source' column to Port table...")
                conn.execute(text("ALTER TABLE port ADD COLUMN source VARCHAR(20)"))
                print("Column added successfully.")

                # Update existing records based on description patterns
                print("Updating existing records...")

                # Update Portainer ports
                conn.execute(text("UPDATE port SET source = 'portainer' WHERE description LIKE 'Portainer (%'"))

                # Update Docker ports
                conn.execute(text("UPDATE port SET source = 'docker' WHERE description LIKE 'Docker (%'"))

                # Update ports with [P] tag
                conn.execute(text("UPDATE port SET source = 'portainer' WHERE description LIKE '[P] %'"))

                # Update ports with [D] tag
                conn.execute(text("UPDATE port SET source = 'docker' WHERE description LIKE '[D] %'"))

                # Set remaining ports as manual
                conn.execute(text("UPDATE port SET source = 'manual' WHERE source IS NULL"))

                print("Existing records updated successfully.")
            else:
                print("'source' column already exists. Skipping migration.")

    except OperationalError as e:
        print(f"Error during migration: {e}")
        return False

    print("Migration completed successfully.")
    return True

if __name__ == "__main__":
    run_migration()

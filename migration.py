# migration.py

# Standard Imports
import os
import sys

# External Imports
from flask_migrate import upgrade, migrate, init, stamp

# Local Imports
from app import app, db

def run_migration():
    with app.app_context():
        # Check if the migrations folder exists
        if not os.path.exists('migrations'):
            # Initialize migrations
            init()

            # Create a stamp for the current state of the database
            stamp()

        # Get the migration message from user input
        message = input("Enter a brief description for this migration: ")

        # Generate the migration script
        migrate(message=message)

        # Apply the migration
        upgrade()

if __name__ == '__main__':
    run_migration()
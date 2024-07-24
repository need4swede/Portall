# app.py

# Standard Imports
import logging
import os

# External Imports
from flask import Flask
from flask_migrate import Migrate, upgrade, stamp, current
from sqlalchemy.exc import OperationalError
from alembic.util import CommandError

# Local Imports
from utils.database import init_db
from utils.routes import routes_bp

# Setup logging
logging.basicConfig(level=logging.DEBUG)

def create_app():
    """
    Create and configure the Flask application.

    Returns:
        tuple: The configured Flask application instance and SQLAlchemy database instance.
    """
    # Create the Flask app
    app = Flask(__name__)

    # Environment variables
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///portall.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.environ.get('SECRET_KEY', 'M1Hd4l58YKm2Tqci6ZU65sEgWDexjuSfRybf2i4G')

    # Initialize database
    db = init_db(app)

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # Register the routes blueprint
    app.register_blueprint(routes_bp)

    return app, db

def init_or_migrate_db(app, db):
    """
    Initialize a new database or migrate an existing one.

    This function handles four scenarios:
    1. Database does not exist: Creates it and all tables.
    2. Database exists, but no migration folder: Ensures all tables exist.
    3. Database exists, migration folder exists, but no changes: No action needed.
    4. Database exists, migration folder exists, and changes detected: Updates database.

    Args:
        app (Flask): The Flask application instance.
        db (SQLAlchemy): The SQLAlchemy database instance.
    """
    with app.app_context():
        # Check if migrations folder exists
        migrations_folder = os.path.join(os.path.dirname(__file__), 'migrations')
        migrations_exist = os.path.exists(migrations_folder)

        try:
            # Try to access the database
            db.engine.connect()
            logging.info("Existing database found.")

            if migrations_exist:
                logging.info("Migrations folder found. Checking for pending migrations...")
                try:
                    # Get current migration version
                    current_version = current(directory=migrations_folder)

                    # Try to upgrade
                    upgrade(directory=migrations_folder)
                    new_version = current(directory=migrations_folder)

                    if new_version != current_version:
                        logging.info("Database updated successfully.")
                    else:
                        logging.info("Database is up-to-date. No migration needed.")
                except CommandError as e:
                    if "Target database is not up to date" in str(e):
                        logging.warning("Database schema has changed. Applying migrations...")
                        upgrade(directory=migrations_folder)
                        logging.info("Migrations applied successfully.")
                    else:
                        raise
            else:
                logging.info("No migrations folder found. Ensuring all tables exist...")
                db.create_all()
                logging.info("Database tables verified/created.")
        except OperationalError:
            logging.info("No existing database found. Creating new database and tables...")
            # If the database doesn't exist, create it and all tables
            db.create_all()
            if migrations_exist:
                # If migrations exist, stamp the database
                stamp(directory=migrations_folder)
                logging.info("New database created, all tables created, and stamped with latest migration version.")
            else:
                logging.info("New database and all tables created. No migrations to apply.")

# Create the app and get the db instance
app, db = create_app()

# Run application
if __name__ == '__main__':
    # Initialize or migrate the database before starting the app
    init_or_migrate_db(app, db)

    port = int(os.environ.get('PORT', 8080))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    logging.info(f"Starting Portall on port {port} with debug mode: {debug_mode}")

    app.run(debug=debug_mode, host='0.0.0.0', port=port)
# Standard Imports
import argparse
import logging
import os
# External Imports
from flask import Flask
from flask_migrate import Migrate
# Local Imports
from utils.database import init_db
from utils.database.migrations import init_migrations
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

    # Environment variables - ensure database is in instance directory
    default_db_url = 'sqlite:////app/instance/portall.db'  # Absolute path to instance directory
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', default_db_url)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.environ.get('SECRET_KEY', 'M1Hd4l58YKm2Tqci6ZU65sEgWDexjuSfRybf2i4G')

    # Log the database URL for debugging
    logging.info(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")

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
    This function uses the MigrationManager to handle all database migrations,
    including both Flask-Migrate migrations and standalone migration scripts.
    Args:
        app (Flask): The Flask application instance.
        db (SQLAlchemy): The SQLAlchemy database instance.
    """
    # Initialize the migration manager and run all migrations
    migration_manager = init_migrations(app, db)
    logging.info("Database initialization and migration completed.")

# Create the app and get the db instance
app, db = create_app()

# Initialize auto-scan threads
def init_auto_scan_threads():
    """
    Initialize the auto-scan threads for Docker, Portainer, and Komodo integrations.
    TODO: Implement auto-scan threads for the new instance-based approach.
    """
    # TODO: Implement auto-scan functionality with the new DockerInstanceManager
    logging.info("Auto-scan threads initialization skipped (TODO: implement for new instance system)")

# Run application
if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the Portall application.')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 8080)),
                        help='Port to run the application on (default: 8080)')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode')
    args = parser.parse_args()

    # Initialize or migrate the database before starting the app
    init_or_migrate_db(app, db)

    # Initialize auto-scan threads
    init_auto_scan_threads()

    port = args.port
    debug_mode = args.debug or os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    logging.info(f"Starting Portall on port {port} with debug mode: {debug_mode}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

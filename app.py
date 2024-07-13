# app.py

# Standard Imports
import logging
import os

# External Imports
from flask import Flask
from flask_migrate import Migrate, upgrade, stamp
from sqlalchemy.exc import OperationalError

# Local Imports
from utils.database import init_db
from utils.routes import routes_bp

# Setup logging
logging.basicConfig(level=logging.DEBUG)

def create_app():
    """
    Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application instance.
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

    This function attempts to connect to the database. If successful, it applies
    any pending migrations. If unsuccessful (likely due to the database not existing),
    it creates all tables and stamps the database with the latest migration version.

    Args:
        app (Flask): The Flask application instance.
        db (SQLAlchemy): The SQLAlchemy database instance.
    """
    with app.app_context():
        try:
            # Try to access the database
            db.engine.connect()
            logging.info("Existing database found. Applying migrations...")
            # If successful, run migrations
            upgrade()
            logging.info("Migrations applied successfully.")
        except OperationalError:
            logging.info("No existing database found. Creating new database...")
            # If the database doesn't exist, create it
            db.create_all()
            # Then stamp it as the latest migration
            stamp()
            logging.info("New database created and stamped with latest migration version.")

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
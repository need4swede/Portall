import os
import logging
import tempfile
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def ensure_database_directory():
    """Ensure the database directory exists and is writable, with fallback options"""
    # Extract database path from DATABASE_URL
    database_url = os.environ.get('DATABASE_URL', 'sqlite:////app/instance/portall.db')

    if database_url.startswith('sqlite:///'):
        db_path = database_url.replace('sqlite:///', '')

        # If it's a relative path, make it absolute from /app
        if not db_path.startswith('/'):
            db_path = os.path.join('/app', db_path)

        db_dir = os.path.dirname(db_path)

        # Try to create and use the intended directory
        try:
            Path(db_dir).mkdir(parents=True, exist_ok=True)

            # Test if we can write to the directory
            test_file = os.path.join(db_dir, '.write_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                logging.info(f"✅ Database directory ready: {db_dir}")
                return  # Success!
            except (PermissionError, OSError) as e:
                logging.warning(f"⚠️  Cannot write to {db_dir}: {e}")
                raise PermissionError(f"Write test failed for {db_dir}")

        except (PermissionError, OSError) as e:
            logging.warning(f"⚠️  Database directory setup failed for {db_dir}: {e}")

            # Fallback 1: Try using /tmp
            temp_db_path = os.path.join('/tmp', 'portall.db')
            logging.warning(f"🔄 Falling back to temporary database: {temp_db_path}")
            os.environ['DATABASE_URL'] = f'sqlite:///{temp_db_path}'

            try:
                # Test writing to /tmp
                with open(temp_db_path + '.test', 'w') as f:
                    f.write('test')
                os.remove(temp_db_path + '.test')
                logging.info(f"✅ Using temporary database location: {temp_db_path}")
                return
            except (PermissionError, OSError) as e2:
                logging.error(f"❌ Cannot write to /tmp either: {e2}")

                # Fallback 2: Use in-memory database
                logging.warning("🔄 Falling back to in-memory database (data will not persist)")
                os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
                logging.info("✅ Using in-memory database")
                return
    else:
        logging.info(f"Using non-SQLite database: {database_url}")

def init_db(app):
    # Ensure database directory exists and is writable before initializing
    ensure_database_directory()

    # Update the app config with any changes to DATABASE_URL
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', app.config['SQLALCHEMY_DATABASE_URI'])

    db.init_app(app)
    return db

def create_tables(app):
    with app.app_context():
        db.create_all()
# app.py

# Standard Imports
import logging
import os

# External Imports
from flask import Flask

# Local Imports
from app.utils.database import init_db, create_tables
from app.routes import routes_bp

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Create the Flask app
app = Flask(__name__, static_folder="./app/static", template_folder="./app/templates")

# Environment variables
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///portall.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'M1Hd4l58YKm2Tqci6ZU65sEgWDexjuSfRybf2i4G')

# Initialize database
db = init_db(app)

# Create database tables
create_tables(app)

# Register the routes blueprint
app.register_blueprint(routes_bp)

# Run application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true',
            host='0.0.0.0',
            port=port)
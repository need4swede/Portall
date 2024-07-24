# manage.py

# Standard Imports
import os

# External Imports
from flask.cli import FlaskGroup

# Local Imports
from app import app, db
from flask_migrate import Migrate

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Create CLI group
cli = FlaskGroup(app)

@cli.command("run")
def run():
    """Run the Flask development server."""
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)

if __name__ == '__main__':
    cli()
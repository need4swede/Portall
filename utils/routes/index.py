# utils/routes/index.py

# External Imports
from flask import Blueprint                     # For creating a blueprint
from flask import render_template               # For rendering HTML templates
from flask import session                       # For storing session data

# Local Imports
from utils.database import db, Port, Setting    # For accessing the database models

# Create the blueprint
index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    """
    Render the main index page of the application.

    This function handles requests to the root URL ('/') and prepares data
    for rendering the main page. It performs the following tasks:
    1. Retrieves distinct IP addresses and their nicknames from the database.
    2. Determines the default IP address to display.
    3. Manages the theme setting for the user interface.

    Returns:
        rendered_template: The 'new.html' template with context data including
                            IP addresses, default IP, and current theme.
    """
    # Query distinct IP addresses and their nicknames from the Port table
    ip_addresses = db.session.query(Port.ip_address, Port.nickname).distinct().all()

    # Determine the default IP address
    default_ip = Setting.query.filter_by(key='default_ip').first()
    default_ip = default_ip.value if default_ip else (ip_addresses[0][0] if ip_addresses else '')

    # Check if theme is set in session, if not, retrieve from database
    if 'theme' not in session:

        # Retrieve theme setting from database
        theme_setting = Setting.query.filter_by(key='theme').first()
        theme = theme_setting.value if theme_setting else 'light'

        # Store theme in session for future requests
        session['theme'] = theme

    else:

        # Use theme from session if already set
        theme = session['theme']

    # Render the template with the prepared data
    return render_template('new.html', ip_addresses=ip_addresses, default_ip=default_ip, theme=theme)
# External Imports
from flask import Blueprint                     # For creating a blueprint
from flask import render_template               # For rendering HTML templates
from flask import session                       # For storing session data

# Local Imports
from utils.database import db, Port, Setting   # For accessing the database models

# Create the blueprint
index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    ip_addresses = db.session.query(Port.ip_address, Port.nickname).distinct().all()
    default_ip = Setting.query.filter_by(key='default_ip').first()
    default_ip = default_ip.value if default_ip else (ip_addresses[0][0] if ip_addresses else '')

    # Check if theme is set in session, if not, retrieve from database
    if 'theme' not in session:
        theme_setting = Setting.query.filter_by(key='theme').first()
        theme = theme_setting.value if theme_setting else 'light'
        session['theme'] = theme
    else:
        theme = session['theme']

    return render_template('new.html', ip_addresses=ip_addresses, default_ip=default_ip, theme=theme)



# utils/routes/settings.py

# Standard Imports
import os                                       # For file operations

# External Imports
from flask import Blueprint                     # For creating a blueprint
from flask import current_app as app            # For accessing the Flask app
from flask import jsonify                       # For returning JSON responses
from flask import render_template               # For rendering HTML templates
from flask import request                       # For handling HTTP requests
from flask import send_from_directory           # For serving static files
from flask import session                       # For storing session data

# Local Imports
from utils.database import db, Port, Setting   # For accessing the database models

# Create the blueprint
settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        default_ip = request.form.get('default_ip', '')
        theme = request.form.get('theme', 'light')
        custom_css = request.form.get('custom_css', '')

        for key, value in [('default_ip', default_ip), ('theme', theme), ('custom_css', custom_css)]:
            if value is not None:  # Update even if the value is an empty string
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    setting = Setting(key=key, value=value)
                    db.session.add(setting)

        try:
            db.session.commit()
            session['theme'] = theme  # Update session with new theme
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving settings: {str(e)}")
            return jsonify({'success': False, 'error': 'Error saving settings'}), 500

    ip_addresses = [ip[0] for ip in db.session.query(Port.ip_address).distinct()]
    default_ip = Setting.query.filter_by(key='default_ip').first()
    default_ip = default_ip.value if default_ip else ''

    # Retrieve theme from session or database
    if 'theme' not in session:
        theme_setting = Setting.query.filter_by(key='theme').first()
        theme = theme_setting.value if theme_setting else 'light'
        session['theme'] = theme
    else:
        theme = session['theme']

    theme_dir = os.path.join(app.static_folder, 'css', 'themes')
    themes = [f.split('.')[0] for f in os.listdir(theme_dir) if f.endswith('.css') and not f.startswith('global-')]

    custom_css = Setting.query.filter_by(key='custom_css').first()
    custom_css = custom_css.value if custom_css else ''

    return render_template('settings.html', ip_addresses=ip_addresses, default_ip=default_ip, current_theme=theme, themes=themes, theme=theme, custom_css=custom_css)

@settings_bp.route('/purge_entries', methods=['POST'])
def purge_entries():
    try:
        num_deleted = Port.query.delete()
        db.session.commit()
        app.logger.info(f"Purged {num_deleted} entries from the database")
        return jsonify({'success': True, 'message': f'All entries have been purged. {num_deleted} entries deleted.'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error purging entries: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/static/css/themes/<path:filename>')
def serve_theme(filename):
    return send_from_directory('static/css/themes', filename)

@settings_bp.route('/port_settings', methods=['GET', 'POST'])
def port_settings():
    if request.method == 'POST':
        # Handle port settings
        port_settings = {
            'port_start': request.form.get('port_start'),
            'port_end': request.form.get('port_end'),
            'port_exclude': request.form.get('port_exclude'),
            'port_length': request.form.get('port_length')
        }

        for key, value in port_settings.items():
            setting = Setting.query.filter_by(key=key).first()
            if value:  # Update or create if a value is provided
                if setting:
                    setting.value = value
                else:
                    setting = Setting(key=key, value=value)
                    db.session.add(setting)
            elif setting:  # Delete if no value is provided and setting exists
                db.session.delete(setting)

        try:
            db.session.commit()
            return jsonify({'success': True, 'message': 'Port settings updated successfully'})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving port settings: {str(e)}")
            return jsonify({'success': False, 'error': 'Error saving port settings'}), 500

    # GET request
    port_settings = {}
    for key in ['port_start', 'port_end', 'port_exclude', 'port_length']:
        setting = Setting.query.filter_by(key=key).first()
        port_settings[key] = setting.value if setting else None

    return jsonify(port_settings)
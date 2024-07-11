# utils/routes/settings.py

# Standard Imports
import json                                     # For JSON operations
import os                                       # For file operations
import re                                       # For regular expressions

# External Imports
from datetime import datetime
from io import BytesIO
from flask import Blueprint                     # For creating a blueprint
from flask import current_app as app            # For accessing the Flask app
from flask import jsonify                       # For returning JSON responses
from flask import render_template               # For rendering HTML templates
from flask import request                       # For handling HTTP requests
from flask import send_file                     # For serving files
from flask import send_from_directory           # For serving static files
from flask import session                       # For storing session data
import markdown                                 # For rendering Markdown text

# Local Imports
from utils.database import db, Port, Setting  # For accessing the database models

# Create the blueprint
settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """
    Handle the settings page for the application.
    This function manages both GET and POST requests for the settings page.
    For GET requests, it retrieves and displays current settings.
    For POST requests, it updates the settings based on form data.

    Returns:
    For GET: Rendered settings.html template
    For POST: JSON response indicating success or failure
    """
    if request.method == 'POST':
        # Extract form data
        default_ip = request.form.get('default_ip')
        theme = request.form.get('theme')
        custom_css = request.form.get('custom_css')

        # Update settings only if they are provided
        settings_to_update = {}
        if default_ip is not None:
            settings_to_update['default_ip'] = default_ip
        if theme is not None:
            settings_to_update['theme'] = theme
        if custom_css is not None:
            settings_to_update['custom_css'] = custom_css

        for key, value in settings_to_update.items():
            setting = Setting.query.filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                setting = Setting(key=key, value=value)
            db.session.add(setting)

        try:
            db.session.commit()
            if 'theme' in settings_to_update:
                session['theme'] = theme
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving settings: {str(e)}")
            return jsonify({'success': False, 'error': 'Error saving settings'}), 500

    # Retrieve unique IP addresses from the database
    ip_addresses = [ip[0] for ip in db.session.query(Port.ip_address).distinct()]

    # Get the default IP address from settings
    default_ip = Setting.query.filter_by(key='default_ip').first()
    default_ip = default_ip.value if default_ip else ''

    # Retrieve theme from session or database
    if 'theme' not in session:
        theme_setting = Setting.query.filter_by(key='theme').first()
        theme = theme_setting.value if theme_setting else 'light'
        session['theme'] = theme
    else:
        theme = session['theme']

    # Get available themes from the themes directory
    theme_dir = os.path.join(app.static_folder, 'css', 'themes')
    themes = [f.split('.')[0] for f in os.listdir(theme_dir) if f.endswith('.css') and not f.startswith('global-')]

    # Retrieve custom CSS from settings
    custom_css = Setting.query.filter_by(key='custom_css').first()
    custom_css = custom_css.value if custom_css else ''

    # Get version from README
    def get_version_from_readme():
        try:
            readme_path = os.path.join(os.path.dirname(__file__), '..', '..', 'README.md')
            if not os.path.exists(readme_path):
                app.logger.error(f"README.md not found at {readme_path}")
                return "Unknown (File Not Found)"
            with open(readme_path, 'r') as file:
                content = file.read()
            match = re.search(r'version-(\d+\.\d+\.\d+)-blue\.svg', content)
            if match:
                version = match.group(1)
                app.logger.info(f"version: {version}")
                return version
            else:
                app.logger.warning("Version pattern not found in README")
                return "Unknown (Pattern Not Found)"
        except Exception as e:
            app.logger.error(f"Error reading version from README: {str(e)}")
            return f"Unknown (Error: {str(e)})"

    # Get app version from README
    version = get_version_from_readme()

    # Render the settings template with all necessary data
    return render_template('settings.html', ip_addresses=ip_addresses, default_ip=default_ip,
                           current_theme=theme, themes=themes, theme=theme, custom_css=custom_css,
                           version=version)

@settings_bp.route('/port_settings', methods=['GET', 'POST'])
def port_settings():
    if request.method == 'POST':
        # Extract port settings from form data
        port_settings = {
            'port_start': request.form.get('port_start'),
            'port_end': request.form.get('port_end'),
            'port_exclude': request.form.get('port_exclude'),
            'port_length': request.form.get('port_length'),
            'copy_format': request.form.get('copy_format', 'port_only')  # Default to 'port_only' if not provided
        }

        # Update or create port settings in the database
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

    # Handle GET request: Retrieve current port settings
    port_settings = {}
    for key in ['port_start', 'port_end', 'port_exclude', 'port_length', 'copy_format']:
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            port_settings[key] = setting.value
        elif key == 'copy_format':
            # If copy_format doesn't exist, create it with default value
            new_setting = Setting(key='copy_format', value='port_only')
            db.session.add(new_setting)
            db.session.commit()
            port_settings[key] = 'port_only'
        else:
            port_settings[key] = None

    return jsonify(port_settings)

@settings_bp.route('/static/css/themes/<path:filename>')
def serve_theme(filename):
    """
    Serve CSS theme files from the themes directory.

    This function handles requests for theme CSS files and serves them directly from the themes directory.

    Args:
        filename (str): The name of the CSS file to serve.

    Returns:
        The requested CSS file.
    """
    return send_from_directory('static/css/themes', filename)

@settings_bp.route('/export_entries', methods=['GET'])
def export_entries():
    """
    Export all port entries from the database as a JSON file.

    This function fetches all ports from the database, formats them into a list of dictionaries,
    converts the list to a JSON string, and returns the JSON data as a downloadable file. The
    filename includes the current date.

    Returns:
        Response: A Flask response object containing the JSON file for download.
    """
    try:
        # Fetch all ports from the database
        ports = Port.query.all()

        # Create a list of dictionaries containing port data
        port_data = [
            {
                'ip_address': port.ip_address,
                'nickname': port.nickname,
                'port_number': port.port_number,
                'description': port.description,
                'port_protocol': port.port_protocol,
                'order': port.order
            } for port in ports
        ]

        # Convert data to JSON
        json_data = json.dumps(port_data, indent=2)

        # Create a BytesIO object
        buffer = BytesIO()
        buffer.write(json_data.encode())
        buffer.seek(0)

        # Generate filename with current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"portall_export_{current_date}.json"

        # Log the export
        app.logger.info(f"Exporting Data to: {filename}")

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
    except Exception as e:
        app.logger.error(f"Error in export_entries: {str(e)}")
        return jsonify({"error": str(e)}), 500

@settings_bp.route('/purge_entries', methods=['POST'])
def purge_entries():
    """
    Purge all entries from the Port table in the database.

    This function handles POST requests to delete all records from the Port table.
    It's typically used for maintenance or reset purposes.

    Returns:
        JSON response indicating success or failure, along with the number of deleted entries.
    """
    try:
        num_deleted = Port.query.delete()
        db.session.commit()
        app.logger.info(f"Purged {num_deleted} entries from the database")
        return jsonify({'success': True, 'message': f'All entries have been purged. {num_deleted} entries deleted.'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error purging entries: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/get_about_content')
def get_about_content():
    def read_md_file(filename):
        filepath = os.path.join(app.root_path, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as file:
                content = file.read()
                return markdown.markdown(content)
        return ""

    planned_features = read_md_file('planned_features.md')
    changelog = read_md_file('changelog.md')

    return jsonify({
        'planned_features': planned_features,
        'changelog': changelog
    })
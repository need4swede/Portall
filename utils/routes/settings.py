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
    """
    Handle GET and POST requests for port settings.

    GET: Retrieve current port settings from the database.
    If settings don't exist, default values are provided.

    POST: Update port settings in the database with values from the form.
    If a setting is not provided, it uses a default value.

    Port settings include:
    - port_start: Starting port number
    - port_end: Ending port number
    - port_exclude: Comma-separated list of ports to exclude
    - port_length: Number of digits in port number (default: '4')
    - copy_format: Format for copying port info (default: 'port_only')

    Returns:
    - For GET: JSON object containing current port settings
    - For POST: JSON object indicating success or failure of the update operation

    Raises:
    - Logs any exceptions and returns a 500 error response
    """
    if request.method == 'GET':
        try:
            port_settings = {}
            for key in ['port_start', 'port_end', 'port_exclude', 'port_length', 'copy_format']:
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    port_settings[key] = setting.value
                elif key == 'copy_format':
                    port_settings[key] = 'port_only'
                elif key == 'port_length':
                    port_settings[key] = '4'  # Set default to '4'
                else:
                    port_settings[key] = ''

            app.logger.debug(f"Retrieved port settings: {port_settings}")
            return jsonify(port_settings)
        except Exception as e:
            app.logger.error(f"Error retrieving port settings: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            # Extract port settings from form data
            port_settings = {
                'port_start': request.form.get('port_start', ''),
                'port_end': request.form.get('port_end', ''),
                'port_exclude': request.form.get('port_exclude', ''),
                'port_length': request.form.get('port_length', '4'),  # Default to '4' if not provided
                'copy_format': request.form.get('copy_format', 'port_only')
            }

            app.logger.debug(f"Received port settings: {port_settings}")

            # Update or create port settings in the database
            for key, value in port_settings.items():
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    new_setting = Setting(key=key, value=value)
                    db.session.add(new_setting)

            db.session.commit()
            app.logger.info("Port settings updated successfully")
            return jsonify({'success': True, 'message': 'Port settings updated successfully'})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving port settings: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500

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
    Export all port entries and configuration settings from the database as a JSON file.

    This function fetches all ports from the database, formats them into a list of dictionaries,
    also includes Docker, Portainer, and Komodo configuration settings,
    converts the data to a JSON string, and returns the JSON data as a downloadable file.
    The filename includes the current date.

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

        # Helper function to get settings
        def get_setting(key, default=''):
            setting = Setting.query.filter_by(key=key).first()
            return setting.value if setting else default

        # Get Docker settings
        docker_enabled = get_setting('docker_enabled', 'false')
        docker_host = get_setting('docker_host', 'unix:///var/run/docker.sock')
        docker_auto_detect = get_setting('docker_auto_detect', 'false')

        # Get Portainer settings
        portainer_enabled = get_setting('portainer_enabled', 'false')
        portainer_url = get_setting('portainer_url', '')
        portainer_api_key = get_setting('portainer_api_key', '')
        portainer_auto_detect = get_setting('portainer_auto_detect', 'false')

        # Get Komodo settings
        komodo_enabled = get_setting('komodo_enabled', 'false')
        komodo_url = get_setting('komodo_url', '')
        komodo_api_key = get_setting('komodo_api_key', '')
        komodo_api_secret = get_setting('komodo_api_secret', '')
        komodo_auto_detect = get_setting('komodo_auto_detect', 'false')

        # Get all tags with their properties
        from utils.database import Tag, TaggingRule
        tags = Tag.query.all()
        tags_data = [{
            'id': tag.id,
            'name': tag.name,
            'color': tag.color,
            'description': tag.description,
            'created_at': tag.created_at.isoformat() if tag.created_at else None
        } for tag in tags]

        # Get all tagging rules
        rules = TaggingRule.query.all()
        rules_data = [{
            'id': rule.id,
            'name': rule.name,
            'description': rule.description,
            'enabled': rule.enabled,
            'auto_execute': rule.auto_execute,
            'priority': rule.priority,
            'conditions': json.loads(rule.conditions),
            'actions': json.loads(rule.actions),
            'execution_count': rule.execution_count,
            'ports_affected': rule.ports_affected,
            'last_executed': rule.last_executed.isoformat() if rule.last_executed else None,
            'created_at': rule.created_at.isoformat() if rule.created_at else None
        } for rule in rules]

        # Add tags to port data
        from utils.database import PortTag
        for port_dict in port_data:
            port_id = Port.query.filter_by(
                ip_address=port_dict['ip_address'],
                port_number=port_dict['port_number'],
                port_protocol=port_dict['port_protocol']
            ).first().id

            port_tags = db.session.query(Tag).join(PortTag).filter(PortTag.port_id == port_id).all()
            port_dict['tags'] = [{
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'description': tag.description
            } for tag in port_tags]

        # Get general application settings
        general_settings = {
            'default_ip': get_setting('default_ip', ''),
            'theme': get_setting('theme', 'light'),
            'custom_css': get_setting('custom_css', '')
        }

        # Get port generation settings
        port_settings = {
            'port_start': get_setting('port_start', ''),
            'port_end': get_setting('port_end', ''),
            'port_exclude': get_setting('port_exclude', ''),
            'port_length': get_setting('port_length', '4'),
            'copy_format': get_setting('copy_format', 'port_only')
        }

        # Get port scanning settings
        port_scanning_settings = {
            'port_scanning_enabled': get_setting('port_scanning_enabled', 'false'),
            'auto_add_discovered': get_setting('auto_add_discovered', 'false'),
            'scan_range_start': get_setting('scan_range_start', '1024'),
            'scan_range_end': get_setting('scan_range_end', '65535'),
            'scan_exclude': get_setting('scan_exclude', ''),
            'scan_timeout': get_setting('scan_timeout', '1000'),
            'scan_threads': get_setting('scan_threads', '50'),
            'scan_interval': get_setting('scan_interval', '24'),
            'scan_retention': get_setting('scan_retention', '30'),
            'verify_ports_on_load': get_setting('verify_ports_on_load', 'false')
        }

        # Get tagging system settings
        tagging_settings = {
            'show_tags_in_tooltips': get_setting('show_tags_in_tooltips', 'true'),
            'show_tags_on_cards': get_setting('show_tags_on_cards', 'false'),
            'max_tags_display': get_setting('max_tags_display', '5'),
            'tag_badge_style': get_setting('tag_badge_style', 'rounded'),
            'allow_duplicate_tag_names': get_setting('allow_duplicate_tag_names', 'false'),
            'auto_generate_colors': get_setting('auto_generate_colors', 'true'),
            'default_tag_color': get_setting('default_tag_color', '#007bff')
        }

        # Create export data dictionary with comprehensive settings
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'version': '3.0',  # Updated version to reflect comprehensive settings export
            'ports': port_data,
            'tags': tags_data,
            'tagging_rules': rules_data,
            'general_settings': general_settings,
            'port_settings': port_settings,
            'port_scanning_settings': port_scanning_settings,
            'tagging_settings': tagging_settings,
            'docker': {
                'enabled': docker_enabled.lower() == 'true',
                'path': docker_host,
                'auto_scan': docker_auto_detect.lower() == 'true',
                'scan_interval': get_setting('docker_scan_interval', '300')
            },
            'portainer': {
                'enabled': portainer_enabled.lower() == 'true',
                'path': portainer_url,
                'auto_scan': portainer_auto_detect.lower() == 'true',
                'api_key': portainer_api_key if portainer_enabled.lower() == 'true' else '',
                'verify_ssl': get_setting('portainer_verify_ssl', 'true'),
                'scan_interval': get_setting('portainer_scan_interval', '300')
            },
            'komodo': {
                'enabled': komodo_enabled.lower() == 'true',
                'path': komodo_url,
                'auto_scan': komodo_auto_detect.lower() == 'true',
                'api_key': komodo_api_key if komodo_enabled.lower() == 'true' else '',
                'api_secret': komodo_api_secret if komodo_enabled.lower() == 'true' else '',
                'scan_interval': get_setting('komodo_scan_interval', '300')
            }
        }

        # Convert data to JSON
        json_data = json.dumps(export_data, indent=2)

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

@settings_bp.route('/port_scanning_settings', methods=['GET', 'POST'])
def port_scanning_settings():
    """
    Handle GET and POST requests for port scanning settings.
    """
    if request.method == 'GET':
        try:
            scanning_settings = {}
            for key in ['port_scanning_enabled', 'auto_add_discovered', 'scan_range_start', 'scan_range_end',
                       'scan_exclude', 'scan_timeout', 'scan_threads', 'scan_interval', 'scan_retention',
                       'verify_ports_on_load']:
                setting = Setting.query.filter_by(key=key).first()
                scanning_settings[key] = setting.value if setting else ''

            return jsonify(scanning_settings)
        except Exception as e:
            app.logger.error(f"Error retrieving port scanning settings: {str(e)}")
            return jsonify({'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            # Extract port scanning settings from form data
            settings_to_update = {
                'port_scanning_enabled': 'true' if request.form.get('port_scanning_enabled') else 'false',
                'auto_add_discovered': 'true' if request.form.get('auto_add_discovered') else 'false',
                'scan_range_start': request.form.get('scan_range_start', '1024'),
                'scan_range_end': request.form.get('scan_range_end', '65535'),
                'scan_exclude': request.form.get('scan_exclude', ''),
                'scan_timeout': request.form.get('scan_timeout', '1000'),
                'scan_threads': request.form.get('scan_threads', '50'),
                'scan_interval': request.form.get('scan_interval', '24'),
                'scan_retention': request.form.get('scan_retention', '30'),
                'verify_ports_on_load': 'true' if request.form.get('verify_ports_on_load') else 'false'
            }

            # Update or create port scanning settings in the database
            for key, value in settings_to_update.items():
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    new_setting = Setting(key=key, value=value)
                    db.session.add(new_setting)

            db.session.commit()
            app.logger.info("Port scanning settings updated successfully")
            return jsonify({'success': True, 'message': 'Port scanning settings updated successfully'})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving port scanning settings: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/tag_display_settings', methods=['GET', 'POST'])
def tag_display_settings():
    """
    Handle GET and POST requests for tag display settings.
    """
    if request.method == 'GET':
        try:
            tag_settings = {}
            for key in ['show_tags_in_tooltips', 'show_tags_on_cards', 'max_tags_display', 'tag_badge_style']:
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    tag_settings[key] = setting.value
                else:
                    # Set defaults
                    if key == 'show_tags_in_tooltips':
                        tag_settings[key] = 'true'
                    elif key == 'show_tags_on_cards':
                        tag_settings[key] = 'false'
                    elif key == 'max_tags_display':
                        tag_settings[key] = '5'
                    elif key == 'tag_badge_style':
                        tag_settings[key] = 'rounded'
                    else:
                        tag_settings[key] = ''

            return jsonify(tag_settings)
        except Exception as e:
            app.logger.error(f"Error retrieving tag display settings: {str(e)}")
            return jsonify({'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            # Extract tag display settings from form data
            tag_settings = {
                'show_tags_in_tooltips': 'true' if request.form.get('show_tags_in_tooltips') else 'false',
                'show_tags_on_cards': 'true' if request.form.get('show_tags_on_cards') else 'false',
                'max_tags_display': request.form.get('max_tags_display', '5'),
                'tag_badge_style': request.form.get('tag_badge_style', 'rounded')
            }

            # Update or create tag display settings in the database
            for key, value in tag_settings.items():
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    new_setting = Setting(key=key, value=value)
                    db.session.add(new_setting)

            db.session.commit()
            app.logger.info("Tag display settings updated successfully")
            return jsonify({'success': True, 'message': 'Tag display settings updated successfully'})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving tag display settings: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

@settings_bp.route('/tag_management_settings', methods=['GET', 'POST'])
def tag_management_settings():
    """
    Handle GET and POST requests for tag management settings.
    """
    if request.method == 'GET':
        try:
            tag_settings = {}
            for key in ['allow_duplicate_tag_names', 'auto_generate_colors', 'default_tag_color']:
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    tag_settings[key] = setting.value
                else:
                    # Set defaults
                    if key == 'allow_duplicate_tag_names':
                        tag_settings[key] = 'false'
                    elif key == 'auto_generate_colors':
                        tag_settings[key] = 'true'
                    elif key == 'default_tag_color':
                        tag_settings[key] = '#007bff'
                    else:
                        tag_settings[key] = ''

            return jsonify(tag_settings)
        except Exception as e:
            app.logger.error(f"Error retrieving tag management settings: {str(e)}")
            return jsonify({'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            # Extract tag management settings from form data
            tag_settings = {
                'allow_duplicate_tag_names': 'true' if request.form.get('allow_duplicate_tag_names') else 'false',
                'auto_generate_colors': 'true' if request.form.get('auto_generate_colors') else 'false',
                'default_tag_color': request.form.get('default_tag_color', '#007bff')
            }

            # Update or create tag management settings in the database
            for key, value in tag_settings.items():
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    new_setting = Setting(key=key, value=value)
                    db.session.add(new_setting)

            db.session.commit()
            app.logger.info("Tag management settings updated successfully")
            return jsonify({'success': True, 'message': 'Tag management settings updated successfully'})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving tag management settings: {str(e)}")
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

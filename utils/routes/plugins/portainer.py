# utils/routes/plugins/portainer.py

# Standard Imports
import json

# External Imports
from flask import Blueprint
from flask import current_app as app
from flask import jsonify
from flask import request
import requests

# Local Imports
from utils.database import db, Setting

# Create the blueprint
portainer_bp = Blueprint('portainer', __name__)

@portainer_bp.route('/get_portainer_config', methods=['GET'])
def get_portainer_config():
    """
    Retrieve the current Portainer configuration.

    This function fetches the Portainer URL, token, and enabled status from the database.

    Returns:
        JSON: A JSON response containing the Portainer configuration or an error message.
    """
    try:
        url_setting = Setting.query.filter_by(key='portainer_url').first()
        token_setting = Setting.query.filter_by(key='portainer_token').first()
        enabled_setting = Setting.query.filter_by(key='portainer_enabled').first()

        config = {
            'url': url_setting.value if url_setting else '',
            'token': token_setting.value if token_setting else '',
            'enabled': enabled_setting.value.lower() == 'true' if enabled_setting else False
        }

        app.logger.debug(f"Retrieved Portainer config: {config}")
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        app.logger.error(f"Error retrieving Portainer configuration: {str(e)}")
        return jsonify({'success': False, 'message': 'Error retrieving configuration'}), 500

@portainer_bp.route('/save_portainer_config', methods=['POST'])
def save_portainer_config():
    """
    Save Portainer configuration.

    This function saves the Portainer URL and access token to the database.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    data = request.json
    url = data.get('url')
    token = data.get('token')
    enabled = data.get('enabled', False)

    app.logger.debug(f"Saving Portainer config: URL={url}, Token={token[:5]}..., Enabled={enabled}")

    if not url or not token:
        return jsonify({'success': False, 'message': 'Missing URL or token'}), 400

    try:
        # Save URL
        url_setting = Setting.query.filter_by(key='portainer_url').first()
        if url_setting:
            url_setting.value = url
        else:
            url_setting = Setting(key='portainer_url', value=url)
            db.session.add(url_setting)

        # Save token
        token_setting = Setting.query.filter_by(key='portainer_token').first()
        if token_setting:
            token_setting.value = token
        else:
            token_setting = Setting(key='portainer_token', value=token)
            db.session.add(token_setting)

        # Save enabled state
        enabled_setting = Setting.query.filter_by(key='portainer_enabled').first()
        if enabled_setting:
            enabled_setting.value = str(enabled)
        else:
            enabled_setting = Setting(key='portainer_enabled', value=str(enabled))
            db.session.add(enabled_setting)

        db.session.commit()
        app.logger.info("Portainer configuration saved successfully")
        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving Portainer configuration: {str(e)}")
        return jsonify({'success': False, 'message': 'Error saving configuration'}), 500

@portainer_bp.route('/test_portainer_config', methods=['POST'])
def test_portainer_connection():
    """
    Test Portainer connection.

    This function tests the connection to Portainer using the provided URL and token.

    Returns:
        JSON: A JSON response indicating success or failure of the connection test.
    """
    data = request.json
    url = data.get('url')
    token = data.get('token')

    if not url or not token:
        return jsonify({'success': False, 'message': 'Missing URL or token'}), 400

    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'{url}/api/endpoints', headers=headers, timeout=10)
        response.raise_for_status()
        app.logger.info("Portainer connection test successful")
        return jsonify({'success': True, 'message': 'Connection successful'})
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error connecting to Portainer: {str(e)}")
        return jsonify({'success': False, 'message': f'Error connecting to Portainer: {str(e)}'}), 400
# utils/routes/imports.py

# Standard Imports
import json                                     # For parsing JSON data
import yaml                                     # For parsing YAML data

# External Imports
from flask import Blueprint                     # For creating a blueprint
from flask import jsonify                       # For returning JSON responses
from flask import render_template               # For rendering HTML templates
from flask import request                       # For handling HTTP requests
from flask import session                       # For storing session data

# Local Imports
from utils.database import db, Port             # For accessing the database models

# Create the blueprint
imports_bp = Blueprint('imports', __name__)

## Import Route ##

@imports_bp.route('/import', methods=['GET', 'POST'])
def import_data():
    """
    Handle data import requests.

    This route function manages both GET and POST requests for data import.
    For GET requests, it renders the import template.
    For POST requests, it processes the uploaded file based on the import type.

    Returns:
        For GET: Rendered HTML template
        For POST: JSON response indicating success or failure of the import
    """
    if request.method == 'POST':
        import_type = request.form.get('import_type')
        file_content = request.form.get('file_content')

        # Determine the import function based on the file type
        if import_type == 'Caddyfile':
            imported_data = import_caddyfile(file_content)
        elif import_type == 'JSON':
            imported_data = import_json(file_content)
        elif import_type == 'Docker-Compose':
            imported_data = import_docker_compose(file_content)
        else:
            return jsonify({'success': False, 'message': 'Unsupported import type'}), 400

        # Process the imported data and add to database
        for item in imported_data:
            port = Port(ip_address=item['ip'], port_number=item['port'], description=item['description'])
            db.session.add(port)
        db.session.commit()

        # Return a success response
        return jsonify({'success': True, 'message': f'Imported {len(imported_data)} entries'})

    # For GET requests, render the template
    return render_template('import.html', theme=session.get('theme', 'light'))

## Import Types ##

def import_caddyfile(content):
    """
    Parse a Caddyfile and extract port information.

    This function processes a Caddyfile content, extracting domain names and
    their associated reverse proxy configurations.

    Args:
        content (str): The content of the Caddyfile

    Returns:
        list: A list of dictionaries containing extracted port information
    """
    entries = []
    lines = content.split('\n')
    current_domain = None

    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            if '{' in line:
                # Extract domain name
                current_domain = line.split('{')[0].strip()
            elif 'reverse_proxy' in line:
                # Extract IP and port from reverse proxy directive
                parts = line.split()
                if len(parts) > 1:
                    ip_port = parts[-1]
                    ip, port = ip_port.split(':')
                    entries.append({
                        'ip': ip,
                        'port': int(port),
                        'description': current_domain
                    })

    return entries

def import_docker_compose(content):
    """
    Parse Docker Compose YAML content and extract port information.

    This function processes Docker Compose YAML content, extracting service names
    and their associated port mappings.

    Args:
        content (str): YAML-formatted string containing Docker Compose configuration

    Returns:
        list: A list of dictionaries containing extracted port information

    Raises:
        ValueError: If the YAML format is invalid
    """
    try:
        # Split the content into separate documents
        documents = content.split('version:')
        entries = []

        for doc in documents:
            if doc.strip():
                # Add back the 'version:' prefix and parse
                data = yaml.safe_load('version:' + doc)
                if isinstance(data, dict) and 'services' in data:
                    for service_name, service_config in data.get('services', {}).items():
                        ports = service_config.get('ports', [])
                        for port_mapping in ports:
                            if isinstance(port_mapping, str) and ':' in port_mapping:
                                host_port, container_port = port_mapping.split(':')
                                entries.append({
                                    'ip': '127.0.0.1',  # Assuming localhost, adjust if needed
                                    'port': int(host_port),
                                    'description': f"{service_name} - {container_port}"
                                })
        return entries
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid Docker-Compose YAML format: {str(e)}")

def import_json(content):
    """
    Parse JSON content and extract port information.

    This function processes JSON content, expecting a specific format
    for port entries.

    Args:
        content (str): JSON-formatted string containing port information

    Returns:
        list: A list of dictionaries containing extracted port information

    Raises:
        ValueError: If the JSON format is invalid
    """
    try:
        data = json.loads(content)
        entries = []
        for item in data:
            entries.append({
                'ip': item['ip'],
                'port': int(item['port']),
                'description': item.get('description', '')
            })
        return entries
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format")
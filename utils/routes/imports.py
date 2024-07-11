# utils/routes/imports.py

# Standard Imports
import json                                     # For parsing JSON data
import re                                       # For regular expressions
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
            port = Port(ip_address=item['ip'], port_number=item['port'], description=item['description'], port_protocol=item['port_protocol'])
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
                        'description': current_domain,
                        'port_protocol': 'tcp' # Assume TCP
                    })

    return entries

def import_docker_compose(content):
    """
    Parse Docker Compose YAML content and extract port information for non-database services.

    Args:
    content (str): YAML-formatted string containing Docker Compose configuration

    Returns:
    list: A list of dictionaries containing extracted port information

    Raises:
    ValueError: If the YAML format is invalid
    """
    try:
        # Parse the YAML content
        data = yaml.safe_load(content)
        entries = []

        if isinstance(data, dict):
            # Extract the services from the Docker Compose file
            services = data.get('services', {})

            # Iterate through each service in the Docker Compose file
            for service_name, service_config in services.items():
                # Skip database-related services
                if any(db in service_name.lower() for db in ['db', 'database', 'mysql', 'postgres', 'mariadb', 'mailhog']):
                    continue

                # Extract ports and image information for the service
                ports = service_config.get('ports', [])
                image = service_config.get('image', '')

                # Process each port mapping for the service
                for port_mapping in ports:
                    if isinstance(port_mapping, str):
                        try:
                            # Attempt to parse the port and protocol from the mapping
                            parsed_port, protocol = parse_port_and_protocol(port_mapping)

                            # Use the image name as description, or fall back to service name
                            description = image if image else service_name

                            # Add the parsed information to our entries list
                            entries.append({
                                'ip': '127.0.0.1',  # Assume localhost for all services
                                'port': parsed_port,
                                'description': description,
                                'port_protocol': protocol
                            })

                            # Log the successfully added entry
                            print(f"Added entry: IP: 127.0.0.1, Port: {parsed_port}, Protocol: {protocol}, Description: {description}")

                        except ValueError as e:
                            # Log a warning if we couldn't parse the port
                            print(f"Warning: {str(e)} for service {service_name}")

        # Log the total number of entries found
        print(f"Total entries found: {len(entries)}")
        return entries

    except yaml.YAMLError as e:
        # If the YAML is invalid, raise a ValueError with a descriptive message
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
                'ip': item['ip_address'],
                'port': int(item['port_number']),
                'description': item['description'],
                'port_protocol': item['port_protocol']
            })
        return entries
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format")

def parse_port_and_protocol(port_value):
    """
    Parse a port value and protocol, handling direct integers, environment variable expressions,
    and complex port mappings.

    Args:
        port_value (str): The port value to parse

    Returns:
        tuple: (int, str) The parsed port number and protocol ('tcp' or 'udp' if specified, else 'tcp')

    Raises:
        ValueError: If no valid port number can be found
    """
    # Remove any leading/trailing whitespace
    port_value = port_value.strip()

    # Check for explicit protocol specification
    if '/tcp' in port_value:
        protocol = 'tcp'
        port_value = port_value.replace('/tcp', '')
    elif '/udp' in port_value:
        protocol = 'udp'
        port_value = port_value.replace('/udp', '')
    else:
        protocol = 'tcp'  # Default to TCP if not explicitly specified

    # Find the last colon in the string
    last_colon_index = port_value.rfind(':')
    if last_colon_index != -1:
        # Look for numbers after the last colon
        after_colon = port_value[last_colon_index + 1:]
        number_match = re.search(r'(\d+)', after_colon)
        if number_match:
            return int(number_match.group(1)), protocol

    # If no number found after the last colon, check for other patterns
    # Check for complete environment variable syntax with default value
    complete_env_var_match = re.search(r':-(\d+)', port_value)
    if complete_env_var_match:
        return int(complete_env_var_match.group(1)), protocol

    # Check if it's a direct integer
    if port_value.isdigit():
        return int(port_value), protocol

    # If we can't parse it, raise an error
    raise ValueError(f"Unable to parse port value: {port_value}")
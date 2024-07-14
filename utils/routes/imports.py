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
    Handle data import requests for various file types.

    This function processes both GET and POST requests:
    - GET: Renders the import template.
    - POST: Processes the uploaded file based on the import type.

    The function supports importing from Caddyfile, JSON, and Docker-Compose formats.
    It checks for existing entries in the database to avoid duplicates and
    provides a summary of added and skipped entries.

    Returns:
        For GET: Rendered HTML template
        For POST: JSON response indicating success or failure of the import,
                    including counts of added and skipped entries.
    """
    if request.method == 'POST':
        # Extract import type and file content from the form data
        import_type = request.form.get('import_type')
        file_content = request.form.get('file_content')

        # Determine the appropriate import function based on the file type
        if import_type == 'Caddyfile':
            imported_data = import_caddyfile(file_content)
        elif import_type == 'JSON':
            imported_data = import_json(file_content)
        elif import_type == 'Docker-Compose':
            imported_data = import_docker_compose(file_content)
        else:
            # Return an error response for unsupported import types
            return jsonify({'success': False, 'message': 'Unsupported import type'}), 400

        # Initialize counters for added and skipped entries
        added_count = 0
        skipped_count = 0

        # Process each item in the imported data
        for item in imported_data:
            # Check if the entry already exists in the database
            existing_port = Port.query.filter_by(
                ip_address=item['ip'],
                port_number=item['port'],
                port_protocol=item['port_protocol']
            ).first()

            if existing_port is None:
                # If the entry doesn't exist, create a new Port object
                port = Port(
                    ip_address=item['ip'],
                    nickname=item['nickname'] if item['nickname'] is not None else None,
                    port_number=item['port'],
                    description=item['description'],
                    port_protocol=item['port_protocol']
                )
                # Add the new port to the database session
                db.session.add(port)
                added_count += 1
            else:
                # If the entry already exists, skip it
                skipped_count += 1

        # Commit all changes to the database
        db.session.commit()

        # Return a success response with summary of the import operation
        return jsonify({
            'success': True,
            'message': f'Imported {added_count} entries, skipped {skipped_count} existing entries'
        })

    # For GET requests, render the import template
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
                        'nickname': None,
                        'port': int(port),
                        'description': current_domain,
                        'port_protocol': 'TCP' # Assume TCP
                    })

    return entries

def parse_docker_compose(content):
    result = {}
    current_service = None
    current_image = None
    in_services = False
    in_ports = False
    indent_level = 0

    def add_port(image, port, protocol):
        image_parts = image.split('/')
        image_name = image_parts[-1].split(':')[0]
        if image_name not in result:
            result[image_name] = []
        result[image_name].append((port, protocol))

    lines = content.split('\n')
    for line_number, line in enumerate(lines, 1):
        original_line = line
        line = line.strip()
        current_indent = len(original_line) - len(original_line.lstrip())

        if line.startswith('services:'):
            in_services = True
            indent_level = current_indent
            continue

        if in_services and current_indent == indent_level + 2:
            if ':' in line and not line.startswith('-'):
                current_service = line.split(':')[0].strip()
                current_image = None
                in_ports = False

        if in_services and current_indent == indent_level + 4:
            if line.startswith('image:'):
                current_image = line.split('image:')[1].strip()
            if line.startswith('ports:'):
                in_ports = True
                continue

        if in_ports and current_indent == indent_level + 6:
            if line.startswith('-'):
                port_mapping = line.split('-')[1].strip().strip('"').strip("'")
                if ':' in port_mapping:
                    host_port = port_mapping.split(':')[0]
                    protocol = 'UDP' if '/udp' in port_mapping else 'TCP'
                    host_port = host_port.split('/')[0]  # Remove any protocol specification from the port
                    if current_image:
                        add_port(current_image, host_port, protocol)
        elif in_ports and current_indent <= indent_level + 4:
            in_ports = False

    return result

def convert_to_json(parsed_data):
    json_data = []
    for image, ports in parsed_data.items():
        for port, protocol in ports:
            json_entry = {
                "ip_address": "127.0.0.1",
                "nickname": None,
                "port_number": int(port),
                "description": image,
                "port_protocol": protocol,
                "order": 0
            }
            json_data.append(json_entry)
    return json_data

def import_docker_compose(content):
    try:
        parsed_data = parse_docker_compose(content)
        json_data = convert_to_json(parsed_data)

        # Convert the JSON data to a string
        json_content = json.dumps(json_data)

        # Use the existing import_json function to process the data
        entries = import_json(json_content)

        print(f"Total entries found: {len(entries)}")
        return entries

    except Exception as e:
        raise ValueError(f"Error parsing Docker-Compose file: {str(e)}")

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
                'nickname': item['nickname'],
                'port': int(item['port_number']),
                'description': item['description'],
                'port_protocol': item['port_protocol'].upper()
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
        tuple: (int, str) The parsed port number and protocol ('TCP' or 'UDP' if specified, else 'TCP')

    Raises:
        ValueError: If no valid port number can be found
    """
    # Remove any leading/trailing whitespace
    port_value = port_value.strip()

    # Check for explicit protocol specification
    if '/tcp' in port_value:
        protocol = 'TCP'
        port_value = port_value.replace('/tcp', '')
    elif '/udp' in port_value:
        protocol = 'UDP'
        port_value = port_value.replace('/udp', '')
    else:
        protocol = 'TCP'  # Default to TCP if not explicitly specified

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
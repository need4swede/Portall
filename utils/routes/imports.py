# utils/routes/imports.py

# Standard Imports
import json                                     # For parsing JSON data
import re                                       # For regular expressions
from urllib.parse import urlsplit               # For splitting Caddyfile port

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

# Import to Database

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
    The order is reset for each unique IP address.

    Returns:
        For GET: Rendered HTML template
        For POST: JSON response indicating success or failure of the import,
                  including counts of added and skipped entries.
    """
    if request.method == 'POST':
        import_type = request.form.get('import_type')
        file_content = request.form.get('file_content')

        if import_type == 'Caddyfile':
            imported_data = import_caddyfile(file_content)
        elif import_type == 'JSON':
            imported_data = import_json(file_content)
        elif import_type == 'Docker-Compose':
            imported_data = import_docker_compose(file_content)
        else:
            return jsonify({'success': False, 'message': 'Unsupported import type'}), 400

        added_count = 0
        skipped_count = 0
        ip_order_map = {}  # To keep track of the current order for each IP

        # Group imported data by IP address
        grouped_data = {}
        for item in imported_data:
            ip = item['ip']
            if ip not in grouped_data:
                grouped_data[ip] = []
            grouped_data[ip].append(item)

        # Store port-tag associations for later processing
        port_tag_associations = []

        for ip, items in grouped_data.items():
            # Get the maximum order for this IP
            max_order = db.session.query(db.func.max(Port.order)).filter(Port.ip_address == ip).scalar()
            current_order = max_order if max_order is not None else -1

            for item in items:
                existing_port = Port.query.filter_by(
                    ip_address=item['ip'],
                    port_number=item['port'],
                    port_protocol=item['port_protocol']
                ).first()

                if existing_port is None:
                    current_order += 1
                    port = Port(
                        ip_address=item['ip'],
                        nickname=item['nickname'] if item['nickname'] is not None else None,
                        port_number=item['port'],
                        description=item['description'],
                        port_protocol=item['port_protocol'],
                        order=current_order
                    )
                    db.session.add(port)
                    added_count += 1

                    # Store tag associations for later processing
                    if 'tags' in item:
                        port_tag_associations.append({
                            'port_data': item,
                            'tags': item['tags']
                        })
                else:
                    skipped_count += 1

        db.session.commit()

        # Process port-tag associations after ports are committed
        if port_tag_associations:
            process_port_tag_associations(port_tag_associations)

        return jsonify({
            'success': True,
            'message': f'Imported {added_count} entries, skipped {skipped_count} existing entries'
        })

    return render_template('import.html', theme=session.get('theme', 'light'))

# Import Types

def import_caddyfile(content):
    """
    Parse a Caddyfile and extract port information.

    This function processes a Caddyfile content, extracting domain names and
    their associated reverse proxy configurations. It supports both domain-block
    reverse_proxy directives and standalone reverse_proxy directives.

    Args:
        content (str): The content of the Caddyfile

    Returns:
        list: A list of dictionaries containing extracted port information
    """
    entries = []
    current_domain = None

    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue

        if line.endswith('{'):                    # domain block opener
            current_domain = line.split('{')[0].strip()
            continue

        if line == '}':                           # domain block closer
            current_domain = None
            continue

        if line.startswith('reverse_proxy'):
            # take everything after the directive, may contain multiple backends
            backends = line.split(None, 1)[1].split(',')
            for backend in backends:
                backend = backend.strip()

                # ensure we always have a scheme so urlsplit works
                if '://' not in backend:
                    backend_for_parse = f'//{backend}'
                else:
                    backend_for_parse = backend

                parsed = urlsplit(backend_for_parse)
                ip   = parsed.hostname
                port = parsed.port or 80           # fall-back when port is omitted

                if ip and port:
                    # Generate description based on context
                    if current_domain:
                        description = current_domain
                    else:
                        # For standalone reverse_proxy, use the backend as description
                        description = f"Reverse proxy to {backend}"

                    entries.append({
                        'ip'           : ip,
                        'nickname'     : None,
                        'port'         : int(port),
                        'description'  : description,
                        'port_protocol': 'TCP'
                    })

    return entries

def parse_docker_compose(content):
    """
    Parse Docker Compose file content and extract service information.

    Args:
        content (str): The content of the Docker Compose file

    Returns:
        dict: A dictionary with service names as keys and lists of (port, protocol) tuples as values
    """
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
    for line in lines:
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

def import_docker_compose(content):
    """
    Parse a Docker Compose file and extract port information.

    This function processes Docker Compose file content, extracting service names,
    ports, and protocols.

    Args:
        content (str): The content of the Docker Compose file

    Returns:
        list: A list of dictionaries containing extracted port information

    Raises:
        ValueError: If there's an error parsing the Docker Compose file
    """
    try:
        parsed_data = parse_docker_compose(content)

        entries = []
        for image, ports in parsed_data.items():
            for port, protocol in ports:
                entry = {
                    "ip": "127.0.0.1",
                    "nickname": None,
                    "port": int(port),
                    "description": image,
                    "port_protocol": protocol
                }
                entries.append(entry)

        print(f"Total entries found: {len(entries)}")
        return entries

    except Exception as e:
        raise ValueError(f"Error parsing Docker-Compose file: {str(e)}")

def import_json(content):
    """
    Parse JSON content and extract port information and settings.

    This function processes JSON content, supporting both the legacy format
    (a list of port entries) and the new comprehensive format (an object with 'ports',
    'tags', 'tagging_rules', and various settings properties).

    For the new format, it also updates all settings, imports tags and tagging rules,
    and restores port-tag associations.

    Args:
        content (str): JSON-formatted string containing port information and settings

    Returns:
        list: A list of dictionaries containing extracted port information

    Raises:
        ValueError: If the JSON format is invalid
    """
    try:
        data = json.loads(content)
        entries = []

        # Check if the data is in the new comprehensive format (version 3.0+)
        if isinstance(data, dict) and 'ports' in data:
            # Import general settings if they exist
            if 'general_settings' in data:
                import_general_settings(data['general_settings'])

            # Import port settings if they exist
            if 'port_settings' in data:
                import_port_settings(data['port_settings'])

            # Import port scanning settings if they exist
            if 'port_scanning_settings' in data:
                import_port_scanning_settings(data['port_scanning_settings'])

            # Import tagging settings if they exist
            if 'tagging_settings' in data:
                import_tagging_settings(data['tagging_settings'])

            # Import integration settings if they exist
            if 'docker' in data:
                import_settings('docker', data['docker'])
            if 'portainer' in data:
                import_settings('portainer', data['portainer'])
            if 'komodo' in data:
                import_settings('komodo', data['komodo'])

            # Import tags if they exist
            if 'tags' in data:
                import_tags(data['tags'])

            # Import tagging rules if they exist
            if 'tagging_rules' in data:
                import_tagging_rules(data['tagging_rules'])

            # Extract port entries from the 'ports' array
            for item in data['ports']:
                port_entry = {
                    'ip': item['ip_address'],
                    'nickname': item['nickname'],
                    'port': int(item['port_number']),
                    'description': item['description'],
                    'port_protocol': item['port_protocol'].upper()
                }

                # Store tags for later association (after ports are created)
                if 'tags' in item:
                    port_entry['tags'] = item['tags']

                entries.append(port_entry)
        else:
            # Legacy format (list of port entries)
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
    except KeyError as e:
        raise ValueError(f"Invalid JSON format: missing required field {e}")

def import_settings(service_type, settings):
    """
    Import settings for a service (docker, portainer, or komodo).

    This function updates the settings in the database based on the
    imported settings for the specified service.

    Args:
        service_type (str): The type of service ('docker', 'portainer', or 'komodo')
        settings (dict): The settings for the service
    """
    from utils.database import Setting

    # Map of settings keys for each service type
    settings_map = {
        'docker': {
            'enabled': 'docker_enabled',
            'path': 'docker_host',
            'auto_scan': 'docker_auto_detect',
            'scan_interval': 'docker_scan_interval'
        },
        'portainer': {
            'enabled': 'portainer_enabled',
            'path': 'portainer_url',
            'auto_scan': 'portainer_auto_detect',
            'api_key': 'portainer_api_key',
            'verify_ssl': 'portainer_verify_ssl',
            'scan_interval': 'portainer_scan_interval'
        },
        'komodo': {
            'enabled': 'komodo_enabled',
            'path': 'komodo_url',
            'auto_scan': 'komodo_auto_detect',
            'api_key': 'komodo_api_key',
            'api_secret': 'komodo_api_secret',
            'scan_interval': 'komodo_scan_interval'
        }
    }

    # Update settings in the database
    for setting_key, db_key in settings_map[service_type].items():
        if setting_key in settings:
            value = settings[setting_key]

            # Convert boolean values to strings
            if isinstance(value, bool):
                value = 'true' if value else 'false'

            # Update or create the setting
            setting = Setting.query.filter_by(key=db_key).first()
            if setting:
                setting.value = str(value)
            else:
                setting = Setting(key=db_key, value=str(value))
                db.session.add(setting)

# Import Helpers

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

def import_general_settings(settings):
    """
    Import general application settings.

    Args:
        settings (dict): The general settings to import
    """
    from utils.database import Setting

    for key, value in settings.items():
        if value is not None:
            setting = Setting.query.filter_by(key=key).first()
            if setting:
                setting.value = str(value)
            else:
                setting = Setting(key=key, value=str(value))
                db.session.add(setting)

def import_port_settings(settings):
    """
    Import port generation settings.

    Args:
        settings (dict): The port settings to import
    """
    from utils.database import Setting

    for key, value in settings.items():
        if value is not None and value != '':
            setting = Setting.query.filter_by(key=key).first()
            if setting:
                setting.value = str(value)
            else:
                setting = Setting(key=key, value=str(value))
                db.session.add(setting)

def import_port_scanning_settings(settings):
    """
    Import port scanning settings.

    Args:
        settings (dict): The port scanning settings to import
    """
    from utils.database import Setting

    for key, value in settings.items():
        if value is not None:
            setting = Setting.query.filter_by(key=key).first()
            if setting:
                setting.value = str(value)
            else:
                setting = Setting(key=key, value=str(value))
                db.session.add(setting)

def import_tagging_settings(settings):
    """
    Import tagging system settings.

    Args:
        settings (dict): The tagging settings to import
    """
    from utils.database import Setting

    for key, value in settings.items():
        if value is not None:
            setting = Setting.query.filter_by(key=key).first()
            if setting:
                setting.value = str(value)
            else:
                setting = Setting(key=key, value=str(value))
                db.session.add(setting)

def import_tags(tags_data):
    """
    Import tags from exported data.

    Args:
        tags_data (list): List of tag dictionaries to import
    """
    from utils.database import Tag

    for tag_data in tags_data:
        # Check if tag already exists by name
        existing_tag = Tag.query.filter_by(name=tag_data['name']).first()
        if not existing_tag:
            tag = Tag(
                name=tag_data['name'],
                color=tag_data.get('color', '#007bff'),
                description=tag_data.get('description')
            )
            db.session.add(tag)

def import_tagging_rules(rules_data):
    """
    Import tagging rules from exported data.

    Args:
        rules_data (list): List of tagging rule dictionaries to import
    """
    from utils.database import TaggingRule

    for rule_data in rules_data:
        # Check if rule already exists by name
        existing_rule = TaggingRule.query.filter_by(name=rule_data['name']).first()
        if not existing_rule:
            rule = TaggingRule(
                name=rule_data['name'],
                description=rule_data.get('description'),
                enabled=rule_data.get('enabled', True),
                auto_execute=rule_data.get('auto_execute', False),
                priority=rule_data.get('priority', 0),
                conditions=json.dumps(rule_data['conditions']),
                actions=json.dumps(rule_data['actions'])
            )
            db.session.add(rule)

def process_port_tag_associations(port_tag_associations):
    """
    Process port-tag associations after ports have been created.

    Args:
        port_tag_associations (list): List of dictionaries containing port data and associated tags
    """
    from utils.database import Tag, PortTag

    for association in port_tag_associations:
        port_data = association['port_data']
        tags = association['tags']

        # Find the port that was just created
        port = Port.query.filter_by(
            ip_address=port_data['ip'],
            port_number=port_data['port'],
            port_protocol=port_data['port_protocol']
        ).first()

        if port:
            for tag_data in tags:
                # Find the tag by name (tags should have been imported already)
                tag = Tag.query.filter_by(name=tag_data['name']).first()
                if tag:
                    # Check if association already exists
                    existing_association = PortTag.query.filter_by(
                        port_id=port.id,
                        tag_id=tag.id
                    ).first()

                    if not existing_association:
                        port_tag = PortTag(port_id=port.id, tag_id=tag.id)
                        db.session.add(port_tag)

    db.session.commit()

def get_max_order():
    """
    Retrieve the maximum order value from the Port table.

    Returns:
        int: The maximum order value, or -1 if the table is empty.
    """
    max_order = db.session.query(db.func.max(Port.order)).scalar()
    return max_order if max_order is not None else -1

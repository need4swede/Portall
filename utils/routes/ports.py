# utils/routes/ports.py

# Standard Imports
import json                                     # For parsing JSON data
import random                                   # For generating random ports

# External Imports
from flask import Blueprint                     # For creating a blueprint
from flask import current_app as app            # For accessing the Flask app
from flask import jsonify                       # For returning JSON responses
from flask import render_template               # For rendering HTML templates
from flask import request                       # For handling HTTP requests
from flask import session                       # For storing session data
from flask import url_for                       # For generating URLs
from sqlalchemy import func                     # For using SQL functions

# Local Imports
from utils.database import db, Port, Setting    # For accessing the database models

# Create the blueprint
ports_bp = Blueprint('ports', __name__)

## Ports ##

@ports_bp.route('/ports')
def ports():
    """
    Render the ports page.

    This function retrieves all ports from the database, organizes them by IP address,
    and renders the 'ports.html' template with the organized port data.

    If Docker integrations are enabled, it automatically checks for new ports to import
    or ports to remove.

    Returns:
        str: Rendered HTML template for the ports page.
    """
    # Check if Docker integrations are enabled
    docker_enabled = get_setting('docker_enabled', 'false').lower() == 'true'
    portainer_enabled = get_setting('portainer_enabled', 'false').lower() == 'true'

    # If Docker is enabled, automatically check for new ports
    if docker_enabled:
        try:
            # Import ports from direct Docker integration
            if get_setting('docker_auto_detect', 'false').lower() == 'true':
                import_from_docker_auto()
                app.logger.info("Automatic Docker port import completed")

            # If Portainer is also enabled, import from Portainer
            if portainer_enabled:
                import_from_portainer_auto()
                app.logger.info("Automatic Portainer port import completed")
        except Exception as e:
            app.logger.error(f"Error during automatic port import: {str(e)}")

    # Retrieve all ports, ordered by order
    ports = Port.query.order_by(Port.order).all()

    # Organize ports by IP address
    ports_by_ip = {}

    # For each port...
    for port in ports:

        # If the port's IP address is not in the dictionary...
        if port.ip_address not in ports_by_ip:
            # ...add the IP address to the dictionary with an empty list of ports, and set its nickname (if available)
            ports_by_ip[port.ip_address] = {'nickname': port.nickname, 'ports': []}

        # Add the port's details to the list of ports for the given IP address
        ports_by_ip[port.ip_address]['ports'].append({
            'id': port.id,                                      # Unique identifier for the port
            'port_number': port.port_number,                    # Port number
            'description': port.description,                    # Description, usually the service name
            'port_protocol': (port.port_protocol).upper(),      # Protocol, converted to uppercase
            'order': port.order,                                # Position of the port within its IP address group
            'is_immutable': port.is_immutable                   # Flag indicating if the port is immutable (Docker-imported)
        })

    # Get the current theme from the session
    theme = session.get('theme', 'light')

    # Render the template with the organized port data and theme
    return render_template('ports.html', ports_by_ip=ports_by_ip, theme=theme)

def get_setting(key, default):
    """Helper function to retrieve settings from the database."""
    setting = Setting.query.filter_by(key=key).first()
    value = setting.value if setting else str(default)
    return value if value != '' else str(default)

def import_from_docker_auto():
    """
    Automatically import containers and port mappings from Docker.
    This is a modified version of the scan_docker_ports function in docker.py
    that handles both adding new ports and removing ports that no longer exist.
    """
    import docker
    from utils.database import DockerService, DockerPort

    # Get Docker connection settings
    docker_host = get_setting('docker_host', 'unix:///var/run/docker.sock')

    try:
        # Initialize Docker client
        client = docker.from_env() if docker_host == 'unix:///var/run/docker.sock' else docker.DockerClient(base_url=docker_host)

        if client is None:
            app.logger.error("Docker client not available")
            return

        # Get all running containers
        containers = client.containers.list()

        added_ports = 0
        removed_ports = 0
        current_docker_ports = set()  # Track all ports from Docker

        # Get Docker host for identification in case of multiple Docker instances
        host_identifier = "local" if docker_host == 'unix:///var/run/docker.sock' else docker_host.replace('tcp://', '')

        for container in containers:
            # Process port mappings
            for container_port, host_bindings in container.ports.items():
                if host_bindings is None:
                    continue

                # Parse container port and protocol
                if '/' in container_port:
                    port_number, protocol = container_port.split('/')
                else:
                    port_number = container_port
                    protocol = 'tcp'

                for binding in host_bindings:
                    host_ip = binding.get('HostIp', '0.0.0.0')
                    if host_ip == '' or host_ip == '0.0.0.0' or host_ip == '::':
                        # Use a meaningful IP for Docker containers
                        # If it's a local Docker instance, use 127.0.0.1, otherwise use the host identifier
                        host_ip = '127.0.0.1' if host_identifier == 'local' else host_identifier

                    host_port = int(binding.get('HostPort', 0))

                    # Add to the set of current Docker ports
                    current_docker_ports.add((host_ip, host_port, protocol.upper()))

                    # Check if port already exists in Port table for this IP and port number
                    existing_port = Port.query.filter_by(
                        ip_address=host_ip,
                        port_number=host_port,
                        port_protocol=protocol.upper()
                    ).first()

                    # Add to Port table if it doesn't exist
                    if not existing_port:
                        # Get the max order for this IP
                        max_order = db.session.query(db.func.max(Port.order)).filter_by(
                            ip_address=host_ip
                        ).scalar() or 0

                        # Create new port entry with host identifier as nickname and container name as description
                        # Set source to 'docker' to identify it as a Docker port
                        # Set is_immutable to True for Docker ports
                        new_port = Port(
                            ip_address=host_ip,
                            nickname=host_identifier,  # Set the host identifier as the nickname
                            port_number=host_port,
                            description=container.name,
                            port_protocol=protocol.upper(),
                            order=max_order + 1,
                            source='docker',
                            is_immutable=True
                        )
                        db.session.add(new_port)
                        added_ports += 1

        # Find and remove ports that no longer exist in Docker
        # Only remove ports that were originally imported from Docker
        docker_ports_in_db = Port.query.filter(
            db.or_(
                Port.source == 'docker',
                Port.description.like(f"Docker ({host_identifier}):%"),  # For backward compatibility
                Port.description.like("[D] %")  # For backward compatibility
            )
        ).all()

        for port in docker_ports_in_db:
            port_key = (port.ip_address, port.port_number, port.port_protocol)
            if port_key not in current_docker_ports:
                db.session.delete(port)
                removed_ports += 1

        db.session.commit()
        app.logger.info(f"Automatic Docker import completed. Added {added_ports} new ports and removed {removed_ports} obsolete ports.")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error during automatic Docker port import: {str(e)}")

def import_from_portainer_auto():
    """
    Automatically import containers and port mappings from Portainer.
    This is a modified version of the import_from_portainer function in docker.py
    that handles both adding new ports and removing ports that no longer exist.
    """
    import requests

    portainer_url = get_setting('portainer_url', '')
    portainer_api_key = get_setting('portainer_api_key', '')

    if not portainer_url or not portainer_api_key:
        app.logger.warning("Portainer URL or API key not configured")
        return

    # Set up headers for Portainer API
    headers = {
        'X-API-Key': portainer_api_key
    }

    # Get endpoints (Docker environments)
    endpoints_response = requests.get(f"{portainer_url}/api/endpoints", headers=headers)
    if endpoints_response.status_code != 200:
        app.logger.error(f"Failed to get Portainer endpoints: {endpoints_response.text}")
        return

    endpoints = endpoints_response.json()
    if not endpoints:
        app.logger.warning("No endpoints found in Portainer")
        return

    added_ports = 0
    removed_ports = 0
    current_portainer_ports = set()  # Track all ports from Portainer

    # Extract server name from URL for identification in case of multiple Portainer instances
    server_name = portainer_url.replace('https://', '').replace('http://', '').split('/')[0]

    # Resolve domain name to IP address
    server_ip = None
    try:
        import socket
        server_ip = socket.gethostbyname(server_name)
        app.logger.info(f"Resolved {server_name} to IP: {server_ip}")
    except Exception as e:
        app.logger.warning(f"Could not resolve {server_name} to IP: {str(e)}")
        server_ip = server_name  # Fall back to using the domain name if resolution fails

    for endpoint in endpoints:
        endpoint_id = endpoint['Id']
        endpoint_name = endpoint.get('Name', f"Endpoint {endpoint_id}")

        # Get containers for this endpoint
        containers_response = requests.get(
            f"{portainer_url}/api/endpoints/{endpoint_id}/docker/containers/json",
            headers=headers
        )

        if containers_response.status_code != 200:
            app.logger.warning(f"Failed to get containers for endpoint {endpoint_id}: {containers_response.text}")
            continue

        containers = containers_response.json()

        for container in containers:
            # Process port mappings
            for port_mapping in container.get('Ports', []):
                if 'PublicPort' not in port_mapping:
                    continue

                host_ip = port_mapping.get('IP', '0.0.0.0')
                if host_ip == '' or host_ip == '0.0.0.0' or host_ip == '::':
                    # Use the resolved IP address instead of placeholder IPs
                    host_ip = server_ip

                host_port = port_mapping['PublicPort']
                container_port = port_mapping['PrivatePort']
                protocol = port_mapping['Type'].lower()

                # Add to the set of current Portainer ports
                current_portainer_ports.add((host_ip, host_port, protocol.upper()))

                # Check if port already exists in Port table for this IP and port number
                existing_port = Port.query.filter_by(
                    ip_address=host_ip,
                    port_number=host_port,
                    port_protocol=protocol.upper()
                ).first()

                # Add to Port table if it doesn't exist
                if not existing_port:
                    # Get the max order for this IP
                    max_order = db.session.query(db.func.max(Port.order)).filter_by(
                        ip_address=host_ip
                    ).scalar() or 0

                    container_name = container['Names'][0].lstrip('/') if container['Names'] else 'unknown'

                    # Create new port entry with server name as nickname and container name as description
                    # Set source to 'portainer' to identify it as a Portainer port
                    # Set is_immutable to True for Portainer ports
                    new_port = Port(
                        ip_address=host_ip,
                        nickname=server_name,  # Set the domain name as the nickname
                        port_number=host_port,
                        description=container_name,
                        port_protocol=protocol.upper(),
                        order=max_order + 1,
                        source='portainer',
                        is_immutable=True
                    )
                    db.session.add(new_port)
                    added_ports += 1

    # Find and remove ports that no longer exist in Portainer
    # Only remove ports that were originally imported from Portainer
    portainer_ports_in_db = Port.query.filter(
        db.or_(
            Port.source == 'portainer',
            Port.description.like(f"Portainer ({server_name}):%"),  # For backward compatibility
            Port.description.like("[P] %")  # For backward compatibility
        )
    ).all()

    for port in portainer_ports_in_db:
        port_key = (port.ip_address, port.port_number, port.port_protocol)
        if port_key not in current_portainer_ports:
            db.session.delete(port)
            removed_ports += 1

    db.session.commit()
    app.logger.info(f"Automatic Portainer import completed. Added {added_ports} new ports and removed {removed_ports} obsolete ports.")

@ports_bp.route('/add_port', methods=['POST'])
def add_port():
    """
    Add a new port for a given IP address.

    This function creates a new port entry in the database with the provided details.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    ip_address = request.form['ip']
    ip_nickname = request.form['ip_nickname'] or None
    port_number = request.form['port_number']
    description = request.form['description']
    protocol = request.form['protocol']

    try:
        max_order = db.session.query(db.func.max(Port.order)).filter_by(ip_address=ip_address).scalar() or 0
        port = Port(ip_address=ip_address, nickname=ip_nickname, port_number=port_number, description=description,
                    port_protocol=protocol, order=max_order + 1, source='manual')  # Set source to 'manual'
        db.session.add(port)
        db.session.commit()

        app.logger.info(f"Added new port {port_number} for IP: {ip_address} with order {port.order}")
        return jsonify({'success': True, 'message': 'Port added successfully', 'order': port.order})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding new port: {str(e)}")
        return jsonify({'success': False, 'message': 'Error adding new port'}), 500

@ports_bp.route('/edit_port', methods=['POST'])
def edit_port():
    """
    Edit an existing port for a given IP address.

    This function updates an existing port entry in the database with the provided details.
    For Docker integration ports, only the description can be changed.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    port_id = request.form.get('port_id')
    new_port_number = request.form.get('new_port_number')
    ip_address = request.form.get('ip')
    description = request.form.get('description')
    protocol = request.form.get('protocol')

    if not all([port_id, new_port_number, ip_address, description, protocol]):
        return jsonify({'success': False, 'message': 'Missing required data'}), 400

    try:
        port_entry = Port.query.get(port_id)
        if not port_entry:
            return jsonify({'success': False, 'message': 'Port entry not found'}), 404

        # Check if this port is immutable (imported from Docker integrations)
        if port_entry.is_immutable:
            # For Docker integration ports, only allow changing the description
            if int(new_port_number) != port_entry.port_number or protocol != port_entry.port_protocol:
                return jsonify({'success': False, 'message': 'Docker integration ports cannot have their port number or protocol changed'}), 403

            # Update only the description
            port_entry.description = description
            db.session.commit()
            return jsonify({'success': True, 'message': 'Port description updated successfully'})
        else:
            # For manually added ports, allow changing all fields
            # Check if the new port number and protocol combination already exists for this IP
            existing_port = Port.query.filter(Port.ip_address == ip_address,
                                            Port.port_number == new_port_number,
                                            Port.port_protocol == protocol,
                                            Port.id != port_id).first()
            if existing_port:
                return jsonify({'success': False, 'message': 'Port number and protocol combination already exists for this IP'}), 400

            port_entry.port_number = new_port_number
            port_entry.description = description
            port_entry.port_protocol = protocol
            db.session.commit()
            return jsonify({'success': True, 'message': 'Port updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@ports_bp.route('/delete_port', methods=['POST'])
def delete_port():
    """
    Delete a specific port for a given IP address.

    This function removes a port entry from the database based on the IP address and port number.
    Docker integration ports cannot be deleted.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    ip_address = request.form['ip']
    port_number = request.form['port_number']

    try:
        port = Port.query.filter_by(ip_address=ip_address, port_number=port_number).first()
        if port:
            # Check if this port is immutable (imported from Docker integrations)
            if port.is_immutable:
                return jsonify({'success': False, 'message': 'Docker integration ports cannot be deleted'}), 403

            # For manually added ports, delete them
            db.session.delete(port)
            db.session.commit()
            app.logger.info(f"Deleted port {port_number} for IP: {ip_address}")

            return jsonify({'success': True, 'message': 'Port deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Port not found'}), 404
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting port: {str(e)}")
        return jsonify({'success': False, 'message': 'Error deleting port'}), 500

@ports_bp.route('/generate_port_number', methods=['POST'])
def generate_port_number():
    """
    Generate a new port number for a given IP address without adding it to the database.

    This function receives IP address from a POST request and generates a new unique port number
    within the configured range based on the port generation settings.

    Returns:
        tuple: A tuple containing a JSON response and an HTTP status code.
               The JSON response includes the new port number and full URL on success,
               or an error message on failure.
    """
    # Extract data from the POST request
    ip_address = request.form['ip_address']
    protocol = request.form['protocol']
    app.logger.debug(f"Received request to generate port number for IP: {ip_address}, Protocol: {protocol}")

    def get_setting(key, default):
        """Helper function to retrieve settings from the database."""
        setting = Setting.query.filter_by(key=key).first()
        value = setting.value if setting else str(default)
        return value if value != '' else str(default)

    # Retrieve port generation settings
    port_start = int(get_setting('port_start', 1024))
    port_end = int(get_setting('port_end', 65535))
    port_exclude = get_setting('port_exclude', '')
    port_length = int(get_setting('port_length', 4))

    # Get existing ports for this IP
    existing_ports = set(p.port_number for p in Port.query.filter_by(ip_address=ip_address).all())

    # Create set of excluded ports
    excluded_ports = set()
    if port_exclude:
        excluded_ports.update(int(p.strip()) for p in port_exclude.split(',') if p.strip().isdigit())

    # Generate list of available ports based on settings
    available_ports = [p for p in range(port_start, port_end + 1)
                       if p not in excluded_ports and
                       (port_length == 0 or len(str(p)) == port_length)]

    # Count ports in use within the current range
    ports_in_use = sum(1 for p in existing_ports if p in available_ports)

    # Check if there are any available ports
    if not available_ports or all(p in existing_ports for p in available_ports):
        total_ports = len(available_ports)
        app.logger.error(f"No available ports for IP: {ip_address}. Used {ports_in_use} out of {total_ports} possible ports.")
        settings_url = url_for('routes.settings.settings', _external=True) + '#ports'
        error_message = (
            f"No available ports.\n"
            f"Used {ports_in_use} out of {total_ports} possible ports.\n"
            f"Consider expanding your port range in the <a href='{settings_url}'>settings</a>."
        )
        return jsonify({'error': error_message, 'html': True}), 400

    # Choose a new port randomly from available ports
    new_port = random.choice([p for p in available_ports if p not in existing_ports])

    # Return the new port and full URL without adding to database
    full_url = f"http://{ip_address}:{new_port}"
    return jsonify({'protocol': protocol, 'port': new_port, 'full_url': full_url})

@ports_bp.route('/generate_port', methods=['POST'])
def generate_port():
    """
    Generate a new port for a given IP address and add it to the database.

    This function receives IP address, nickname, and description from a POST request,
    generates a new unique port number within the configured range, and saves it to the database.

    Returns:
        tuple: A tuple containing a JSON response and an HTTP status code.
               The JSON response includes the new port number and full URL on success,
               or an error message on failure.
    """
    # Extract data from the POST request
    ip_address = request.form['ip_address']
    nickname = request.form['nickname']
    description = request.form['description']
    protocol = request.form['protocol']
    app.logger.debug(f"Received request to generate port for IP: {ip_address}, Nickname: {nickname}, Description: {description}, Protocol: {protocol}")

    def get_setting(key, default):
        """Helper function to retrieve settings from the database."""
        setting = Setting.query.filter_by(key=key).first()
        value = setting.value if setting else str(default)
        return value if value != '' else str(default)

    # Retrieve port generation settings
    port_start = int(get_setting('port_start', 1024))
    port_end = int(get_setting('port_end', 65535))
    port_exclude = get_setting('port_exclude', '')
    port_length = int(get_setting('port_length', 4))

    # Get existing ports for this IP
    existing_ports = set(p.port_number for p in Port.query.filter_by(ip_address=ip_address).all())

    # Create set of excluded ports
    excluded_ports = set()
    if port_exclude:
        excluded_ports.update(int(p.strip()) for p in port_exclude.split(',') if p.strip().isdigit())

    # Generate list of available ports based on settings
    available_ports = [p for p in range(port_start, port_end + 1)
                       if p not in excluded_ports and
                       (port_length == 0 or len(str(p)) == port_length)]

    # Count ports in use within the current range
    ports_in_use = sum(1 for p in existing_ports if p in available_ports)

    # Check if there are any available ports
    if not available_ports or all(p in existing_ports for p in available_ports):
        total_ports = len(available_ports)
        app.logger.error(f"No available ports for IP: {ip_address}. Used {ports_in_use} out of {total_ports} possible ports.")
        settings_url = url_for('routes.settings.settings', _external=True) + '#ports'
        error_message = (
            f"No available ports.\n"
            f"Used {ports_in_use} out of {total_ports} possible ports.\n"
            f"Consider expanding your port range in the <a href='{settings_url}'>settings</a>."
        )
        return jsonify({'error': error_message, 'html': True}), 400

    # Choose a new port randomly from available ports
    new_port = random.choice([p for p in available_ports if p not in existing_ports])

    # Create and save the new port
    try:
        last_port_position = db.session.query(func.max(Port.order)).filter_by(ip_address=ip_address).scalar() or -1
        port = Port(ip_address=ip_address, nickname=nickname, port_number=new_port, description=description,
                    port_protocol=protocol, order=last_port_position + 1, source='manual')
        db.session.add(port)
        db.session.commit()
        app.logger.info(f"Generated new port {new_port} for IP: {ip_address}")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving new port: {str(e)}")
        return jsonify({'error': 'Error saving new port'}), 500

    # Return the new port and full URL
    full_url = f"http://{ip_address}:{new_port}"
    return jsonify({'protocol': protocol, 'port': new_port, 'full_url': full_url})

@ports_bp.route('/move_port', methods=['POST'])
def move_port():
    """
    Move a port from one IP address to another.

    This function updates the IP address and order of a port based on the target IP.
    It also updates the nickname of the port to match the target IP's nickname.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
              On success, it includes the updated port details.
    """
    port_number = request.form.get('port_number')
    source_ip = request.form.get('source_ip')
    target_ip = request.form.get('target_ip')
    protocol = request.form.get('protocol', '').upper()  # Convert to uppercase

    app.logger.info(f"Moving {port_number} ({protocol}) from Source IP: {source_ip} to Target IP: {target_ip}")

    if not all([port_number, source_ip, target_ip, protocol]):
        app.logger.error(f"Missing required data. port_number: {port_number}, source_ip: {source_ip}, target_ip: {target_ip}, protocol: {protocol}")
        return jsonify({'success': False, 'message': 'Missing required data'}), 400

    try:
        # Check if the port already exists in the target IP with the same protocol
        existing_port = Port.query.filter_by(port_number=port_number, ip_address=target_ip, port_protocol=protocol).first()
        if existing_port:
            app.logger.info(f"Port {port_number} ({protocol}) already exists in target IP {target_ip}")
            return jsonify({'success': False, 'message': 'Port number and protocol combination already exists in the target IP group'}), 400

        # Log all ports for the source IP to check if the port exists
        all_source_ports = Port.query.filter_by(ip_address=source_ip).all()
        app.logger.info(f"All ports for source IP {source_ip}: {[(p.port_number, p.port_protocol) for p in all_source_ports]}")

        port = Port.query.filter_by(port_number=port_number, ip_address=source_ip, port_protocol=protocol).first()
        if port:
            app.logger.info(f"Found port to move: {port.id}, {port.port_number}, {port.ip_address}, {port.port_protocol}")

            # Check if this port is immutable (imported from Docker integrations)
            if port.is_immutable:
                app.logger.info(f"Port {port_number} ({protocol}) is immutable and cannot be moved")
                return jsonify({'success': False, 'message': 'This port cannot be moved because it\'s from a Docker integration'}), 403

            # Get the nickname of the target IP
            target_port = Port.query.filter_by(ip_address=target_ip).first()
            target_nickname = target_port.nickname if target_port else None

            # Update IP address and nickname
            port.ip_address = target_ip
            port.nickname = target_nickname

            # Update order
            max_order = db.session.query(db.func.max(Port.order)).filter_by(ip_address=target_ip).scalar() or 0
            port.order = max_order + 1

            db.session.commit()
            app.logger.info(f"Port moved successfully: {port.id}, {port.port_number}, {port.ip_address}, {port.port_protocol}, {port.nickname}")
            return jsonify({
                'success': True,
                'message': 'Port moved successfully',
                'port': {
                    'id': port.id,
                    'port_number': port.port_number,
                    'ip_address': port.ip_address,
                    'protocol': port.port_protocol,
                    'description': port.description,
                    'order': port.order,
                    'nickname': port.nickname
                }
            })
        else:
            app.logger.error(f"Port not found: {port_number}, {source_ip}, {protocol}")
            return jsonify({'success': False, 'message': 'Port not found'}), 404
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error moving port: {str(e)}")
        return jsonify({'success': False, 'message': f'Error moving port: {str(e)}'}), 500

@ports_bp.route('/update_port_order', methods=['POST'])
def update_port_order():
    """
    Update the order of ports for a specific IP address.

    This function receives a new order for ports of a given IP and updates the database accordingly.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    data = request.json
    ip = data.get('ip')
    port_order = data.get('port_order')

    if not ip or not port_order:
        return jsonify({'success': False, 'message': 'Missing IP or port order data'}), 400

    try:
        # Get the base order for this IP
        base_order = Port.query.filter_by(ip_address=ip).order_by(Port.order).first().order

        # Update the order for each port
        for index, port_number in enumerate(port_order):
            port = Port.query.filter_by(ip_address=ip, port_number=port_number).first()
            if port:
                port.order = base_order + index

        db.session.commit()
        return jsonify({'success': True, 'message': 'Port order updated successfully'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating port order: {str(e)}")
        return jsonify({'success': False, 'message': f'Error updating port order: {str(e)}'}), 500

@ports_bp.route('/change_port_number', methods=['POST'])
def change_port_number():
    """
    Change the port number for a given IP address.

    This function updates the port number for an existing port entry.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    ip = request.form['ip']
    old_port_number = request.form['old_port_number']
    new_port_number = request.form['new_port_number']

    try:
        port = Port.query.filter_by(ip_address=ip, port_number=old_port_number).first()
        if port:
            port.port_number = new_port_number
            db.session.commit()
            return jsonify({'success': True, 'message': 'Port number changed successfully'})
        else:
            return jsonify({'success': False, 'message': 'Port not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

## IP Addresses ##

@ports_bp.route('/edit_ip', methods=['POST'])
def edit_ip():
    """
    Edit an IP address and its associated nickname.

    This function updates the IP address and nickname for all ports associated with the old IP.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    old_ip = request.form['old_ip']
    new_ip = request.form['new_ip']
    new_nickname = request.form['new_nickname']

    try:
        # Find all ports associated with the old IP
        ports = Port.query.filter_by(ip_address=old_ip).all()

        if not ports:
            return jsonify({'success': False, 'message': 'No ports found for the given IP'}), 404

        # Update IP and nickname for all associated ports
        for port in ports:
            port.ip_address = new_ip
            port.nickname = new_nickname

        # Commit changes to the database
        db.session.commit()

        return jsonify({'success': True, 'message': 'IP updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating IP: {str(e)}'}), 500

@ports_bp.route('/add_ip', methods=['POST'])
def add_ip():
    """
    Add a new IP address with a default port.

    This function creates a new IP address entry with a default port (8080) and description ('Generic').

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    ip_address = request.form['ip']
    nickname = request.form.get('nickname', '')
    port_number = request.form.get('port_number', 8080)  # Default to 8080
    description = request.form.get('description', 'Generic')  # Default to 'Generic'
    protocol = request.form.get('protocol', 'TCP')  # Default to TCP

    try:
        # Check if the IP already exists
        existing_ip = Port.query.filter_by(ip_address=ip_address).first()
        if existing_ip:
            return jsonify({'success': False, 'message': 'IP address already exists'}), 400

        # Create a new port entry for the IP
        port = Port(
            ip_address=ip_address,
            nickname=nickname if nickname else None,
            port_number=port_number,
            description=description,
            port_protocol=protocol,
            order=0,  # First port for this IP
            source='manual'  # Set source to 'manual'
        )

        db.session.add(port)
        db.session.commit()

        app.logger.info(f"Added new IP {ip_address} with port {port_number}")
        return jsonify({'success': True, 'message': 'IP added successfully with default port'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding new IP: {str(e)}")
        return jsonify({'success': False, 'message': f'Error adding IP: {str(e)}'}), 500

@ports_bp.route('/delete_ip', methods=['POST'])
def delete_ip():
    """
    Delete an IP address and all its associated ports.

    This function removes an IP address and all ports assigned to it from the database.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    ip = request.form['ip']

    try:
        # Delete all ports associated with the IP
        ports = Port.query.filter_by(ip_address=ip).all()
        for port in ports:
            db.session.delete(port)

        # Commit changes to the database
        db.session.commit()

        return jsonify({'success': True, 'message': 'IP and all assigned ports deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting IP: {str(e)}'}), 500


@ports_bp.route('/update_ip_order', methods=['POST'])
def update_ip_order():
    """
    Update the order of IP address panels.

    This function receives a new order for IP addresses and updates the database accordingly.
    It uses a large step between IP orders to allow for many ports per IP.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    data = json.loads(request.data)
    ip_order = data.get('ip_order', [])

    try:
        # Update the order for each IP
        for index, ip in enumerate(ip_order):
            base_order = index * 1000  # Use a large step to allow for many ports per IP
            ports = Port.query.filter_by(ip_address=ip).order_by(Port.order).all()
            for i, port in enumerate(ports):
                port.order = base_order + i

        db.session.commit()
        return jsonify({'success': True, 'message': 'IP panel order updated successfully'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating IP panel order: {str(e)}")
        return jsonify({'success': False, 'message': f'Error updating IP panel order: {str(e)}'}), 500

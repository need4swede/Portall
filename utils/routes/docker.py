# utils/routes/docker.py

# Standard Imports
import json
import socket
import subprocess
import threading
import time
from datetime import datetime

# External Imports
from flask import Blueprint
from flask import current_app as app
from flask import jsonify, request, session
import docker

# Local Imports
from utils.database import db, Port, Setting, DockerService, DockerPort, PortScan

# Create the blueprint
docker_bp = Blueprint('docker', __name__)

# Initialize Docker client
docker_client = None

def get_docker_client():
    """
    Get or initialize the Docker client based on settings.

    Returns:
        docker.DockerClient: The Docker client instance.
    """
    global docker_client

    if docker_client is not None:
        return docker_client

    try:
        # Get Docker connection settings
        docker_host = get_setting('docker_host', 'unix:///var/run/docker.sock')
        docker_client = docker.from_env() if docker_host == 'unix:///var/run/docker.sock' else docker.DockerClient(base_url=docker_host)
        return docker_client
    except Exception as e:
        app.logger.error(f"Error initializing Docker client: {str(e)}")
        return None

def get_setting(key, default):
    """Helper function to retrieve settings from the database."""
    setting = Setting.query.filter_by(key=key).first()
    value = setting.value if setting else str(default)
    return value if value != '' else str(default)

@docker_bp.route('/docker/settings', methods=['GET', 'POST'])
def docker_settings():
    """
    Handle GET and POST requests for Docker integration settings.

    GET: Retrieve current Docker integration settings.
    POST: Update Docker integration settings.

    Returns:
        For GET: JSON object containing current Docker settings
        For POST: JSON object indicating success or failure of the update operation
    """
    if request.method == 'GET':
        try:
            docker_settings = {}
            for key in ['docker_enabled', 'docker_host', 'docker_auto_detect', 'docker_scan_interval',
                       'portainer_enabled', 'portainer_url', 'portainer_api_key', 'portainer_auto_detect', 'portainer_scan_interval',
                       'komodo_enabled', 'komodo_url', 'komodo_api_key', 'komodo_api_secret', 'komodo_auto_detect', 'komodo_scan_interval']:
                setting = Setting.query.filter_by(key=key).first()
                docker_settings[key] = setting.value if setting else ''

            return jsonify(docker_settings)
        except Exception as e:
            app.logger.error(f"Error retrieving Docker settings: {str(e)}")
            return jsonify({'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            # Extract Docker settings from form data
            docker_settings = {
                'docker_enabled': request.form.get('docker_enabled', 'false'),
                'docker_host': request.form.get('docker_host', 'unix:///var/run/docker.sock'),
                'docker_auto_detect': request.form.get('docker_auto_detect', 'false'),
                'docker_scan_interval': request.form.get('docker_scan_interval', '300'),
                'portainer_enabled': request.form.get('portainer_enabled', 'false'),
                'portainer_url': request.form.get('portainer_url', ''),
                'portainer_api_key': request.form.get('portainer_api_key', ''),
                'portainer_auto_detect': request.form.get('portainer_auto_detect', 'false'),
                'portainer_scan_interval': request.form.get('portainer_scan_interval', '300'),
                'komodo_enabled': request.form.get('komodo_enabled', 'false'),
                'komodo_url': request.form.get('komodo_url', ''),
                'komodo_api_key': request.form.get('komodo_api_key', ''),
                'komodo_api_secret': request.form.get('komodo_api_secret', ''),
                'komodo_auto_detect': request.form.get('komodo_auto_detect', 'false'),
                'komodo_scan_interval': request.form.get('komodo_scan_interval', '300')
            }

            # Update or create Docker settings in the database
            for key, value in docker_settings.items():
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                else:
                    new_setting = Setting(key=key, value=value)
                    db.session.add(new_setting)

            db.session.commit()

            # Reset Docker client to pick up new settings
            global docker_client
            docker_client = None

            return jsonify({'success': True, 'message': 'Docker settings updated successfully'})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving Docker settings: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/containers', methods=['GET'])
def get_containers():
    """
    Get a list of running Docker containers.

    Returns:
        JSON: A JSON response containing the list of containers.
    """
    try:
        client = get_docker_client()
        if client is None:
            return jsonify({'error': 'Docker client not available'}), 500

        containers = client.containers.list()
        container_list = []

        for container in containers:
            container_info = {
                'id': container.id,
                'name': container.name,
                'image': container.image.tags[0] if container.image.tags else container.image.id,
                'status': container.status,
                'ports': container.ports
            }
            container_list.append(container_info)

        return jsonify({'containers': container_list})
    except Exception as e:
        app.logger.error(f"Error getting Docker containers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@docker_bp.route('/docker/scan', methods=['POST'])
def scan_docker_ports():
    """
    Scan Docker containers for port mappings and add them to the database.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    try:
        client = get_docker_client()
        if client is None:
            return jsonify({'error': 'Docker client not available'}), 500

        # Get all running containers
        containers = client.containers.list()

        # Clear existing Docker services and ports
        DockerPort.query.delete()
        DockerService.query.delete()
        db.session.commit()

        added_ports = 0
        added_to_port_table = 0

        # Get Docker host for identification in case of multiple Docker instances
        docker_host = get_setting('docker_host', 'unix:///var/run/docker.sock')
        host_identifier = "local" if docker_host == 'unix:///var/run/docker.sock' else docker_host.replace('tcp://', '')

        for container in containers:
            # Add container to DockerService table
            service = DockerService(
                container_id=container.id,
                name=container.name,
                image=container.image.tags[0] if container.image.tags else container.image.id,
                status=container.status
            )
            db.session.add(service)
            db.session.flush()  # Flush to get the service ID

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

                    # Add port mapping to DockerPort table
                    docker_port = DockerPort(
                        service_id=service.id,
                        host_ip=host_ip,
                        host_port=host_port,
                        container_port=int(port_number),
                        protocol=protocol.upper()
                    )
                    db.session.add(docker_port)
                    added_ports += 1

                    # Check if port already exists in Port table for this IP and port number
                    existing_port = Port.query.filter_by(
                        ip_address=host_ip,
                        port_number=host_port,
                        port_protocol=protocol.upper()
                    ).first()

                    # Always add to Port table if it doesn't exist, regardless of auto-detect setting
                    if not existing_port:
                        # Get the max order for this IP
                        max_order = db.session.query(db.func.max(Port.order)).filter_by(
                            ip_address=host_ip
                        ).scalar() or 0

                        # Create new port entry with host identifier in description and as nickname
                        # Set is_immutable to True for Docker ports
                        new_port = Port(
                            ip_address=host_ip,
                            nickname=host_identifier,  # Set the host identifier as the nickname
                            port_number=host_port,
                            description=f"Docker ({host_identifier}): {container.name} ({port_number}/{protocol})",
                            port_protocol=protocol.upper(),
                            order=max_order + 1,
                            source='docker',
                            is_immutable=True
                        )
                        db.session.add(new_port)
                        added_to_port_table += 1

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Docker scan completed. Found {len(containers)} containers with {added_ports} port mappings and added {added_to_port_table} ports to the ports page.'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error scanning Docker ports: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/import_from_portainer', methods=['POST'])
def import_from_portainer():
    """
    Import containers and port mappings from Portainer.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    try:
        import requests

        portainer_url = get_setting('portainer_url', '')
        portainer_api_key = get_setting('portainer_api_key', '')

        if not portainer_url or not portainer_api_key:
            return jsonify({'error': 'Portainer URL or API key not configured'}), 400

        # Set up headers for Portainer API
        headers = {
            'X-API-Key': portainer_api_key
        }

        # Get endpoints (Docker environments)
        endpoints_response = requests.get(f"{portainer_url}/api/endpoints", headers=headers)
        if endpoints_response.status_code != 200:
            return jsonify({'error': f'Failed to get Portainer endpoints: {endpoints_response.text}'}), 500

        endpoints = endpoints_response.json()
        if not endpoints:
            return jsonify({'error': 'No endpoints found in Portainer'}), 404

        added_ports = 0
        added_to_port_table = 0

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
                # Add container to DockerService table
                service = DockerService(
                    container_id=container['Id'],
                    name=container['Names'][0].lstrip('/') if container['Names'] else 'unknown',
                    image=container['Image'],
                    status=container['State']
                )
                db.session.add(service)
                db.session.flush()  # Flush to get the service ID

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

                    # Add port mapping to DockerPort table
                    docker_port = DockerPort(
                        service_id=service.id,
                        host_ip=host_ip,
                        host_port=host_port,
                        container_port=container_port,
                        protocol=protocol.upper()
                    )
                    db.session.add(docker_port)
                    added_ports += 1

                    # Check if port already exists in Port table for this IP and port number
                    existing_port = Port.query.filter_by(
                        ip_address=host_ip,
                        port_number=host_port,
                        port_protocol=protocol.upper()
                    ).first()

                    # Always add to Port table if it doesn't exist, regardless of auto-detect setting
                    if not existing_port:
                        # Get the max order for this IP
                        max_order = db.session.query(db.func.max(Port.order)).filter_by(
                            ip_address=host_ip
                        ).scalar() or 0

                        # Create new port entry with server name in description and as nickname
                        # Set is_immutable to True for Portainer ports
                        new_port = Port(
                            ip_address=host_ip,
                            nickname=server_name,  # Set the domain name as the nickname
                            port_number=host_port,
                            description=service.name,
                            port_protocol=protocol.upper(),
                            order=max_order + 1,
                            source='portainer',
                            is_immutable=True
                        )
                        db.session.add(new_port)
                        added_to_port_table += 1

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Portainer import completed. Added {added_ports} port mappings and {added_to_port_table} ports to the ports page.'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error importing from Portainer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/import_from_komodo', methods=['POST'])
def import_from_komodo():
    """
    Import containers and port mappings from Komodo.
    Uses the proper API endpoints based on Komodo API documentation.

    For Komodo: All API operations use POST requests with a JSON body containing
    'type' and 'params' fields. Authentication is via X-Api-Key and X-Api-Secret headers.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    try:
        import requests
        import json
        import re  # For regex pattern matching

        komodo_url = get_setting('komodo_url', '')
        komodo_api_key = get_setting('komodo_api_key', '')
        komodo_api_secret = get_setting('komodo_api_secret', '')

        if not komodo_url or not komodo_api_key or not komodo_api_secret:
            return jsonify({'error': 'Komodo URL, API key, or API secret not configured'}), 400

        # Ensure the URL doesn't have a trailing slash
        komodo_url = komodo_url.rstrip('/')

        # Extract server name from URL for identification
        server_name = komodo_url.replace('https://', '').replace('http://', '').split('/')[0]

        # Remove port number from server_name if present (for the nickname)
        nickname = server_name
        if ':' in nickname:
            nickname = nickname.split(':')[0]

        # Special case for localhost
        if nickname.lower() == 'localhost' or nickname == '127.0.0.1':
            nickname = 'localhost'

        # Resolve domain name to IP address
        server_ip = None
        try:
            # Handle localhost specially
            if nickname.lower() == 'localhost' or server_name.lower().startswith('localhost:') or server_name == '127.0.0.1':
                server_ip = '127.0.0.1'
                app.logger.info(f"Using 127.0.0.1 for localhost")
            else:
                server_ip = socket.gethostbyname(nickname)
                app.logger.info(f"Resolved {nickname} to IP: {server_ip}")
        except Exception as e:
            app.logger.warning(f"Could not resolve {nickname} to IP: {str(e)}")
            # If we couldn't resolve and it's localhost, use 127.0.0.1
            if 'localhost' in nickname.lower():
                server_ip = '127.0.0.1'
            else:
                server_ip = nickname  # Fall back to using the domain name if resolution fails

        # Set up the API auth headers
        headers = {
            'X-Api-Key': komodo_api_key,
            'X-Api-Secret': komodo_api_secret,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Try the standard endpoint first
        try:
            app.logger.info(f"Trying POST {komodo_url}/read for ListStacks")
            response = requests.post(
                f"{komodo_url}/read",
                headers=headers,
                json={'type': 'ListStacks', 'params': {}},
                timeout=10
            )
            app.logger.info(f"Response: {response.status_code} - Content-Type: {response.headers.get('Content-Type')}")

            if response.status_code == 200:
                app.logger.info(f"Successful connection with {komodo_url}/read")
                stacks = response.json()
            else:
                app.logger.warning(f"Failed to get stacks from {komodo_url}/read: {response.status_code}")
                return jsonify({'error': f'Komodo API returned status {response.status_code}'}), 500

        except Exception as e:
            app.logger.error(f"Error connecting to Komodo API: {str(e)}")
            return jsonify({'error': f'Failed to connect to Komodo API: {str(e)}'}), 500

        # Debug log the response
        if not isinstance(stacks, list):
            app.logger.warning(f"Expected a list of stacks, but got {type(stacks)}")
            if isinstance(stacks, dict) and 'result' in stacks and isinstance(stacks['result'], list):
                stacks = stacks['result']
            else:
                app.logger.error(f"Unexpected response format: {json.dumps(stacks)}")
                return jsonify({'error': 'Unexpected response format from Komodo API'}), 500

        app.logger.info(f"Found {len(stacks)} stacks")

        # Process stacks and extract port mappings
        added_ports = 0
        added_to_port_table = 0

        # Clear existing Docker services and ports for this instance
        try:
            services_to_delete = db.session.query(DockerService.id).filter(
                DockerService.name.like(f"%{server_name}%")
            ).all()

            service_ids = [s.id for s in services_to_delete]

            if service_ids:
                DockerPort.query.filter(DockerPort.service_id.in_(service_ids)).delete(synchronize_session=False)
                DockerService.query.filter(DockerService.id.in_(service_ids)).delete(synchronize_session=False)
                db.session.commit()
                app.logger.info(f"Deleted {len(service_ids)} existing Komodo services")
        except Exception as e:
            app.logger.warning(f"Error clearing existing Komodo services: {str(e)}")
            db.session.rollback()

        for stack in stacks:
            app.logger.info(f"Processing stack: {json.dumps(stack, indent=2)}")

            # Get stack ID and name
            stack_id = stack.get('id')
            stack_name = stack.get('name', 'unknown')

            # Get detailed stack information
            try:
                get_stack_response = requests.post(
                    f"{komodo_url}/read",
                    headers=headers,
                    json={'type': 'GetStack', 'params': {'id': stack_id}},
                    timeout=10
                )

                if get_stack_response.status_code != 200:
                    app.logger.warning(f"Failed to get details for stack {stack_name}: {get_stack_response.status_code}")
                    continue

                stack_detail = get_stack_response.json()
                app.logger.info(f"Got stack details for {stack_name}")

                # Extract compose file content
                compose_content = None

                # Try to find the compose file in deployed_contents
                if 'info' in stack_detail and 'deployed_contents' in stack_detail['info']:
                    for content_file in stack_detail['info']['deployed_contents']:
                        if content_file.get('path') in ['compose.yaml', 'docker-compose.yaml', 'docker-compose.yml']:
                            compose_content = content_file.get('contents')
                            app.logger.info(f"Found compose file: {content_file['path']}")
                            break

                # If not found in deployed_contents, check file_contents in config
                if not compose_content and 'config' in stack_detail and 'file_contents' in stack_detail['config']:
                    compose_content = stack_detail['config']['file_contents']
                    app.logger.info("Using file_contents from config")

                if not compose_content:
                    app.logger.warning(f"No compose file content found for stack {stack_name}")
                    continue

                app.logger.info(f"Compose content for {stack_name}: {compose_content}")

                # Extract services from the stack
                services = []
                if 'info' in stack_detail and 'services' in stack_detail['info']:
                    services = stack_detail['info']['services']
                elif 'info' in stack_detail and 'deployed_services' in stack_detail['info']:
                    services = stack_detail['info']['deployed_services']

                app.logger.info(f"Found {len(services)} services in stack {stack_name}")

                # Process each service
                for service in services:
                    # Extract service info
                    service_name = service.get('service', service.get('service_name', service.get('container_name', 'unknown')))
                    service_image = service.get('image', 'unknown')

                    app.logger.info(f"Processing service: {service_name}, image: {service_image}")

                    # Add service to DockerService table
                    docker_service = DockerService(
                        container_id=f"komodo-{server_name}-{stack_name}-{service_name}",
                        name=f"{stack_name}/{service_name}",
                        image=service_image,
                        status="running"  # Assume running since we can see it
                    )
                    db.session.add(docker_service)
                    db.session.flush()  # Get the ID

                    # Parse the compose file to find port mappings for this service
                    # This is a simplified approach focusing on the most common format

                    # Split into lines for processing
                    lines = compose_content.split('\n')
                    in_service_section = False
                    in_ports_section = False
                    port_mappings = []

                    for line in lines:
                        line = line.rstrip()

                        # Check if we're in the right service section
                        if line.strip() == f"{service_name}:" or line.strip() == f"  {service_name}:":
                            in_service_section = True
                            in_ports_section = False
                            continue

                        # If we're in a service section and hit another top-level item, we're done with this service
                        if in_service_section and line.strip() and not line.startswith(' ') and line.strip().endswith(':'):
                            in_service_section = False
                            in_ports_section = False
                            continue

                        # If we're in the service section, look for ports
                        if in_service_section and "ports:" in line:
                            in_ports_section = True
                            continue

                        # If we're in the ports section, extract port mappings
                        if in_service_section and in_ports_section and line.strip().startswith('-'):
                            port_line = line.strip()[1:].strip()  # Remove dash and whitespace

                            # Handle quoted port mappings
                            if (port_line.startswith('"') and port_line.endswith('"')) or \
                               (port_line.startswith("'") and port_line.endswith("'")):
                                port_line = port_line[1:-1]

                            # Check for port:port format
                            if ':' in port_line:
                                port_mappings.append(port_line)
                                app.logger.info(f"Found port mapping: {port_line}")

                        # If we're in the ports section but hit a non-port line, we're done with ports
                        elif in_service_section and in_ports_section and line.strip() and not line.strip().startswith('-'):
                            in_ports_section = False

                    # If we didn't find port mappings in the compose file, try regex
                    if not port_mappings:
                        # Use regex to look for port mappings
                        service_pattern = re.compile(rf'{service_name}:\s*\n(?:.*\n)*?(?:\s+ports:\s*\n(?:\s+-\s+"?\'?([^"\'\n]+)"?\'?\s*\n)+)', re.MULTILINE)
                        service_match = service_pattern.search(compose_content)

                        if service_match:
                            # Extract all port lines
                            port_lines = re.findall(r'\s+-\s+"?\'?([^"\'\n]+)"?\'?', service_match.group(0))
                            for port_line in port_lines:
                                if ':' in port_line:
                                    port_mappings.append(port_line)
                                    app.logger.info(f"Found port mapping via regex: {port_line}")

                    # Process port mappings
                    for port_mapping in port_mappings:
                        # Parse port mapping (host:container or host:container/protocol)
                        parts = port_mapping.split(':')
                        if len(parts) != 2:
                            app.logger.warning(f"Invalid port mapping format: {port_mapping}")
                            continue

                        host_port = parts[0]
                        container_port_part = parts[1]

                        # Check for protocol specification
                        protocol = 'TCP'
                        if '/' in container_port_part:
                            container_port, protocol = container_port_part.split('/')
                            protocol = protocol.upper()
                        else:
                            container_port = container_port_part

                        try:
                            host_port_int = int(host_port)
                            container_port_int = int(container_port)
                        except ValueError:
                            app.logger.warning(f"Invalid port numbers: host={host_port}, container={container_port}")
                            continue

                        # Add port mapping to DockerPort table
                        docker_port = DockerPort(
                            service_id=docker_service.id,
                            host_ip=server_ip,
                            host_port=host_port_int,
                            container_port=container_port_int,
                            protocol=protocol
                        )
                        db.session.add(docker_port)
                        added_ports += 1

                        # Check if port already exists in Port table
                        existing_port = Port.query.filter_by(
                            ip_address=server_ip,
                            port_number=host_port_int,
                            port_protocol=protocol
                        ).first()

                        # Add to Port table if it doesn't exist
                        if not existing_port:
                            max_order = db.session.query(db.func.max(Port.order)).filter_by(
                                ip_address=server_ip
                            ).scalar() or 0

                            new_port = Port(
                                ip_address=server_ip,  # IP address
                                nickname=nickname,     # Human-readable name without port
                                port_number=host_port_int,
                                description=f"Komodo ({nickname}): {stack_name}/{service_name} ({container_port_int}/{protocol})",
                                port_protocol=protocol,
                                order=max_order + 1,
                                source='komodo',
                                is_immutable=True
                            )
                            db.session.add(new_port)
                            added_to_port_table += 1

            except Exception as e:
                app.logger.error(f"Error processing stack {stack_name}: {str(e)}")
                continue

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Komodo import completed. Added {added_ports} port mappings and {added_to_port_table} ports to the ports page.'
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error importing from Komodo: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/scan_ports', methods=['POST'])
def scan_ports():
    """
    Scan ports for a given IP address.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    try:
        data = request.json
        ip_address = data.get('ip_address')

        if not ip_address:
            return jsonify({'error': 'IP address is required'}), 400

        # Check if a scan is already in progress for this IP
        existing_scan = PortScan.query.filter_by(ip_address=ip_address).filter(
            PortScan.status.in_(['pending', 'in_progress'])
        ).first()

        if existing_scan:
            return jsonify({
                'success': False,
                'message': f'A scan is already {existing_scan.status} for {ip_address}'
            }), 409

        # Create a new scan entry
        scan = PortScan(ip_address=ip_address)
        db.session.add(scan)
        db.session.commit()

        # Start the scan in a background thread
        threading.Thread(target=run_port_scan, args=(ip_address, scan.id)).start()

        return jsonify({
            'success': True,
            'message': f'Port scan started for {ip_address}',
            'scan_id': scan.id
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error starting port scan: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/scan_status/<int:scan_id>', methods=['GET'])
def scan_status(scan_id):
    """
    Get the status of a port scan.

    Args:
        scan_id (int): The ID of the scan to check.

    Returns:
        JSON: A JSON response containing the scan status.
    """
    try:
        scan = PortScan.query.get(scan_id)
        if not scan:
            return jsonify({'error': 'Scan not found'}), 404

        return jsonify({
            'id': scan.id,
            'ip_address': scan.ip_address,
            'status': scan.status,
            'created_at': scan.created_at.isoformat() if scan.created_at else None,
            'completed_at': scan.completed_at.isoformat() if scan.completed_at else None
        })
    except Exception as e:
        app.logger.error(f"Error getting scan status: {str(e)}")
        return jsonify({'error': str(e)}), 500

def run_port_scan(ip_address, scan_id):
    """
    Run a port scan for the given IP address.

    Args:
        ip_address (str): The IP address to scan.
        scan_id (int): The ID of the scan entry.
    """
    try:
        with app.app_context():
            # Update scan status to in_progress
            scan = PortScan.query.get(scan_id)
            scan.status = 'in_progress'
            db.session.commit()

            # Get port range settings
            port_start = int(get_setting('port_start', '1024'))
            port_end = int(get_setting('port_end', '65535'))

            # Run nmap scan if available
            open_ports = []
            try:
                # Try to use nmap for faster scanning
                result = subprocess.run(
                    ['nmap', '-p', f'{port_start}-{port_end}', '-T4', '--open', ip_address],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )

                # Parse nmap output to get open ports
                for line in result.stdout.splitlines():
                    if '/tcp' in line and 'open' in line:
                        parts = line.split()
                        port_protocol = parts[0].split('/')
                        port = int(port_protocol[0])
                        protocol = port_protocol[1].upper()
                        open_ports.append((port, protocol))
            except (subprocess.SubprocessError, FileNotFoundError):
                # Fallback to Python socket scanning (much slower)
                app.logger.warning("Nmap not available, falling back to socket scanning")
                for port in range(port_start, port_end + 1):
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(0.1)
                            result = s.connect_ex((ip_address, port))
                            if result == 0:
                                open_ports.append((port, 'TCP'))
                    except:
                        pass

            # Add discovered ports to the database
            for port, protocol in open_ports:
                # Check if port already exists
                existing_port = Port.query.filter_by(
                    ip_address=ip_address,
                    port_number=port,
                    port_protocol=protocol
                ).first()

                if not existing_port:
                    # Get the max order for this IP
                    max_order = db.session.query(db.func.max(Port.order)).filter_by(
                        ip_address=ip_address
                    ).scalar() or 0

                    # Try to get service name
                    service_name = "Unknown"
                    try:
                        service = socket.getservbyport(port)
                        service_name = service.capitalize()
                    except:
                        pass

                    # Create new port entry
                    new_port = Port(
                        ip_address=ip_address,
                        port_number=port,
                        description=f"Discovered: {service_name}",
                        port_protocol=protocol,
                        order=max_order + 1
                    )
                    db.session.add(new_port)

            # Update scan status to completed
            scan.status = 'completed'
            scan.completed_at = datetime.utcnow()
            db.session.commit()

            app.logger.info(f"Port scan completed for {ip_address}. Found {len(open_ports)} open ports.")
    except Exception as e:
        app.logger.error(f"Error during port scan: {str(e)}")
        try:
            with app.app_context():
                scan = PortScan.query.get(scan_id)
                scan.status = 'failed'
                db.session.commit()
        except:
            pass

# Background thread for auto-scanning containers
def start_auto_scan_threads():
    """
    Start background threads for auto-scanning Docker, Portainer, and Komodo containers.
    """
    # Import Flask's current_app to get the actual app instance
    from flask import current_app as flask_app

    # Get the actual app instance, not the proxy
    flask_app_instance = flask_app._get_current_object()

    def docker_auto_scan_worker(app_instance):
        """Worker function that runs in a separate thread to auto-scan Docker containers.

        Args:
            app_instance: The Flask application instance.
        """
        import logging

        # Configure a separate logger for the worker thread
        worker_logger = logging.getLogger('docker_worker')
        worker_logger.setLevel(logging.INFO)

        while True:
            scan_interval = 300  # Default scan interval
            try:
                # Create a new application context for this thread
                with app_instance.app_context():
                    # Check if Docker is enabled and auto-detect is enabled
                    if get_setting('docker_enabled', 'false').lower() == 'true' and get_setting('docker_auto_detect', 'false').lower() == 'true':
                        worker_logger.info("Running automatic Docker container scan")
                        app_instance.logger.info("Running automatic Docker container scan")

                        client = get_docker_client()
                        if client is not None:
                            # Get Docker host for identification in case of multiple Docker instances
                            docker_host = get_setting('docker_host', 'unix:///var/run/docker.sock')
                            host_identifier = "local" if docker_host == 'unix:///var/run/docker.sock' else docker_host.replace('tcp://', '')

                            # Get all running containers
                            containers = client.containers.list()

                            # Process containers and their port mappings
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

                                        # Check if port already exists in Port table for this IP and port number
                                        existing_port = Port.query.filter_by(
                                            ip_address=host_ip,
                                            port_number=host_port,
                                            port_protocol=protocol.upper()
                                        ).first()

                                        # Always add to Port table if it doesn't exist, regardless of auto-detect setting
                                        if not existing_port:
                                            # Get the max order for this IP
                                            max_order = db.session.query(db.func.max(Port.order)).filter_by(
                                                ip_address=host_ip
                                            ).scalar() or 0

                                            # Create new port entry with host identifier in description and as nickname
                                            # Set is_immutable to True for Docker ports
                                            new_port = Port(
                                                ip_address=host_ip,
                                                nickname=host_identifier,  # Set the host identifier as the nickname
                                                port_number=host_port,
                                                description=f"Docker ({host_identifier}): {container.name} ({port_number}/{protocol})",
                                                port_protocol=protocol.upper(),
                                                order=max_order + 1,
                                                source='docker',
                                                is_immutable=True
                                            )
                                            db.session.add(new_port)

                            db.session.commit()

                    # Get scan interval inside app context
                    scan_interval = int(get_setting('docker_scan_interval', '300'))
            except Exception as e:
                # Log error using the worker logger
                worker_logger.error(f"Error in Docker auto-scan thread: {str(e)}")

                # Try to log with app logger if possible
                try:
                    with app_instance.app_context():
                        app_instance.logger.error(f"Error in Docker auto-scan thread: {str(e)}")
                except Exception:
                    pass

            # Sleep for the configured interval
            time.sleep(scan_interval)

    def portainer_auto_scan_worker(app_instance):
        """Worker function that runs in a separate thread to auto-scan Portainer containers.

        Args:
            app_instance: The Flask application instance.
        """
        import logging

        # Configure a separate logger for the worker thread
        worker_logger = logging.getLogger('portainer_worker')
        worker_logger.setLevel(logging.INFO)

        while True:
            scan_interval = 300  # Default scan interval
            try:
                # Create a new application context for this thread
                with app_instance.app_context():
                    # Check if Portainer is enabled and auto-detect is enabled
                    if get_setting('portainer_enabled', 'false').lower() == 'true' and get_setting('portainer_auto_detect', 'false').lower() == 'true':
                        worker_logger.info("Running automatic Portainer container scan")
                        app_instance.logger.info("Running automatic Portainer container scan")

                        # Call the import_from_portainer function directly
                        try:
                            # We need to call the function directly, not through the route
                            import requests

                            portainer_url = get_setting('portainer_url', '')
                            portainer_api_key = get_setting('portainer_api_key', '')

                            if not portainer_url or not portainer_api_key:
                                worker_logger.error("Portainer URL or API key not configured")
                                continue

                            # Set up headers for Portainer API
                            headers = {
                                'X-API-Key': portainer_api_key
                            }

                            # Get endpoints (Docker environments)
                            worker_logger.info(f"Requesting endpoints from {portainer_url}/api/endpoints")
                            endpoints_response = requests.get(f"{portainer_url}/api/endpoints", headers=headers)
                            worker_logger.info(f"Endpoints response status: {endpoints_response.status_code}")

                            if endpoints_response.status_code != 200:
                                worker_logger.error(f"Failed to get Portainer endpoints: {endpoints_response.text}")
                                continue

                            endpoints = endpoints_response.json()
                            worker_logger.info(f"Found {len(endpoints)} endpoints in Portainer")

                            if not endpoints:
                                worker_logger.error("No endpoints found in Portainer")
                                continue

                            added_ports = 0
                            added_to_port_table = 0

                            # Extract server name from URL for identification in case of multiple Portainer instances
                            server_name = portainer_url.replace('https://', '').replace('http://', '').split('/')[0]

                            # Resolve domain name to IP address
                            server_ip = None
                            try:
                                server_ip = socket.gethostbyname(server_name)
                                worker_logger.info(f"Resolved {server_name} to IP: {server_ip}")
                            except Exception as e:
                                worker_logger.warning(f"Could not resolve {server_name} to IP: {str(e)}")
                                server_ip = server_name  # Fall back to using the domain name if resolution fails

                            for endpoint in endpoints:
                                endpoint_id = endpoint['Id']
                                endpoint_name = endpoint.get('Name', f"Endpoint {endpoint_id}")

                                # Get containers for this endpoint
                                worker_logger.info(f"Requesting containers from endpoint {endpoint_id} ({endpoint_name})")
                                containers_response = requests.get(
                                    f"{portainer_url}/api/endpoints/{endpoint_id}/docker/containers/json",
                                    headers=headers
                                )
                                worker_logger.info(f"Containers response status: {containers_response.status_code}")

                                if containers_response.status_code != 200:
                                    worker_logger.warning(f"Failed to get containers for endpoint {endpoint_id}: {containers_response.text}")
                                    continue

                                containers = containers_response.json()
                                worker_logger.info(f"Found {len(containers)} containers in endpoint {endpoint_id}")

                                for container in containers:
                                    # Add container to DockerService table
                                    service = DockerService(
                                        container_id=container['Id'],
                                        name=container['Names'][0].lstrip('/') if container['Names'] else 'unknown',
                                        image=container['Image'],
                                        status=container['State']
                                    )
                                    db.session.add(service)
                                    db.session.flush()  # Flush to get the service ID

                                    # Process port mappings
                                    container_ports = container.get('Ports', [])
                                    worker_logger.info(f"Container {container['Names'][0] if container['Names'] else 'unknown'} has {len(container_ports)} port mappings")

                                    for port_mapping in container_ports:
                                        if 'PublicPort' not in port_mapping:
                                            worker_logger.info(f"Skipping port mapping without PublicPort: {port_mapping}")
                                            continue

                                        host_ip = port_mapping.get('IP', '0.0.0.0')
                                        if host_ip == '' or host_ip == '0.0.0.0' or host_ip == '::':
                                            # Use the resolved IP address instead of placeholder IPs
                                            host_ip = server_ip

                                        host_port = port_mapping['PublicPort']
                                        container_port = port_mapping['PrivatePort']
                                        protocol = port_mapping['Type'].lower()

                                        # Add port mapping to DockerPort table
                                        docker_port = DockerPort(
                                            service_id=service.id,
                                            host_ip=host_ip,
                                            host_port=host_port,
                                            container_port=container_port,
                                            protocol=protocol.upper()
                                        )
                                        db.session.add(docker_port)
                                        added_ports += 1
                                        worker_logger.info(f"Added port mapping: {host_ip}:{host_port} -> {container_port}/{protocol}")

                                        # Check if port already exists in Port table for this IP and port number
                                        existing_port = Port.query.filter_by(
                                            ip_address=host_ip,
                                            port_number=host_port,
                                            port_protocol=protocol.upper()
                                        ).first()

                                        # Always add to Port table if it doesn't exist, regardless of auto-detect setting
                                        if not existing_port:
                                            # Get the max order for this IP
                                            max_order = db.session.query(db.func.max(Port.order)).filter_by(
                                                ip_address=host_ip
                                            ).scalar() or 0

                                            # Create new port entry with server name in description and as nickname
                                            # Set is_immutable to True for Portainer ports
                                            new_port = Port(
                                                ip_address=host_ip,
                                                nickname=server_name,  # Set the domain name as the nickname
                                                port_number=host_port,
                                                description=service.name,
                                                port_protocol=protocol.upper(),
                                                order=max_order + 1,
                                                source='portainer',
                                                is_immutable=True
                                            )
                                            db.session.add(new_port)
                                            added_to_port_table += 1
                                            worker_logger.info(f"Added new port to Port table: {host_ip}:{host_port}/{protocol.upper()} - {service.name}")
                                        else:
                                            worker_logger.info(f"Port already exists in Port table: {host_ip}:{host_port}/{protocol.upper()}")

                            try:
                                db.session.commit()
                                worker_logger.info(f"Portainer auto-scan completed successfully. Added {added_ports} port mappings and {added_to_port_table} ports.")
                            except Exception as e:
                                db.session.rollback()
                                worker_logger.error(f"Error committing changes to database: {str(e)}")
                        except Exception as e:
                            worker_logger.error(f"Error in Portainer auto-scan: {str(e)}")

                    # Get scan interval inside app context
                    scan_interval = int(get_setting('portainer_scan_interval', '300'))
            except Exception as e:
                # Log error using the worker logger
                worker_logger.error(f"Error in Portainer auto-scan thread: {str(e)}")

                # Try to log with app logger if possible
                try:
                    with app_instance.app_context():
                        app_instance.logger.error(f"Error in Portainer auto-scan thread: {str(e)}")
                except Exception:
                    pass

            # Sleep for the configured interval
            time.sleep(scan_interval)

    def komodo_auto_scan_worker(app_instance):
        """Worker function that runs in a separate thread to auto-scan Komodo containers.

        Args:
            app_instance: The Flask application instance.
        """
        import logging

        # Configure a separate logger for the worker thread
        worker_logger = logging.getLogger('komodo_worker')
        worker_logger.setLevel(logging.INFO)

        while True:
            scan_interval = 300  # Default scan interval
            try:
                # Create a new application context for this thread
                with app_instance.app_context():
                    # Check if Komodo is enabled and auto-detect is enabled
                    if get_setting('komodo_enabled', 'false').lower() == 'true' and get_setting('komodo_auto_detect', 'false').lower() == 'true':
                        worker_logger.info("Running automatic Komodo container scan")
                        app_instance.logger.info("Running automatic Komodo container scan")

                        # Call the import_from_komodo function directly
                        try:
                            # We need to implement the Komodo import logic directly here
                            import requests
                            import json
                            import re  # For regex pattern matching

                            komodo_url = get_setting('komodo_url', '')
                            komodo_api_key = get_setting('komodo_api_key', '')
                            komodo_api_secret = get_setting('komodo_api_secret', '')

                            if not komodo_url or not komodo_api_key or not komodo_api_secret:
                                worker_logger.error("Komodo URL, API key, or API secret not configured")
                                continue

                            # Ensure the URL doesn't have a trailing slash
                            komodo_url = komodo_url.rstrip('/')

                            # Extract server name from URL for identification
                            server_name = komodo_url.replace('https://', '').replace('http://', '').split('/')[0]

                            # Remove port number from server_name if present (for the nickname)
                            nickname = server_name
                            if ':' in nickname:
                                nickname = nickname.split(':')[0]

                            # Special case for localhost
                            if nickname.lower() == 'localhost' or nickname == '127.0.0.1':
                                nickname = 'localhost'

                            # Resolve domain name to IP address
                            server_ip = None
                            try:
                                # Handle localhost specially
                                if nickname.lower() == 'localhost' or server_name.lower().startswith('localhost:') or server_name == '127.0.0.1':
                                    server_ip = '127.0.0.1'
                                    worker_logger.info(f"Using 127.0.0.1 for localhost")
                                else:
                                    server_ip = socket.gethostbyname(nickname)
                                    worker_logger.info(f"Resolved {nickname} to IP: {server_ip}")
                            except Exception as e:
                                worker_logger.warning(f"Could not resolve {nickname} to IP: {str(e)}")
                                # If we couldn't resolve and it's localhost, use 127.0.0.1
                                if 'localhost' in nickname.lower():
                                    server_ip = '127.0.0.1'
                                else:
                                    server_ip = nickname  # Fall back to using the domain name if resolution fails

                            # Set up the API auth headers
                            headers = {
                                'X-Api-Key': komodo_api_key,
                                'X-Api-Secret': komodo_api_secret,
                                'Content-Type': 'application/json',
                                'Accept': 'application/json'
                            }

                            # Try the standard endpoint first
                            try:
                                worker_logger.info(f"Trying POST {komodo_url}/read for ListStacks")
                                response = requests.post(
                                    f"{komodo_url}/read",
                                    headers=headers,
                                    json={'type': 'ListStacks', 'params': {}},
                                    timeout=10
                                )
                                worker_logger.info(f"Response: {response.status_code} - Content-Type: {response.headers.get('Content-Type')}")

                                if response.status_code == 200:
                                    worker_logger.info(f"Successful connection with {komodo_url}/read")
                                    stacks = response.json()
                                else:
                                    worker_logger.warning(f"Failed to get stacks from {komodo_url}/read: {response.status_code}")
                                    continue

                            except Exception as e:
                                worker_logger.error(f"Error connecting to Komodo API: {str(e)}")
                                continue

                            # Debug log the response
                            if not isinstance(stacks, list):
                                worker_logger.warning(f"Expected a list of stacks, but got {type(stacks)}")
                                if isinstance(stacks, dict) and 'result' in stacks and isinstance(stacks['result'], list):
                                    stacks = stacks['result']
                                else:
                                    worker_logger.error(f"Unexpected response format: {json.dumps(stacks)}")
                                    continue

                            worker_logger.info(f"Found {len(stacks)} stacks")

                            # Process stacks and extract port mappings
                            added_ports = 0
                            added_to_port_table = 0

                            # Clear existing Docker services and ports for this instance
                            try:
                                services_to_delete = db.session.query(DockerService.id).filter(
                                    DockerService.name.like(f"%{server_name}%")
                                ).all()

                                service_ids = [s.id for s in services_to_delete]

                                if service_ids:
                                    DockerPort.query.filter(DockerPort.service_id.in_(service_ids)).delete(synchronize_session=False)
                                    DockerService.query.filter(DockerService.id.in_(service_ids)).delete(synchronize_session=False)
                                    db.session.commit()
                                    worker_logger.info(f"Deleted {len(service_ids)} existing Komodo services")
                            except Exception as e:
                                worker_logger.warning(f"Error clearing existing Komodo services: {str(e)}")
                                db.session.rollback()

                            for stack in stacks:
                                worker_logger.info(f"Processing stack: {json.dumps(stack, indent=2)}")

                                # Get stack ID and name
                                stack_id = stack.get('id')
                                stack_name = stack.get('name', 'unknown')

                                # Get detailed stack information
                                try:
                                    get_stack_response = requests.post(
                                        f"{komodo_url}/read",
                                        headers=headers,
                                        json={'type': 'GetStack', 'params': {'id': stack_id}},
                                        timeout=10
                                    )

                                    if get_stack_response.status_code != 200:
                                        worker_logger.warning(f"Failed to get details for stack {stack_name}: {get_stack_response.status_code}")
                                        continue

                                    stack_detail = get_stack_response.json()
                                    worker_logger.info(f"Got stack details for {stack_name}")

                                    # Extract compose file content
                                    compose_content = None

                                    # Try to find the compose file in deployed_contents
                                    if 'info' in stack_detail and 'deployed_contents' in stack_detail['info']:
                                        for content_file in stack_detail['info']['deployed_contents']:
                                            if content_file.get('path') in ['compose.yaml', 'docker-compose.yaml', 'docker-compose.yml']:
                                                compose_content = content_file.get('contents')
                                                worker_logger.info(f"Found compose file: {content_file['path']}")
                                                break

                                    # If not found in deployed_contents, check file_contents in config
                                    if not compose_content and 'config' in stack_detail and 'file_contents' in stack_detail['config']:
                                        compose_content = stack_detail['config']['file_contents']
                                        worker_logger.info("Using file_contents from config")

                                    if not compose_content:
                                        worker_logger.warning(f"No compose file content found for stack {stack_name}")
                                        continue

                                    worker_logger.info(f"Compose content for {stack_name}: {compose_content}")

                                    # Extract services from the stack
                                    services = []
                                    if 'info' in stack_detail and 'services' in stack_detail['info']:
                                        services = stack_detail['info']['services']
                                    elif 'info' in stack_detail and 'deployed_services' in stack_detail['info']:
                                        services = stack_detail['info']['deployed_services']

                                    worker_logger.info(f"Found {len(services)} services in stack {stack_name}")

                                    # Process each service
                                    for service in services:
                                        # Extract service info
                                        service_name = service.get('service', service.get('service_name', service.get('container_name', 'unknown')))
                                        service_image = service.get('image', 'unknown')

                                        worker_logger.info(f"Processing service: {service_name}, image: {service_image}")

                                        # Add service to DockerService table
                                        docker_service = DockerService(
                                            container_id=f"komodo-{server_name}-{stack_name}-{service_name}",
                                            name=f"{stack_name}/{service_name}",
                                            image=service_image,
                                            status="running"  # Assume running since we can see it
                                        )
                                        db.session.add(docker_service)
                                        db.session.flush()  # Get the ID

                                        # Parse the compose file to find port mappings for this service
                                        # This is a simplified approach focusing on the most common format

                                        # Split into lines for processing
                                        lines = compose_content.split('\n')
                                        in_service_section = False
                                        in_ports_section = False
                                        port_mappings = []

                                        for line in lines:
                                            line = line.rstrip()

                                            # Check if we're in the right service section
                                            if line.strip() == f"{service_name}:" or line.strip() == f"  {service_name}:":
                                                in_service_section = True
                                                in_ports_section = False
                                                continue

                                            # If we're in a service section and hit another top-level item, we're done with this service
                                            if in_service_section and line.strip() and not line.startswith(' ') and line.strip().endswith(':'):
                                                in_service_section = False
                                                in_ports_section = False
                                                continue

                                            # If we're in the service section, look for ports
                                            if in_service_section and "ports:" in line:
                                                in_ports_section = True
                                                continue

                                            # If we're in the ports section, extract port mappings
                                            if in_service_section and in_ports_section and line.strip().startswith('-'):
                                                port_line = line.strip()[1:].strip()  # Remove dash and whitespace

                                                # Handle quoted port mappings
                                                if (port_line.startswith('"') and port_line.endswith('"')) or \
                                                   (port_line.startswith("'") and port_line.endswith("'")):
                                                    port_line = port_line[1:-1]

                                                # Check for port:port format
                                                if ':' in port_line:
                                                    port_mappings.append(port_line)
                                                    worker_logger.info(f"Found port mapping: {port_line}")

                                            # If we're in the ports section but hit a non-port line, we're done with ports
                                            elif in_service_section and in_ports_section and line.strip() and not line.strip().startswith('-'):
                                                in_ports_section = False

                                        # If we didn't find port mappings in the compose file, try regex
                                        if not port_mappings:
                                            # Use regex to look for port mappings
                                            service_pattern = re.compile(rf'{service_name}:\s*\n(?:.*\n)*?(?:\s+ports:\s*\n(?:\s+-\s+"?\'?([^"\'\n]+)"?\'?\s*\n)+)', re.MULTILINE)
                                            service_match = service_pattern.search(compose_content)

                                            if service_match:
                                                # Extract all port lines
                                                port_lines = re.findall(r'\s+-\s+"?\'?([^"\'\n]+)"?\'?', service_match.group(0))
                                                for port_line in port_lines:
                                                    if ':' in port_line:
                                                        port_mappings.append(port_line)
                                                        worker_logger.info(f"Found port mapping via regex: {port_line}")

                                        # Process port mappings
                                        for port_mapping in port_mappings:
                                            # Parse port mapping (host:container or host:container/protocol)
                                            parts = port_mapping.split(':')
                                            if len(parts) != 2:
                                                worker_logger.warning(f"Invalid port mapping format: {port_mapping}")
                                                continue

                                            host_port = parts[0]
                                            container_port_part = parts[1]

                                            # Check for protocol specification
                                            protocol = 'TCP'
                                            if '/' in container_port_part:
                                                container_port, protocol = container_port_part.split('/')
                                                protocol = protocol.upper()
                                            else:
                                                container_port = container_port_part

                                            try:
                                                host_port_int = int(host_port)
                                                container_port_int = int(container_port)
                                            except ValueError:
                                                worker_logger.warning(f"Invalid port numbers: host={host_port}, container={container_port}")
                                                continue

                                            # Add port mapping to DockerPort table
                                            docker_port = DockerPort(
                                                service_id=docker_service.id,
                                                host_ip=server_ip,
                                                host_port=host_port_int,
                                                container_port=container_port_int,
                                                protocol=protocol
                                            )
                                            db.session.add(docker_port)
                                            added_ports += 1

                                            # Check if port already exists in Port table
                                            existing_port = Port.query.filter_by(
                                                ip_address=server_ip,
                                                port_number=host_port_int,
                                                port_protocol=protocol
                                            ).first()

                                            # Add to Port table if it doesn't exist
                                            if not existing_port:
                                                max_order = db.session.query(db.func.max(Port.order)).filter_by(
                                                    ip_address=server_ip
                                                ).scalar() or 0

                                                new_port = Port(
                                                    ip_address=server_ip,  # IP address
                                                    nickname=nickname,     # Human-readable name without port
                                                    port_number=host_port_int,
                                                    description=f"Komodo ({nickname}): {stack_name}/{service_name} ({container_port_int}/{protocol})",
                                                    port_protocol=protocol,
                                                    order=max_order + 1,
                                                    source='komodo',
                                                    is_immutable=True
                                                )
                                                db.session.add(new_port)
                                                added_to_port_table += 1

                                except Exception as e:
                                    worker_logger.error(f"Error processing stack {stack_name}: {str(e)}")
                                    continue

                            db.session.commit()
                            worker_logger.info(f"Komodo auto-scan completed successfully. Added {added_ports} port mappings and {added_to_port_table} ports.")
                        except Exception as e:
                            worker_logger.error(f"Error in Komodo auto-scan: {str(e)}")

                    # Get scan interval inside app context
                    scan_interval = int(get_setting('komodo_scan_interval', '300'))
            except Exception as e:
                # Log error using the worker logger
                worker_logger.error(f"Error in Komodo auto-scan thread: {str(e)}")

                # Try to log with app logger if possible
                try:
                    with app_instance.app_context():
                        app_instance.logger.error(f"Error in Komodo auto-scan thread: {str(e)}")
                except Exception:
                    pass

            # Sleep for the configured interval
            time.sleep(scan_interval)

    # Start the worker threads with the app instance as an argument
    docker_thread = threading.Thread(target=docker_auto_scan_worker, args=(flask_app_instance,), daemon=True)
    docker_thread.start()
    flask_app.logger.info("Docker auto-scan thread started")

    portainer_thread = threading.Thread(target=portainer_auto_scan_worker, args=(flask_app_instance,), daemon=True)
    portainer_thread.start()
    flask_app.logger.info("Portainer auto-scan thread started")

    komodo_thread = threading.Thread(target=komodo_auto_scan_worker, args=(flask_app_instance,), daemon=True)
    komodo_thread.start()
    flask_app.logger.info("Komodo auto-scan thread started")

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
                       'portainer_enabled', 'portainer_url', 'portainer_api_key',
                       'komodo_enabled', 'komodo_url', 'komodo_api_key', 'komodo_api_secret']:
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
                'komodo_enabled': request.form.get('komodo_enabled', 'false'),
                'komodo_url': request.form.get('komodo_url', ''),
                'komodo_api_key': request.form.get('komodo_api_key', ''),
                'komodo_api_secret': request.form.get('komodo_api_secret', '')
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

        komodo_url = get_setting('komodo_url', '')
        komodo_api_key = get_setting('komodo_api_key', '')
        komodo_api_secret = get_setting('komodo_api_secret', '')

        if not komodo_url or not komodo_api_key or not komodo_api_secret:
            return jsonify({'error': 'Komodo URL, API key, or API secret not configured'}), 400

        # Ensure the URL doesn't have a trailing slash
        komodo_url = komodo_url.rstrip('/')

        # Extract server name from URL for identification
        server_name = komodo_url.replace('https://', '').replace('http://', '').split('/')[0]

        # Resolve domain name to IP address
        server_ip = None
        try:
            server_ip = socket.gethostbyname(server_name)
            app.logger.info(f"Resolved {server_name} to IP: {server_ip}")
        except Exception as e:
            app.logger.warning(f"Could not resolve {server_name} to IP: {str(e)}")
            server_ip = server_name  # Fall back to using the domain name if resolution fails

        # Set up the API auth headers according to Komodo API documentation
        headers = {
            'X-Api-Key': komodo_api_key,
            'X-Api-Secret': komodo_api_secret,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Try multiple API endpoint formats based on Komodo API documentation
        endpoints_to_try = [
            # Standard path as per documentation
            {
                'url': f"{komodo_url}/read",
                'method': 'POST',
                'body': {'type': 'ListStacks', 'params': {}},
                'operation': 'ListStacks'
            },
            {
                'url': f"{komodo_url}/read",
                'method': 'POST',
                'body': {'type': 'ListContainers', 'params': {}},
                'operation': 'ListContainers'
            },
            # Try with /api prefix in case the API is mounted under /api
            {
                'url': f"{komodo_url}/api/read",
                'method': 'POST',
                'body': {'type': 'ListStacks', 'params': {}},
                'operation': 'ListStacks'
            },
            {
                'url': f"{komodo_url}/api/read",
                'method': 'POST',
                'body': {'type': 'ListContainers', 'params': {}},
                'operation': 'ListContainers'
            }
        ]

        # Try each endpoint until we get a successful response
        response = None
        successful_endpoint = None

        for endpoint in endpoints_to_try:
            try:
                app.logger.info(f"Trying {endpoint['method']} {endpoint['url']} for {endpoint['operation']}")

                if endpoint['method'] == 'POST':
                    response = requests.post(
                        endpoint['url'],
                        headers=headers,
                        json=endpoint['body'],  # Use json parameter to automatically serialize the body
                        timeout=10
                    )

                app.logger.info(f"Response: {response.status_code} - Content-Type: {response.headers.get('Content-Type')}")

                # If successful, break the loop
                if response.status_code == 200:
                    app.logger.info(f"Successful connection with {endpoint['url']}")
                    successful_endpoint = endpoint
                    break

            except requests.exceptions.RequestException as e:
                app.logger.warning(f"Error connecting to {endpoint['url']}: {str(e)}")
                continue

        # If we still don't have a successful response, try Bearer token authentication
        if not successful_endpoint:
            app.logger.info("Trying with Bearer token authentication")

            bearer_headers = {
                'Authorization': f'Bearer {komodo_api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            for endpoint in endpoints_to_try:
                try:
                    app.logger.info(f"Trying {endpoint['method']} {endpoint['url']} with Bearer token")

                    if endpoint['method'] == 'POST':
                        response = requests.post(
                            endpoint['url'],
                            headers=bearer_headers,
                            json=endpoint['body'],
                            timeout=10
                        )

                    app.logger.info(f"Response: {response.status_code} - Content-Type: {response.headers.get('Content-Type')}")

                    # If successful, break the loop
                    if response.status_code == 200:
                        app.logger.info(f"Successful connection with Bearer token and {endpoint['url']}")
                        successful_endpoint = endpoint
                        break

                except requests.exceptions.RequestException as e:
                    app.logger.warning(f"Error connecting with Bearer token to {endpoint['url']}: {str(e)}")
                    continue

        # If we still don't get a good response
        if not successful_endpoint:
            app.logger.error("Could not connect to Komodo API with any endpoint")
            return jsonify({
                'success': False,
                'error': 'Failed to connect to Komodo API. Tried multiple endpoints but none were successful. Ensure the URL and credentials are correct.'
            }), 500

        # Process the response
        try:
            response_data = response.json()
        except ValueError:
            app.logger.error("Response is not valid JSON")
            return jsonify({
                'success': False,
                'error': 'Komodo API response is not valid JSON'
            }), 500

        # Debug log to help understand the structure
        app.logger.info(f"Response type: {type(response_data)}")
        if isinstance(response_data, dict):
            app.logger.info(f"Response keys: {response_data.keys()}")

        # Extract containers list based on response format
        containers_list = []

        # Case 1: Direct list of stacks/containers
        if isinstance(response_data, list):
            containers_list = response_data
            app.logger.info("Response is a direct list of containers/stacks")

        # Case 2: Result within response object
        elif isinstance(response_data, dict):
            # Try common keys that might contain the result
            if 'result' in response_data and isinstance(response_data['result'], list):
                containers_list = response_data['result']
                app.logger.info("Found containers in 'result' key")

            # Look for other common keys
            for key in ['containers', 'stacks', 'services', 'items']:
                if key in response_data and isinstance(response_data[key], list):
                    containers_list = response_data[key]
                    app.logger.info(f"Found containers in '{key}' key")
                    break

        if not containers_list:
            app.logger.warning("Could not extract container data from response")
            sample_data = str(response_data)[:1000] + "..." if len(str(response_data)) > 1000 else str(response_data)
            app.logger.info(f"Sample response data: {sample_data}")
            return jsonify({
                'success': False,
                'error': 'Could not extract container data from Komodo API response'
            }), 500

        app.logger.info(f"Found {len(containers_list)} containers/stacks")

        # Process containers
        added_ports = 0
        added_to_port_table = 0

        # Clear existing Docker services and ports for this instance
        # To avoid duplicates from previous imports
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

        for container in containers_list:
            # Try to extract container information
            # Support different possible field names
            container_id = (
                container.get('id') or
                container.get('containerId') or
                container.get('container_id') or
                f"komodo-{server_name}-{container.get('name', 'unknown')}"
            )

            container_name = (
                container.get('name') or
                container.get('containerName') or
                container.get('container_name') or
                'unknown'
            )

            container_image = (
                container.get('image') or
                container.get('imageName') or
                container.get('image_name') or
                'unknown'
            )

            container_status = (
                container.get('status') or
                container.get('state') or
                container.get('containerStatus') or
                'unknown'
            )

            # Add container to DockerService table
            service = DockerService(
                container_id=container_id,
                name=container_name,
                image=container_image,
                status=container_status
            )
            db.session.add(service)
            db.session.flush()  # Flush to get the service ID

            # Extract port mappings - try different field names
            port_mappings = []
            for field in ['ports', 'portBindings', 'port_bindings', 'publish']:
                if field in container and container[field]:
                    port_mappings = container[field]
                    break

            # Process port mappings
            app.logger.info(f"Found {len(port_mappings) if port_mappings else 0} port mappings for {container_name}")

            for port_mapping in port_mappings:
                # Try different potential structures for port mapping
                host_port = None
                container_port = None
                protocol = 'tcp'

                if isinstance(port_mapping, dict):
                    # Dict format - try various field names
                    host_port = (
                        port_mapping.get('published') or
                        port_mapping.get('hostPort') or
                        port_mapping.get('host_port') or
                        port_mapping.get('public')
                    )

                    container_port = (
                        port_mapping.get('target') or
                        port_mapping.get('containerPort') or
                        port_mapping.get('container_port') or
                        port_mapping.get('private')
                    )

                    protocol = (
                        port_mapping.get('protocol') or
                        port_mapping.get('proto') or
                        'tcp'
                    ).lower()
                elif isinstance(port_mapping, str):
                    # String format like "80:8080/tcp"
                    try:
                        parts = port_mapping.split(':')
                        if len(parts) == 2:
                            proto_parts = parts[1].split('/')
                            host_port = parts[0]
                            if len(proto_parts) == 2:
                                container_port = proto_parts[0]
                                protocol = proto_parts[1]
                            else:
                                container_port = proto_parts[0]
                    except:
                        app.logger.warning(f"Could not parse port mapping string: {port_mapping}")

                if not host_port or not container_port:
                    app.logger.warning(f"Missing host_port or container_port in mapping: {port_mapping}")
                    continue

                # Convert to integers
                try:
                    host_port_int = int(host_port)
                    container_port_int = int(container_port)
                except ValueError:
                    app.logger.warning(f"Invalid port numbers: host={host_port}, container={container_port}")
                    continue

                # Add port mapping to DockerPort table
                docker_port = DockerPort(
                    service_id=service.id,
                    host_ip=server_ip,
                    host_port=host_port_int,
                    container_port=container_port_int,
                    protocol=protocol.upper()
                )
                db.session.add(docker_port)
                added_ports += 1

                # Check if port already exists in Port table
                existing_port = Port.query.filter_by(
                    ip_address=server_ip,
                    port_number=host_port_int,
                    port_protocol=protocol.upper()
                ).first()

                # Add to Port table if it doesn't exist
                if not existing_port:
                    max_order = db.session.query(db.func.max(Port.order)).filter_by(
                        ip_address=server_ip
                    ).scalar() or 0

                    new_port = Port(
                        ip_address=server_ip,
                        nickname=server_name,
                        port_number=host_port_int,
                        description=f"Komodo ({server_name}): {container_name} ({container_port_int}/{protocol})",
                        port_protocol=protocol.upper(),
                        order=max_order + 1,
                        source='komodo',
                        is_immutable=True
                    )
                    db.session.add(new_port)
                    added_to_port_table += 1

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Komodo import completed. Added {added_ports} port mappings and {added_to_port_table} ports to the ports page.',
            'api_details': {
                'endpoint': successful_endpoint['url'],
                'operation': successful_endpoint['operation'],
                'method': successful_endpoint['method']
            }
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

# Background thread for auto-scanning Docker containers
def start_docker_auto_scan_thread():
    """
    Start a background thread for auto-scanning Docker containers.
    """
    def docker_auto_scan_worker():
        while True:
            try:
                with app.app_context():
                    # Check if Docker is enabled
                    if get_setting('docker_enabled', 'false').lower() == 'true':
                        app.logger.info("Running automatic Docker container scan")

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
            except Exception as e:
                app.logger.error(f"Error in Docker auto-scan thread: {str(e)}")

            # Sleep for the configured interval
            scan_interval = int(get_setting('docker_scan_interval', '300'))
            time.sleep(scan_interval)

    # Start the worker thread
    thread = threading.Thread(target=docker_auto_scan_worker, daemon=True)
    thread.start()
    app.logger.info("Docker auto-scan thread started")

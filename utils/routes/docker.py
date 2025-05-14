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
                       'komodo_enabled', 'komodo_url', 'komodo_api_key']:
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
                'komodo_api_key': request.form.get('komodo_api_key', '')
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

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    try:
        import requests

        komodo_url = get_setting('komodo_url', '')
        komodo_api_key = get_setting('komodo_api_key', '')

        if not komodo_url or not komodo_api_key:
            return jsonify({'error': 'Komodo URL or API key not configured'}), 400

        # Set up headers for Komodo API
        headers = {
            'X-API-Key': komodo_api_key,
            'Content-Type': 'application/json'
        }

        # Get containers from Komodo
        containers_response = requests.get(f"{komodo_url}/api/v1/containers", headers=headers)
        if containers_response.status_code != 200:
            return jsonify({'error': f'Failed to get Komodo containers: {containers_response.text}'}), 500

        containers = containers_response.json()
        added_ports = 0
        added_to_port_table = 0

        # Extract server name from URL for identification in case of multiple Komodo instances
        server_name = komodo_url.replace('https://', '').replace('http://', '').split('/')[0]

        # Resolve domain name to IP address
        server_ip = None
        try:
            server_ip = socket.gethostbyname(server_name)
            app.logger.info(f"Resolved {server_name} to IP: {server_ip}")
        except Exception as e:
            app.logger.warning(f"Could not resolve {server_name} to IP: {str(e)}")
            server_ip = server_name  # Fall back to using the domain name if resolution fails

        for container in containers:
            # Add container to DockerService table
            service = DockerService(
                container_id=container['id'],
                name=container.get('name', 'unknown').lstrip('/'),
                image=container.get('image', 'unknown'),
                status=container.get('status', 'unknown')
            )
            db.session.add(service)
            db.session.flush()  # Flush to get the service ID

            # Process port mappings
            for port_mapping in container.get('ports', []):
                host_ip = port_mapping.get('host_ip', '0.0.0.0')
                if host_ip == '' or host_ip == '0.0.0.0' or host_ip == '::':
                    # Use the resolved IP address instead of placeholder IPs
                    host_ip = server_ip

                host_port = port_mapping.get('host_port')
                container_port = port_mapping.get('container_port')
                protocol = port_mapping.get('protocol', 'tcp')

                if not host_port or not container_port:
                    continue

                # Add port mapping to DockerPort table
                docker_port = DockerPort(
                    service_id=service.id,
                    host_ip=host_ip,
                    host_port=int(host_port),
                    container_port=int(container_port),
                    protocol=protocol.upper()
                )
                db.session.add(docker_port)
                added_ports += 1

                # Check if port already exists in Port table for this IP and port number
                existing_port = Port.query.filter_by(
                    ip_address=host_ip,
                    port_number=int(host_port),
                    port_protocol=protocol.upper()
                ).first()

                # Always add to Port table if it doesn't exist, regardless of auto-detect setting
                if not existing_port:
                    # Get the max order for this IP
                    max_order = db.session.query(db.func.max(Port.order)).filter_by(
                        ip_address=host_ip
                    ).scalar() or 0

                    # Create new port entry with server name in description and as nickname
                    # Set is_immutable to True for Komodo ports
                    new_port = Port(
                        ip_address=host_ip,
                        nickname=server_name,  # Set the domain name as the nickname
                        port_number=int(host_port),
                        description=f"Komodo ({server_name}): {service.name} ({container_port}/{protocol})",
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

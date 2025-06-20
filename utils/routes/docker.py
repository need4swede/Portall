# utils/routes/docker_new.py

# Standard Imports
import os
import socket
import subprocess
import threading
import time
from datetime import datetime

# External Imports
from flask import Blueprint
from flask import current_app as app
from flask import jsonify, request
import docker
import requests

# Local Imports
from utils.database import db, Port, Setting, DockerInstance, DockerService, DockerPort, PortScan
from utils.docker_instance_manager import DockerInstanceManager

# Create the blueprint
docker_bp = Blueprint('docker', __name__)

# Initialize instance manager
instance_manager = DockerInstanceManager()

def get_setting(key, default):
    """Helper function to retrieve settings from the database."""
    setting = Setting.query.filter_by(key=key).first()
    value = setting.value if setting else str(default)
    return value if value != '' else str(default)

def clean_and_validate_ip(ip_string):
    """
    Clean and validate IP address with extensive edge case handling.
    Supports various input formats and handles common user mistakes.
    """
    import re

    if not ip_string:
        return None

    # Remove whitespace
    cleaned = ip_string.strip()

    if not cleaned:
        return None

    app.logger.debug(f"Cleaning IP string: '{ip_string}' -> '{cleaned}'")

    # Remove protocol prefixes
    for prefix in ['http://', 'https://', 'tcp://', 'udp://', 'ftp://']:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
            app.logger.debug(f"Removed protocol prefix, now: '{cleaned}'")

    # Remove trailing slashes and paths
    if '/' in cleaned:
        cleaned = cleaned.split('/')[0]
        app.logger.debug(f"Removed path, now: '{cleaned}'")

    # Remove port numbers (but not for IPv6)
    if ':' in cleaned and not cleaned.count(':') > 1:  # Not IPv6
        cleaned = cleaned.split(':')[0]
        app.logger.debug(f"Removed port, now: '{cleaned}'")

    # Handle special cases
    if cleaned.lower() in ['localhost', 'local']:
        app.logger.debug("Converting localhost to 127.0.0.1")
        return '127.0.0.1'

    # Validate IP format using regex
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(ip_pattern, cleaned):
        app.logger.debug(f"IP format validation failed for: '{cleaned}'")
        return None

    # Validate IP ranges (0-255 for each octet)
    try:
        parts = cleaned.split('.')
        if not all(0 <= int(part) <= 255 for part in parts):
            app.logger.debug(f"IP range validation failed for: '{cleaned}'")
            return None
    except ValueError:
        app.logger.debug(f"IP parsing failed for: '{cleaned}'")
        return None

    app.logger.debug(f"IP validation successful: '{cleaned}'")
    return cleaned

def get_server_ip():
    """
    Simple server IP detection with robust validation and fallback.
    Uses HOST_IP environment variable with extensive input validation.
    """
    app.logger.info("=== Starting server IP detection ===")

    # Get HOST_IP environment variable
    host_ip = os.environ.get('HOST_IP', '').strip()
    app.logger.info(f"HOST_IP environment variable: '{host_ip}'")

    if host_ip:
        # Clean and validate the IP
        cleaned_ip = clean_and_validate_ip(host_ip)
        if cleaned_ip:
            app.logger.info(f"✓ SUCCESS: Using HOST_IP: {cleaned_ip}")
            app.logger.info(f"=== Server IP detection complete: {cleaned_ip} (via HOST_IP) ===")
            return cleaned_ip
        else:
            app.logger.warning(f"✗ Invalid HOST_IP '{host_ip}', falling back to 127.0.0.1")
    else:
        app.logger.info("✗ No HOST_IP set, using default 127.0.0.1")

    app.logger.info("=== Server IP detection complete: 127.0.0.1 (fallback) ===")
    return '127.0.0.1'

def get_final_host_ip(detected_ip, source='docker'):
    """
    Determine the final host IP to use based on detection and settings.
    Only replaces 127.0.0.1 for Docker integrations when valid HOST_IP is set.
    """
    # Get the server IP (which includes HOST_IP validation)
    server_ip = get_server_ip()

    # Only replace 127.0.0.1 if:
    # 1. We have a valid HOST_IP set (server_ip != '127.0.0.1')
    # 2. This is from a Docker integration
    # 3. The detected IP is 127.0.0.1
    if (server_ip != '127.0.0.1' and
        source in ['docker', 'portainer', 'komodo'] and
        detected_ip == '127.0.0.1'):
        app.logger.info(f"Replacing Docker localhost IP with HOST_IP: {detected_ip} -> {server_ip}")
        return server_ip

    # For all other cases, use the detected IP as-is
    app.logger.debug(f"Using detected IP as-is: {detected_ip} (source: {source})")
    return detected_ip

# Instance Management Routes

@docker_bp.route('/docker/instances', methods=['GET'])
def get_instances():
    """
    Get all Docker instances.

    Returns:
        JSON: List of all Docker instances with their configurations.
    """
    try:
        instances = DockerInstance.query.all()
        return jsonify({
            'success': True,
            'instances': [instance.to_dict() for instance in instances]
        })
    except Exception as e:
        app.logger.error(f"Error getting instances: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/instances', methods=['POST'])
def create_instance():
    """
    Create a new Docker instance.

    Returns:
        JSON: The created instance data or error message.
    """
    try:
        data = request.get_json()

        name = data.get('name', '').strip()
        instance_type = data.get('type')
        config = data.get('config', {})
        enabled = data.get('enabled', True)
        auto_detect = data.get('auto_detect', True)
        scan_interval = data.get('scan_interval', 300)

        # Validate required fields
        if not instance_type:
            return jsonify({'success': False, 'error': 'Instance type is required'}), 400

        if instance_type not in ['docker', 'portainer', 'komodo']:
            return jsonify({'success': False, 'error': 'Invalid instance type'}), 400

        # Create the instance
        instance = instance_manager.create_instance(
            name=name,
            instance_type=instance_type,
            config=config,
            enabled=enabled,
            auto_detect=auto_detect,
            scan_interval=scan_interval
        )

        if instance:
            return jsonify({
                'success': True,
                'message': f'{instance_type.capitalize()} instance created successfully',
                'instance': instance.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create instance'}), 500

    except Exception as e:
        app.logger.error(f"Error creating instance: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/instances/<int:instance_id>', methods=['PUT'])
def update_instance(instance_id):
    """
    Update an existing Docker instance.

    Args:
        instance_id (int): The ID of the instance to update.

    Returns:
        JSON: The updated instance data or error message.
    """
    try:
        data = request.get_json()

        # Update the instance
        instance = instance_manager.update_instance(instance_id, **data)

        if instance:
            return jsonify({
                'success': True,
                'message': 'Instance updated successfully',
                'instance': instance.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': 'Instance not found or update failed'}), 404

    except Exception as e:
        app.logger.error(f"Error updating instance {instance_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/instances/<int:instance_id>', methods=['DELETE'])
def delete_instance(instance_id):
    """
    Delete a Docker instance.

    Args:
        instance_id (int): The ID of the instance to delete.

    Returns:
        JSON: Success or error message.
    """
    try:
        success = instance_manager.delete_instance(instance_id)

        if success:
            return jsonify({
                'success': True,
                'message': 'Instance deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Instance not found'}), 404

    except Exception as e:
        app.logger.error(f"Error deleting instance {instance_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/instances/<int:instance_id>/test', methods=['POST'])
def test_instance_connection(instance_id):
    """
    Test connection to a Docker instance.

    Args:
        instance_id (int): The ID of the instance to test.

    Returns:
        JSON: Test result with success status and message.
    """
    try:
        result = instance_manager.test_connection(instance_id)

        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code

    except Exception as e:
        app.logger.error(f"Error testing instance {instance_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Legacy Settings Routes (for backward compatibility)

@docker_bp.route('/docker/settings', methods=['GET', 'POST'])
def docker_settings():
    """
    Handle GET and POST requests for Docker integration settings.
    This route maintains backward compatibility with the old settings system.
    """
    if request.method == 'GET':
        try:
            # Get all instances and convert to legacy format
            docker_instances = instance_manager.get_instances_by_type('docker')
            portainer_instances = instance_manager.get_instances_by_type('portainer')
            komodo_instances = instance_manager.get_instances_by_type('komodo')

            # Convert to legacy settings format
            docker_settings = {
                'docker_enabled': 'true' if docker_instances else 'false',
                'docker_host': docker_instances[0].get_config_value('host', 'unix:///var/run/docker.sock') if docker_instances else 'unix:///var/run/docker.sock',
                'docker_auto_detect': 'true' if docker_instances and docker_instances[0].auto_detect else 'false',
                'docker_scan_interval': str(docker_instances[0].scan_interval) if docker_instances else '300',

                'portainer_enabled': 'true' if portainer_instances else 'false',
                'portainer_url': portainer_instances[0].get_config_value('url', '') if portainer_instances else '',
                'portainer_api_key': portainer_instances[0].get_config_value('api_key', '') if portainer_instances else '',
                'portainer_verify_ssl': 'true' if portainer_instances and portainer_instances[0].get_config_value('verify_ssl', True) else 'false',
                'portainer_auto_detect': 'true' if portainer_instances and portainer_instances[0].auto_detect else 'false',
                'portainer_scan_interval': str(portainer_instances[0].scan_interval) if portainer_instances else '300',

                'komodo_enabled': 'true' if komodo_instances else 'false',
                'komodo_url': komodo_instances[0].get_config_value('url', '') if komodo_instances else '',
                'komodo_api_key': komodo_instances[0].get_config_value('api_key', '') if komodo_instances else '',
                'komodo_api_secret': komodo_instances[0].get_config_value('api_secret', '') if komodo_instances else '',
                'komodo_auto_detect': 'true' if komodo_instances and komodo_instances[0].auto_detect else 'false',
                'komodo_scan_interval': str(komodo_instances[0].scan_interval) if komodo_instances else '300'
            }

            return jsonify(docker_settings)
        except Exception as e:
            app.logger.error(f"Error retrieving Docker settings: {str(e)}")
            return jsonify({'error': str(e)}), 500

    elif request.method == 'POST':
        try:
            # Handle legacy settings update by creating/updating instances
            form_keys = request.form.keys()

            # Docker form
            if any(key in form_keys for key in ['docker_enabled', 'docker_host', 'docker_auto_detect', 'docker_scan_interval']):
                docker_enabled = request.form.get('docker_enabled', 'false') == 'true'
                docker_host = request.form.get('docker_host', 'unix:///var/run/docker.sock')
                docker_auto_detect = request.form.get('docker_auto_detect', 'false') == 'true'
                docker_scan_interval = int(request.form.get('docker_scan_interval', '300'))

                # Get or create Docker instance
                docker_instances = instance_manager.get_instances_by_type('docker')
                if docker_instances:
                    # Update existing instance
                    instance_manager.update_instance(
                        docker_instances[0].id,
                        enabled=docker_enabled,
                        auto_detect=docker_auto_detect,
                        scan_interval=docker_scan_interval,
                        config={'host': docker_host, 'timeout': 30}
                    )
                elif docker_enabled:
                    # Create new instance
                    instance_manager.create_instance(
                        name='Docker Instance',
                        instance_type='docker',
                        config={'host': docker_host, 'timeout': 30},
                        enabled=docker_enabled,
                        auto_detect=docker_auto_detect,
                        scan_interval=docker_scan_interval
                    )

            # Portainer form
            if any(key in form_keys for key in ['portainer_enabled', 'portainer_url', 'portainer_api_key', 'portainer_verify_ssl', 'portainer_auto_detect', 'portainer_scan_interval']):
                portainer_enabled = request.form.get('portainer_enabled', 'false') == 'true'
                portainer_url = request.form.get('portainer_url', '')
                portainer_api_key = request.form.get('portainer_api_key', '')
                portainer_verify_ssl = request.form.get('portainer_verify_ssl', 'true') == 'true'
                portainer_auto_detect = request.form.get('portainer_auto_detect', 'false') == 'true'
                portainer_scan_interval = int(request.form.get('portainer_scan_interval', '300'))

                # Get or create Portainer instance
                portainer_instances = instance_manager.get_instances_by_type('portainer')
                if portainer_instances:
                    # Update existing instance
                    instance_manager.update_instance(
                        portainer_instances[0].id,
                        enabled=portainer_enabled,
                        auto_detect=portainer_auto_detect,
                        scan_interval=portainer_scan_interval,
                        config={
                            'url': portainer_url,
                            'api_key': portainer_api_key,
                            'verify_ssl': portainer_verify_ssl
                        }
                    )
                elif portainer_enabled:
                    # Create new instance
                    instance_manager.create_instance(
                        name='Portainer Instance',
                        instance_type='portainer',
                        config={
                            'url': portainer_url,
                            'api_key': portainer_api_key,
                            'verify_ssl': portainer_verify_ssl
                        },
                        enabled=portainer_enabled,
                        auto_detect=portainer_auto_detect,
                        scan_interval=portainer_scan_interval
                    )

            # Komodo form
            if any(key in form_keys for key in ['komodo_enabled', 'komodo_url', 'komodo_api_key', 'komodo_api_secret', 'komodo_auto_detect', 'komodo_scan_interval']):
                komodo_enabled = request.form.get('komodo_enabled', 'false') == 'true'
                komodo_url = request.form.get('komodo_url', '')
                komodo_api_key = request.form.get('komodo_api_key', '')
                komodo_api_secret = request.form.get('komodo_api_secret', '')
                komodo_auto_detect = request.form.get('komodo_auto_detect', 'false') == 'true'
                komodo_scan_interval = int(request.form.get('komodo_scan_interval', '300'))

                # Get or create Komodo instance
                komodo_instances = instance_manager.get_instances_by_type('komodo')
                if komodo_instances:
                    # Update existing instance
                    instance_manager.update_instance(
                        komodo_instances[0].id,
                        enabled=komodo_enabled,
                        auto_detect=komodo_auto_detect,
                        scan_interval=komodo_scan_interval,
                        config={
                            'url': komodo_url,
                            'api_key': komodo_api_key,
                            'api_secret': komodo_api_secret
                        }
                    )
                elif komodo_enabled:
                    # Create new instance
                    instance_manager.create_instance(
                        name='Komodo Instance',
                        instance_type='komodo',
                        config={
                            'url': komodo_url,
                            'api_key': komodo_api_key,
                            'api_secret': komodo_api_secret
                        },
                        enabled=komodo_enabled,
                        auto_detect=komodo_auto_detect,
                        scan_interval=komodo_scan_interval
                    )

            return jsonify({'success': True, 'message': 'Docker settings updated successfully'})
        except Exception as e:
            app.logger.error(f"Error saving Docker settings: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

# Scanning Routes

@docker_bp.route('/docker/scan/<int:instance_id>', methods=['POST'])
def scan_instance(instance_id):
    """
    Scan a specific Docker instance for containers and port mappings.

    Args:
        instance_id (int): The ID of the instance to scan.

    Returns:
        JSON: Scan results with success status and message.
    """
    try:
        instance = instance_manager.get_instance(instance_id)
        if not instance:
            return jsonify({'success': False, 'error': 'Instance not found'}), 404

        if not instance.enabled:
            return jsonify({'success': False, 'error': 'Instance is disabled'}), 400

        if instance.type == 'docker':
            return _scan_docker_instance(instance)
        elif instance.type == 'portainer':
            return _scan_portainer_instance(instance)
        elif instance.type == 'komodo':
            return _scan_komodo_instance(instance)
        else:
            return jsonify({'success': False, 'error': f'Unknown instance type: {instance.type}'}), 400

    except Exception as e:
        app.logger.error(f"Error scanning instance {instance_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def _scan_docker_instance(instance):
    """Scan a Docker instance for containers and port mappings."""
    try:
        client = instance_manager.get_client(instance.id)
        if not client:
            return jsonify({'success': False, 'error': 'Failed to create Docker client'}), 500

        # Get all running containers
        containers = client.containers.list()

        # Clear existing services for this instance
        DockerPort.query.filter(
            DockerPort.service_id.in_(
                db.session.query(DockerService.id).filter_by(instance_id=instance.id)
            )
        ).delete(synchronize_session=False)
        DockerService.query.filter_by(instance_id=instance.id).delete()
        db.session.commit()

        added_ports = 0
        added_to_port_table = 0

        for container in containers:
            # Add container to DockerService table
            service = DockerService(
                instance_id=instance.id,
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
                        # Use the detected server IP instead of localhost
                        detected_server_ip = get_server_ip()
                        host_ip = detected_server_ip
                    else:
                        # Apply the final host IP logic for Docker integrations
                        host_ip = get_final_host_ip(host_ip, 'docker')

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

                    # Always add to Port table if it doesn't exist
                    if not existing_port:
                        # Get the max order for this IP
                        max_order = db.session.query(db.func.max(Port.order)).filter_by(
                            ip_address=host_ip
                        ).scalar() or 0

                        # Create new port entry
                        new_port = Port(
                            ip_address=host_ip,
                            nickname=instance.name,
                            port_number=host_port,
                            description=f"{container.name} ({port_number}/{protocol})",
                            port_protocol=protocol.upper(),
                            order=max_order + 1,
                            source='docker',
                            is_immutable=True
                        )
                        db.session.add(new_port)
                        db.session.flush()  # Ensure we have the port ID

                        # Apply automatic tagging rules to the new port
                        try:
                            from utils.tagging_engine import tagging_engine
                            tagging_engine.apply_automatic_rules_to_port(new_port, commit=False)
                        except Exception as e:
                            app.logger.error(f"Error applying automatic tagging rules to Docker port {new_port.id}: {str(e)}")

                        added_to_port_table += 1

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Docker scan completed. Found {len(containers)} containers with {added_ports} port mappings and added {added_to_port_table} ports to the ports page.'
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error scanning Docker instance: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def _scan_portainer_instance(instance):
    """Scan a Portainer instance for containers and port mappings."""
    try:
        client_config = instance_manager.get_client(instance.id)
        if not client_config:
            return jsonify({'success': False, 'error': 'Failed to get Portainer client configuration'}), 500

        portainer_url = client_config['url']
        headers = {'X-API-Key': client_config['api_key']}
        verify_ssl = client_config['verify_ssl']

        # Get endpoints (Docker environments)
        endpoints_response = requests.get(f"{portainer_url}/api/endpoints", headers=headers, verify=verify_ssl)
        if endpoints_response.status_code != 200:
            return jsonify({'success': False, 'error': f'Failed to get Portainer endpoints: {endpoints_response.text}'}), 500

        endpoints = endpoints_response.json()
        if not endpoints:
            return jsonify({'success': False, 'error': 'No endpoints found in Portainer'}), 404

        # Clear existing services for this instance
        DockerPort.query.filter(
            DockerPort.service_id.in_(
                db.session.query(DockerService.id).filter_by(instance_id=instance.id)
            )
        ).delete(synchronize_session=False)
        DockerService.query.filter_by(instance_id=instance.id).delete()
        db.session.commit()

        added_ports = 0
        added_to_port_table = 0

        # Extract server name from URL for identification
        server_name = portainer_url.replace('https://', '').replace('http://', '').split('/')[0]

        # Resolve domain name to IP address
        server_ip = None
        try:
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
                headers=headers,
                verify=verify_ssl
            )

            if containers_response.status_code != 200:
                app.logger.warning(f"Failed to get containers for endpoint {endpoint_id}: {containers_response.text}")
                continue

            containers = containers_response.json()

            for container in containers:
                # Add container to DockerService table
                service = DockerService(
                    instance_id=instance.id,
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
                    if host_ip == '' or host_ip == '0.0.0.0' or host_ip == '::' or host_ip == '127.0.0.1':
                        # Use the resolved IP address instead of placeholder IPs or localhost
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

                    # Always add to Port table if it doesn't exist
                    if not existing_port:
                        # Get the max order for this IP
                        max_order = db.session.query(db.func.max(Port.order)).filter_by(
                            ip_address=host_ip
                        ).scalar() or 0

                        # Create new port entry
                        new_port = Port(
                            ip_address=host_ip,
                            nickname=instance.name,
                            port_number=host_port,
                            description=service.name,
                            port_protocol=protocol.upper(),
                            order=max_order + 1,
                            source='portainer',
                            is_immutable=True
                        )
                        db.session.add(new_port)
                        db.session.flush()  # Ensure we have the port ID

                        # Apply automatic tagging rules to the new port
                        try:
                            from utils.tagging_engine import tagging_engine
                            tagging_engine.apply_automatic_rules_to_port(new_port, commit=False)
                        except Exception as e:
                            app.logger.error(f"Error applying automatic tagging rules to Portainer port {new_port.id}: {str(e)}")

                        added_to_port_table += 1

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Portainer scan completed. Added {added_ports} port mappings and {added_to_port_table} ports to the ports page.'
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error scanning Portainer instance: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def _scan_komodo_instance(instance):
    """Scan a Komodo instance for containers and port mappings."""
    try:
        client_config = instance_manager.get_client(instance.id)
        if not client_config:
            return jsonify({'success': False, 'error': 'Failed to get Komodo client configuration'}), 500

        komodo_url = client_config['url']
        headers = {
            'X-Api-Key': client_config['api_key'],
            'X-Api-Secret': client_config['api_secret'],
            'Content-Type': 'application/json'
        }

        # Get stacks from Komodo
        response = requests.post(
            f"{komodo_url}/read",
            headers=headers,
            json={'type': 'ListStacks', 'params': {}},
            timeout=10
        )

        if response.status_code != 200:
            return jsonify({'success': False, 'error': f'Komodo API returned status {response.status_code}'}), 500

        stacks = response.json()
        if not isinstance(stacks, list):
            if isinstance(stacks, dict) and 'result' in stacks and isinstance(stacks['result'], list):
                stacks = stacks['result']
            else:
                return jsonify({'success': False, 'error': 'Unexpected response format from Komodo API'}), 500

        # Clear existing services for this instance
        DockerPort.query.filter(
            DockerPort.service_id.in_(
                db.session.query(DockerService.id).filter_by(instance_id=instance.id)
            )
        ).delete(synchronize_session=False)
        DockerService.query.filter_by(instance_id=instance.id).delete()
        db.session.commit()

        added_ports = 0
        added_to_port_table = 0

        # Extract server name from URL for identification
        server_name = komodo_url.replace('https://', '').replace('http://', '').split('/')[0]
        nickname = server_name
        if ':' in nickname:
            nickname = nickname.split(':')[0]

        # Resolve domain name to IP address
        server_ip = None
        try:
            if nickname.lower() == 'localhost' or server_name.lower().startswith('localhost:') or server_name == '127.0.0.1':
                server_ip = '127.0.0.1'
            else:
                server_ip = socket.gethostbyname(nickname)
        except Exception as e:
            app.logger.warning(f"Could not resolve {nickname} to IP: {str(e)}")
            if 'localhost' in nickname.lower():
                server_ip = '127.0.0.1'
            else:
                server_ip = nickname

        for stack in stacks:
            stack_id = stack.get('id')
            stack_name = stack.get('name', 'unknown')

            # Get detailed stack information
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

            # Extract compose file content
            compose_content = None
            if 'info' in stack_detail and 'deployed_contents' in stack_detail['info']:
                for content_file in stack_detail['info']['deployed_contents']:
                    if content_file.get('path') in ['compose.yaml', 'docker-compose.yaml', 'docker-compose.yml']:
                        compose_content = content_file.get('contents')
                        break

            if not compose_content and 'config' in stack_detail and 'file_contents' in stack_detail['config']:
                compose_content = stack_detail['config']['file_contents']

            if not compose_content:
                app.logger.warning(f"No compose file content found for stack {stack_name}")
                continue

            # Extract services from the stack
            services = []
            if 'info' in stack_detail and 'services' in stack_detail['info']:
                services = stack_detail['info']['services']
            elif 'info' in stack_detail and 'deployed_services' in stack_detail['info']:
                services = stack_detail['info']['deployed_services']

            # Process each service
            for service in services:
                service_name = service.get('service', service.get('service_name', service.get('container_name', 'unknown')))
                service_image = service.get('image', 'unknown')

                # Add service to DockerService table
                docker_service = DockerService(
                    instance_id=instance.id,
                    container_id=f"komodo-{server_name}-{stack_name}-{service_name}",
                    name=f"{stack_name}/{service_name}",
                    image=service_image,
                    status="running"
                )
                db.session.add(docker_service)
                db.session.flush()

                # Parse compose file for port mappings (simplified approach)
                import re
                port_mappings = []

                # Use regex to find port mappings for this service
                service_pattern = re.compile(rf'{service_name}:\s*\n(?:.*\n)*?(?:\s+ports:\s*\n(?:\s+-\s+"?\'?([^"\'\n]+)"?\'?\s*\n)+)', re.MULTILINE)
                service_match = service_pattern.search(compose_content)

                if service_match:
                    port_lines = re.findall(r'\s+-\s+"?\'?([^"\'\n]+)"?\'?', service_match.group(0))
                    for port_line in port_lines:
                        if ':' in port_line:
                            port_mappings.append(port_line)

                # Process port mappings
                for port_mapping in port_mappings:
                    parts = port_mapping.split(':')
                    if len(parts) != 2:
                        continue

                    host_port = parts[0]
                    container_port_part = parts[1]

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

                    if not existing_port:
                        max_order = db.session.query(db.func.max(Port.order)).filter_by(
                            ip_address=server_ip
                        ).scalar() or 0

                        new_port = Port(
                            ip_address=server_ip,
                            nickname=instance.name,
                            port_number=host_port_int,
                            description=f"{stack_name}/{service_name} ({container_port_int}/{protocol})",
                            port_protocol=protocol,
                            order=max_order + 1,
                            source='komodo',
                            is_immutable=True
                        )
                        db.session.add(new_port)
                        db.session.flush()

                        # Apply automatic tagging rules to the new port
                        try:
                            from utils.tagging_engine import tagging_engine
                            tagging_engine.apply_automatic_rules_to_port(new_port, commit=False)
                        except Exception as e:
                            app.logger.error(f"Error applying automatic tagging rules to Komodo port {new_port.id}: {str(e)}")

                        added_to_port_table += 1

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Komodo scan completed. Added {added_ports} port mappings and {added_to_port_table} ports to the ports page.'
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error scanning Komodo instance: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Legacy routes for backward compatibility

@docker_bp.route('/docker/containers', methods=['GET'])
def get_containers():
    """
    Get a list of running Docker containers from all enabled Docker instances.
    """
    try:
        all_containers = []
        docker_instances = instance_manager.get_enabled_instances_by_type('docker')

        for instance in docker_instances:
            client = instance_manager.get_client(instance.id)
            if client:
                containers = client.containers.list()
                for container in containers:
                    container_info = {
                        'id': container.id,
                        'name': container.name,
                        'image': container.image.tags[0] if container.image.tags else container.image.id,
                        'status': container.status,
                        'ports': container.ports,
                        'instance_id': instance.id,
                        'instance_name': instance.name
                    }
                    all_containers.append(container_info)

        return jsonify({'containers': all_containers})
    except Exception as e:
        app.logger.error(f"Error getting Docker containers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@docker_bp.route('/docker/scan', methods=['POST'])
def scan_docker_ports():
    """
    Scan all enabled Docker instances for port mappings.
    """
    try:
        total_containers = 0
        total_ports = 0
        total_added = 0

        docker_instances = instance_manager.get_enabled_instances_by_type('docker')

        for instance in docker_instances:
            result = _scan_docker_instance(instance)
            if result.status_code == 200:
                data = result.get_json()
                # Parse the message to extract numbers (simplified)
                message = data.get('message', '')
                if 'Found' in message and 'containers' in message:
                    # This is a simplified parsing - in production you might want more robust parsing
                    pass

        return jsonify({
            'success': True,
            'message': f'Scanned all Docker instances successfully.'
        })
    except Exception as e:
        app.logger.error(f"Error scanning Docker ports: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/import_from_portainer', methods=['POST'])
def import_from_portainer():
    """
    Import containers from all enabled Portainer instances.
    """
    try:
        portainer_instances = instance_manager.get_enabled_instances_by_type('portainer')

        if not portainer_instances:
            return jsonify({'error': 'No enabled Portainer instances found'}), 400

        total_ports = 0
        total_added = 0

        for instance in portainer_instances:
            result = _scan_portainer_instance(instance)
            if result.status_code == 200:
                data = result.get_json()
                # Aggregate results
                pass

        return jsonify({
            'success': True,
            'message': f'Imported from all Portainer instances successfully.'
        })
    except Exception as e:
        app.logger.error(f"Error importing from Portainer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/import_from_komodo', methods=['POST'])
def import_from_komodo():
    """
    Import containers from all enabled Komodo instances.
    """
    try:
        komodo_instances = instance_manager.get_enabled_instances_by_type('komodo')

        if not komodo_instances:
            return jsonify({'error': 'No enabled Komodo instances found'}), 400

        total_ports = 0
        total_added = 0

        for instance in komodo_instances:
            result = _scan_komodo_instance(instance)
            if result.status_code == 200:
                data = result.get_json()
                # Aggregate results
                pass

        return jsonify({
            'success': True,
            'message': f'Imported from all Komodo instances successfully.'
        })
    except Exception as e:
        app.logger.error(f"Error importing from Komodo: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Port scanning routes (unchanged)

@docker_bp.route('/docker/scan_ports', methods=['POST'])
def scan_ports():
    """
    Scan ports for a given IP address.
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

# Global Settings Routes

@docker_bp.route('/docker/global_settings', methods=['GET'])
def get_global_settings():
    """
    Get global Docker integration settings.

    Returns:
        JSON: Global settings dictionary.
    """
    try:
        settings = {
            'global_auto_scan': get_setting('docker_global_auto_scan', 'true') == 'true',
            'default_scan_interval': int(get_setting('docker_default_scan_interval', '300')),
            'service_retention': int(get_setting('docker_service_retention', '30')),
            'auto_add_services': get_setting('docker_auto_add_services', 'true') == 'true',
            'connection_timeout': int(get_setting('docker_connection_timeout', '30'))
        }
        return jsonify(settings)
    except Exception as e:
        app.logger.error(f"Error getting global Docker settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/global_settings', methods=['POST'])
def save_global_settings():
    """
    Save global Docker integration settings.

    Returns:
        JSON: Success or error message.
    """
    try:
        data = request.get_json()

        # Save each setting
        settings_map = {
            'global_auto_scan': 'docker_global_auto_scan',
            'default_scan_interval': 'docker_default_scan_interval',
            'service_retention': 'docker_service_retention',
            'auto_add_services': 'docker_auto_add_services',
            'connection_timeout': 'docker_connection_timeout'
        }

        for key, setting_key in settings_map.items():
            if key in data:
                value = str(data[key]).lower() if isinstance(data[key], bool) else str(data[key])

                # Update or create setting
                setting = Setting.query.filter_by(key=setting_key).first()
                if setting:
                    setting.value = value
                else:
                    setting = Setting(key=setting_key, value=value)
                    db.session.add(setting)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Global Docker settings saved successfully'})

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving global Docker settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@docker_bp.route('/docker/instances/<int:instance_id>/scan', methods=['POST'])
def scan_instance_endpoint(instance_id):
    """
    Scan a specific Docker instance for containers and services.

    Args:
        instance_id (int): The ID of the instance to scan.

    Returns:
        JSON: Scan result with success status and message.
    """
    try:
        result = instance_manager.scan_instance(instance_id)
        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code

    except Exception as e:
        app.logger.error(f"Error in scan instance endpoint: {str(e)}")
        return jsonify({'success': False, 'message': f'Error scanning instance: {str(e)}'}), 500

@docker_bp.route('/docker/instances/<int:instance_id>', methods=['GET'])
def get_instance(instance_id):
    """
    Get a specific Docker instance.

    Args:
        instance_id (int): The ID of the instance to retrieve.

    Returns:
        JSON: Instance data or error message.
    """
    try:
        instance = instance_manager.get_instance(instance_id)
        if instance:
            return jsonify({
                'success': True,
                'instance': instance.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': 'Instance not found'}), 404

    except Exception as e:
        app.logger.error(f"Error getting instance {instance_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

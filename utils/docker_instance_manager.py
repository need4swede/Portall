# utils/docker_instance_manager.py

import logging
import docker
import requests
from datetime import datetime
from flask import current_app as app
from utils.database import db, DockerInstance

logger = logging.getLogger(__name__)

class DockerInstanceManager:
    """
    Manager class for Docker, Portainer, and Komodo instances.
    Provides CRUD operations, validation, and client factory methods.
    """

    def __init__(self, db_session=None):
        """
        Initialize the instance manager.

        Args:
            db_session: Optional database session. If None, uses db.session.
        """
        self.db = db_session or db.session

    def get_instances_by_type(self, instance_type):
        """
        Get all instances of a specific type.

        Args:
            instance_type (str): The type of instance ('docker', 'portainer', 'komodo').

        Returns:
            list: List of DockerInstance objects.
        """
        try:
            instances = DockerInstance.query.filter_by(type=instance_type).all()
            logger.debug(f"Found {len(instances)} instances of type {instance_type}")
            return instances
        except Exception as e:
            logger.error(f"Error getting instances by type {instance_type}: {str(e)}")
            return []

    def get_enabled_instances_by_type(self, instance_type):
        """
        Get all enabled instances of a specific type.

        Args:
            instance_type (str): The type of instance ('docker', 'portainer', 'komodo').

        Returns:
            list: List of enabled DockerInstance objects.
        """
        try:
            instances = DockerInstance.query.filter_by(type=instance_type, enabled=True).all()
            logger.debug(f"Found {len(instances)} enabled instances of type {instance_type}")
            return instances
        except Exception as e:
            logger.error(f"Error getting enabled instances by type {instance_type}: {str(e)}")
            return []

    def get_instance(self, instance_id):
        """
        Get single instance by ID.

        Args:
            instance_id (int): The ID of the instance.

        Returns:
            DockerInstance: The instance object or None if not found.
        """
        try:
            instance = DockerInstance.query.get(instance_id)
            if instance:
                logger.debug(f"Found instance {instance_id}: {instance.name}")
            else:
                logger.warning(f"Instance {instance_id} not found")
            return instance
        except Exception as e:
            logger.error(f"Error getting instance {instance_id}: {str(e)}")
            return None

    def create_instance(self, name, instance_type, config, enabled=True, auto_detect=True, scan_interval=300):
        """
        Create new instance.

        Args:
            name (str): Name of the instance.
            instance_type (str): Type of instance ('docker', 'portainer', 'komodo').
            config (dict): Configuration dictionary.
            enabled (bool): Whether the instance is enabled.
            auto_detect (bool): Whether auto-detection is enabled.
            scan_interval (int): Scan interval in seconds.

        Returns:
            DockerInstance: The created instance or None if creation failed.
        """
        try:
            # Validate instance type
            if instance_type not in ['docker', 'portainer', 'komodo']:
                logger.error(f"Invalid instance type: {instance_type}")
                return None

            # Validate configuration
            if not self.validate_config(instance_type, config):
                logger.error(f"Invalid configuration for {instance_type} instance")
                return None

            # Generate unique name if needed
            if not name or name.strip() == '':
                name = self.generate_instance_name(instance_type)

            # Check for duplicate names
            existing = DockerInstance.query.filter_by(name=name).first()
            if existing:
                logger.error(f"Instance with name '{name}' already exists")
                return None

            # Create the instance
            instance = DockerInstance(
                name=name.strip(),
                type=instance_type,
                enabled=enabled,
                auto_detect=auto_detect,
                scan_interval=scan_interval,
                config=config
            )

            self.db.add(instance)
            self.db.commit()

            logger.info(f"Created {instance_type} instance: {name} (ID: {instance.id})")
            return instance

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating instance: {str(e)}")
            return None

    def update_instance(self, instance_id, **kwargs):
        """
        Update existing instance.

        Args:
            instance_id (int): The ID of the instance to update.
            **kwargs: Fields to update (name, enabled, auto_detect, scan_interval, config).

        Returns:
            DockerInstance: The updated instance or None if update failed.
        """
        try:
            instance = self.get_instance(instance_id)
            if not instance:
                logger.error(f"Instance {instance_id} not found")
                return None

            logger.info(f"Updating instance {instance_id} with fields: {list(kwargs.keys())}")

            # Update fields
            if 'name' in kwargs:
                new_name = kwargs['name'].strip()
                if new_name != instance.name:
                    # Check for duplicate names
                    existing = DockerInstance.query.filter_by(name=new_name).filter(
                        DockerInstance.id != instance_id
                    ).first()
                    if existing:
                        logger.error(f"Instance with name '{new_name}' already exists")
                        return None
                    instance.name = new_name
                    logger.info(f"Updated name to: {new_name}")

            if 'enabled' in kwargs:
                instance.enabled = bool(kwargs['enabled'])
                logger.info(f"Updated enabled to: {instance.enabled}")

            if 'auto_detect' in kwargs:
                instance.auto_detect = bool(kwargs['auto_detect'])
                logger.info(f"Updated auto_detect to: {instance.auto_detect}")

            if 'scan_interval' in kwargs:
                scan_interval = int(kwargs['scan_interval'])
                if scan_interval < 60:  # Minimum 1 minute
                    logger.error("Scan interval must be at least 60 seconds")
                    return None
                instance.scan_interval = scan_interval
                logger.info(f"Updated scan_interval to: {scan_interval}")

            if 'config' in kwargs:
                config = kwargs['config']
                # Only validate config if it's being completely replaced
                # For partial updates (like just enabling/disabling), skip validation
                if not self.validate_config(instance.type, config):
                    logger.error(f"Invalid configuration for {instance.type} instance: {config}")
                    return None
                instance.config = config
                logger.info(f"Updated config to: {config}")

            instance.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Successfully updated instance {instance_id}: {instance.name}")
            return instance

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating instance {instance_id}: {str(e)}")
            return None

    def delete_instance(self, instance_id):
        """
        Delete instance and associated services.

        Args:
            instance_id (int): The ID of the instance to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        try:
            instance = self.get_instance(instance_id)
            if not instance:
                return False

            instance_name = instance.name
            service_count = len(instance.services)

            # Delete the instance (cascade will handle services and ports)
            self.db.delete(instance)
            self.db.commit()

            logger.info(f"Deleted instance {instance_id}: {instance_name} (with {service_count} services)")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting instance {instance_id}: {str(e)}")
            return False

    def test_connection(self, instance_id):
        """
        Test connection to instance.

        Args:
            instance_id (int): The ID of the instance to test.

        Returns:
            dict: Test result with 'success' boolean and 'message' string.
        """
        try:
            instance = self.get_instance(instance_id)
            if not instance:
                return {'success': False, 'message': 'Instance not found'}

            if instance.type == 'docker':
                return self._test_docker_connection(instance)
            elif instance.type == 'portainer':
                return self._test_portainer_connection(instance)
            elif instance.type == 'komodo':
                return self._test_komodo_connection(instance)
            else:
                return {'success': False, 'message': f'Unknown instance type: {instance.type}'}

        except Exception as e:
            logger.error(f"Error testing connection for instance {instance_id}: {str(e)}")
            return {'success': False, 'message': f'Connection test failed: {str(e)}'}

    def get_client(self, instance_id):
        """
        Get appropriate client for instance.

        Args:
            instance_id (int): The ID of the instance.

        Returns:
            Client object or None if creation failed.
        """
        try:
            instance = self.get_instance(instance_id)
            if not instance or not instance.enabled:
                return None

            if instance.type == 'docker':
                return self._get_docker_client(instance)
            elif instance.type == 'portainer':
                return self._get_portainer_client(instance)
            elif instance.type == 'komodo':
                return self._get_komodo_client(instance)
            else:
                logger.error(f"Unknown instance type: {instance.type}")
                return None

        except Exception as e:
            logger.error(f"Error getting client for instance {instance_id}: {str(e)}")
            return None

    def generate_instance_name(self, instance_type):
        """
        Generate fallback name for instance.

        Args:
            instance_type (str): The type of instance.

        Returns:
            str: Generated instance name.
        """
        try:
            # Count existing instances of this type
            count = DockerInstance.query.filter_by(type=instance_type).count()

            type_names = {
                'docker': 'Docker',
                'portainer': 'Portainer',
                'komodo': 'Komodo'
            }

            base_name = type_names.get(instance_type, instance_type.capitalize())
            return f"{base_name} Instance {count + 1}"

        except Exception as e:
            logger.error(f"Error generating instance name: {str(e)}")
            return f"{instance_type.capitalize()} Instance"

    def validate_config(self, instance_type, config):
        """
        Validate instance configuration.

        Args:
            instance_type (str): The type of instance.
            config (dict): Configuration to validate.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        try:
            if not isinstance(config, dict):
                return False

            if instance_type == 'docker':
                return 'host' in config and config['host'].strip() != ''

            elif instance_type == 'portainer':
                return (
                    'url' in config and config['url'].strip() != '' and
                    'api_key' in config and config['api_key'].strip() != ''
                )

            elif instance_type == 'komodo':
                return (
                    'url' in config and config['url'].strip() != '' and
                    'api_key' in config and config['api_key'].strip() != '' and
                    'api_secret' in config and config['api_secret'].strip() != ''
                )

            return False

        except Exception as e:
            logger.error(f"Error validating config: {str(e)}")
            return False

    def _test_docker_connection(self, instance):
        """Test Docker connection."""
        try:
            client = self._get_docker_client(instance)
            if client:
                client.ping()
                return {'success': True, 'message': 'Docker connection successful'}
            else:
                return {'success': False, 'message': 'Failed to create Docker client'}
        except Exception as e:
            return {'success': False, 'message': f'Docker connection failed: {str(e)}'}

    def _test_portainer_connection(self, instance):
        """Test Portainer connection."""
        try:
            url = instance.get_config_value('url')
            api_key = instance.get_config_value('api_key')
            verify_ssl = instance.get_config_value('verify_ssl', True)

            headers = {'X-API-Key': api_key}
            response = requests.get(f"{url}/api/endpoints", headers=headers, verify=verify_ssl, timeout=10)

            if response.status_code == 200:
                return {'success': True, 'message': 'Portainer connection successful'}
            else:
                return {'success': False, 'message': f'Portainer API returned status {response.status_code}'}

        except Exception as e:
            return {'success': False, 'message': f'Portainer connection failed: {str(e)}'}

    def _test_komodo_connection(self, instance):
        """Test Komodo connection."""
        try:
            url = instance.get_config_value('url')
            api_key = instance.get_config_value('api_key')
            api_secret = instance.get_config_value('api_secret')

            headers = {
                'X-Api-Key': api_key,
                'X-Api-Secret': api_secret,
                'Content-Type': 'application/json'
            }

            response = requests.post(
                f"{url}/read",
                headers=headers,
                json={'type': 'ListStacks', 'params': {}},
                timeout=10
            )

            if response.status_code == 200:
                return {'success': True, 'message': 'Komodo connection successful'}
            else:
                return {'success': False, 'message': f'Komodo API returned status {response.status_code}'}

        except Exception as e:
            return {'success': False, 'message': f'Komodo connection failed: {str(e)}'}

    def _get_docker_client(self, instance):
        """Get Docker client for instance."""
        try:
            host = instance.get_config_value('host', 'unix:///var/run/docker.sock')
            timeout = instance.get_config_value('timeout', 30)

            if host == 'unix:///var/run/docker.sock':
                client = docker.from_env(timeout=timeout)
            else:
                client = docker.DockerClient(base_url=host, timeout=timeout)

            return client

        except Exception as e:
            logger.error(f"Error creating Docker client: {str(e)}")
            return None

    def _get_portainer_client(self, instance):
        """Get Portainer client configuration."""
        try:
            return {
                'url': instance.get_config_value('url'),
                'api_key': instance.get_config_value('api_key'),
                'verify_ssl': instance.get_config_value('verify_ssl', True)
            }
        except Exception as e:
            logger.error(f"Error creating Portainer client config: {str(e)}")
            return None

    def _get_komodo_client(self, instance):
        """Get Komodo client configuration."""
        try:
            return {
                'url': instance.get_config_value('url'),
                'api_key': instance.get_config_value('api_key'),
                'api_secret': instance.get_config_value('api_secret')
            }
        except Exception as e:
            logger.error(f"Error creating Komodo client config: {str(e)}")
            return None

    def scan_instance(self, instance_id):
        """
        Scan instance for containers and services.

        Args:
            instance_id (int): The ID of the instance to scan.

        Returns:
            dict: Scan result with 'success' boolean, 'message' string, and 'services_found' count.
        """
        try:
            instance = self.get_instance(instance_id)
            if not instance:
                return {'success': False, 'message': 'Instance not found', 'services_found': 0}

            if not instance.enabled:
                return {'success': False, 'message': 'Instance is disabled', 'services_found': 0}

            if instance.type == 'docker':
                return self._scan_docker_instance(instance)
            elif instance.type == 'portainer':
                return self._scan_portainer_instance(instance)
            elif instance.type == 'komodo':
                return self._scan_komodo_instance(instance)
            else:
                return {'success': False, 'message': f'Unknown instance type: {instance.type}', 'services_found': 0}

        except Exception as e:
            logger.error(f"Error scanning instance {instance_id}: {str(e)}")
            return {'success': False, 'message': f'Scan failed: {str(e)}', 'services_found': 0}

    def _scan_docker_instance(self, instance):
        """Scan Docker instance for containers."""
        try:
            from utils.database.docker import DockerService, DockerPort

            client = self._get_docker_client(instance)
            if not client:
                return {'success': False, 'message': 'Failed to create Docker client', 'services_found': 0}

            containers = client.containers.list(all=True)
            services_found = 0

            for container in containers:
                try:
                    # Get or create service record
                    service = DockerService.query.filter_by(
                        instance_id=instance.id,
                        container_id=container.id
                    ).first()

                    if not service:
                        service = DockerService(
                            instance_id=instance.id,
                            container_id=container.id,
                            name=container.name,
                            image=container.image.tags[0] if container.image.tags else 'unknown',
                            status=container.status
                        )
                        self.db.add(service)
                        services_found += 1
                    else:
                        # Update existing service
                        service.name = container.name
                        service.image = container.image.tags[0] if container.image.tags else 'unknown'
                        service.status = container.status
                        service.updated_at = datetime.utcnow()

                    # Update port mappings
                    if container.status == 'running' and hasattr(container, 'ports') and container.ports:
                        # Clear existing ports for this service
                        DockerPort.query.filter_by(service_id=service.id).delete()

                        # Add current port mappings
                        for container_port, host_bindings in container.ports.items():
                            if host_bindings:
                                for binding in host_bindings:
                                    port_record = DockerPort(
                                        service_id=service.id,
                                        host_ip=binding.get('HostIp', '0.0.0.0'),
                                        host_port=int(binding.get('HostPort', 0)),
                                        container_port=int(container_port.split('/')[0]),
                                        protocol=container_port.split('/')[1] if '/' in container_port else 'tcp'
                                    )
                                    self.db.add(port_record)

                except Exception as e:
                    logger.error(f"Error processing container {container.name}: {str(e)}")
                    continue

            self.db.commit()
            return {
                'success': True,
                'message': f'Scanned {len(containers)} containers, found {services_found} new services',
                'services_found': services_found
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error scanning Docker instance: {str(e)}")
            return {'success': False, 'message': f'Docker scan failed: {str(e)}', 'services_found': 0}

    def _scan_portainer_instance(self, instance):
        """Scan Portainer instance for containers."""
        try:
            from utils.database.docker import DockerService, DockerPort

            url = instance.get_config_value('url')
            api_key = instance.get_config_value('api_key')
            verify_ssl = instance.get_config_value('verify_ssl', True)

            headers = {'X-API-Key': api_key}

            # Get endpoints
            endpoints_response = requests.get(f"{url}/api/endpoints", headers=headers, verify=verify_ssl, timeout=10)
            if endpoints_response.status_code != 200:
                return {'success': False, 'message': 'Failed to get Portainer endpoints', 'services_found': 0}

            endpoints = endpoints_response.json()
            services_found = 0

            for endpoint in endpoints:
                endpoint_id = endpoint['Id']

                # Get containers for this endpoint
                containers_response = requests.get(
                    f"{url}/api/endpoints/{endpoint_id}/docker/containers/json?all=true",
                    headers=headers,
                    verify=verify_ssl,
                    timeout=10
                )

                if containers_response.status_code != 200:
                    continue

                containers = containers_response.json()

                for container in containers:
                    try:
                        container_id = container['Id']
                        container_name = container['Names'][0].lstrip('/') if container['Names'] else 'unknown'

                        # Get or create service record
                        service = DockerService.query.filter_by(
                            instance_id=instance.id,
                            container_id=container_id
                        ).first()

                        if not service:
                            service = DockerService(
                                instance_id=instance.id,
                                container_id=container_id,
                                name=container_name,
                                image=container['Image'],
                                status=container['State']
                            )
                            self.db.add(service)
                            services_found += 1
                        else:
                            # Update existing service
                            service.name = container_name
                            service.image = container['Image']
                            service.status = container['State']
                            service.updated_at = datetime.utcnow()

                        # Update port mappings
                        if container['State'] == 'running' and container.get('Ports'):
                            # Clear existing ports for this service
                            DockerPort.query.filter_by(service_id=service.id).delete()

                            # Add current port mappings
                            for port_info in container['Ports']:
                                if port_info.get('PublicPort'):
                                    port_record = DockerPort(
                                        service_id=service.id,
                                        host_ip=port_info.get('IP', '0.0.0.0'),
                                        host_port=port_info['PublicPort'],
                                        container_port=port_info['PrivatePort'],
                                        protocol=port_info.get('Type', 'tcp')
                                    )
                                    self.db.add(port_record)

                    except Exception as e:
                        logger.error(f"Error processing Portainer container {container.get('Names', ['unknown'])[0]}: {str(e)}")
                        continue

            self.db.commit()
            return {
                'success': True,
                'message': f'Scanned Portainer endpoints, found {services_found} new services',
                'services_found': services_found
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error scanning Portainer instance: {str(e)}")
            return {'success': False, 'message': f'Portainer scan failed: {str(e)}', 'services_found': 0}

    def _scan_komodo_instance(self, instance):
        """Scan Komodo instance for stacks and services."""
        try:
            from utils.database.docker import DockerService, DockerPort

            url = instance.get_config_value('url')
            api_key = instance.get_config_value('api_key')
            api_secret = instance.get_config_value('api_secret')

            headers = {
                'X-Api-Key': api_key,
                'X-Api-Secret': api_secret,
                'Content-Type': 'application/json'
            }

            # Get stacks
            stacks_response = requests.post(
                f"{url}/read",
                headers=headers,
                json={'type': 'ListStacks', 'params': {}},
                timeout=10
            )

            if stacks_response.status_code != 200:
                return {'success': False, 'message': 'Failed to get Komodo stacks', 'services_found': 0}

            stacks_data = stacks_response.json()
            stacks = stacks_data.get('stacks', [])
            services_found = 0

            for stack in stacks:
                try:
                    stack_name = stack.get('name', 'unknown')
                    stack_id = stack.get('id', 'unknown')

                    # Get stack details including services
                    stack_response = requests.post(
                        f"{url}/read",
                        headers=headers,
                        json={'type': 'GetStack', 'params': {'stack': stack_name}},
                        timeout=10
                    )

                    if stack_response.status_code != 200:
                        continue

                    stack_details = stack_response.json()
                    services = stack_details.get('services', [])

                    for service_info in services:
                        service_name = service_info.get('name', 'unknown')
                        container_id = f"komodo_{stack_name}_{service_name}"

                        # Get or create service record
                        service = DockerService.query.filter_by(
                            instance_id=instance.id,
                            container_id=container_id
                        ).first()

                        if not service:
                            service = DockerService(
                                instance_id=instance.id,
                                container_id=container_id,
                                name=f"{stack_name}/{service_name}",
                                image=service_info.get('image', 'unknown'),
                                status=service_info.get('state', 'unknown')
                            )
                            self.db.add(service)
                            services_found += 1
                        else:
                            # Update existing service
                            service.name = f"{stack_name}/{service_name}"
                            service.image = service_info.get('image', 'unknown')
                            service.status = service_info.get('state', 'unknown')
                            service.updated_at = datetime.utcnow()

                        # Note: Komodo port mapping extraction would need more specific API calls
                        # This is a basic implementation that could be enhanced

                except Exception as e:
                    logger.error(f"Error processing Komodo stack {stack.get('name', 'unknown')}: {str(e)}")
                    continue

            self.db.commit()
            return {
                'success': True,
                'message': f'Scanned Komodo stacks, found {services_found} new services',
                'services_found': services_found
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error scanning Komodo instance: {str(e)}")
            return {'success': False, 'message': f'Komodo scan failed: {str(e)}', 'services_found': 0}

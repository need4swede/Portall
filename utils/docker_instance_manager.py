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
                return self._validate_docker_config(config)

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

    def _validate_docker_config(self, config):
        """
        Validate Docker-specific configuration.

        Args:
            config (dict): Docker configuration to validate.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        try:
            # Basic host validation
            if 'host' not in config or not config['host'].strip():
                return False

            host = config['host'].strip()
            connection_type = config.get('connection_type', 'auto')

            # Auto-detect connection type if not specified
            if connection_type == 'auto':
                if host.startswith('unix://'):
                    connection_type = 'socket'
                elif host.startswith('ssh://'):
                    connection_type = 'ssh'
                elif host.startswith('tcp://'):
                    connection_type = 'tcp'
                else:
                    # Default to socket for backward compatibility
                    connection_type = 'socket'

            # Validate based on connection type
            if connection_type == 'socket':
                return True  # Basic host validation already done

            elif connection_type == 'ssh':
                # SSH connections require username
                if host.startswith('ssh://'):
                    # Parse ssh://user@host format
                    return '@' in host
                else:
                    # Require separate username field
                    return 'ssh_username' in config and config['ssh_username'].strip()

            elif connection_type == 'tcp':
                # TCP connections should have valid host:port format
                if host.startswith('tcp://'):
                    return True  # Basic format validation
                else:
                    return 'port' in config and isinstance(config.get('port'), int)

            return False

        except Exception as e:
            logger.error(f"Error validating Docker config: {str(e)}")
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
        """Get Docker client for instance with enhanced connection support."""
        try:
            host = instance.get_config_value('host', 'unix:///var/run/docker.sock')
            timeout = instance.get_config_value('timeout', 30)
            connection_type = instance.get_config_value('connection_type', 'auto')

            # Auto-detect connection type if not specified
            if connection_type == 'auto':
                connection_type = self._detect_connection_type(host)

            logger.info(f"Creating Docker client for {instance.name} using {connection_type} connection to {host}")

            # Create client based on connection type
            if connection_type == 'socket':
                return self._create_socket_client(instance, host, timeout)
            elif connection_type == 'ssh':
                return self._create_ssh_client(instance, host, timeout)
            elif connection_type == 'tcp':
                return self._create_tcp_client(instance, host, timeout)
            else:
                logger.error(f"Unknown connection type: {connection_type}")
                return None

        except Exception as e:
            logger.error(f"Error creating Docker client for {instance.name}: {str(e)}")
            return None

    def _detect_connection_type(self, host):
        """
        Auto-detect connection type based on host string.

        Args:
            host (str): Host connection string.

        Returns:
            str: Detected connection type ('socket', 'ssh', 'tcp').
        """
        if host.startswith('unix://') or host.startswith('/'):
            return 'socket'
        elif host.startswith('ssh://'):
            return 'ssh'
        elif host.startswith('tcp://'):
            return 'tcp'
        else:
            # Default to socket for backward compatibility
            return 'socket'

    def _create_socket_client(self, instance, host, timeout):
        """
        Create Docker client for Unix socket connection.

        Args:
            instance: DockerInstance object.
            host (str): Socket path.
            timeout (int): Connection timeout.

        Returns:
            docker.DockerClient: Docker client or None if failed.
        """
        try:
            if host == 'unix:///var/run/docker.sock' or host == '/var/run/docker.sock':
                # Use environment-based client for default socket
                client = docker.from_env(timeout=timeout)
            else:
                # Use custom socket path
                if not host.startswith('unix://'):
                    host = f'unix://{host}'
                client = docker.DockerClient(base_url=host, timeout=timeout)

            logger.debug(f"Created socket client for {instance.name} at {host}")
            return client

        except Exception as e:
            logger.error(f"Failed to create socket client for {instance.name}: {str(e)}")
            raise

    def _should_use_manual_ssh_tunnel(self):
        """
        Determine if we should use manual SSH tunnel instead of docker-py's SSH support.
        Start with False to try the standard approach first.
        """
        return False  # Try standard approach first, fall back to manual if needed

    def _test_ssh_connection(self, ssh_config):
        """
        Test SSH connection manually before creating Docker client.
        """
        try:
            import paramiko

            ssh_client = paramiko.SSHClient()

            # Load our custom known_hosts file
            ssh_dir = self._get_ssh_directory()
            known_hosts_file = ssh_dir / 'known_hosts'

            if known_hosts_file.exists():
                ssh_client.load_host_keys(str(known_hosts_file))

            # Set policy to reject unknown hosts
            ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())

            # Test connection
            connect_kwargs = {
                'hostname': ssh_config['host'],
                'port': ssh_config['port'],
                'username': ssh_config['username'],
                'timeout': 10
            }

            # Add private key if specified
            if ssh_config.get('key_path'):
                connect_kwargs['key_filename'] = ssh_config['key_path']

            logger.info(f"Testing SSH connection to {ssh_config['host']}:{ssh_config['port']} as {ssh_config['username']}")
            ssh_client.connect(**connect_kwargs)

            # Test if we can run a simple command
            stdin, stdout, stderr = ssh_client.exec_command('echo "SSH connection test successful"')
            result = stdout.read().decode().strip()
            error_output = stderr.read().decode().strip()

            if error_output:
                logger.warning(f"SSH test stderr: {error_output}")

            ssh_client.close()

            logger.info(f"SSH connection test successful: {result}")
            return True

        except Exception as e:
            logger.error(f"SSH connection test failed: {str(e)}")
            return False

    def _create_ssh_client(self, instance, host, timeout):
        """
        Create Docker client for SSH connection with improved error handling.
        """
        try:
            # Check if paramiko is available for SSH support
            try:
                import paramiko
                import os
            except ImportError:
                raise ImportError(
                    "SSH connections require the 'paramiko' package. "
                    "Install it with: pip install paramiko"
                )

            # Parse SSH connection details
            ssh_config = self._parse_ssh_config(instance, host)

            # Ensure SSH host key is available
            self._ensure_ssh_host_key(ssh_config)

            # Configure SSH environment
            self._configure_paramiko_known_hosts(ssh_config)

            # Test SSH connection manually first
            if not self._test_ssh_connection(ssh_config):
                logger.error("SSH connection test failed, cannot proceed")
                raise Exception("SSH connection test failed")

            # Try standard docker-py SSH approach first
            if not self._should_use_manual_ssh_tunnel():
                try:
                    # Build SSH connection string
                    ssh_host = self._build_ssh_connection_string(ssh_config)
                    logger.info(f"Attempting standard SSH connection: {ssh_host}")

                    # Create Docker client with SSH connection
                    client = docker.DockerClient(base_url=ssh_host, timeout=timeout)

                    # Test the client with a simple ping
                    client.ping()

                    logger.info(f"Successfully created standard SSH client for {instance.name}")
                    return client

                except Exception as e:
                    logger.warning(f"Standard SSH approach failed: {str(e)}, trying manual tunnel")
                    # Fall back to manual tunnel
                    pass

            # Use manual SSH tunnel approach
            logger.info(f"Using manual SSH tunnel for {instance.name}")
            return self._create_manual_ssh_tunnel_client(instance, ssh_config, timeout)

        except Exception as e:
            logger.error(f"Failed to create SSH client for {instance.name}: {str(e)}")
            raise

    def _create_manual_ssh_tunnel_client(self, instance, ssh_config, timeout):
        """
        Create Docker client using manual SSH tunnel.
        This approach gives us more control over SSH connection parameters.
        """
        try:
            import paramiko
            import socket
            import threading
            import time

            # Create SSH client
            ssh_client = paramiko.SSHClient()

            # Load our custom known_hosts file
            ssh_dir = self._get_ssh_directory()
            known_hosts_file = ssh_dir / 'known_hosts'

            if known_hosts_file.exists():
                ssh_client.load_host_keys(str(known_hosts_file))

            # Set policy to reject unknown hosts
            ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())

            # Connect to SSH server
            connect_kwargs = {
                'hostname': ssh_config['host'],
                'port': ssh_config['port'],
                'username': ssh_config['username'],
                'timeout': timeout
            }

            # Add private key if specified
            if ssh_config.get('key_path'):
                connect_kwargs['key_filename'] = ssh_config['key_path']

            logger.info(f"Establishing SSH connection for tunnel to {ssh_config['host']}")
            ssh_client.connect(**connect_kwargs)

            # Find a free local port for the tunnel
            local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_socket.bind(('127.0.0.1', 0))
            local_port = local_socket.getsockname()[1]
            local_socket.close()

            logger.info(f"Creating SSH tunnel on local port {local_port}")

            # Create the tunnel in a separate thread
            tunnel_active = threading.Event()
            tunnel_error = threading.Event()

            def tunnel_worker():
                try:
                    # Create server socket for tunnel
                    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server_socket.bind(('127.0.0.1', local_port))
                    server_socket.listen(1)
                    server_socket.settimeout(1.0)  # Allow periodic checks

                    tunnel_active.set()
                    logger.debug(f"SSH tunnel listening on 127.0.0.1:{local_port}")

                    while not tunnel_error.is_set():
                        try:
                            client_socket, addr = server_socket.accept()
                            logger.debug(f"Accepted tunnel connection from {addr}")

                            # Create SSH channel for Docker socket
                            # Try Unix socket first, fall back to TCP
                            try:
                                ssh_channel = ssh_client.get_transport().open_channel(
                                    'direct-streamlocal',
                                    '/var/run/docker.sock',
                                    addr
                                )
                            except paramiko.ChannelException:
                                # Fall back to TCP connection (Docker daemon on port 2375/2376)
                                ssh_channel = ssh_client.get_transport().open_channel(
                                    'direct-tcpip',
                                    ('127.0.0.1', 2375),
                                    addr
                                )

                            # Start data forwarding in separate threads
                            self._forward_tunnel_data(client_socket, ssh_channel)

                        except socket.timeout:
                            # Normal timeout, continue loop
                            continue
                        except Exception as e:
                            logger.error(f"Error accepting tunnel connection: {str(e)}")
                            # Don't break the loop for individual connection errors
                            continue

                except Exception as e:
                    logger.error(f"SSH tunnel worker failed: {str(e)}")
                    tunnel_error.set()
                finally:
                    try:
                        server_socket.close()
                    except:
                        pass

            # Start tunnel worker thread
            tunnel_thread = threading.Thread(target=tunnel_worker, daemon=True)
            tunnel_thread.start()

            # Wait for tunnel to be ready
            if not tunnel_active.wait(timeout=10):
                tunnel_error.set()
                ssh_client.close()
                raise Exception("SSH tunnel failed to start within 10 seconds")

            if tunnel_error.is_set():
                ssh_client.close()
                raise Exception("SSH tunnel encountered an error during startup")

            # Give the tunnel a moment to stabilize
            time.sleep(0.5)

            # Create Docker client using the tunnel
            tunnel_url = f'tcp://127.0.0.1:{local_port}'
            logger.info(f"Creating Docker client using SSH tunnel: {tunnel_url}")

            client = docker.DockerClient(base_url=tunnel_url, timeout=timeout)

            # Test the connection
            try:
                client.ping()
                logger.info(f"Successfully created SSH tunnel client for {instance.name}")
                return client
            except Exception as e:
                tunnel_error.set()
                ssh_client.close()
                raise Exception(f"Docker client test failed through SSH tunnel: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to create manual SSH tunnel for {instance.name}: {str(e)}")
            raise

    def _forward_tunnel_data(self, client_socket, ssh_channel):
        """
        Forward data between client socket and SSH channel.
        """
        import threading

        def forward(source, destination, direction):
            try:
                while True:
                    try:
                        data = source.recv(4096)
                        if not data:
                            break
                        destination.send(data)
                    except Exception as e:
                        logger.debug(f"Tunnel forwarding {direction} ended: {str(e)}")
                        break
            except Exception as e:
                logger.debug(f"Error in tunnel forwarding {direction}: {str(e)}")
            finally:
                try:
                    source.close()
                except:
                    pass
                try:
                    destination.close()
                except:
                    pass

        # Start forwarding in both directions
        thread1 = threading.Thread(
            target=forward,
            args=(client_socket, ssh_channel, "client->ssh"),
            daemon=True
        )
        thread2 = threading.Thread(
            target=forward,
            args=(ssh_channel, client_socket, "ssh->client"),
            daemon=True
        )

        thread1.start()
        thread2.start()

    def _ensure_ssh_host_key(self, ssh_config):
        """
        Ensure SSH host key is available in known_hosts.
        Automatically fetches and stores host keys if missing.
        Uses container-isolated SSH directory for security.

        Args:
            ssh_config (dict): SSH configuration containing host and port.
        """
        try:
            import subprocess
            import os
            from pathlib import Path

            host = ssh_config['host']
            port = ssh_config.get('port', 22)

            # Use container-isolated SSH directory
            ssh_dir = self._get_ssh_directory()
            known_hosts_file = ssh_dir / 'known_hosts'

            # Check if host key already exists
            if known_hosts_file.exists():
                try:
                    with open(known_hosts_file, 'r') as f:
                        known_hosts_content = f.read()
                        # Check for host (with or without port specification)
                        if host in known_hosts_content or f'[{host}]:{port}' in known_hosts_content:
                            logger.debug(f"SSH host key for {host}:{port} already exists in known_hosts")
                            return
                except Exception as e:
                    logger.warning(f"Error reading known_hosts file: {str(e)}")

            # Host key not found, fetch it automatically
            logger.info(f"Fetching SSH host key for {host}:{port}")

            # Use ssh-keyscan to fetch the host key
            cmd = ['ssh-keyscan', '-p', str(port), host]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True
                )

                if result.stdout.strip():
                    # Extract and log host key fingerprint for security audit
                    self._log_host_key_fingerprint(host, port, result.stdout)

                    # Append the host key to known_hosts
                    with open(known_hosts_file, 'a') as f:
                        f.write(result.stdout)
                        if not result.stdout.endswith('\n'):
                            f.write('\n')

                    # Set proper permissions
                    known_hosts_file.chmod(0o600)

                    logger.info(f"Successfully added SSH host key for {host}:{port} to container-isolated known_hosts")
                else:
                    logger.warning(f"ssh-keyscan returned empty result for {host}:{port}")

            except subprocess.TimeoutExpired:
                logger.error(f"Timeout while fetching SSH host key for {host}:{port}")
                raise Exception(f"Timeout connecting to SSH host {host}:{port}")

            except subprocess.CalledProcessError as e:
                logger.error(f"ssh-keyscan failed for {host}:{port}: {e.stderr}")
                raise Exception(f"Failed to fetch SSH host key for {host}:{port}: {e.stderr}")

            except FileNotFoundError:
                logger.error("ssh-keyscan command not found. SSH client tools may not be installed.")
                raise Exception("SSH client tools not available. Cannot fetch host keys automatically.")

        except Exception as e:
            logger.error(f"Error ensuring SSH host key for {ssh_config['host']}: {str(e)}")
            # Re-raise the exception to let the caller handle it
            raise

    def _get_ssh_directory(self):
        """
        Get or create the container-isolated SSH directory.

        Returns:
            Path: SSH directory path with proper permissions.
        """
        try:
            from pathlib import Path
            import os

            # Use application directory for SSH storage (container-isolated)
            app_dir = Path('/app')
            if not app_dir.exists() or not os.access(app_dir, os.W_OK):
                # Fallback to /tmp if /app is not writable
                ssh_dir = Path('/tmp/portall_ssh')
                logger.info("Using /tmp/portall_ssh for SSH storage (fallback)")
            else:
                ssh_dir = app_dir / 'ssh'
                logger.debug("Using /app/ssh for SSH storage")

            # Create SSH directory with secure permissions
            ssh_dir.mkdir(mode=0o700, exist_ok=True)

            # Create subdirectories for organization
            keys_dir = ssh_dir / 'keys'
            keys_dir.mkdir(mode=0o700, exist_ok=True)

            # Ensure proper permissions on existing directory
            ssh_dir.chmod(0o700)
            keys_dir.chmod(0o700)

            logger.debug(f"SSH directory ready: {ssh_dir}")
            return ssh_dir

        except Exception as e:
            logger.error(f"Failed to create SSH directory: {str(e)}")
            raise Exception(f"Cannot create secure SSH directory: {str(e)}")

    def _log_host_key_fingerprint(self, host, port, host_key_data):
        """
        Log SSH host key fingerprint for security audit trail.

        Args:
            host (str): SSH host.
            port (int): SSH port.
            host_key_data (str): Raw host key data from ssh-keyscan.
        """
        try:
            import hashlib
            import base64

            # Extract the key part (skip hostname and key type)
            lines = host_key_data.strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        key_type = parts[1]
                        key_data = parts[2]

                        # Calculate SHA256 fingerprint
                        key_bytes = base64.b64decode(key_data)
                        fingerprint = hashlib.sha256(key_bytes).digest()
                        fingerprint_b64 = base64.b64encode(fingerprint).decode().rstrip('=')

                        logger.info(f"SSH host key fingerprint for {host}:{port} ({key_type}): SHA256:{fingerprint_b64}")
                        break

        except Exception as e:
            logger.warning(f"Could not calculate host key fingerprint for {host}:{port}: {str(e)}")

    def _configure_paramiko_known_hosts(self, ssh_config):
        """
        Configure paramiko to use our custom known_hosts file.
        """
        try:
            import paramiko
            import os

            # Get our custom known_hosts file
            ssh_dir = self._get_ssh_directory()
            known_hosts_file = ssh_dir / 'known_hosts'

            # Method 1: Set environment variables (most reliable)
            os.environ['SSH_KNOWN_HOSTS'] = str(known_hosts_file)
            os.environ['SSH_USER_KNOWN_HOSTS_FILE'] = str(known_hosts_file)

            # Method 2: Configure paramiko's default SSH config directory
            paramiko_ssh_dir = ssh_dir / 'paramiko_config'
            paramiko_ssh_dir.mkdir(exist_ok=True)

            # Create a paramiko-compatible config
            config_file = paramiko_ssh_dir / 'config'
            with open(config_file, 'w') as f:
                f.write(f"Host *\n")
                f.write(f"    UserKnownHostsFile {known_hosts_file}\n")
                f.write(f"    StrictHostKeyChecking yes\n")

            # Set SSH config file location
            os.environ['SSH_CONFIG_FILE'] = str(config_file)

            logger.info(f"Configured paramiko to use known_hosts file: {known_hosts_file}")

        except Exception as e:
            logger.warning(f"Could not configure paramiko known_hosts: {str(e)}")

    def _create_tcp_client(self, instance, host, timeout):
        """
        Create Docker client for TCP connection.

        Args:
            instance: DockerInstance object.
            host (str): TCP connection string.
            timeout (int): Connection timeout.

        Returns:
            docker.DockerClient: Docker client or None if failed.
        """
        try:
            # Parse TCP connection details
            tcp_config = self._parse_tcp_config(instance, host)

            # Build TCP connection string
            tcp_host = self._build_tcp_connection_string(tcp_config)

            # Configure TLS if enabled
            tls_config = None
            if tcp_config.get('tls_enabled', False):
                tls_config = self._create_tls_config(instance, tcp_config)

            logger.debug(f"Creating TCP client for {instance.name} to {tcp_config['host']}:{tcp_config['port']}")

            # Create Docker client with TCP connection
            client = docker.DockerClient(
                base_url=tcp_host,
                timeout=timeout,
                tls=tls_config
            )

            logger.info(f"Created TCP client for {instance.name} to {tcp_config['host']}:{tcp_config['port']}")
            return client

        except Exception as e:
            logger.error(f"Failed to create TCP client for {instance.name}: {str(e)}")
            raise

    def _parse_ssh_config(self, instance, host):
        """
        Parse SSH connection configuration.

        Args:
            instance: DockerInstance object.
            host (str): SSH host string.

        Returns:
            dict: SSH configuration.
        """
        config = {
            'host': None,
            'username': None,
            'port': 22,
            'key_path': None
        }

        if host.startswith('ssh://'):
            # Parse ssh://user@host:port format
            import re
            match = re.match(r'ssh://(?:([^@]+)@)?([^:]+)(?::(\d+))?', host)
            if match:
                config['username'] = match.group(1)
                config['host'] = match.group(2)
                if match.group(3):
                    config['port'] = int(match.group(3))
        else:
            config['host'] = host

        # Override with instance-specific config
        config['username'] = instance.get_config_value('ssh_username', config['username'])
        config['port'] = instance.get_config_value('ssh_port', config['port'])
        config['key_path'] = instance.get_config_value('ssh_key_path')

        if not config['host']:
            raise ValueError("SSH host is required")
        if not config['username']:
            raise ValueError("SSH username is required")

        return config

    def _parse_tcp_config(self, instance, host):
        """
        Parse TCP connection configuration.

        Args:
            instance: DockerInstance object.
            host (str): TCP host string.

        Returns:
            dict: TCP configuration.
        """
        config = {
            'host': None,
            'port': 2376,  # Default Docker TLS port
            'tls_enabled': False
        }

        if host.startswith('tcp://'):
            # Parse tcp://host:port format
            import re
            match = re.match(r'tcp://([^:]+)(?::(\d+))?', host)
            if match:
                config['host'] = match.group(1)
                if match.group(2):
                    config['port'] = int(match.group(2))
                    # Auto-detect TLS based on port
                    config['tls_enabled'] = config['port'] == 2376
        else:
            config['host'] = host

        # Override with instance-specific config
        config['port'] = instance.get_config_value('tcp_port', config['port'])
        config['tls_enabled'] = instance.get_config_value('tls_enabled', config['tls_enabled'])

        if not config['host']:
            raise ValueError("TCP host is required")

        return config

    def _build_ssh_connection_string(self, ssh_config):
        """
        Build SSH connection string for Docker client.
        """
        # Build base SSH connection string
        ssh_host = f"ssh://{ssh_config['username']}@{ssh_config['host']}"

        if ssh_config['port'] != 22:
            ssh_host += f":{ssh_config['port']}"

        return ssh_host

    def _build_tcp_connection_string(self, tcp_config):
        """
        Build TCP connection string for Docker client.

        Args:
            tcp_config (dict): TCP configuration.

        Returns:
            str: TCP connection string.
        """
        protocol = 'https' if tcp_config['tls_enabled'] else 'http'
        return f"{protocol}://{tcp_config['host']}:{tcp_config['port']}"

    def _create_tls_config(self, instance, tcp_config):
        """
        Create TLS configuration for Docker client.

        Args:
            instance: DockerInstance object.
            tcp_config (dict): TCP configuration.

        Returns:
            docker.tls.TLSConfig: TLS configuration or None.
        """
        try:
            import docker.tls

            verify = instance.get_config_value('tls_verify', True)
            cert_path = instance.get_config_value('tls_cert_path')
            key_path = instance.get_config_value('tls_key_path')
            ca_cert_path = instance.get_config_value('tls_ca_path')

            if cert_path and key_path:
                # Client certificate authentication
                return docker.tls.TLSConfig(
                    client_cert=(cert_path, key_path),
                    ca_cert=ca_cert_path,
                    verify=verify
                )
            elif verify and ca_cert_path:
                # CA certificate verification only
                return docker.tls.TLSConfig(
                    ca_cert=ca_cert_path,
                    verify=verify
                )
            elif verify:
                # Default TLS verification
                return docker.tls.TLSConfig(verify=verify)
            else:
                # TLS without verification (not recommended)
                return docker.tls.TLSConfig(verify=False)

        except Exception as e:
            logger.error(f"Failed to create TLS config for {instance.name}: {str(e)}")
            raise

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
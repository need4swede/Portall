# utils/database/docker.py

from .db import db
from datetime import datetime
import json

class DockerInstance(db.Model):
    """
    Represents a Docker, Portainer, or Komodo instance configuration.
    Supports multiple instances of each integration type.
    """
    __tablename__ = 'docker_instance'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum('docker', 'portainer', 'komodo', name='instance_type'), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    auto_detect = db.Column(db.Boolean, default=True)
    scan_interval = db.Column(db.Integer, default=300)
    config = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    services = db.relationship('DockerService', backref='instance', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<DockerInstance {self.name} ({self.type})>'

    def get_config_value(self, key, default=None):
        """
        Get a specific configuration value.

        Args:
            key (str): The configuration key to retrieve.
            default: Default value if key is not found.

        Returns:
            The configuration value or default.
        """
        if isinstance(self.config, dict):
            return self.config.get(key, default)
        return default

    def set_config_value(self, key, value):
        """
        Set a specific configuration value.

        Args:
            key (str): The configuration key to set.
            value: The value to set.
        """
        if not isinstance(self.config, dict):
            self.config = {}
        self.config[key] = value
        # Mark the column as modified for SQLAlchemy to detect changes
        db.session.merge(self)

    def to_dict(self):
        """
        Convert the instance to a dictionary for JSON serialization.

        Returns:
            dict: Dictionary representation of the instance.
        """
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'enabled': self.enabled,
            'auto_detect': self.auto_detect,
            'scan_interval': self.scan_interval,
            'config': self.config,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'service_count': len(self.services) if self.services else 0
        }

    @staticmethod
    def get_default_config(instance_type, connection_type='socket'):
        """
        Get default configuration for a given instance type.

        Args:
            instance_type (str): The type of instance ('docker', 'portainer', 'komodo').
            connection_type (str): The connection type for Docker instances ('socket', 'ssh', 'tcp').

        Returns:
            dict: Default configuration for the instance type.
        """
        if instance_type == 'docker':
            base_config = {
                'connection_type': connection_type,
                'timeout': 30
            }

            if connection_type == 'socket':
                base_config.update({
                    'host': 'unix:///var/run/docker.sock'
                })
            elif connection_type == 'ssh':
                base_config.update({
                    'host': '',
                    'ssh_username': '',
                    'ssh_port': 22,
                    'ssh_key_path': ''
                })
            elif connection_type == 'tcp':
                base_config.update({
                    'host': '',
                    'tcp_port': 2376,
                    'tls_enabled': True,
                    'tls_verify': True,
                    'tls_cert_path': '',
                    'tls_key_path': '',
                    'tls_ca_path': ''
                })

            return base_config

        elif instance_type == 'portainer':
            return {
                'url': '',
                'api_key': '',
                'verify_ssl': True
            }

        elif instance_type == 'komodo':
            return {
                'url': '',
                'api_key': '',
                'api_secret': ''
            }

        return {}

    @staticmethod
    def get_connection_type_options():
        """
        Get available connection type options for Docker instances.

        Returns:
            dict: Connection type options with descriptions.
        """
        return {
            'socket': {
                'name': 'Local Socket',
                'description': 'Connect to local Docker daemon via Unix socket',
                'icon': 'fas fa-plug',
                'example': 'unix:///var/run/docker.sock'
            },
            'ssh': {
                'name': 'SSH Connection',
                'description': 'Connect to remote Docker daemon via SSH tunnel',
                'icon': 'fas fa-key',
                'example': 'ssh://user@remote-host'
            },
            'tcp': {
                'name': 'TCP Connection',
                'description': 'Connect to remote Docker daemon via TCP (with/without TLS)',
                'icon': 'fas fa-network-wired',
                'example': 'tcp://remote-host:2376'
            }
        }

class DockerService(db.Model):
    """
    Represents a Docker service detected by the auto port detection feature.
    """
    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey('docker_instance.id', ondelete='CASCADE'), nullable=True)
    container_id = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DockerPort(db.Model):
    """
    Represents a port mapping for a Docker service.
    """
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('docker_service.id', ondelete='CASCADE'), nullable=False)
    host_ip = db.Column(db.String(15), nullable=False)
    host_port = db.Column(db.Integer, nullable=False)
    container_port = db.Column(db.Integer, nullable=False)
    protocol = db.Column(db.String(3), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to DockerService
    service = db.relationship('DockerService', backref=db.backref('ports', cascade='all, delete-orphan'))

class PortScan(db.Model):
    """
    Represents a port scan request with enhanced capabilities.
    """
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False)
    port_range_start = db.Column(db.Integer, default=1)
    port_range_end = db.Column(db.Integer, default=65535)
    excluded_ports = db.Column(db.Text)  # JSON array of excluded ports
    scan_type = db.Column(db.String(10), default='TCP')  # TCP, UDP, BOTH
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, failed
    discovered_ports = db.Column(db.Text)  # JSON array of discovered ports
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    scheduled_scan = db.Column(db.Boolean, default=False)
    next_scan_time = db.Column(db.DateTime, nullable=True)
    scan_duration = db.Column(db.Float, nullable=True)  # Duration in seconds
    ports_scanned = db.Column(db.Integer, default=0)
    ports_found = db.Column(db.Integer, default=0)

class PortScanSchedule(db.Model):
    """
    Represents a scheduled port scan configuration.
    """
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False)
    port_range_start = db.Column(db.Integer, default=1024)
    port_range_end = db.Column(db.Integer, default=65535)
    excluded_ports = db.Column(db.Text)  # JSON array of excluded ports
    scan_type = db.Column(db.String(10), default='TCP')  # TCP, UDP, BOTH
    scan_interval = db.Column(db.Integer, nullable=False)  # seconds
    enabled = db.Column(db.Boolean, default=True)
    last_scan = db.Column(db.DateTime, nullable=True)
    next_scan = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('ip_address', name='_ip_schedule_uc'),)

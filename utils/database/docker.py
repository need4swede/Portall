# utils/database/docker.py

from .db import db
from datetime import datetime

class DockerService(db.Model):
    """
    Represents a Docker service detected by the auto port detection feature.
    """
    id = db.Column(db.Integer, primary_key=True)
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

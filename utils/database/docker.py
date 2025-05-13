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
    Represents a port scan request.
    """
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (db.UniqueConstraint('ip_address', 'status', name='_ip_status_uc'),)

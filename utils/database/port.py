# utils/database/port.py

from .db import db

class Port(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False)
    nickname = db.Column(db.String(50), nullable=True)
    port_number = db.Column(db.Integer, nullable=False)
    port_protocol = db.Column(db.String(3), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, default=0)
    source = db.Column(db.String(20), nullable=True)  # 'manual', 'docker', 'portainer', etc.
    is_immutable = db.Column(db.Boolean, default=False)  # If True, port number, protocol can't be changed and port can't be deleted

    __table_args__ = (db.UniqueConstraint('ip_address', 'port_number', 'port_protocol', name='_ip_port_protocol_uc'),)

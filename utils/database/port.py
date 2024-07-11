# utils/database/port.py

from .db import db

class Port(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False)
    nickname = db.Column(db.String(50), nullable=True)
    port_number = db.Column(db.Interger, nullable=False)
    description = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, default=0)
    docker_id = db.Column(db.String(20), nullable=True)

    __table_args__ = (db.UniqueConstraint('ip_address', 'port_number', name='_ip_port_uc'),)
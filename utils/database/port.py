# utils/database/port.py

from .db import db

class Port(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False)
    nickname = db.Column(db.String(50))
    port_number = db.Column(db.Integer, nullable=False)
    port_protocol = db.Column(db.String(3), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('ip_address', 'port_number', name='_ip_port_uc'),)
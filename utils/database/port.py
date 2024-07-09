# utils/database/port.py

from .db import db

class Port(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False)
    nickname = db.Column(db.String(50))
    port_number = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, default=0)
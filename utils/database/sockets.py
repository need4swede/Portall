# utils/database/sockets.py

from .db import db

class Sockets(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False)
    docker_url = db.Column(db.String(50), nullable=True)
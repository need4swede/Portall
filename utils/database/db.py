# utils/database/db.py

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    return db

def create_tables(app):
    with app.app_context():
        db.create_all()
# utils/routes/__init__.py

# Import Blueprints
from flask import Blueprint
from .imports import imports_bp
from .index import index_bp
from .ports import ports_bp
from .settings import settings_bp

# Register Blueprints
routes_bp = Blueprint('routes', __name__)
routes_bp.register_blueprint(imports_bp)
routes_bp.register_blueprint(index_bp)
routes_bp.register_blueprint(ports_bp)
routes_bp.register_blueprint(settings_bp)
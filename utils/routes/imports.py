# Standard Imports
import json                                     # For parsing JSON data
import yaml                                     # For parsing YAML data

# External Imports
from flask import Blueprint                     # For creating a blueprint
from flask import jsonify                       # For returning JSON responses
from flask import render_template               # For rendering HTML templates
from flask import request                       # For handling HTTP requests
from flask import session                       # For storing session data

# Local Imports
from utils.database import db, Port            # For accessing the database models

# Create the blueprint
imports_bp = Blueprint('imports', __name__)

@imports_bp.route('/import', methods=['GET', 'POST'])
def import_data():
    if request.method == 'POST':
        import_type = request.form.get('import_type')
        file_content = request.form.get('file_content')

        if import_type == 'Caddyfile':
            imported_data = import_caddyfile(file_content)
        elif import_type == 'JSON':
            imported_data = import_json(file_content)
        elif import_type == 'Docker-Compose':
            imported_data = import_docker_compose(file_content)
        else:
            return jsonify({'success': False, 'message': 'Unsupported import type'}), 400

        # Process the imported data
        for item in imported_data:
            port = Port(ip_address=item['ip'], port_number=item['port'], description=item['description'])
            db.session.add(port)
        db.session.commit()

        # Return a success response
        return jsonify({'success': True, 'message': f'Imported {len(imported_data)} entries'})

    # For GET requests, render the template
    return render_template('imPort.html', theme=session.get('theme', 'light'))

def import_caddyfile(content):
    entries = []
    lines = content.split('\n')
    current_domain = None

    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            if '{' in line:
                current_domain = line.split('{')[0].strip()
            elif 'reverse_proxy' in line:
                parts = line.split()
                if len(parts) > 1:
                    ip_port = parts[-1]
                    ip, port = ip_port.split(':')
                    entries.append({
                        'ip': ip,
                        'port': int(port),
                        'description': current_domain
                    })

    return entries

def import_json(content):
    try:
        data = json.loads(content)
        entries = []
        for item in data:
            entries.append({
                'ip': item['ip'],
                'port': int(item['port']),
                'description': item.get('description', '')
            })
        return entries
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format")

import yaml

def import_docker_compose(content):
    try:
        # Split the content into separate documents
        documents = content.split('version:')
        entries = []

        for doc in documents:
            if doc.strip():
                # Add back the 'version:' prefix and parse
                data = yaml.safe_load('version:' + doc)
                if isinstance(data, dict) and 'services' in data:
                    for service_name, service_config in data.get('services', {}).items():
                        ports = service_config.get('ports', [])
                        for port_mapping in ports:
                            if isinstance(port_mapping, str) and ':' in port_mapping:
                                host_port, container_port = port_mapping.split(':')
                                entries.append({
                                    'ip': '127.0.0.1',  # Assuming localhost, adjust if needed
                                    'port': int(host_port),
                                    'description': f"{service_name} - {container_port}"
                                })
        return entries
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid Docker-Compose YAML format: {str(e)}")
# utils/routes/ports.py

# Standard Imports
import json                                     # For parsing JSON data
import random                                   # For generating random ports

# External Imports
from flask import Blueprint                     # For creating a blueprint
from flask import current_app as app            # For accessing the Flask app
from flask import jsonify                       # For returning JSON responses
from flask import render_template               # For rendering HTML templates
from flask import request                       # For handling HTTP requests
from flask import session                       # For storing session data
from flask import url_for                       # For generating URLs

# Local Imports
from utils.database import db, Port, Setting    # For accessing the database models

# Create the blueprint
ports_bp = Blueprint('ports', __name__)

@ports_bp.route('/ports')
def ports():
    ports = Port.query.order_by(Port.ip_order, Port.ip_address).all()
    ports_by_ip = {}
    for port in ports:
        if port.ip_address not in ports_by_ip:
            ports_by_ip[port.ip_address] = {'nickname': port.nickname, 'ports': []}
        ports_by_ip[port.ip_address]['ports'].append(port)
    theme = session.get('theme', 'light')
    return render_template('ports.html', ports_by_ip=ports_by_ip, theme=theme)

@ports_bp.route('/generate_port', methods=['POST'])
def generate_port():
    ip_address = request.form['ip_address']
    nickname = request.form['nickname']
    description = request.form['description']
    app.logger.debug(f"Received request to generate port for IP: {ip_address}, Nickname: {nickname}, Description: {description}")

    def get_setting(key, default):
        setting = Setting.query.filter_by(key=key).first()
        return setting.value if setting else default

    port_start = int(get_setting('port_start', 1024))
    port_end = int(get_setting('port_end', 65535))
    port_exclude = get_setting('port_exclude', '')
    port_length = int(get_setting('port_length', 0))

    # Get existing ports for this IP
    existing_ports = set(p.port_number for p in Port.query.filter_by(ip_address=ip_address).all())

    # Create set of excluded ports
    excluded_ports = set()
    if port_exclude:
        excluded_ports.update(int(p.strip()) for p in port_exclude.split(',') if p.strip().isdigit())

    # Generate list of available ports
    available_ports = [p for p in range(port_start, port_end + 1)
                       if p not in excluded_ports and
                       (port_length == 0 or len(str(p)) == port_length)]

    # Count ports in use within the current range
    ports_in_use = sum(1 for p in existing_ports if p in available_ports)

    if not available_ports or all(p in existing_ports for p in available_ports):
        total_ports = len(available_ports)
        app.logger.error(f"No available ports for IP: {ip_address}. Used {ports_in_use} out of {total_ports} possible ports.")
        settings_url = url_for('routes.settings.settings', _external=True) + '#ports'
        error_message = (
            f"No available ports.\n"
            f"Used {ports_in_use} out of {total_ports} possible ports.\n"
            f"Consider expanding your port range in the <a href='{settings_url}'>settings</a>."
        )
        return jsonify({'error': error_message, 'html': True}), 400

    new_port = random.choice([p for p in available_ports if p not in existing_ports])

    try:
        port = Port(ip_address=ip_address, nickname=nickname, port_number=new_port, description=description)
        db.session.add(port)
        db.session.commit()
        app.logger.info(f"Generated new port {new_port} for IP: {ip_address}")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving new port: {str(e)}")
        return jsonify({'error': 'Error saving new port'}), 500

    full_url = f"http://{ip_address}:{new_port}"
    return jsonify({'port': new_port, 'full_url': full_url})

@ports_bp.route('/edit_port', methods=['POST'])
def edit_port():
    new_port_number = request.form['new_port_number']
    old_port_number = request.form['old_port_number']
    ip_address = request.form['ip']
    description = request.form['description']
    try:
        port_entry = Port.query.filter_by(ip_address=ip_address, port_number=old_port_number).first()
        if port_entry:
            port_entry.port_number = new_port_number
            port_entry.description = description
            db.session.commit()
            return jsonify({'success': True, 'message': 'Port updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Port entry not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@ports_bp.route('/edit_ip', methods=['POST'])
def edit_ip():
    old_ip = request.form['old_ip']
    new_ip = request.form['new_ip']
    new_nickname = request.form['new_nickname']

    try:
        # Find all ports associated with the old IP
        ports = Port.query.filter_by(ip_address=old_ip).all()

        if not ports:
            return jsonify({'success': False, 'message': 'No ports found for the given IP'}), 404

        # Update IP and nickname for all associated ports
        for port in ports:
            port.ip_address = new_ip
            port.nickname = new_nickname

        # Commit changes to the database
        db.session.commit()

        return jsonify({'success': True, 'message': 'IP updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating IP: {str(e)}'}), 500

@ports_bp.route('/delete_ip', methods=['POST'])
def delete_ip():
    ip = request.form['ip']

    try:
        # Delete all ports associated with the IP
        ports = Port.query.filter_by(ip_address=ip).all()
        for port in ports:
            db.session.delete(port)

        # Commit changes to the database
        db.session.commit()

        return jsonify({'success': True, 'message': 'IP and all assigned ports deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting IP: {str(e)}'}), 500

@ports_bp.route('/add_port', methods=['POST'])
def add_port():
    ip_address = request.form['ip']
    port_number = request.form['port_number']
    description = request.form['description']

    try:
        port = Port(ip_address=ip_address, port_number=port_number, description=description)
        db.session.add(port)
        db.session.commit()
        app.logger.info(f"Added new port {port_number} for IP: {ip_address}")
        return jsonify({'success': True, 'message': 'Port added successfully'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding new port: {str(e)}")
        return jsonify({'success': False, 'message': 'Error adding new port'}), 500

@ports_bp.route('/delete_port', methods=['POST'])
def delete_port():
    ip_address = request.form['ip']
    port_number = request.form['port_number']

    try:
        port = Port.query.filter_by(ip_address=ip_address, port_number=port_number).first()
        if port:
            db.session.delete(port)
            db.session.commit()
            app.logger.info(f"Deleted port {port_number} for IP: {ip_address}")
            return jsonify({'success': True, 'message': 'Port deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Port not found'}), 404
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting port: {str(e)}")
        return jsonify({'success': False, 'message': 'Error deleting port'}), 500

@ports_bp.route('/update_port_order', methods=['POST'])
def update_port_order():
    ip = request.form['ip']
    port_order = request.form.getlist('port_order[]')

    try:
        ports = Port.query.filter_by(ip_address=ip).all()
        for i, port_number in enumerate(port_order):
            port = next(p for p in ports if str(p.port_number) == port_number)
            port.order = i
        db.session.commit()
        return jsonify({'success': True, 'message': 'Port order updated successfully'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating port order: {str(e)}")
        return jsonify({'success': False, 'message': 'Error updating port order'}), 500

@ports_bp.route('/move_port', methods=['POST'])
def move_port():
    app.logger.info(f"Received move_port request: {request.form}")
    port_number = request.form.get('port_number')
    source_ip = request.form.get('source_ip')
    target_ip = request.form.get('target_ip')
    app.logger.info(f"Parsed data: port_number={port_number}, source_ip={source_ip}, target_ip={target_ip}")

    if not all([port_number, target_ip]):
        return jsonify({'success': False, 'message': 'Missing required data'}), 400

    try:
        port = Port.query.filter_by(port_number=port_number).first()
        if port:
            old_ip = port.ip_address

            # Get the nickname of the target IP
            target_port = Port.query.filter_by(ip_address=target_ip).first()
            target_nickname = target_port.nickname if target_port else None

            # Update the port's IP address and nickname
            port.ip_address = target_ip
            port.nickname = target_nickname

            db.session.commit()
            app.logger.info(f"Moved port {port_number} from {old_ip} to {target_ip}")
            return jsonify({'success': True, 'message': 'Port moved successfully'})
        else:
            app.logger.warning(f"Port not found: {port_number}")
            return jsonify({'success': False, 'message': 'Port not found'}), 404
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error moving port: {str(e)}")
        return jsonify({'success': False, 'message': 'Error moving port'}), 500

@ports_bp.route('/update_ip_order', methods=['POST'])
def update_ip_order():
    data = json.loads(request.data)
    ip_order = data.get('ip_order', [])
    app.logger.info(f"Received IP order: {ip_order}")

    try:
        # Update the order for each IP
        for index, ip in enumerate(ip_order):
            Port.query.filter_by(ip_address=ip).update({Port.ip_order: index})
            app.logger.info(f"Updated order for IP {ip} to {index}")

        # Set a high order number for any IPs not in the received order
        Port.query.filter(Port.ip_address.notin_(ip_order)).update({Port.ip_order: len(ip_order)}, synchronize_session=False)

        db.session.commit()
        return jsonify({'success': True, 'message': 'IP panel order updated successfully'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating IP panel order: {str(e)}")
        return jsonify({'success': False, 'message': f'Error updating IP panel order: {str(e)}'}), 500
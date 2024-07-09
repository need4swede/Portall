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

## Ports ##

@ports_bp.route('/ports')
def ports():
    """
    Render the ports page.

    This function retrieves all ports from the database, organizes them by IP address,
    and renders the 'ports.html' template with the organized port data.

    Returns:
        str: Rendered HTML template for the ports page.
    """
    # Retrieve all ports, ordered by order
    ports = Port.query.order_by(Port.order).all()

    # Organize ports by IP address
    ports_by_ip = {}
    for port in ports:
        if port.ip_address not in ports_by_ip:
            ports_by_ip[port.ip_address] = {'nickname': port.nickname, 'ports': []}
        ports_by_ip[port.ip_address]['ports'].append(port)

    # Get the current theme from the session
    theme = session.get('theme', 'light')

    # Render the template with the organized port data and theme
    return render_template('ports.html', ports_by_ip=ports_by_ip, theme=theme)

@ports_bp.route('/add_port', methods=['POST'])
def add_port():
    """
    Add a new port for a given IP address.

    This function creates a new port entry in the database with the provided details.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
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

@ports_bp.route('/edit_port', methods=['POST'])
def edit_port():
    """
    Edit an existing port's details.

    This function updates the port number and description for a given IP address.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
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

@ports_bp.route('/delete_port', methods=['POST'])
def delete_port():
    """
    Delete a specific port for a given IP address.

    This function removes a port entry from the database based on the IP address and port number.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
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

@ports_bp.route('/generate_port', methods=['POST'])
def generate_port():
    """
    Generate a new port for a given IP address.

    This function receives IP address, nickname, and description from a POST request,
    generates a new unique port number within the configured range, and saves it to the database.

    Returns:
        tuple: A tuple containing a JSON response and an HTTP status code.
               The JSON response includes the new port number and full URL on success,
               or an error message on failure.
    """
    # Extract data from the POST request
    ip_address = request.form['ip_address']
    nickname = request.form['nickname']
    description = request.form['description']
    app.logger.debug(f"Received request to generate port for IP: {ip_address}, Nickname: {nickname}, Description: {description}")

    def get_setting(key, default):
        """Helper function to retrieve settings from the database."""
        setting = Setting.query.filter_by(key=key).first()
        return setting.value if setting else default

    # Retrieve port generation settings
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

    # Generate list of available ports based on settings
    available_ports = [p for p in range(port_start, port_end + 1)
                       if p not in excluded_ports and
                       (port_length == 0 or len(str(p)) == port_length)]

    # Count ports in use within the current range
    ports_in_use = sum(1 for p in existing_ports if p in available_ports)

    # Check if there are any available ports
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

    # Choose a new port randomly from available ports
    new_port = random.choice([p for p in available_ports if p not in existing_ports])

    try:
        # Create and save the new port
        port = Port(ip_address=ip_address, nickname=nickname, port_number=new_port, description=description)
        db.session.add(port)
        db.session.commit()
        app.logger.info(f"Generated new port {new_port} for IP: {ip_address}")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving new port: {str(e)}")
        return jsonify({'error': 'Error saving new port'}), 500

    # Return the new port and full URL
    full_url = f"http://{ip_address}:{new_port}"
    return jsonify({'port': new_port, 'full_url': full_url})

@ports_bp.route('/move_port', methods=['POST'])
def move_port():
    """
    Move a port from one IP address to another.

    This function updates the IP address and order of a port based on the target IP.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    port_number = request.form.get('port_number')
    source_ip = request.form.get('source_ip')
    target_ip = request.form.get('target_ip')

    if not all([port_number, source_ip, target_ip]):
        return jsonify({'success': False, 'message': 'Missing required data'}), 400

    try:
        port = Port.query.filter_by(port_number=port_number, ip_address=source_ip).first()
        if port:
            # Update IP address
            port.ip_address = target_ip

            # Update order
            max_order = db.session.query(db.func.max(Port.order)).filter_by(ip_address=target_ip).scalar() or 0
            port.order = max_order + 1

            db.session.commit()
            return jsonify({'success': True, 'message': 'Port moved successfully'})
        else:
            return jsonify({'success': False, 'message': 'Port not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error moving port: {str(e)}'}), 500

@ports_bp.route('/update_port_order', methods=['POST'])
def update_port_order():
    """
    Update the order of ports for a specific IP address.

    This function receives a new order for ports of a given IP and updates the database accordingly.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    data = request.json
    ip = data.get('ip')
    port_order = data.get('port_order')

    if not ip or not port_order:
        return jsonify({'success': False, 'message': 'Missing IP or port order data'}), 400

    try:
        # Get the base order for this IP
        base_order = Port.query.filter_by(ip_address=ip).order_by(Port.order).first().order

        # Update the order for each port
        for index, port_number in enumerate(port_order):
            port = Port.query.filter_by(ip_address=ip, port_number=port_number).first()
            if port:
                port.order = base_order + index

        db.session.commit()
        return jsonify({'success': True, 'message': 'Port order updated successfully'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating port order: {str(e)}")
        return jsonify({'success': False, 'message': f'Error updating port order: {str(e)}'}), 500

## IP Addresses ##

@ports_bp.route('/edit_ip', methods=['POST'])
def edit_ip():
    """
    Edit an IP address and its associated nickname.

    This function updates the IP address and nickname for all ports associated with the old IP.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
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
    """
    Delete an IP address and all its associated ports.

    This function removes an IP address and all ports assigned to it from the database.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
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

@ports_bp.route('/update_ip_order', methods=['POST'])
def update_ip_order():
    """
    Update the order of IP address panels.

    This function receives a new order for IP addresses and updates the database accordingly.
    It uses a large step between IP orders to allow for many ports per IP.

    Returns:
        JSON: A JSON response indicating success or failure of the operation.
    """
    data = json.loads(request.data)
    ip_order = data.get('ip_order', [])

    try:
        # Update the order for each IP
        for index, ip in enumerate(ip_order):
            base_order = index * 1000  # Use a large step to allow for many ports per IP
            ports = Port.query.filter_by(ip_address=ip).order_by(Port.order).all()
            for i, port in enumerate(ports):
                port.order = base_order + i

        db.session.commit()
        return jsonify({'success': True, 'message': 'IP panel order updated successfully'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating IP panel order: {str(e)}")
        return jsonify({'success': False, 'message': f'Error updating IP panel order: {str(e)}'}), 500
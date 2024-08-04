# External Imports
from flask import current_app as app            # For accessing the Flask app
import docker
from utils.database import db, Port, Setting    # For accessing the database models
def access_docker_socket(url = "unix://var/run/docker.sock", ip = "127.0.0.1" ):
    client = docker.DockerClient(base_url=url, version="auto")
    for container in client.containers.list():
        for key in container.ports:
            if container.ports[key] == None:
                continue
            else:
                if bool(container.labels.get("com.portall.ip")):
                    ip = str(container.labels["com.portall.ip"])

                if bool(container.labels["com.portall.description"]):
                    description = str(container.labels["com.portall.description"])
                else:
                    description = str(container.name)
                write_port(ip, int(container.ports[key][0]['HostPort']), description, container.id)

def write_port(ip, port, description, docker_id):
    try:
        port_entry = Port.query.filter_by(docker_id=docker_id).one()
        if not port_entry:
            port = Port(ip_address=ip, port_number=port, description=description)
            db.session.add(port)

        else:
            # Check if the new port number already exists for this IP
            existing_port = Port.query.filter(Port.ip_address == ip,
                                              Port.port_number == port, 
                                              Port.docker_id != docker_id ).first()
            if existing_port:
                app.logger.info(f"Warning: Port {port} already exists on this ip")

        port_entry.port_number = port
        port_entry.description = description
        port_entry.ip = ip
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.info(f"Error: There Was an error whilst Accessing The Docker Socket")

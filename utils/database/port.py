# utils/database/port.py

from .db import db

class Port(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(15), nullable=False)
    nickname = db.Column(db.String(50), nullable=True)
    port_number = db.Column(db.Integer, nullable=False)
    port_protocol = db.Column(db.String(3), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, default=0)
    source = db.Column(db.String(20), nullable=True)  # 'manual', 'docker', 'portainer', etc.
    is_immutable = db.Column(db.Boolean, default=False)  # If True, port number, protocol can't be changed and port can't be deleted

    # Relationship to tag associations
    tag_associations = db.relationship('PortTag', back_populates='port', cascade='all, delete-orphan')

    __table_args__ = (db.UniqueConstraint('ip_address', 'port_number', 'port_protocol', name='_ip_port_protocol_uc'),)

    @property
    def tags(self):
        """Get all tags associated with this port."""
        return [assoc.tag for assoc in self.tag_associations]

    def has_tag(self, tag_name):
        """Check if this port has a specific tag."""
        return any(assoc.tag.name == tag_name for assoc in self.tag_associations)

    def add_tag(self, tag):
        """Add a tag to this port if not already present."""
        if not self.has_tag(tag.name):
            from .tag import PortTag
            association = PortTag(port=self, tag=tag)
            self.tag_associations.append(association)
            return True
        return False

    def remove_tag(self, tag_name):
        """Remove a tag from this port."""
        for assoc in self.tag_associations:
            if assoc.tag.name == tag_name:
                self.tag_associations.remove(assoc)
                return True
        return False

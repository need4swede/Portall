# utils/database/tag.py

from datetime import datetime
from .db import db

class Tag(db.Model):
    """Model for tags that can be applied to ports."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), nullable=False, default='#007bff')  # Hex color code
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to port associations
    port_associations = db.relationship('PortTag', back_populates='tag', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Tag {self.name}>'

class PortTag(db.Model):
    """Association table for many-to-many relationship between ports and tags."""
    __tablename__ = 'port_tag'

    id = db.Column(db.Integer, primary_key=True)
    port_id = db.Column(db.Integer, db.ForeignKey('port.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    port = db.relationship('Port', back_populates='tag_associations')
    tag = db.relationship('Tag', back_populates='port_associations')

    # Ensure unique port-tag combinations
    __table_args__ = (db.UniqueConstraint('port_id', 'tag_id', name='_port_tag_uc'),)

    def __repr__(self):
        return f'<PortTag port_id={self.port_id} tag_id={self.tag_id}>'

class TaggingRule(db.Model):
    """Model for automated tagging rules."""
    __tablename__ = 'tagging_rule'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    priority = db.Column(db.Integer, default=0, nullable=False)  # Higher number = higher priority

    # Rule conditions stored as JSON
    conditions = db.Column(db.Text, nullable=False)  # JSON string

    # Actions to take when conditions match (tags to add/remove)
    actions = db.Column(db.Text, nullable=False)  # JSON string

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_executed = db.Column(db.DateTime, nullable=True)

    # Statistics
    execution_count = db.Column(db.Integer, default=0, nullable=False)
    ports_affected = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<TaggingRule {self.name}>'

class RuleExecutionLog(db.Model):
    """Log of rule executions for debugging and auditing."""
    __tablename__ = 'rule_execution_log'

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('tagging_rule.id'), nullable=False)
    port_id = db.Column(db.Integer, db.ForeignKey('port.id'), nullable=False)

    # What action was taken
    action_type = db.Column(db.String(20), nullable=False)  # 'add_tag', 'remove_tag'
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)

    # When it happened
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Success/failure status
    success = db.Column(db.Boolean, default=True, nullable=False)
    error_message = db.Column(db.String(500), nullable=True)

    # Relationships
    rule = db.relationship('TaggingRule')
    port = db.relationship('Port')
    tag = db.relationship('Tag')

    def __repr__(self):
        return f'<RuleExecutionLog rule_id={self.rule_id} port_id={self.port_id} action={self.action_type}>'

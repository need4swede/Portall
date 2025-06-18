# utils/routes/tags.py

import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, session
from sqlalchemy import func, or_
from utils.database import db, Port, Tag, PortTag, TaggingRule, RuleExecutionLog
from utils.tagging_engine import tagging_engine

logger = logging.getLogger(__name__)

# Create the blueprint
tags_bp = Blueprint('tags', __name__)

## Tag Management ##

@tags_bp.route('/tags')
def tags_page():
    """Render the tags management page."""
    # Get all tags with usage statistics
    tags_with_stats = db.session.query(
        Tag,
        func.count(PortTag.id).label('usage_count')
    ).outerjoin(PortTag).group_by(Tag.id).all()

    # Get all tagging rules
    rules = TaggingRule.query.order_by(TaggingRule.priority.desc()).all()

    # Get current theme from session
    theme = session.get('theme', 'light')

    return render_template('tags.html',
                         tags_with_stats=tags_with_stats,
                         rules=rules,
                         theme=theme)

@tags_bp.route('/api/tags', methods=['GET'])
def get_tags():
    """Get all tags with optional filtering."""
    search = request.args.get('search', '').strip()

    query = Tag.query

    if search:
        query = query.filter(or_(
            Tag.name.ilike(f'%{search}%'),
            Tag.description.ilike(f'%{search}%')
        ))

    tags = query.order_by(Tag.name).all()

    # Include usage count for each tag
    tags_data = []
    for tag in tags:
        usage_count = PortTag.query.filter_by(tag_id=tag.id).count()
        tags_data.append({
            'id': tag.id,
            'name': tag.name,
            'color': tag.color,
            'description': tag.description,
            'usage_count': usage_count,
            'created_at': tag.created_at.isoformat() if tag.created_at else None
        })

    return jsonify(tags_data)

@tags_bp.route('/api/tags', methods=['POST'])
def create_tag():
    """Create a new tag."""
    try:
        data = request.get_json()

        name = data.get('name', '').strip()
        color = data.get('color', '#007bff')
        description = data.get('description', '').strip()

        if not name:
            return jsonify({'success': False, 'message': 'Tag name is required'}), 400

        # Check if tag already exists
        existing_tag = Tag.query.filter_by(name=name).first()
        if existing_tag:
            return jsonify({'success': False, 'message': 'Tag with this name already exists'}), 400

        # Create new tag
        tag = Tag(
            name=name,
            color=color,
            description=description if description else None
        )

        db.session.add(tag)
        db.session.commit()

        logger.info(f"Created new tag: {name}")

        return jsonify({
            'success': True,
            'message': 'Tag created successfully',
            'tag': {
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'description': tag.description,
                'usage_count': 0
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating tag: {str(e)}")
        return jsonify({'success': False, 'message': f'Error creating tag: {str(e)}'}), 500

@tags_bp.route('/api/tags/<int:tag_id>', methods=['PUT'])
def update_tag(tag_id):
    """Update an existing tag."""
    try:
        tag = Tag.query.get(tag_id)
        if not tag:
            return jsonify({'success': False, 'message': 'Tag not found'}), 404

        data = request.get_json()

        name = data.get('name', '').strip()
        color = data.get('color')
        description = data.get('description', '').strip()

        if not name:
            return jsonify({'success': False, 'message': 'Tag name is required'}), 400

        # Check if another tag with this name exists
        existing_tag = Tag.query.filter(Tag.name == name, Tag.id != tag_id).first()
        if existing_tag:
            return jsonify({'success': False, 'message': 'Tag with this name already exists'}), 400

        # Update tag
        tag.name = name
        if color:
            tag.color = color
        tag.description = description if description else None

        db.session.commit()

        logger.info(f"Updated tag: {name}")

        usage_count = PortTag.query.filter_by(tag_id=tag.id).count()

        return jsonify({
            'success': True,
            'message': 'Tag updated successfully',
            'tag': {
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'description': tag.description,
                'usage_count': usage_count
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating tag: {str(e)}")
        return jsonify({'success': False, 'message': f'Error updating tag: {str(e)}'}), 500

@tags_bp.route('/api/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    """Delete a tag and all its associations."""
    try:
        tag = Tag.query.get(tag_id)
        if not tag:
            return jsonify({'success': False, 'message': 'Tag not found'}), 404

        tag_name = tag.name

        # Delete all port-tag associations (cascade should handle this)
        db.session.delete(tag)
        db.session.commit()

        logger.info(f"Deleted tag: {tag_name}")

        return jsonify({
            'success': True,
            'message': f'Tag "{tag_name}" deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting tag: {str(e)}")
        return jsonify({'success': False, 'message': f'Error deleting tag: {str(e)}'}), 500

## Port Tagging ##

@tags_bp.route('/api/ports/<int:port_id>/tags', methods=['GET'])
def get_port_tags(port_id):
    """Get all tags for a specific port."""
    try:
        port = Port.query.get(port_id)
        if not port:
            return jsonify([]), 404

        tags_data = [{
            'id': tag.id,
            'name': tag.name,
            'color': tag.color,
            'description': tag.description
        } for tag in port.tags]

        return jsonify(tags_data)

    except Exception as e:
        logger.error(f"Error getting port tags: {str(e)}")
        return jsonify([]), 500

@tags_bp.route('/api/ports/<int:port_id>/tags', methods=['POST'])
def add_tags_to_port(port_id):
    """Add one or more tags to a port."""
    try:
        port = Port.query.get(port_id)
        if not port:
            return jsonify({'success': False, 'message': 'Port not found'}), 404

        data = request.get_json()
        tag_id = data.get('tag_id')
        tag_ids = data.get('tag_ids', [])

        # Support both single tag_id and multiple tag_ids
        if tag_id:
            tag_ids = [tag_id]

        if not tag_ids:
            return jsonify({'success': False, 'message': 'Tag ID(s) required'}), 400

        success_count = 0
        messages = []

        for tid in tag_ids:
            tag = Tag.query.get(tid)
            if not tag:
                messages.append(f'Tag ID {tid} not found')
                continue

            # Add tag to port
            if port.add_tag(tag):
                success_count += 1
                messages.append(f'Added tag "{tag.name}"')
            else:
                messages.append(f'Tag "{tag.name}" already assigned')

        db.session.commit()

        if success_count > 0:
            logger.info(f"Added {success_count} tags to port {port_id}")

        return jsonify({
            'success': True,
            'message': f'{success_count} tags processed',
            'details': messages,
            'added_count': success_count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding tags to port: {str(e)}")
        return jsonify({'success': False, 'message': f'Error adding tags to port: {str(e)}'}), 500

@tags_bp.route('/api/ports/<int:port_id>/tags/<int:tag_id>', methods=['DELETE'])
def remove_tag_from_port(port_id, tag_id):
    """Remove a tag from a port."""
    try:
        port = Port.query.get(port_id)
        if not port:
            return jsonify({'success': False, 'message': 'Port not found'}), 404

        tag = Tag.query.get(tag_id)
        if not tag:
            return jsonify({'success': False, 'message': 'Tag not found'}), 404

        # Remove tag from port
        if port.remove_tag(tag.name):
            db.session.commit()
            logger.info(f"Removed tag '{tag.name}' from port {port_id}")
            return jsonify({'success': True, 'message': f'Tag "{tag.name}" removed from port'})
        else:
            return jsonify({'success': False, 'message': 'Tag not assigned to this port'}), 400

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing tag from port: {str(e)}")
        return jsonify({'success': False, 'message': f'Error removing tag from port: {str(e)}'}), 500

@tags_bp.route('/api/ports/tags/bulk', methods=['POST'])
def bulk_tag_ports():
    """Add or remove tags from multiple ports."""
    try:
        data = request.get_json()
        port_ids = data.get('port_ids', [])
        tag_ids = data.get('tag_ids', [])
        action = data.get('action', 'add')  # 'add' or 'remove'

        if not port_ids or not tag_ids:
            return jsonify({'success': False, 'message': 'Port IDs and Tag IDs are required'}), 400

        if action not in ['add', 'remove']:
            return jsonify({'success': False, 'message': 'Action must be "add" or "remove"'}), 400

        # Get ports and tags
        ports = Port.query.filter(Port.id.in_(port_ids)).all()
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()

        if len(ports) != len(port_ids):
            return jsonify({'success': False, 'message': 'Some ports not found'}), 404

        if len(tags) != len(tag_ids):
            return jsonify({'success': False, 'message': 'Some tags not found'}), 404

        success_count = 0

        for port in ports:
            for tag in tags:
                if action == 'add':
                    if port.add_tag(tag):
                        success_count += 1
                else:  # remove
                    if port.remove_tag(tag.name):
                        success_count += 1

        db.session.commit()

        action_word = 'added to' if action == 'add' else 'removed from'
        logger.info(f"Bulk operation: {success_count} tag assignments {action_word} ports")

        return jsonify({
            'success': True,
            'message': f'{success_count} tag assignments {action_word} ports',
            'affected_count': success_count
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in bulk tag operation: {str(e)}")
        return jsonify({'success': False, 'message': f'Error in bulk tag operation: {str(e)}'}), 500

## Tagging Rules ##

@tags_bp.route('/api/tagging-rules', methods=['GET'])
def get_tagging_rules():
    """Get all tagging rules."""
    try:
        rules = TaggingRule.query.order_by(TaggingRule.priority.desc()).all()

        rules_data = []
        for rule in rules:
            rules_data.append({
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'enabled': rule.enabled,
                'auto_execute': rule.auto_execute,
                'priority': rule.priority,
                'conditions': json.loads(rule.conditions),
                'actions': json.loads(rule.actions),
                'execution_count': rule.execution_count,
                'ports_affected': rule.ports_affected,
                'last_executed': rule.last_executed.isoformat() if rule.last_executed else None,
                'created_at': rule.created_at.isoformat() if rule.created_at else None
            })

        return jsonify({'success': True, 'rules': rules_data})

    except Exception as e:
        logger.error(f"Error getting tagging rules: {str(e)}")
        return jsonify({'success': False, 'message': f'Error getting tagging rules: {str(e)}'}), 500

@tags_bp.route('/api/tagging-rules', methods=['POST'])
def create_tagging_rule():
    """Create a new tagging rule."""
    try:
        data = request.get_json()

        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        enabled = data.get('enabled', True)
        auto_execute = data.get('auto_execute', False)
        priority = data.get('priority', 0)
        conditions = data.get('conditions', {})
        actions = data.get('actions', [])

        if not name:
            return jsonify({'success': False, 'message': 'Rule name is required'}), 400

        if not conditions:
            return jsonify({'success': False, 'message': 'Rule conditions are required'}), 400

        if not actions:
            return jsonify({'success': False, 'message': 'Rule actions are required'}), 400

        # Validate JSON serialization
        try:
            conditions_json = json.dumps(conditions)
            actions_json = json.dumps(actions)
        except (TypeError, ValueError) as e:
            return jsonify({'success': False, 'message': f'Invalid JSON in conditions or actions: {str(e)}'}), 400

        # Create new rule
        rule = TaggingRule(
            name=name,
            description=description if description else None,
            enabled=enabled,
            auto_execute=auto_execute,
            priority=priority,
            conditions=conditions_json,
            actions=actions_json
        )

        db.session.add(rule)
        db.session.commit()

        logger.info(f"Created new tagging rule: {name}")

        return jsonify({
            'success': True,
            'message': 'Tagging rule created successfully',
            'rule': {
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'enabled': rule.enabled,
                'priority': rule.priority,
                'conditions': conditions,
                'actions': actions
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating tagging rule: {str(e)}")
        return jsonify({'success': False, 'message': f'Error creating tagging rule: {str(e)}'}), 500

@tags_bp.route('/api/tagging-rules/<int:rule_id>', methods=['PUT'])
def update_tagging_rule(rule_id):
    """Update an existing tagging rule."""
    try:
        rule = TaggingRule.query.get(rule_id)
        if not rule:
            return jsonify({'success': False, 'message': 'Rule not found'}), 404

        data = request.get_json()

        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        enabled = data.get('enabled')
        auto_execute = data.get('auto_execute')
        priority = data.get('priority')
        conditions = data.get('conditions')
        actions = data.get('actions')

        if name:
            rule.name = name
        if description is not None:
            rule.description = description if description else None
        if enabled is not None:
            rule.enabled = enabled
        if auto_execute is not None:
            rule.auto_execute = auto_execute
        if priority is not None:
            rule.priority = priority
        if conditions is not None:
            try:
                rule.conditions = json.dumps(conditions)
            except (TypeError, ValueError) as e:
                return jsonify({'success': False, 'message': f'Invalid JSON in conditions: {str(e)}'}), 400
        if actions is not None:
            try:
                rule.actions = json.dumps(actions)
            except (TypeError, ValueError) as e:
                return jsonify({'success': False, 'message': f'Invalid JSON in actions: {str(e)}'}), 400

        db.session.commit()

        logger.info(f"Updated tagging rule: {rule.name}")

        return jsonify({
            'success': True,
            'message': 'Tagging rule updated successfully',
            'rule': {
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'enabled': rule.enabled,
                'priority': rule.priority,
                'conditions': json.loads(rule.conditions),
                'actions': json.loads(rule.actions)
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating tagging rule: {str(e)}")
        return jsonify({'success': False, 'message': f'Error updating tagging rule: {str(e)}'}), 500

@tags_bp.route('/api/tagging-rules/<int:rule_id>', methods=['DELETE'])
def delete_tagging_rule(rule_id):
    """Delete a tagging rule."""
    try:
        rule = TaggingRule.query.get(rule_id)
        if not rule:
            return jsonify({'success': False, 'message': 'Rule not found'}), 404

        rule_name = rule.name

        # Delete execution logs first (if needed, or let cascade handle it)
        db.session.delete(rule)
        db.session.commit()

        logger.info(f"Deleted tagging rule: {rule_name}")

        return jsonify({
            'success': True,
            'message': f'Tagging rule "{rule_name}" deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting tagging rule: {str(e)}")
        return jsonify({'success': False, 'message': f'Error deleting tagging rule: {str(e)}'}), 500

@tags_bp.route('/api/tagging-rules/<int:rule_id>/execute', methods=['POST'])
def execute_tagging_rule(rule_id):
    """Execute a specific tagging rule on all ports."""
    try:
        rule = TaggingRule.query.get(rule_id)
        if not rule:
            return jsonify({'success': False, 'message': 'Rule not found'}), 404

        # Get all ports
        ports = Port.query.all()

        success_count = 0
        error_count = 0

        for port in ports:
            try:
                actions = tagging_engine.evaluate_port_against_rules(port, [rule])
                logs = tagging_engine.execute_actions(port, actions)

                # Add logs to database
                for log in logs:
                    db.session.add(log)

                success_count += len([log for log in logs if log.success])
                error_count += len([log for log in logs if not log.success])

            except Exception as e:
                logger.error(f"Error executing rule on port {port.id}: {str(e)}")
                error_count += 1

        # Update rule statistics
        rule.last_executed = datetime.utcnow()
        rule.execution_count += 1
        rule.ports_affected += success_count

        db.session.commit()

        logger.info(f"Executed rule '{rule.name}': {success_count} successful actions, {error_count} errors")

        return jsonify({
            'success': True,
            'message': f'Rule executed successfully',
            'stats': {
                'ports_processed': len(ports),
                'successful_actions': success_count,
                'errors': error_count
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error executing tagging rule: {str(e)}")
        return jsonify({'success': False, 'message': f'Error executing tagging rule: {str(e)}'}), 500

@tags_bp.route('/api/tagging-rules/execute-all', methods=['POST'])
def execute_all_tagging_rules():
    """Execute all enabled tagging rules on all ports."""
    try:
        stats = tagging_engine.apply_rules_to_all_ports()

        logger.info(f"Executed all tagging rules: {stats}")

        return jsonify({
            'success': True,
            'message': 'All tagging rules executed successfully',
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Error executing all tagging rules: {str(e)}")
        return jsonify({'success': False, 'message': f'Error executing all tagging rules: {str(e)}'}), 500

## Filtering and Search ##

@tags_bp.route('/api/ports/filter', methods=['POST'])
def filter_ports_by_tags():
    """Filter ports by tags and other criteria."""
    try:
        data = request.get_json()

        tag_ids = data.get('tag_ids', [])
        tag_operator = data.get('tag_operator', 'AND')  # 'AND' or 'OR'
        ip_filter = data.get('ip_filter', '').strip()
        port_filter = data.get('port_filter', '').strip()
        description_filter = data.get('description_filter', '').strip()

        query = Port.query

        # Filter by tags
        if tag_ids:
            if tag_operator == 'AND':
                # Port must have ALL specified tags
                for tag_id in tag_ids:
                    query = query.filter(Port.tag_associations.any(PortTag.tag_id == tag_id))
            else:  # OR
                # Port must have ANY of the specified tags
                query = query.filter(Port.tag_associations.any(PortTag.tag_id.in_(tag_ids)))

        # Filter by IP
        if ip_filter:
            query = query.filter(Port.ip_address.ilike(f'%{ip_filter}%'))

        # Filter by port number
        if port_filter:
            try:
                port_num = int(port_filter)
                query = query.filter(Port.port_number == port_num)
            except ValueError:
                pass  # Ignore invalid port numbers

        # Filter by description
        if description_filter:
            query = query.filter(Port.description.ilike(f'%{description_filter}%'))

        ports = query.order_by(Port.order).all()

        # Format response
        ports_data = []
        for port in ports:
            port_tags = [{
                'id': tag.id,
                'name': tag.name,
                'color': tag.color
            } for tag in port.tags]

            ports_data.append({
                'id': port.id,
                'ip_address': port.ip_address,
                'nickname': port.nickname,
                'port_number': port.port_number,
                'port_protocol': port.port_protocol,
                'description': port.description,
                'source': port.source,
                'is_immutable': port.is_immutable,
                'tags': port_tags
            })

        return jsonify({
            'success': True,
            'ports': ports_data,
            'count': len(ports_data)
        })

    except Exception as e:
        logger.error(f"Error filtering ports: {str(e)}")
        return jsonify({'success': False, 'message': f'Error filtering ports: {str(e)}'}), 500

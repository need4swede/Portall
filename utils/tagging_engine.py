# utils/tagging_engine.py

import json
import re
import ipaddress
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from utils.database import db, Port, Tag, PortTag, TaggingRule, RuleExecutionLog

logger = logging.getLogger(__name__)

class TaggingEngine:
    """Engine for evaluating and executing automated tagging rules."""

    def __init__(self):
        self.condition_evaluators = {
            'ip_exact': self._evaluate_ip_exact,
            'ip_regex': self._evaluate_ip_regex,
            'ip_cidr': self._evaluate_ip_cidr,
            'port_exact': self._evaluate_port_exact,
            'port_range': self._evaluate_port_range,
            'port_list': self._evaluate_port_list,
            'protocol': self._evaluate_protocol,
            'description_contains': self._evaluate_description_contains,
            'description_regex': self._evaluate_description_regex,
            'source': self._evaluate_source,
            'nickname_contains': self._evaluate_nickname_contains,
            'nickname_regex': self._evaluate_nickname_regex,
        }

    def evaluate_port_against_rules(self, port: Port, rules: Optional[List[TaggingRule]] = None) -> List[Dict[str, Any]]:
        """
        Evaluate a port against all enabled tagging rules.

        Args:
            port: The port to evaluate
            rules: Optional list of rules to evaluate. If None, all enabled rules are used.

        Returns:
            List of actions to execute (tag additions/removals)
        """
        if rules is None:
            rules = TaggingRule.query.filter_by(enabled=True).order_by(TaggingRule.priority.desc()).all()

        actions_to_execute = []

        for rule in rules:
            try:
                if self._evaluate_rule_conditions(port, rule):
                    rule_actions = json.loads(rule.actions)
                    for action in rule_actions:
                        action['rule_id'] = rule.id
                        actions_to_execute.append(action)

                    logger.debug(f"Port {port.id} matched rule '{rule.name}'")

            except Exception as e:
                logger.error(f"Error evaluating rule '{rule.name}' for port {port.id}: {str(e)}")

        return actions_to_execute

    def execute_actions(self, port: Port, actions: List[Dict[str, Any]]) -> List[RuleExecutionLog]:
        """
        Execute a list of tagging actions on a port.

        Args:
            port: The port to apply actions to
            actions: List of actions to execute

        Returns:
            List of execution log entries
        """
        execution_logs = []

        for action in actions:
            try:
                log_entry = self._execute_single_action(port, action)
                execution_logs.append(log_entry)

            except Exception as e:
                logger.error(f"Error executing action {action} on port {port.id}: {str(e)}")
                # Create error log entry
                log_entry = RuleExecutionLog(
                    rule_id=action.get('rule_id'),
                    port_id=port.id,
                    action_type=action.get('type', 'unknown'),
                    tag_id=None,
                    success=False,
                    error_message=str(e)
                )
                execution_logs.append(log_entry)

        return execution_logs

    def apply_rules_to_port(self, port: Port, commit: bool = True) -> int:
        """
        Apply all enabled tagging rules to a single port.

        Args:
            port: The port to apply rules to
            commit: Whether to commit changes to database

        Returns:
            Number of actions executed
        """
        actions = self.evaluate_port_against_rules(port)
        logs = self.execute_actions(port, actions)

        # Add logs to database
        for log in logs:
            db.session.add(log)

        if commit:
            db.session.commit()

        return len([log for log in logs if log.success])

    def apply_automatic_rules_to_port(self, port: Port, commit: bool = True) -> int:
        """
        Apply only auto-execute enabled tagging rules to a single port.
        This is called automatically when ports are created or modified.

        Args:
            port: The port to apply rules to
            commit: Whether to commit changes to database

        Returns:
            Number of actions executed
        """
        # Get only rules that are enabled AND have auto_execute = True
        auto_rules = TaggingRule.query.filter_by(
            enabled=True,
            auto_execute=True
        ).order_by(TaggingRule.priority.desc()).all()

        if not auto_rules:
            return 0

        actions = self.evaluate_port_against_rules(port, auto_rules)
        logs = self.execute_actions(port, actions)

        # Add logs to database
        for log in logs:
            db.session.add(log)

        # Update rule statistics for auto-executed rules
        executed_rule_ids = set(action.get('rule_id') for action in actions if action.get('rule_id'))
        for rule_id in executed_rule_ids:
            rule = TaggingRule.query.get(rule_id)
            if rule:
                rule.last_executed = datetime.utcnow()
                rule.execution_count += 1
                # Count successful actions for this rule
                successful_actions = len([log for log in logs if log.success and log.rule_id == rule_id])
                rule.ports_affected += successful_actions

        if commit:
            db.session.commit()

        successful_actions = len([log for log in logs if log.success])
        if successful_actions > 0:
            logger.info(f"Automatically applied {successful_actions} tagging actions to port {port.id}")

        return successful_actions

    def apply_rules_to_all_ports(self, commit: bool = True) -> Dict[str, int]:
        """
        Apply all enabled tagging rules to all ports.

        Args:
            commit: Whether to commit changes to database

        Returns:
            Dictionary with statistics
        """
        ports = Port.query.all()
        rules = TaggingRule.query.filter_by(enabled=True).order_by(TaggingRule.priority.desc()).all()

        stats = {
            'ports_processed': 0,
            'actions_executed': 0,
            'errors': 0
        }

        for port in ports:
            try:
                actions = self.evaluate_port_against_rules(port, rules)
                logs = self.execute_actions(port, actions)

                # Add logs to database
                for log in logs:
                    db.session.add(log)

                stats['ports_processed'] += 1
                stats['actions_executed'] += len([log for log in logs if log.success])
                stats['errors'] += len([log for log in logs if not log.success])

            except Exception as e:
                logger.error(f"Error processing port {port.id}: {str(e)}")
                stats['errors'] += 1

        # Update rule statistics
        for rule in rules:
            rule.last_executed = datetime.utcnow()
            rule.execution_count += 1

        if commit:
            db.session.commit()

        return stats

    def _evaluate_rule_conditions(self, port: Port, rule: TaggingRule) -> bool:
        """Evaluate if a port matches all conditions in a rule."""
        try:
            conditions = json.loads(rule.conditions)

            # Handle different condition structures
            if isinstance(conditions, dict):
                if 'operator' in conditions:
                    # Complex condition with AND/OR logic
                    return self._evaluate_complex_condition(port, conditions)
                else:
                    # Simple condition object
                    return self._evaluate_simple_condition(port, conditions)
            elif isinstance(conditions, list):
                # List of conditions (default AND logic)
                return all(self._evaluate_simple_condition(port, cond) for cond in conditions)
            else:
                logger.warning(f"Invalid condition format in rule {rule.id}")
                return False

        except Exception as e:
            logger.error(f"Error parsing conditions for rule {rule.id}: {str(e)}")
            return False

    def _evaluate_complex_condition(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Evaluate complex conditions with AND/OR logic."""
        operator = condition.get('operator', 'AND').upper()
        subconditions = condition.get('conditions', [])

        if operator == 'AND':
            return all(self._evaluate_condition_item(port, cond) for cond in subconditions)
        elif operator == 'OR':
            return any(self._evaluate_condition_item(port, cond) for cond in subconditions)
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False

    def _evaluate_condition_item(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Evaluate a single condition item (could be simple or complex)."""
        if 'operator' in condition:
            return self._evaluate_complex_condition(port, condition)
        else:
            return self._evaluate_simple_condition(port, condition)

    def _evaluate_simple_condition(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Evaluate a simple condition against a port."""
        condition_type = condition.get('type')

        if condition_type not in self.condition_evaluators:
            logger.warning(f"Unknown condition type: {condition_type}")
            return False

        return self.condition_evaluators[condition_type](port, condition)

    def _execute_single_action(self, port: Port, action: Dict[str, Any]) -> RuleExecutionLog:
        """Execute a single tagging action."""
        action_type = action.get('type')
        tag_name = action.get('tag_name')
        rule_id = action.get('rule_id')

        # Get or create tag
        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            # Create tag with default color if it doesn't exist
            tag = Tag(name=tag_name, color=action.get('tag_color', '#007bff'))
            db.session.add(tag)
            db.session.flush()  # Get the ID

        success = False
        error_message = None

        try:
            if action_type == 'add_tag':
                success = port.add_tag(tag)
            elif action_type == 'remove_tag':
                success = port.remove_tag(tag_name)
            else:
                error_message = f"Unknown action type: {action_type}"

        except Exception as e:
            error_message = str(e)

        return RuleExecutionLog(
            rule_id=rule_id,
            port_id=port.id,
            action_type=action_type,
            tag_id=tag.id,
            success=success,
            error_message=error_message
        )

    # Condition evaluators
    def _evaluate_ip_exact(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if IP matches exactly."""
        return port.ip_address == condition.get('value')

    def _evaluate_ip_regex(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if IP matches regex pattern."""
        pattern = condition.get('value')
        try:
            return bool(re.match(pattern, port.ip_address))
        except re.error:
            return False

    def _evaluate_ip_cidr(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if IP is in CIDR range."""
        cidr = condition.get('value')
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            ip = ipaddress.ip_address(port.ip_address)
            return ip in network
        except (ipaddress.AddressValueError, ValueError):
            return False

    def _evaluate_port_exact(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if port number matches exactly."""
        return port.port_number == condition.get('value')

    def _evaluate_port_range(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if port is in range."""
        start = condition.get('start')
        end = condition.get('end')
        return start <= port.port_number <= end

    def _evaluate_port_list(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if port is in list of ports."""
        ports = condition.get('value', [])
        return port.port_number in ports

    def _evaluate_protocol(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if protocol matches."""
        return port.port_protocol.upper() == condition.get('value', '').upper()

    def _evaluate_description_contains(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if description contains text."""
        text = condition.get('value', '').lower()
        return text in port.description.lower()

    def _evaluate_description_regex(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if description matches regex."""
        pattern = condition.get('value')
        try:
            return bool(re.search(pattern, port.description, re.IGNORECASE))
        except re.error:
            return False

    def _evaluate_source(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if source matches."""
        return port.source == condition.get('value')

    def _evaluate_nickname_contains(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if nickname contains text."""
        if not port.nickname:
            return False
        text = condition.get('value', '').lower()
        return text in port.nickname.lower()

    def _evaluate_nickname_regex(self, port: Port, condition: Dict[str, Any]) -> bool:
        """Check if nickname matches regex."""
        if not port.nickname:
            return False
        pattern = condition.get('value')
        try:
            return bool(re.search(pattern, port.nickname, re.IGNORECASE))
        except re.error:
            return False

# Global instance
tagging_engine = TaggingEngine()

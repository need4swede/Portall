# utils/tag_templates.py

import json
from typing import Dict, List, Any
from datetime import datetime

class TagTemplateManager:
    """Manager for predefined tagging rule templates and presets."""

    def __init__(self):
        self.templates = self._load_builtin_templates()

    def _load_builtin_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load built-in rule templates for common scenarios."""
        return {
            "security_hardening": {
                "name": "Security Hardening",
                "description": "Automatically tag potentially risky and security-critical services",
                "category": "Security",
                "rules": [
                    {
                        "name": "Tag SSH Services",
                        "description": "Identify SSH services for security monitoring",
                        "priority": 100,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "port_exact", "value": 22},
                                {"type": "port_exact", "value": 2222},
                                {"type": "description_contains", "value": "ssh"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "SSH", "tag_color": "#dc3545"},
                            {"type": "add_tag", "tag_name": "Security-Critical", "tag_color": "#fd7e14"}
                        ]
                    },
                    {
                        "name": "Tag Database Services",
                        "description": "Identify database services requiring protection",
                        "priority": 90,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "port_list", "value": [3306, 5432, 1433, 27017, 6379, 5984]},
                                {"type": "description_regex", "value": "(?i)(mysql|postgres|sql|mongo|redis|couch)"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Database", "tag_color": "#6f42c1"},
                            {"type": "add_tag", "tag_name": "Data-Store", "tag_color": "#20c997"}
                        ]
                    },
                    {
                        "name": "Tag Public Web Services",
                        "description": "Identify web services exposed to public",
                        "priority": 80,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "port_list", "value": [80, 443, 8080, 8443, 3000, 8000]},
                                {"type": "description_regex", "value": "(?i)(web|http|nginx|apache|caddy)"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Web-Service", "tag_color": "#0d6efd"},
                            {"type": "add_tag", "tag_name": "Public-Facing", "tag_color": "#ffc107"}
                        ]
                    },
                    {
                        "name": "Tag Administrative Services",
                        "description": "Identify administrative and management interfaces",
                        "priority": 85,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "description_regex", "value": "(?i)(admin|management|dashboard|panel|console)"},
                                {"type": "port_list", "value": [9000, 9090, 8090, 3001, 8081]}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Administrative", "tag_color": "#e83e8c"},
                            {"type": "add_tag", "tag_name": "Restricted-Access", "tag_color": "#6c757d"}
                        ]
                    }
                ]
            },

            "infrastructure_mapping": {
                "name": "Infrastructure Mapping",
                "description": "Automatically categorize services by infrastructure type",
                "category": "Infrastructure",
                "rules": [
                    {
                        "name": "Tag Monitoring Services",
                        "description": "Identify monitoring and observability tools",
                        "priority": 70,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "description_regex", "value": "(?i)(prometheus|grafana|influx|elastic|kibana|jaeger|zipkin)"},
                                {"type": "port_list", "value": [9090, 3000, 8086, 9200, 5601, 14268, 9411]}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Monitoring", "tag_color": "#198754"},
                            {"type": "add_tag", "tag_name": "Observability", "tag_color": "#0dcaf0"}
                        ]
                    },
                    {
                        "name": "Tag Container Services",
                        "description": "Identify container orchestration services",
                        "priority": 75,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "description_regex", "value": "(?i)(docker|kubernetes|k8s|portainer|rancher)"},
                                {"type": "port_list", "value": [2375, 2376, 6443, 8443, 9000, 8000]},
                                {"type": "source", "value": "docker"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Container", "tag_color": "#0d6efd"},
                            {"type": "add_tag", "tag_name": "Orchestration", "tag_color": "#6610f2"}
                        ]
                    },
                    {
                        "name": "Tag Message Queues",
                        "description": "Identify message queue and streaming services",
                        "priority": 65,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "description_regex", "value": "(?i)(rabbitmq|kafka|redis|nats|mqtt)"},
                                {"type": "port_list", "value": [5672, 9092, 6379, 4222, 1883]}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Message-Queue", "tag_color": "#fd7e14"},
                            {"type": "add_tag", "tag_name": "Middleware", "tag_color": "#20c997"}
                        ]
                    },
                    {
                        "name": "Tag Development Tools",
                        "description": "Identify development and CI/CD tools",
                        "priority": 60,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "description_regex", "value": "(?i)(jenkins|gitlab|github|sonar|nexus|artifactory|registry)"},
                                {"type": "port_list", "value": [8080, 8081, 9000, 5000, 8082]}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Development", "tag_color": "#6f42c1"},
                            {"type": "add_tag", "tag_name": "CI-CD", "tag_color": "#d63384"}
                        ]
                    }
                ]
            },

            "network_segmentation": {
                "name": "Network Segmentation",
                "description": "Tag services based on network location and access patterns",
                "category": "Network",
                "rules": [
                    {
                        "name": "Tag DMZ Services",
                        "description": "Identify services in DMZ networks",
                        "priority": 95,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "ip_cidr", "value": "10.0.1.0/24"},
                                {"type": "ip_cidr", "value": "192.168.100.0/24"},
                                {"type": "description_contains", "value": "dmz"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "DMZ", "tag_color": "#ffc107"},
                            {"type": "add_tag", "tag_name": "External-Facing", "tag_color": "#fd7e14"}
                        ]
                    },
                    {
                        "name": "Tag Internal Services",
                        "description": "Identify internal-only services",
                        "priority": 50,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "ip_cidr", "value": "192.168.0.0/16"},
                                {"type": "ip_cidr", "value": "10.0.0.0/8"},
                                {"type": "ip_cidr", "value": "172.16.0.0/12"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Internal", "tag_color": "#198754"}
                        ]
                    },
                    {
                        "name": "Tag Management Network",
                        "description": "Identify management network services",
                        "priority": 90,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "ip_cidr", "value": "192.168.1.0/24"},
                                {"type": "ip_cidr", "value": "10.0.0.0/24"},
                                {"type": "description_contains", "value": "mgmt"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Management", "tag_color": "#6c757d"},
                            {"type": "add_tag", "tag_name": "Admin-Network", "tag_color": "#495057"}
                        ]
                    }
                ]
            },

            "compliance_pci": {
                "name": "PCI DSS Compliance",
                "description": "Tag services for PCI DSS compliance requirements",
                "category": "Compliance",
                "rules": [
                    {
                        "name": "Tag Payment Processing",
                        "description": "Identify payment processing services",
                        "priority": 100,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "description_regex", "value": "(?i)(payment|stripe|paypal|square|checkout)"},
                                {"type": "port_list", "value": [443, 8443]}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "PCI-Scope", "tag_color": "#dc3545"},
                            {"type": "add_tag", "tag_name": "Payment-Processing", "tag_color": "#fd7e14"}
                        ]
                    },
                    {
                        "name": "Tag Cardholder Data Environment",
                        "description": "Identify CDE components",
                        "priority": 95,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "description_regex", "value": "(?i)(cde|cardholder|card.?data)"},
                                {"type": "ip_cidr", "value": "10.1.0.0/24"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "CDE", "tag_color": "#dc3545"},
                            {"type": "add_tag", "tag_name": "High-Security", "tag_color": "#6f42c1"}
                        ]
                    }
                ]
            },

            "monitoring_setup": {
                "name": "Monitoring Setup",
                "description": "Tag services for different monitoring tools and alerting",
                "category": "Operations",
                "rules": [
                    {
                        "name": "Tag Critical Services",
                        "description": "Identify business-critical services requiring 24/7 monitoring",
                        "priority": 100,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "description_regex", "value": "(?i)(critical|production|prod|api|gateway)"},
                                {"type": "port_list", "value": [80, 443, 8080, 8443]}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Critical", "tag_color": "#dc3545"},
                            {"type": "add_tag", "tag_name": "24x7-Monitor", "tag_color": "#fd7e14"}
                        ]
                    },
                    {
                        "name": "Tag Health Check Endpoints",
                        "description": "Identify services with health check endpoints",
                        "priority": 80,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "OR",
                            "conditions": [
                                {"type": "description_regex", "value": "(?i)(health|status|ping|ready|live)"},
                                {"type": "port_list", "value": [8080, 9090, 8081]}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Health-Check", "tag_color": "#198754"},
                            {"type": "add_tag", "tag_name": "Monitorable", "tag_color": "#0dcaf0"}
                        ]
                    }
                ]
            }
        }

    def get_template_categories(self) -> List[str]:
        """Get all available template categories."""
        categories = set()
        for template in self.templates.values():
            categories.add(template.get("category", "Other"))
        return sorted(list(categories))

    def get_templates_by_category(self, category: str = None) -> Dict[str, Dict[str, Any]]:
        """Get templates filtered by category."""
        if not category:
            return self.templates

        return {
            key: template for key, template in self.templates.items()
            if template.get("category") == category
        }

    def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get a specific template by ID."""
        return self.templates.get(template_id)

    def apply_template(self, template_id: str, customize_options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Apply a template and return the rules to be created.

        Args:
            template_id: ID of the template to apply
            customize_options: Optional customization options like IP ranges, tag colors, etc.

        Returns:
            List of rule dictionaries ready to be created
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        rules = template["rules"].copy()

        # Apply customizations if provided
        if customize_options:
            rules = self._apply_customizations(rules, customize_options)

        return rules

    def _apply_customizations(self, rules: List[Dict[str, Any]], options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply customization options to template rules."""
        customized_rules = []

        for rule in rules:
            customized_rule = rule.copy()

            # Customize IP ranges
            if "ip_ranges" in options:
                customized_rule = self._customize_ip_ranges(customized_rule, options["ip_ranges"])

            # Customize tag colors
            if "tag_colors" in options:
                customized_rule = self._customize_tag_colors(customized_rule, options["tag_colors"])

            # Customize rule priorities
            if "priority_offset" in options:
                customized_rule["priority"] += options["priority_offset"]

            # Customize auto-execution
            if "auto_execute" in options:
                customized_rule["auto_execute"] = options["auto_execute"]

            customized_rules.append(customized_rule)

        return customized_rules

    def _customize_ip_ranges(self, rule: Dict[str, Any], ip_ranges: Dict[str, str]) -> Dict[str, Any]:
        """Customize IP ranges in rule conditions."""
        conditions = rule.get("conditions", {})

        def update_condition(condition):
            if condition.get("type") == "ip_cidr":
                # Map common network types to custom ranges
                current_cidr = condition.get("value", "")
                if current_cidr.startswith("192.168.100."):  # DMZ
                    condition["value"] = ip_ranges.get("dmz", current_cidr)
                elif current_cidr.startswith("192.168.1."):  # Management
                    condition["value"] = ip_ranges.get("management", current_cidr)
                elif current_cidr.startswith("10.1."):  # Secure/CDE
                    condition["value"] = ip_ranges.get("secure", current_cidr)

        # Handle both simple and complex condition structures
        if "conditions" in conditions:
            for condition in conditions["conditions"]:
                update_condition(condition)
        else:
            update_condition(conditions)

        return rule

    def _customize_tag_colors(self, rule: Dict[str, Any], tag_colors: Dict[str, str]) -> Dict[str, Any]:
        """Customize tag colors in rule actions."""
        for action in rule.get("actions", []):
            if action.get("type") == "add_tag":
                tag_name = action.get("tag_name", "")
                if tag_name in tag_colors:
                    action["tag_color"] = tag_colors[tag_name]

        return rule

    def export_template(self, template_id: str) -> str:
        """Export a template as JSON string."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        export_data = {
            "template_id": template_id,
            "exported_at": datetime.utcnow().isoformat(),
            "template": template
        }

        return json.dumps(export_data, indent=2)

    def import_template(self, template_data: str) -> str:
        """Import a template from JSON string."""
        try:
            data = json.loads(template_data)
            template_id = data.get("template_id")
            template = data.get("template")

            if not template_id or not template:
                raise ValueError("Invalid template format")

            # Add imported template
            self.templates[template_id] = template

            return template_id

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")

# Global instance
tag_template_manager = TagTemplateManager()

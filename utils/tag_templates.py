# utils/tag_templates.py

import json
import os
from typing import Dict, List, Any
from datetime import datetime

class TagTemplateManager:
    """Manager for predefined tagging rule templates and presets."""

    def __init__(self):
        self.apps_data = self._load_apps_data()
        self.templates = self._load_builtin_templates()

    def _load_apps_data(self) -> List[Dict[str, Any]]:
        """Load application data from apps.json."""
        try:
            apps_json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resource', 'apps.json')
            with open(apps_json_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _generate_application_rules(self) -> List[Dict[str, Any]]:
        """Generate intelligent categorical rules from apps.json data."""
        if not self.apps_data:
            return []

        # Define application categories with their apps and colors
        app_categories = {
            "Media Server": {
                "color": "#e5a00d",
                "apps": ["Plex", "Jellyfin", "Emby", "Airsonic", "Navidrome", "Audiobookshelf", "Funkwhale", "Peertube"],
                "description": "Media streaming and entertainment services"
            },
            "Home Automation": {
                "color": "#41bdf5",
                "apps": ["Home Assistant", "Frigate", "HomeBox"],
                "description": "Home automation and IoT management"
            },
            "Security Tools": {
                "color": "#dc3545",
                "apps": ["Pi-hole", "AdGuard Home", "Authelia", "Authentik", "Bitwarden (Self-hosted)", "Vaultwarden", "Keycloak"],
                "description": "Security, authentication, and privacy tools"
            },
            "File Storage": {
                "color": "#0082c9",
                "apps": ["Nextcloud", "Filebrowser", "Seafile", "Pydio", "WebDAV", "Syncthing", "Resilio Sync"],
                "description": "File storage, sync, and sharing services"
            },
            "Media Management": {
                "color": "#6f42c1",
                "apps": ["Sonarr", "Radarr", "Lidarr", "Readarr", "Bazarr", "Prowlarr", "Whisparr", "Overseerr", "Jellyseerr", "Ombi", "Requestrr"],
                "description": "Media acquisition and management tools"
            },
            "Download Client": {
                "color": "#fd7e14",
                "apps": ["qBittorrent", "Transmission", "rTorrent", "rFlood", "SABnzbd", "NZBGet", "NZBHydra2", "Jackett", "Jdownloader"],
                "description": "Download clients and indexers"
            },
            "Monitoring": {
                "color": "#198754",
                "apps": ["Grafana", "Prometheus", "Netdata", "Uptime Kuma", "Zabbix", "Scrutiny", "Tautulli", "Speedtest Tracker"],
                "description": "System monitoring and observability"
            },
            "Development": {
                "color": "#6610f2",
                "apps": ["GitLab", "Gitea", "Gogs", "Jenkins", "Drone CI", "Docker Registry"],
                "description": "Development and CI/CD tools"
            },
            "Container Management": {
                "color": "#13bef9",
                "apps": ["Portainer", "Rancher", "Dockage", "Kubernetes", "K8s", "Docker Swarm", "Komodo"],
                "description": "Container orchestration and management"
            },
            "Documentation": {
                "color": "#20c997",
                "apps": ["BookStack", "Wiki.js", "Trilium Notes", "Joplin Server"],
                "description": "Documentation and note-taking platforms"
            },
            "Communication": {
                "color": "#e83e8c",
                "apps": ["Mattermost", "Rocket.Chat", "Jitsi Meet", "TeamSpeak", "TheLounge", "ZNC"],
                "description": "Communication and collaboration tools"
            },
            "Analytics": {
                "color": "#fd7e14",
                "apps": ["Matomo", "Plausible Analytics", "Simple Analytics", "Umami"],
                "description": "Web analytics and tracking"
            },
            "Backup": {
                "color": "#6c757d",
                "apps": ["Duplicacy Web Edition", "Kopia"],
                "description": "Backup and archival solutions"
            },
            "Productivity": {
                "color": "#0d6efd",
                "apps": ["Kanboard", "Mealie", "Tandoor Recipes", "Monica", "Firefly III"],
                "description": "Personal productivity and organization"
            },
            "Content Management": {
                "color": "#198754",
                "apps": ["WordPress", "Ghost", "Flarum", "Mastodon"],
                "description": "Content management and publishing"
            },
            "Network Tools": {
                "color": "#ffc107",
                "apps": ["Nginx", "Nginx Proxy Manager", "Traefik", "OpenVPN", "WireGuard", "ntopng", "PiAlert"],
                "description": "Network infrastructure and tools"
            },
            "Database": {
                "color": "#6f42c1",
                "apps": ["InfluxDB", "Loki"],
                "description": "Database and data storage services"
            },
            "Automation": {
                "color": "#20c997",
                "apps": ["n8n", "Nodered", "Huginn"],
                "description": "Workflow automation and integration"
            },
            "Remote Access": {
                "color": "#fd7e14",
                "apps": ["Kasm Workspaces", "Webtop"],
                "description": "Remote desktop and access solutions"
            }
        }

        rules = []
        priority = 80  # Higher priority for categorical detection

        for category, config in app_categories.items():
            # Create a list of app names for regex matching
            app_names = config["apps"]

            # Build regex pattern for all apps in this category
            app_patterns = []
            for app_name in app_names:
                # Extract keywords from app name for better matching
                keywords = self._extract_keywords(app_name)
                app_patterns.extend(keywords)

            if app_patterns:
                rule = {
                    "name": f"Tag {category} Applications",
                    "description": f"Identify {config['description']} - {', '.join(app_names[:3])}{'...' if len(app_names) > 3 else ''}",
                    "priority": priority,
                    "enabled": True,
                    "auto_execute": True,
                    "conditions": {
                        "operator": "OR",
                        "conditions": [
                            {"type": "description_regex", "value": f"(?i)({'|'.join(app_patterns)})"}
                        ]
                    },
                    "actions": [
                        {"type": "add_tag", "tag_name": category, "tag_color": config["color"]}
                    ]
                }
                rules.append(rule)
                priority -= 1

        return rules

    def _extract_keywords(self, app_name: str) -> List[str]:
        """Extract keywords from application name for regex matching."""
        import re

        # Remove common suffixes and prefixes
        name = re.sub(r'\(.*?\)', '', app_name)  # Remove parentheses
        name = re.sub(r'\b(Self-hosted|Web UI|Server|Edition)\b', '', name, flags=re.IGNORECASE)

        # Split on common separators and filter out short words
        keywords = []
        for word in re.split(r'[-\s/]+', name):
            word = word.strip()
            if len(word) >= 3 and word.lower() not in ['the', 'and', 'for', 'web', 'app']:
                keywords.append(re.escape(word))

        return keywords if keywords else [re.escape(app_name)]

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
                        ]
                    },
                    {
                        "name": "Tag Database Services",
                        "description": "Identify database services requiring protection",
                        "priority": 90,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "AND",
                            "conditions": [
                                {"type": "port_list", "value": [3306, 5432, 1433, 27017, 6379, 5984]},
                                {"type": "description_regex", "value": "(?i)(mysql|postgres|sql|mongo|redis|couch)"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Database", "tag_color": "#6f42c1"},
                        ]
                    },
                    {
                        "name": "Tag Web Services",
                        "description": "Identify web services",
                        "priority": 80,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "AND",
                            "conditions": [
                                {"type": "description_regex", "value": "(?i)(web|http|apache|iis)"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Web-Service", "tag_color": "#0d6efd"},
                        ]
                    },
                    {
                        "name": "Tag Reverse Proxy Services",
                        "description": "Identify reverse proxy services",
                        "priority": 80,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "AND",
                            "conditions": [
                                {"type": "port_list", "value": [80, 443, 8080, 8443, 3000, 8000]},
                                {"type": "description_regex", "value": "(?i)(nginx|caddy|haproxy|traefik)"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Reverse-Proxy", "tag_color": "#ffc107"},
                        ]
                    },
                    {
                        "name": "Tag Administrative Services",
                        "description": "Identify administrative and management interfaces",
                        "priority": 85,
                        "enabled": True,
                        "auto_execute": True,
                        "conditions": {
                            "operator": "AND",
                            "conditions": [
                                {"type": "description_regex", "value": "(?i)(admin|management|dashboard|panel|console)"},
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Administrative", "tag_color": "#e83e8c"},
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
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Monitoring", "tag_color": "#198754"},
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
                                {"type": "source", "value": "docker"}
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Container", "tag_color": "#0d6efd"},
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
                            ]
                        },
                        "actions": [
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
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Development", "tag_color": "#6f42c1"},
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
                                {"type": "description_regex", "value": "(?i)(health|status|ping|uptime)"},
                            ]
                        },
                        "actions": [
                            {"type": "add_tag", "tag_name": "Health-Check", "tag_color": "#198754"},
                        ]
                    }
                ]
            },

            "application_detection": {
                "name": "Application Detection",
                "description": "Automatically detect and tag applications by category based on apps.json data",
                "category": "Applications",
                "rules": self._generate_application_rules()
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

#!/usr/bin/env python3
"""
Migration: Docker Multi-Instance Support

This migration adds support for multiple Docker, Portainer, and Komodo instances
by creating a new DockerInstance table and migrating existing settings.

Changes:
1. Create DockerInstance table for managing multiple instances
2. Add instance_id column to DockerService table
3. Migrate existing settings to default instances
4. Link existing services to appropriate default instances

Author: Portall Migration System
Date: 2025-01-19
"""

import os
import sys
import json
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """
    Run the Docker multi-instance migration.

    Returns:
        bool: True if migration was successful, False otherwise.
    """
    try:
        # Import Flask app and database
        from app import app
        from utils.database import db, Setting, DockerService
        from sqlalchemy import text, Column, Integer, String, Boolean, DateTime, JSON, ForeignKey

        with app.app_context():
            logger.info("Starting Docker multi-instance migration...")

            # Step 1: Create DockerInstance table
            logger.info("Creating DockerInstance table...")

            # Check if table already exists
            inspector = db.inspect(db.engine)
            if 'docker_instance' in inspector.get_table_names():
                logger.info("DockerInstance table already exists. Skipping creation.")
            else:
                # Create the table using raw SQL to avoid model dependencies
                create_table_sql = """
                CREATE TABLE docker_instance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    type VARCHAR(20) NOT NULL CHECK (type IN ('docker', 'portainer', 'komodo')),
                    enabled BOOLEAN DEFAULT 1,
                    auto_detect BOOLEAN DEFAULT 1,
                    scan_interval INTEGER DEFAULT 300,
                    config JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """

                db.session.execute(text(create_table_sql))
                db.session.commit()
                logger.info("✅ DockerInstance table created successfully")

            # Step 2: Check for existing Docker settings and create default instances
            logger.info("Checking for existing Docker integration settings...")

            # Get current settings
            settings = {}
            setting_keys = [
                'docker_enabled', 'docker_host', 'docker_auto_detect', 'docker_scan_interval',
                'portainer_enabled', 'portainer_url', 'portainer_api_key', 'portainer_verify_ssl',
                'portainer_auto_detect', 'portainer_scan_interval',
                'komodo_enabled', 'komodo_url', 'komodo_api_key', 'komodo_api_secret',
                'komodo_auto_detect', 'komodo_scan_interval'
            ]

            for key in setting_keys:
                setting = Setting.query.filter_by(key=key).first()
                settings[key] = setting.value if setting else ''

            # Step 3: Create default instances based on existing settings
            instances_created = []

            # Docker instance
            if settings.get('docker_enabled', 'false').lower() == 'true':
                logger.info("Creating default Docker instance...")

                docker_config = {
                    'host': settings.get('docker_host', 'unix:///var/run/docker.sock'),
                    'timeout': 30
                }

                insert_sql = """
                INSERT INTO docker_instance (name, type, enabled, auto_detect, scan_interval, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """

                db.session.execute(text(insert_sql), (
                    'Default Docker',
                    'docker',
                    1,  # enabled
                    1 if settings.get('docker_auto_detect', 'false').lower() == 'true' else 0,
                    int(settings.get('docker_scan_interval', '300')),
                    json.dumps(docker_config),
                    datetime.utcnow(),
                    datetime.utcnow()
                ))

                instances_created.append('Default Docker')
                logger.info("✅ Default Docker instance created")

            # Portainer instance
            if settings.get('portainer_enabled', 'false').lower() == 'true':
                logger.info("Creating default Portainer instance...")

                portainer_config = {
                    'url': settings.get('portainer_url', ''),
                    'api_key': settings.get('portainer_api_key', ''),
                    'verify_ssl': settings.get('portainer_verify_ssl', 'true').lower() == 'true'
                }

                insert_sql = """
                INSERT INTO docker_instance (name, type, enabled, auto_detect, scan_interval, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """

                db.session.execute(text(insert_sql), (
                    'Default Portainer',
                    'portainer',
                    1,  # enabled
                    1 if settings.get('portainer_auto_detect', 'false').lower() == 'true' else 0,
                    int(settings.get('portainer_scan_interval', '300')),
                    json.dumps(portainer_config),
                    datetime.utcnow(),
                    datetime.utcnow()
                ))

                instances_created.append('Default Portainer')
                logger.info("✅ Default Portainer instance created")

            # Komodo instance
            if settings.get('komodo_enabled', 'false').lower() == 'true':
                logger.info("Creating default Komodo instance...")

                komodo_config = {
                    'url': settings.get('komodo_url', ''),
                    'api_key': settings.get('komodo_api_key', ''),
                    'api_secret': settings.get('komodo_api_secret', '')
                }

                insert_sql = """
                INSERT INTO docker_instance (name, type, enabled, auto_detect, scan_interval, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """

                db.session.execute(text(insert_sql), (
                    'Default Komodo',
                    'komodo',
                    1,  # enabled
                    1 if settings.get('komodo_auto_detect', 'false').lower() == 'true' else 0,
                    int(settings.get('komodo_scan_interval', '300')),
                    json.dumps(komodo_config),
                    datetime.utcnow(),
                    datetime.utcnow()
                ))

                instances_created.append('Default Komodo')
                logger.info("✅ Default Komodo instance created")

            # Step 4: Add instance_id column to DockerService table
            logger.info("Adding instance_id column to DockerService table...")

            # Check if column already exists
            columns = [col['name'] for col in inspector.get_columns('docker_service')]
            if 'instance_id' in columns:
                logger.info("instance_id column already exists in DockerService table")
            else:
                # Add the column
                alter_sql = "ALTER TABLE docker_service ADD COLUMN instance_id INTEGER"
                db.session.execute(text(alter_sql))
                db.session.commit()
                logger.info("✅ instance_id column added to DockerService table")

            # Step 5: Link existing services to default instances
            logger.info("Linking existing DockerService records to default instances...")

            # Get existing services
            existing_services = DockerService.query.all()
            logger.info(f"Found {len(existing_services)} existing DockerService records")

            if existing_services:
                # Get the default instances we just created
                default_instances = {}
                for instance_name in instances_created:
                    result = db.session.execute(
                        text("SELECT id, type FROM docker_instance WHERE name = ?"),
                        (instance_name,)
                    ).fetchone()
                    if result:
                        default_instances[result[1]] = result[0]  # type -> id

                # Link services to instances based on their source
                services_updated = 0
                for service in existing_services:
                    instance_id = None

                    # Determine which instance this service belongs to based on naming patterns
                    if 'portainer' in service.name.lower() or service.container_id.startswith('portainer'):
                        instance_id = default_instances.get('portainer')
                    elif 'komodo' in service.name.lower() or service.container_id.startswith('komodo'):
                        instance_id = default_instances.get('komodo')
                    else:
                        # Default to Docker instance
                        instance_id = default_instances.get('docker')

                    if instance_id:
                        update_sql = "UPDATE docker_service SET instance_id = ? WHERE id = ?"
                        db.session.execute(text(update_sql), (instance_id, service.id))
                        services_updated += 1

                db.session.commit()
                logger.info(f"✅ Linked {services_updated} existing services to default instances")

            # Step 6: Verify migration success
            logger.info("Verifying migration success...")

            # Check that DockerInstance table exists and has data
            instance_count = db.session.execute(text("SELECT COUNT(*) FROM docker_instance")).scalar()
            logger.info(f"DockerInstance table contains {instance_count} instances")

            # Check that DockerService table has instance_id column
            columns = [col['name'] for col in inspector.get_columns('docker_service')]
            if 'instance_id' in columns:
                logger.info("✅ DockerService table has instance_id column")
            else:
                raise Exception("instance_id column not found in DockerService table")

            # Check that existing services are linked
            unlinked_services = db.session.execute(
                text("SELECT COUNT(*) FROM docker_service WHERE instance_id IS NULL")
            ).scalar()

            if unlinked_services > 0:
                logger.warning(f"⚠️  {unlinked_services} services are not linked to instances")
            else:
                logger.info("✅ All services are properly linked to instances")

            logger.info("🎉 Docker multi-instance migration completed successfully!")
            logger.info(f"Created instances: {', '.join(instances_created) if instances_created else 'None'}")

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("✅ Migration completed successfully")
        sys.exit(0)
    else:
        print("❌ Migration failed")
        sys.exit(1)

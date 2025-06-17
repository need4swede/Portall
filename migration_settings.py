# migration_settings.py

import logging
from utils.database import db, Setting

# Setup logging
logger = logging.getLogger(__name__)

def run_migration():
    """
    Run the settings migration to ensure all required settings exist with proper defaults.
    This migration adds any missing settings that are required for the application to function properly.

    Returns:
        bool: True if migration completed successfully, False otherwise.
    """
    try:
        logger.info("Starting settings migration...")

        # Define all required settings with their default values
        required_settings = {
            # Core App Settings
            'default_ip': '',
            'theme': 'light',
            'custom_css': '',

            # Port Management Settings
            'port_start': '1024',
            'port_end': '65535',
            'port_exclude': '',
            'port_length': '4',
            'copy_format': 'port_only',

            # Docker Integration Settings
            'docker_enabled': 'false',
            'docker_host': 'unix:///var/run/docker.sock',
            'docker_auto_detect': 'false',
            'docker_scan_interval': '300',

            # Portainer Integration Settings
            'portainer_enabled': 'false',
            'portainer_url': '',
            'portainer_api_key': '',
            'portainer_verify_ssl': 'true',  # This is the new SSL verification setting
            'portainer_auto_detect': 'false',
            'portainer_scan_interval': '300',

            # Komodo Integration Settings
            'komodo_enabled': 'false',
            'komodo_url': '',
            'komodo_api_key': '',
            'komodo_api_secret': '',
            'komodo_auto_detect': 'false',
            'komodo_scan_interval': '300',

            # Port Scanning Settings
            'port_scanning_enabled': 'false',
            'scan_range_start': '1024',
            'scan_range_end': '65535',
            'scan_exclude': '',
            'verify_ports_on_load': 'false',
            'scan_timeout': '1000',
            'scan_threads': '50',
            'auto_add_discovered': 'false'
        }

        settings_added = 0
        settings_skipped = 0

        # Check each required setting and create if missing
        for key, default_value in required_settings.items():
            existing_setting = Setting.query.filter_by(key=key).first()

            if existing_setting is None:
                # Setting doesn't exist, create it with the default value
                new_setting = Setting(key=key, value=default_value)
                db.session.add(new_setting)
                settings_added += 1
                logger.info(f"Added missing setting: {key} = '{default_value}'")
            else:
                # Setting already exists, skip it
                settings_skipped += 1
                logger.debug(f"Setting already exists: {key} = '{existing_setting.value}'")

        # Commit all changes
        db.session.commit()

        logger.info(f"Settings migration completed successfully. Added {settings_added} settings, skipped {settings_skipped} existing settings.")
        return True

    except Exception as e:
        logger.error(f"Error during settings migration: {str(e)}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    # Allow running this migration standalone for testing
    from flask import Flask
    from utils.database import init_db

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/portall.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        init_db(app)
        success = run_migration()
        if success:
            print("Settings migration completed successfully!")
        else:
            print("Settings migration failed!")

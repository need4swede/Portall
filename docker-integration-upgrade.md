# Docker Integration Multi-Instance Upgrade Plan

## Overview

This document outlines the step-by-step implementation plan for upgrading Portall's Docker integration to support multiple instances of Docker, Portainer, and Komodo across different hosts.

### Current State
- Single instance support for each integration type
- Settings stored as individual key-value pairs
- Single background thread per integration type
- Separate forms for each integration in settings

### Target State
- Multiple instances per integration type
- Instance-based configuration with JSON storage
- Dynamic thread management per instance
- Unified modal-based UI following ports page pattern

## Architecture Overview

### Database Schema Changes
```
DockerInstance Table (NEW)
├── id (Primary Key)
├── name (User-defined name)
├── type (ENUM: 'docker', 'portainer', 'komodo')
├── enabled (Boolean)
├── auto_detect (Boolean)
├── scan_interval (Integer)
├── config (JSON - type-specific settings)
├── created_at, updated_at (Timestamps)

DockerService Table (UPDATED)
├── instance_id (Foreign Key to DockerInstance) - NEW
├── [existing fields remain unchanged]
```

### Configuration Storage Strategy
- **Docker Config**: `{"host": "unix:///var/run/docker.sock", "timeout": 30}`
- **Portainer Config**: `{"url": "https://portainer.example.com", "api_key": "...", "verify_ssl": true}`
- **Komodo Config**: `{"url": "https://komodo.example.com", "api_key": "...", "api_secret": "..."}`

## Implementation Steps

### Phase 1: Core Infrastructure (Docker Multi-Instance)

#### Step 1: Create Database Migration
**Files to modify:**
- `migration_docker_instances.py` (NEW)
- `utils/database/migrations.py` (UPDATE)

**Tasks:**
1. Create new migration file `migration_docker_instances.py`
2. Implement `DockerInstance` table creation
3. Add `instance_id` column to `DockerService` table
4. Migrate existing settings to default instances
5. Link existing services to default instances
6. Add migration to the migration manager

**Migration Logic:**
```python
def run_migration():
    # 1. Create DockerInstance table
    # 2. Check for existing Docker settings
    # 3. Create "Default Docker" instance if docker_enabled=true
    # 4. Create "Default Portainer" instance if portainer_enabled=true
    # 5. Create "Default Komodo" instance if komodo_enabled=true
    # 6. Add instance_id column to DockerService
    # 7. Link all existing DockerService records to appropriate default instance
    # 8. Verify migration success
```

**Testing Criteria:**
- [ ] Migration runs without errors
- [ ] Existing Docker services are preserved
- [ ] Default instances are created correctly
- [ ] All existing functionality continues to work

#### Step 2: Create DockerInstance Model
**Files to modify:**
- `utils/database/docker.py` (UPDATE)
- `utils/database/__init__.py` (UPDATE)

**Tasks:**
1. Add `DockerInstance` model class
2. Update `DockerService` model with `instance_id` relationship
3. Add model to database imports
4. Create helper methods for instance management

**Model Definition:**
```python
class DockerInstance(db.Model):
    __tablename__ = 'docker_instance'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum('docker', 'portainer', 'komodo', name='instance_type'), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    auto_detect = db.Column(db.Boolean, default=True)
    scan_interval = db.Column(db.Integer, default=300)
    config = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    services = db.relationship('DockerService', backref='instance', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<DockerInstance {self.name} ({self.type})>'
```

**Testing Criteria:**
- [ ] Model imports correctly
- [ ] Relationships work properly
- [ ] JSON config field stores/retrieves data correctly

#### Step 3: Create Instance Manager Class
**Files to modify:**
- `utils/docker_instance_manager.py` (NEW)

**Tasks:**
1. Create `DockerInstanceManager` class
2. Implement CRUD operations for instances
3. Add instance validation methods
4. Create client factory methods

**Class Structure:**
```python
class DockerInstanceManager:
    def __init__(self, db):
        self.db = db

    def get_instances_by_type(self, instance_type):
        """Get all instances of a specific type"""

    def get_instance(self, instance_id):
        """Get single instance by ID"""

    def create_instance(self, name, instance_type, config, **kwargs):
        """Create new instance"""

    def update_instance(self, instance_id, **kwargs):
        """Update existing instance"""

    def delete_instance(self, instance_id):
        """Delete instance and associated services"""

    def test_connection(self, instance_id):
        """Test connection to instance"""

    def get_client(self, instance_id):
        """Get appropriate client for instance"""

    def generate_instance_name(self, instance_type):
        """Generate fallback name for instance"""
```

**Testing Criteria:**
- [ ] All CRUD operations work correctly
- [ ] Instance validation prevents invalid configurations
- [ ] Client factory returns appropriate clients
- [ ] Name generation works with fallback logic

#### Step 4: Update Docker Routes for Instance Management
**Files to modify:**
- `utils/routes/docker.py` (UPDATE)

**Tasks:**
1. Add new instance management routes
2. Update existing routes to work with instances
3. Maintain backward compatibility
4. Add instance testing endpoints

**New Routes:**
```python
@docker_bp.route('/docker/instances', methods=['GET', 'POST'])
def manage_instances():
    """List all instances or create new instance"""

@docker_bp.route('/docker/instances/<int:instance_id>', methods=['GET', 'PUT', 'DELETE'])
def instance_detail(instance_id):
    """Get, update, or delete specific instance"""

@docker_bp.route('/docker/instances/<int:instance_id>/scan', methods=['POST'])
def scan_instance(instance_id):
    """Trigger scan for specific instance"""

@docker_bp.route('/docker/instances/<int:instance_id>/test', methods=['POST'])
def test_instance(instance_id):
    """Test connection to specific instance"""

@docker_bp.route('/docker/instances/types', methods=['GET'])
def get_instance_types():
    """Get available instance types and their config schemas"""
```

**Testing Criteria:**
- [ ] All new routes respond correctly
- [ ] Instance CRUD operations work via API
- [ ] Connection testing works for all instance types
- [ ] Backward compatibility maintained

#### Step 5: Update UI - Instance Blocks Display
**Files to modify:**
- `templates/settings.html` (UPDATE)
- `static/js/core/settings.js` (UPDATE)

**Tasks:**
1. Replace single Docker form with instance blocks
2. Add "Add Docker Integration" button
3. Display instance status and information
4. Add action buttons (Edit, Delete, Scan Now)

**UI Structure:**
```html
<!-- Docker Integration Section -->
<div class="tab-pane fade" id="docker" role="tabpanel">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h2>Docker Integration</h2>
        <button id="add-docker-instance-btn" class="btn btn-primary">
            <i class="fas fa-plus"></i> Add Docker Integration
        </button>
    </div>

    <!-- Instance Blocks Container -->
    <div id="docker-instances-container">
        <!-- Instance blocks will be loaded here -->
    </div>
</div>
```

**Instance Block Template:**
```html
<div class="docker-instance-block glass-card mb-3" data-instance-id="{id}">
    <div class="instance-header">
        <h4>{name} <span class="badge badge-{type}">{type}</span></h4>
        <div class="instance-status">
            <span class="status-indicator {status}"></span>
            <span class="status-text">{status_text}</span>
        </div>
    </div>
    <div class="instance-details">
        <div class="detail-item">
            <span class="label">Last Scan:</span>
            <span class="value">{last_scan}</span>
        </div>
        <div class="detail-item">
            <span class="label">Services:</span>
            <span class="value">{service_count} containers, {port_count} ports</span>
        </div>
        <div class="detail-item">
            <span class="label">Auto-scan:</span>
            <span class="value">Every {scan_interval} minutes</span>
        </div>
    </div>
    <div class="instance-actions">
        <button class="btn btn-sm btn-outline-primary scan-instance-btn">
            <i class="fas fa-search"></i> Scan Now
        </button>
        <button class="btn btn-sm btn-outline-secondary edit-instance-btn">
            <i class="fas fa-edit"></i> Edit
        </button>
        <button class="btn btn-sm btn-outline-danger delete-instance-btn">
            <i class="fas fa-trash"></i> Delete
        </button>
    </div>
</div>
```

**Testing Criteria:**
- [ ] Instance blocks display correctly
- [ ] Status indicators work properly
- [ ] Action buttons trigger correct functions
- [ ] Responsive design works on mobile

#### Step 6: Create Add/Edit Instance Modal
**Files to modify:**
- `templates/settings.html` (UPDATE)
- `static/js/core/settings.js` (UPDATE)

**Tasks:**
1. Create modal HTML structure
2. Implement two-step modal flow
3. Add form validation
4. Handle type-specific configuration

**Modal Structure:**
```html
<!-- Add/Edit Docker Instance Modal -->
<div class="modal fade" id="dockerInstanceModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="dockerInstanceModalLabel">Add Docker Integration</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <!-- Step 1: Type Selection -->
                <div id="instance-type-step" class="modal-step">
                    <h6>Choose Integration Type:</h6>
                    <div class="type-selection">
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="instance_type" id="type-docker" value="docker">
                            <label class="form-check-label" for="type-docker">
                                <i class="fab fa-docker"></i> Docker Engine
                            </label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="instance_type" id="type-portainer" value="portainer">
                            <label class="form-check-label" for="type-portainer">
                                <i class="fas fa-ship"></i> Portainer
                            </label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="instance_type" id="type-komodo" value="komodo">
                            <label class="form-check-label" for="type-komodo">
                                <i class="fas fa-server"></i> Komodo
                            </label>
                        </div>
                    </div>
                </div>

                <!-- Step 2: Configuration -->
                <div id="instance-config-step" class="modal-step" style="display: none;">
                    <form id="docker-instance-form">
                        <input type="hidden" id="instance-id" name="instance_id">
                        <input type="hidden" id="selected-type" name="type">

                        <!-- Common Fields -->
                        <div class="mb-3">
                            <label for="instance-name" class="form-label">Name</label>
                            <input type="text" class="form-control" id="instance-name" name="name" required>
                        </div>

                        <div class="mb-3 form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="instance-enabled" name="enabled" checked>
                            <label class="form-check-label" for="instance-enabled">Enable Integration</label>
                        </div>

                        <div class="mb-3 form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="instance-auto-detect" name="auto_detect" checked>
                            <label class="form-check-label" for="instance-auto-detect">Auto-detect Ports</label>
                        </div>

                        <div class="mb-3">
                            <label for="instance-scan-interval" class="form-label">Scan Interval (seconds)</label>
                            <input type="number" class="form-control" id="instance-scan-interval" name="scan_interval" min="60" value="300">
                        </div>

                        <!-- Type-specific Configuration -->
                        <div id="docker-config" class="type-config" style="display: none;">
                            <div class="mb-3">
                                <label for="docker-host" class="form-label">Docker Host</label>
                                <input type="text" class="form-control" id="docker-host" name="host" value="unix:///var/run/docker.sock">
                                <small class="form-text text-muted">Examples: unix:///var/run/docker.sock, tcp://docker.example.com:2376</small>
                            </div>
                            <div class="mb-3">
                                <label for="docker-timeout" class="form-label">Connection Timeout (seconds)</label>
                                <input type="number" class="form-control" id="docker-timeout" name="timeout" min="5" max="120" value="30">
                            </div>
                        </div>

                        <div id="portainer-config" class="type-config" style="display: none;">
                            <div class="mb-3">
                                <label for="portainer-url" class="form-label">Portainer URL</label>
                                <input type="url" class="form-control" id="portainer-url" name="url" placeholder="https://portainer.example.com">
                            </div>
                            <div class="mb-3">
                                <label for="portainer-api-key" class="form-label">API Key</label>
                                <input type="password" class="form-control" id="portainer-api-key" name="api_key">
                            </div>
                            <div class="mb-3 form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="portainer-verify-ssl" name="verify_ssl" checked>
                                <label class="form-check-label" for="portainer-verify-ssl">Verify SSL Certificates</label>
                            </div>
                        </div>

                        <div id="komodo-config" class="type-config" style="display: none;">
                            <div class="mb-3">
                                <label for="komodo-url" class="form-label">Komodo URL</label>
                                <input type="url" class="form-control" id="komodo-url" name="url" placeholder="https://komodo.example.com">
                            </div>
                            <div class="mb-3">
                                <label for="komodo-api-key" class="form-label">API Key</label>
                                <input type="password" class="form-control" id="komodo-api-key" name="api_key">
                            </div>
                            <div class="mb-3">
                                <label for="komodo-api-secret" class="form-label">API Secret</label>
                                <input type="password" class="form-control" id="komodo-api-secret" name="api_secret">
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="button" id="instance-back-btn" class="btn btn-outline-secondary" style="display: none;">Back</button>
                <button type="button" id="instance-next-btn" class="btn btn-primary">Next</button>
                <button type="button" id="test-connection-btn" class="btn btn-outline-info" style="display: none;">Test Connection</button>
                <button type="button" id="save-instance-btn" class="btn btn-success" style="display: none;">Save</button>
            </div>
        </div>
    </div>
</div>
```

**Testing Criteria:**
- [ ] Modal opens and closes correctly
- [ ] Two-step flow works smoothly
- [ ] Form validation prevents invalid submissions
- [ ] Type-specific fields show/hide correctly
- [ ] Connection testing works for all types

#### Step 7: Update Auto-Scanning System
**Files to modify:**
- `utils/routes/docker.py` (UPDATE)
- `utils/instance_scan_manager.py` (NEW)

**Tasks:**
1. Create new scan manager for instance-based scanning
2. Update existing auto-scan threads
3. Implement dynamic thread management
4. Handle thread lifecycle (start/stop/restart)

**Scan Manager Structure:**
```python
class InstanceScanManager:
    def __init__(self, app, db, instance_manager):
        self.app = app
        self.db = db
        self.instance_manager = instance_manager
        self.active_threads = {}  # instance_id -> thread
        self.shutdown_event = threading.Event()

    def start_all_scanning(self):
        """Start scanning for all enabled instances"""

    def stop_all_scanning(self):
        """Stop all scanning threads"""

    def start_instance_scanning(self, instance_id):
        """Start scanning for specific instance"""

    def stop_instance_scanning(self, instance_id):
        """Stop scanning for specific instance"""

    def restart_instance_scanning(self, instance_id):
        """Restart scanning for specific instance"""

    def _scan_worker(self, instance_id):
        """Worker function for instance scanning"""
```

**Testing Criteria:**
- [ ] Multiple instances can scan simultaneously
- [ ] Thread management works correctly
- [ ] Scan intervals are respected per instance
- [ ] Threads stop/start properly when instances are modified

#### Step 8: Backward Compatibility Layer
**Files to modify:**
- `utils/routes/docker.py` (UPDATE)

**Tasks:**
1. Maintain existing `/docker/settings` endpoints
2. Map old settings to default instances
3. Ensure existing functionality continues to work
4. Add deprecation warnings for old endpoints

**Compatibility Functions:**
```python
def get_legacy_docker_settings():
    """Get settings in old format for backward compatibility"""
    default_docker = DockerInstance.query.filter_by(type='docker', name='Default Docker').first()
    if default_docker:
        return {
            'docker_enabled': str(default_docker.enabled).lower(),
            'docker_host': default_docker.config.get('host', 'unix:///var/run/docker.sock'),
            'docker_auto_detect': str(default_docker.auto_detect).lower(),
            'docker_scan_interval': str(default_docker.scan_interval)
        }
    return {}

def update_legacy_docker_settings(form_data):
    """Update default instance from legacy settings format"""
    default_docker = DockerInstance.query.filter_by(type='docker', name='Default Docker').first()
    if default_docker:
        default_docker.enabled = form_data.get('docker_enabled', 'false').lower() == 'true'
        default_docker.auto_detect = form_data.get('docker_auto_detect', 'false').lower() == 'true'
        default_docker.scan_interval = int(form_data.get('docker_scan_interval', '300'))
        default_docker.config['host'] = form_data.get('docker_host', 'unix:///var/run/docker.sock')
        db.session.commit()
```

**Testing Criteria:**
- [ ] Existing API calls continue to work
- [ ] Legacy settings map correctly to default instances
- [ ] No breaking changes for existing integrations

### Phase 2: Portainer Multi-Instance Extension

#### Step 9: Extend Instance Management to Portainer
**Files to modify:**
- `utils/docker_instance_manager.py` (UPDATE)
- `utils/routes/docker.py` (UPDATE)

**Tasks:**
1. Add Portainer-specific client creation
2. Update scanning logic for Portainer instances
3. Test multi-instance Portainer functionality

#### Step 10: Update UI for Portainer Instances
**Files to modify:**
- `templates/settings.html` (UPDATE)
- `static/js/core/settings.js` (UPDATE)

**Tasks:**
1. Ensure Portainer instances display correctly
2. Test Portainer-specific configuration fields
3. Verify Portainer connection testing

### Phase 3: Komodo Multi-Instance Extension

#### Step 11: Extend Instance Management to Komodo
**Files to modify:**
- `utils/docker_instance_manager.py` (UPDATE)
- `utils/routes/docker.py` (UPDATE)

**Tasks:**
1. Add Komodo-specific client creation
2. Update scanning logic for Komodo instances
3. Test multi-instance Komodo functionality

#### Step 12: Complete UI Implementation
**Files to modify:**
- `templates/settings.html` (UPDATE)
- `static/js/core/settings.js` (UPDATE)

**Tasks:**
1. Ensure Komodo instances display correctly
2. Test Komodo-specific configuration fields
3. Verify Komodo connection testing

#### Step 13: Final Testing and Polish
**Tasks:**
1. Comprehensive testing of all instance types
2. Performance testing with multiple instances
3. UI/UX improvements and polish
4. Documentation updates

## Testing Checklist

### Database Migration Testing
- [ ] Migration runs successfully on fresh database
- [ ] Migration runs successfully on existing database with data
- [ ] Existing Docker services are preserved and linked correctly
- [ ] Default instances are created with correct configurations
- [ ] Rollback works if migration fails

### Instance Management Testing
- [ ] Create instances of all types (Docker, Portainer, Komodo)
- [ ] Edit instance configurations
- [ ] Delete instances and verify cleanup
- [ ] Test connection for all instance types
- [ ] Verify instance name generation and fallbacks

### UI Testing
- [ ] Instance blocks display correctly for all types
- [ ] Add/Edit modal works for all instance types
- [ ] Form validation prevents invalid configurations
- [ ] Responsive design works on mobile devices
- [ ] Action buttons (Scan, Edit, Delete) work correctly

### Scanning Testing
- [ ] Multiple instances can scan simultaneously
- [ ] Individual scan intervals are respected
- [ ] Auto-scanning can be enabled/disabled per instance
- [ ] Manual scanning works for individual instances
- [ ] Thread management handles instance changes correctly

### Backward Compatibility Testing
- [ ] Existing installations upgrade seamlessly
- [ ] Legacy API endpoints continue to work
- [ ] Existing Docker services continue to function
- [ ] No data loss during migration

### Performance Testing
- [ ] Multiple instances scanning doesn't overload system
- [ ] UI remains responsive with many instances
- [ ] Database queries are optimized
- [ ] Memory usage is reasonable with multiple threads

## Rollback Procedures

### Database Rollback
1. Stop the application
2. Restore database from pre-migration backup
3. Restart application with previous version
4. Verify functionality

### Partial Rollback
1. Disable problematic instances via UI
2. Stop auto-scanning for affected instances
3. Fix issues and re-enable
4. Resume normal operation

### Emergency Rollback
1. Set all instances to disabled in database
2. Restart application
3. Investigate and fix issues
4. Re-enable instances gradually

## Success Criteria

### Functional Requirements
- [ ] Support unlimited instances per integration type
- [ ] Maintain all existing functionality
- [ ] Seamless upgrade from single-instance setup
- [ ] Intuitive UI following established patterns

### Performance Requirements
- [ ] No significant performance degradation
- [ ] Efficient resource usage with multiple instances
- [ ] Responsive UI with many instances

### Reliability Requirements
- [ ] Robust error handling and recovery
- [ ] Safe migration with automatic backup
- [ ] Graceful handling of connection failures

### Usability Requirements
- [ ] Familiar UI patterns from ports page
- [ ] Clear instance status indicators
- [ ] Easy instance management workflow

## Implementation Timeline

### Week 1: Core Infrastructure
- Steps 1-4: Database migration and instance management

### Week 2: UI Implementation
- Steps 5-6: Instance blocks and modal implementation

### Week 3: Scanning and Compatibility
- Steps 7-8: Auto-scanning updates and backward compatibility

### Week 4: Extensions and Testing
- Steps 9-13: Portainer/Komodo extensions and final testing

## Notes

- Each step should be completed and tested before moving to the next
- Database backups should be created before each major change
- Backward compatibility must be maintained throughout
- UI should follow existing design patterns from the ports page
- Performance impact should be monitored during implementation

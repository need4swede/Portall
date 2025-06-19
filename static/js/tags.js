// static/js/tags.js

class TagManager {
    constructor() {
        this.tags = [];
        this.rules = [];
        this.selectedPorts = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadTags();
        this.loadRules();
        this.loadTemplates();
        this.setupTabHandlers();
    }

    bindEvents() {
        // Tag management
        document.getElementById('create-tag-btn').addEventListener('click', () => this.showTagModal());
        document.getElementById('save-tag-btn').addEventListener('click', () => this.saveTag());
        document.getElementById('tag-search').addEventListener('input', (e) => this.searchTags(e.target.value));

        // Rule management
        document.getElementById('create-rule-btn').addEventListener('click', () => this.showRuleModal());
        document.getElementById('save-rule-btn').addEventListener('click', () => this.saveRule());
        document.getElementById('execute-all-rules-btn').addEventListener('click', () => this.executeAllRules());
        document.getElementById('add-condition-btn').addEventListener('click', () => this.addCondition());
        document.getElementById('add-action-btn').addEventListener('click', () => this.addAction());

        // Filter
        document.getElementById('filter-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.filterPorts();
        });
        document.getElementById('clear-filter-btn').addEventListener('click', () => this.clearFilter());

        // Bulk operations
        document.getElementById('execute-bulk-btn').addEventListener('click', () => this.executeBulkOperation());

        // Template management
        document.getElementById('template-category-filter').addEventListener('change', (e) => this.filterTemplates(e.target.value));
        document.getElementById('import-template-btn').addEventListener('click', () => this.showImportTemplateModal());
        document.getElementById('export-config-btn').addEventListener('click', () => this.exportConfiguration());
        document.getElementById('import-config-btn').addEventListener('click', () => this.showImportConfigModal());
        document.getElementById('backup-config-btn').addEventListener('click', () => this.backupConfiguration());

        // Quick template actions
        document.getElementById('apply-security-template').addEventListener('click', () => this.applyQuickTemplate('security_hardening'));
        document.getElementById('apply-infrastructure-template').addEventListener('click', () => this.applyQuickTemplate('infrastructure_mapping'));
        document.getElementById('apply-network-template').addEventListener('click', () => this.applyQuickTemplate('network_segmentation'));
        document.getElementById('apply-monitoring-template').addEventListener('click', () => this.applyQuickTemplate('monitoring_setup'));
    }

    setupConditionOperatorHandler() {
        const operatorSelect = document.getElementById('condition-operator');
        const helpText = document.getElementById('condition-logic-help');

        if (operatorSelect && helpText) {
            operatorSelect.addEventListener('change', (e) => {
                const operator = e.target.value;
                if (operator === 'OR') {
                    helpText.textContent = 'At least one condition must be met (OR logic)';
                } else {
                    helpText.textContent = 'All conditions must be met (AND logic)';
                }
            });
        }
    }

    setupTabHandlers() {
        const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
        tabButtons.forEach(button => {
            button.addEventListener('shown.bs.tab', (e) => {
                const target = e.target.getAttribute('data-bs-target');
                if (target === '#filter-panel') {
                    this.loadFilterTags();
                }
            });
        });
    }

    // Tag Management
    async loadTags() {
        try {
            const response = await fetch('/api/tags');
            const data = await response.json();

            // The API returns a direct array of tags, not wrapped in a success object
            if (Array.isArray(data)) {
                this.tags = data;
                this.renderTags();
                this.updateTagStats();
            } else if (data.success) {
                this.tags = data.tags;
                this.renderTags();
                this.updateTagStats();
            } else {
                this.showNotification('Error loading tags: ' + (data.message || 'Unknown error'), 'error');
            }
        } catch (error) {
            this.showNotification('Error loading tags: ' + error.message, 'error');
        }
    }

    renderTags(filteredTags = null) {
        const tagsToRender = filteredTags || this.tags;
        const container = document.getElementById('tags-list');

        if (tagsToRender.length === 0) {
            container.innerHTML = '<p class="text-muted">No tags found.</p>';
            return;
        }

        container.innerHTML = tagsToRender.map(tag => `
            <div class="tag-item" data-tag-id="${tag.id}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center mb-2">
                            <span class="tag-badge" style="background-color: ${tag.color}">
                                ${tag.name}
                            </span>
                            <span class="usage-badge ms-2">${tag.usage_count} ports</span>
                        </div>
                        ${tag.description ? `<p class="text-muted mb-0">${tag.description}</p>` : ''}
                    </div>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="tagManager.editTag(${tag.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="tagManager.deleteTag(${tag.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    updateTagStats() {
        const totalTags = this.tags.length;
        const totalUsage = this.tags.reduce((sum, tag) => sum + tag.usage_count, 0);
        const mostUsed = this.tags.reduce((max, tag) => tag.usage_count > max.usage_count ? tag : max, { usage_count: 0 });

        document.getElementById('tag-stats').innerHTML = `
            <div class="mb-3">
                <h6>Total Tags</h6>
                <div class="h4 text-primary">${totalTags}</div>
            </div>
            <div class="mb-3">
                <h6>Total Tag Assignments</h6>
                <div class="h4 text-success">${totalUsage}</div>
            </div>
            ${mostUsed.name ? `
                <div class="mb-3">
                    <h6>Most Used Tag</h6>
                    <span class="tag-badge" style="background-color: ${mostUsed.color}">
                        ${mostUsed.name}
                    </span>
                    <div class="text-muted small">${mostUsed.usage_count} ports</div>
                </div>
            ` : ''}
        `;
    }

    searchTags(query) {
        if (!query.trim()) {
            this.renderTags();
            return;
        }

        const filtered = this.tags.filter(tag =>
            tag.name.toLowerCase().includes(query.toLowerCase()) ||
            (tag.description && tag.description.toLowerCase().includes(query.toLowerCase()))
        );
        this.renderTags(filtered);
    }

    showTagModal(tag = null) {
        const modal = new bootstrap.Modal(document.getElementById('tagModal'));
        const title = document.getElementById('tagModalTitle');
        const form = document.getElementById('tag-form');

        if (tag) {
            title.textContent = 'Edit Tag';
            document.getElementById('tag-id').value = tag.id;
            document.getElementById('tag-name').value = tag.name;
            document.getElementById('tag-color').value = tag.color;
            document.getElementById('tag-description').value = tag.description || '';
        } else {
            title.textContent = 'Create Tag';
            form.reset();
            document.getElementById('tag-id').value = '';
            document.getElementById('tag-color').value = '#007bff';
        }

        modal.show();

        // Setup the condition operator handler after modal is shown
        setTimeout(() => {
            this.setupConditionOperatorHandler();
        }, 100);
    }

    async saveTag() {
        const tagId = document.getElementById('tag-id').value;
        const name = document.getElementById('tag-name').value.trim();
        const color = document.getElementById('tag-color').value;
        const description = document.getElementById('tag-description').value.trim();

        if (!name) {
            this.showNotification('Tag name is required', 'error');
            return;
        }

        const data = { name, color, description };
        const url = tagId ? `/api/tags/${tagId}` : '/api/tags';
        const method = tagId ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                bootstrap.Modal.getInstance(document.getElementById('tagModal')).hide();
                this.loadTags();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error saving tag: ' + error.message, 'error');
        }
    }

    editTag(tagId) {
        const tag = this.tags.find(t => t.id === tagId);
        if (tag) {
            this.showTagModal(tag);
        }
    }

    async deleteTag(tagId) {
        const tag = this.tags.find(t => t.id === tagId);
        if (!tag) return;

        if (!confirm(`Are you sure you want to delete the tag "${tag.name}"? This will remove it from all ports.`)) {
            return;
        }

        try {
            const response = await fetch(`/api/tags/${tagId}`, { method: 'DELETE' });
            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                this.loadTags();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error deleting tag: ' + error.message, 'error');
        }
    }

    // Rule Management
    async loadRules() {
        try {
            const response = await fetch('/api/tagging-rules');
            const data = await response.json();

            if (data.success) {
                this.rules = data.rules;
                this.renderRules();
            } else {
                this.showNotification('Error loading rules: ' + data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error loading rules: ' + error.message, 'error');
        }
    }

    renderRules() {
        const container = document.getElementById('rules-list');

        if (this.rules.length === 0) {
            container.innerHTML = '<p class="text-muted">No tagging rules found.</p>';
            return;
        }

        container.innerHTML = this.rules.map(rule => {
            // Parse conditions to determine logic type
            let conditionLogic = 'ALL conditions';
            let conditionCount = 0;
            try {
                const conditions = JSON.parse(rule.conditions);
                if (conditions.operator) {
                    conditionLogic = conditions.operator === 'OR' ? 'ANY condition' : 'ALL conditions';
                    conditionCount = conditions.conditions ? conditions.conditions.length : 0;
                } else if (Array.isArray(conditions)) {
                    conditionCount = conditions.length;
                } else {
                    conditionCount = 1;
                }
            } catch (e) {
                conditionCount = 1;
            }

            // Parse actions to count them
            let actionCount = 0;
            try {
                const actions = JSON.parse(rule.actions);
                actionCount = Array.isArray(actions) ? actions.length : 1;
            } catch (e) {
                actionCount = 1;
            }

            return `
                <div class="rule-item ${!rule.enabled ? 'disabled' : ''}" data-rule-id="${rule.id}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-center mb-2">
                                <h6 class="mb-0 me-2">${rule.name}</h6>
                                <span class="badge ${rule.enabled ? 'bg-success' : 'bg-secondary'} me-1">
                                    ${rule.enabled ? 'Enabled' : 'Disabled'}
                                </span>
                                <span class="badge ${rule.auto_execute ? 'bg-primary' : 'bg-outline-secondary'} me-1">
                                    ${rule.auto_execute ? '✅ Auto-execute: ON' : '❌ Auto-execute: OFF'}
                                </span>
                                <span class="badge bg-info me-1">Priority: ${rule.priority}</span>
                            </div>
                            <div class="small text-muted mb-2">
                                Match ${conditionLogic} • ${conditionCount} condition${conditionCount !== 1 ? 's' : ''} • ${actionCount} action${actionCount !== 1 ? 's' : ''}
                            </div>
                            ${rule.description ? `<p class="text-muted mb-2">${rule.description}</p>` : ''}
                            <div class="small text-muted">
                                Executed ${rule.execution_count} times • ${rule.ports_affected} ports affected
                                ${rule.last_executed ? `<br>Last run: ${new Date(rule.last_executed).toLocaleString()}` : ''}
                            </div>
                        </div>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-success" onclick="tagManager.executeRule(${rule.id})" title="Execute Rule">
                                <i class="fas fa-play"></i>
                            </button>
                            <button class="btn btn-outline-primary" onclick="tagManager.editRule(${rule.id})" title="Edit Rule">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-outline-danger" onclick="tagManager.deleteRule(${rule.id})" title="Delete Rule">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    showRuleModal(rule = null) {
        const modal = new bootstrap.Modal(document.getElementById('ruleModal'));
        const title = document.getElementById('ruleModalTitle');
        const form = document.getElementById('rule-form');

        if (rule) {
            title.textContent = 'Edit Tagging Rule';
            document.getElementById('rule-id').value = rule.id;
            document.getElementById('rule-name').value = rule.name;
            document.getElementById('rule-description').value = rule.description || '';
            document.getElementById('rule-priority').value = rule.priority;
            document.getElementById('rule-enabled').checked = rule.enabled;
            document.getElementById('rule-auto-execute').checked = rule.auto_execute;
            this.loadRuleConditions(rule.conditions);
            this.loadRuleActions(rule.actions);
        } else {
            title.textContent = 'Create Tagging Rule';
            form.reset();
            document.getElementById('rule-id').value = '';
            document.getElementById('rule-priority').value = '0';
            document.getElementById('rule-enabled').checked = true;
            this.clearRuleConditions();
            this.clearRuleActions();
            this.addCondition(); // Add one default condition
            this.addAction(); // Add one default action
        }

        modal.show();
    }

    addCondition() {
        const container = document.getElementById('rule-conditions');
        const conditionId = Date.now();

        const conditionHtml = `
            <div class="condition-item mb-3" data-condition-id="${conditionId}">
                <div class="card">
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-md-3">
                                <label class="form-label small text-muted">IF</label>
                                <select class="form-select condition-type" onchange="tagManager.updateConditionInput(this)">
                                    <option value="">Select condition...</option>
                                    <optgroup label="Port Details">
                                        <option value="port_exact">Port number equals</option>
                                        <option value="port_range">Port number between</option>
                                        <option value="port_list">Port number in list</option>
                                        <option value="protocol">Protocol is</option>
                                    </optgroup>
                                    <optgroup label="Network">
                                        <option value="ip_exact">IP address equals</option>
                                        <option value="ip_contains">IP address contains</option>
                                        <option value="ip_regex">IP address matches pattern</option>
                                    </optgroup>
                                    <optgroup label="Description & Names">
                                        <option value="description_contains">Description contains</option>
                                        <option value="description_regex">Description matches pattern</option>
                                        <option value="nickname_contains">Nickname contains</option>
                                        <option value="nickname_regex">Nickname matches pattern</option>
                                    </optgroup>
                                    <optgroup label="Source">
                                        <option value="source">Source is</option>
                                    </optgroup>
                                </select>
                            </div>
                            <div class="col-md-8">
                                <label class="form-label small text-muted">VALUE</label>
                                <div class="condition-input-container">
                                    <input type="text" class="form-control condition-value" placeholder="Enter value..." disabled>
                                </div>
                            </div>
                            <div class="col-md-1">
                                <button type="button" class="btn btn-outline-danger btn-sm mt-4" onclick="this.closest('.condition-item').remove()" title="Remove condition">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', conditionHtml);
    }

    updateConditionInput(selectElement) {
        const conditionItem = selectElement.closest('.condition-item');
        const inputContainer = conditionItem.querySelector('.condition-input-container');
        const conditionType = selectElement.value;

        let inputHtml = '';

        switch (conditionType) {
            case 'port_exact':
                inputHtml = '<input type="number" class="form-control condition-value" placeholder="e.g., 8080" min="1" max="65535">';
                break;
            case 'port_range':
                inputHtml = `
                    <div class="row">
                        <div class="col-6">
                            <input type="number" class="form-control condition-value-start" placeholder="From" min="1" max="65535">
                        </div>
                        <div class="col-6">
                            <input type="number" class="form-control condition-value-end" placeholder="To" min="1" max="65535">
                        </div>
                    </div>
                `;
                break;
            case 'port_list':
                inputHtml = '<input type="text" class="form-control condition-value" placeholder="e.g., 80,443,8080">';
                break;
            case 'protocol':
                inputHtml = `
                    <select class="form-select condition-value">
                        <option value="TCP">TCP</option>
                        <option value="UDP">UDP</option>
                    </select>
                `;
                break;
            case 'ip_exact':
                inputHtml = '<input type="text" class="form-control condition-value" placeholder="e.g., 192.168.1.100">';
                break;
            case 'ip_contains':
                inputHtml = '<input type="text" class="form-control condition-value" placeholder="e.g., 192.168.1">';
                break;
            case 'ip_regex':
                inputHtml = '<input type="text" class="form-control condition-value" placeholder="e.g., ^192\\.168\\.">';
                break;
            case 'source':
                inputHtml = `
                    <select class="form-select condition-value">
                        <option value="manual">Manual</option>
                        <option value="docker">Docker</option>
                        <option value="portainer">Portainer</option>
                        <option value="komodo">Komodo</option>
                        <option value="import">Import</option>
                    </select>
                `;
                break;
            case 'description_contains':
            case 'nickname_contains':
                inputHtml = '<input type="text" class="form-control condition-value" placeholder="Enter text to search for">';
                break;
            case 'description_regex':
            case 'nickname_regex':
                inputHtml = '<input type="text" class="form-control condition-value" placeholder="Enter regex pattern">';
                break;
            default:
                inputHtml = '<input type="text" class="form-control condition-value" placeholder="Enter value..." disabled>';
        }

        inputContainer.innerHTML = inputHtml;
    }

    addAction() {
        const container = document.getElementById('rule-actions');
        const actionId = Date.now();

        // Get existing tags for dropdown
        const existingTagOptions = this.tags.map(tag =>
            `<option value="${tag.name}" data-color="${tag.color}">${tag.name}</option>`
        ).join('');

        const actionHtml = `
            <div class="action-item mb-3" data-action-id="${actionId}">
                <div class="card">
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-md-2">
                                <label class="form-label small text-muted">ACTION</label>
                                <select class="form-select action-type" onchange="tagManager.updateActionInput(this)">
                                    <option value="add_tag">Add Tag</option>
                                    <option value="remove_tag">Remove Tag</option>
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label small text-muted">TAG</label>
                                <div class="action-tag-container">
                                    <select class="form-select action-tag-select" onchange="tagManager.updateTagSelection(this)">
                                        <option value="">Select existing tag...</option>
                                        ${existingTagOptions}
                                        <option value="__new__">+ Create new tag</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label small text-muted">PREVIEW</label>
                                <div class="action-tag-preview">
                                    <span class="badge bg-secondary">Select a tag</span>
                                </div>
                            </div>
                            <div class="col-md-2">
                                <label class="form-label small text-muted">&nbsp;</label>
                                <div>
                                    <button type="button" class="btn btn-outline-danger btn-sm" onclick="this.closest('.action-item').remove()" title="Remove action">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-2 new-tag-inputs" style="display: none;">
                            <div class="col-md-6">
                                <input type="text" class="form-control action-tag-name" placeholder="New tag name">
                            </div>
                            <div class="col-md-3">
                                <input type="color" class="form-control form-control-color action-tag-color" value="#007bff">
                            </div>
                            <div class="col-md-3">
                                <input type="text" class="form-control action-tag-description" placeholder="Description (optional)">
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', actionHtml);
    }

    updateActionInput(selectElement) {
        const actionItem = selectElement.closest('.action-item');
        const preview = actionItem.querySelector('.action-tag-preview');
        const actionType = selectElement.value;

        if (actionType === 'remove_tag') {
            preview.innerHTML = '<span class="badge bg-danger">Will remove tag</span>';
        } else {
            preview.innerHTML = '<span class="badge bg-success">Will add tag</span>';
        }
    }

    updateTagSelection(selectElement) {
        const actionItem = selectElement.closest('.action-item');
        const newTagInputs = actionItem.querySelector('.new-tag-inputs');
        const preview = actionItem.querySelector('.action-tag-preview');
        const selectedValue = selectElement.value;

        if (selectedValue === '__new__') {
            newTagInputs.style.display = 'block';
            preview.innerHTML = '<span class="badge bg-info">New tag</span>';

            // Update preview when typing new tag name
            const nameInput = newTagInputs.querySelector('.action-tag-name');
            const colorInput = newTagInputs.querySelector('.action-tag-color');

            const updateNewTagPreview = () => {
                const name = nameInput.value.trim();
                const color = colorInput.value;
                if (name) {
                    preview.innerHTML = `<span class="badge" style="background-color: ${color}; color: white;">${name}</span>`;
                } else {
                    preview.innerHTML = '<span class="badge bg-info">New tag</span>';
                }
            };

            nameInput.addEventListener('input', updateNewTagPreview);
            colorInput.addEventListener('change', updateNewTagPreview);
        } else if (selectedValue === '') {
            newTagInputs.style.display = 'none';
            preview.innerHTML = '<span class="badge bg-secondary">Select a tag</span>';
        } else {
            newTagInputs.style.display = 'none';
            const selectedOption = selectElement.querySelector(`option[value="${selectedValue}"]`);
            const color = selectedOption.getAttribute('data-color') || '#007bff';
            preview.innerHTML = `<span class="badge" style="background-color: ${color}; color: white;">${selectedValue}</span>`;
        }
    }

    loadRuleConditions(conditions) {
        this.clearRuleConditions();

        // Handle the new condition structure with operator and conditions array
        if (conditions && typeof conditions === 'object') {
            // Set the operator if it exists
            const operatorSelect = document.getElementById('condition-operator');
            if (operatorSelect && conditions.operator) {
                operatorSelect.value = conditions.operator;
            }

            // Handle conditions array
            let conditionsArray = [];
            if (conditions.conditions && Array.isArray(conditions.conditions)) {
                conditionsArray = conditions.conditions;
            } else if (Array.isArray(conditions)) {
                // Legacy format - direct array
                conditionsArray = conditions;
            } else if (conditions.type) {
                // Single condition object
                conditionsArray = [conditions];
            }

            // Add each condition
            conditionsArray.forEach(condition => {
                this.addCondition();
                const conditionItems = document.querySelectorAll('#rule-conditions .condition-item');
                const lastItem = conditionItems[conditionItems.length - 1];

                // Set condition type
                const typeSelect = lastItem.querySelector('.condition-type');
                if (typeSelect && condition.type) {
                    typeSelect.value = condition.type;
                    // Trigger the change event to update the input fields
                    this.updateConditionInput(typeSelect);
                }

                // Set condition value(s)
                if (condition.type === 'port_range') {
                    const startInput = lastItem.querySelector('.condition-value-start');
                    const endInput = lastItem.querySelector('.condition-value-end');
                    if (startInput && condition.start) startInput.value = condition.start;
                    if (endInput && condition.end) endInput.value = condition.end;
                } else {
                    const valueInput = lastItem.querySelector('.condition-value');
                    if (valueInput && condition.value !== undefined) {
                        valueInput.value = condition.value;
                    }
                }
            });
        }

        // If no conditions were loaded, add one empty condition
        if (document.querySelectorAll('#rule-conditions .condition-item').length === 0) {
            this.addCondition();
        }
    }

    loadRuleActions(actions) {
        this.clearRuleActions();

        actions.forEach(action => {
            this.addAction();
            const actionItems = document.querySelectorAll('#rule-actions .action-item');
            const lastItem = actionItems[actionItems.length - 1];

            // Set action type
            const actionTypeSelect = lastItem.querySelector('.action-type');
            if (actionTypeSelect && action.type) {
                actionTypeSelect.value = action.type;
                // Trigger change event to update UI
                this.updateActionInput(actionTypeSelect);
            }

            // Set tag selection
            const tagSelect = lastItem.querySelector('.action-tag-select');
            if (tagSelect && action.tag_name) {
                // Check if this tag exists in the dropdown
                const existingOption = tagSelect.querySelector(`option[value="${action.tag_name}"]`);
                if (existingOption) {
                    // Use existing tag
                    tagSelect.value = action.tag_name;
                    this.updateTagSelection(tagSelect);
                } else {
                    // This is a new tag that will be created
                    tagSelect.value = '__new__';
                    this.updateTagSelection(tagSelect);

                    // Fill in the new tag details
                    const nameInput = lastItem.querySelector('.action-tag-name');
                    const colorInput = lastItem.querySelector('.action-tag-color');
                    const descInput = lastItem.querySelector('.action-tag-description');

                    if (nameInput) nameInput.value = action.tag_name;
                    if (colorInput && action.tag_color) colorInput.value = action.tag_color;
                    if (descInput && action.tag_description) descInput.value = action.tag_description;

                    // Update preview
                    const preview = lastItem.querySelector('.action-tag-preview');
                    if (preview && action.tag_name) {
                        const color = action.tag_color || '#007bff';
                        preview.innerHTML = `<span class="badge" style="background-color: ${color}; color: white;">${action.tag_name}</span>`;
                    }
                }
            }
        });

        // If no actions were loaded, add one empty action
        if (document.querySelectorAll('#rule-actions .action-item').length === 0) {
            this.addAction();
        }
    }

    clearRuleConditions() {
        document.getElementById('rule-conditions').innerHTML = '';
    }

    clearRuleActions() {
        document.getElementById('rule-actions').innerHTML = '';
    }

    async saveRule() {
        const ruleId = document.getElementById('rule-id').value;
        const name = document.getElementById('rule-name').value.trim();
        const description = document.getElementById('rule-description').value.trim();
        const priority = parseInt(document.getElementById('rule-priority').value);
        const enabled = document.getElementById('rule-enabled').checked;
        const autoExecute = document.getElementById('rule-auto-execute').checked;

        if (!name) {
            this.showNotification('Rule name is required', 'error');
            return;
        }

        // Collect conditions with operator logic
        const conditionOperator = document.getElementById('condition-operator').value || 'AND';
        const conditionList = [];

        document.querySelectorAll('#rule-conditions .condition-item').forEach(item => {
            const type = item.querySelector('.condition-type').value;

            if (!type) return; // Skip empty conditions

            let conditionData = { type };

            // Handle different condition types
            if (type === 'port_range') {
                const startValue = item.querySelector('.condition-value-start')?.value;
                const endValue = item.querySelector('.condition-value-end')?.value;
                if (startValue && endValue) {
                    conditionData.start = parseInt(startValue);
                    conditionData.end = parseInt(endValue);
                }
            } else {
                const value = item.querySelector('.condition-value')?.value?.trim();
                if (value) {
                    conditionData.value = value;
                }
            }

            // Only add condition if it has required data
            if (conditionData.value || (conditionData.start && conditionData.end)) {
                conditionList.push(conditionData);
            }
        });

        if (conditionList.length === 0) {
            this.showNotification('At least one valid condition is required', 'error');
            return;
        }

        // Structure conditions with operator
        const conditions = {
            operator: conditionOperator,
            conditions: conditionList
        };

        // Collect actions
        const actions = [];
        document.querySelectorAll('#rule-actions .action-item').forEach(item => {
            const type = item.querySelector('.action-type').value;
            const tagSelect = item.querySelector('.action-tag-select');
            const selectedTag = tagSelect?.value;

            if (!selectedTag) return; // Skip empty actions

            let actionData = { type };

            if (selectedTag === '__new__') {
                // New tag creation
                const tagName = item.querySelector('.action-tag-name')?.value?.trim();
                const tagColor = item.querySelector('.action-tag-color')?.value || '#007bff';
                const tagDescription = item.querySelector('.action-tag-description')?.value?.trim();

                if (tagName) {
                    actionData.tag_name = tagName;
                    actionData.tag_color = tagColor;
                    if (tagDescription) {
                        actionData.tag_description = tagDescription;
                    }
                }
            } else {
                // Existing tag
                actionData.tag_name = selectedTag;
                // Get color from the selected option
                const selectedOption = tagSelect.querySelector(`option[value="${selectedTag}"]`);
                if (selectedOption) {
                    actionData.tag_color = selectedOption.getAttribute('data-color') || '#007bff';
                }
            }

            if (actionData.tag_name) {
                actions.push(actionData);
            }
        });

        if (actions.length === 0) {
            this.showNotification('At least one valid action is required', 'error');
            return;
        }

        const data = { name, description, priority, enabled, auto_execute: autoExecute, conditions, actions };
        const url = ruleId ? `/api/tagging-rules/${ruleId}` : '/api/tagging-rules';
        const method = ruleId ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                bootstrap.Modal.getInstance(document.getElementById('ruleModal')).hide();
                this.loadRules();
                // Reload tags in case new ones were created
                this.loadTags();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error saving rule: ' + error.message, 'error');
        }
    }

    editRule(ruleId) {
        const rule = this.rules.find(r => r.id === ruleId);
        if (rule) {
            this.showRuleModal(rule);
        }
    }

    async deleteRule(ruleId) {
        const rule = this.rules.find(r => r.id === ruleId);
        if (!rule) return;

        if (!confirm(`Are you sure you want to delete the rule "${rule.name}"?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/tagging-rules/${ruleId}`, { method: 'DELETE' });
            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                this.loadRules();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error deleting rule: ' + error.message, 'error');
        }
    }

    async executeRule(ruleId) {
        try {
            const response = await fetch(`/api/tagging-rules/${ruleId}/execute`, { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.showNotification(`Rule executed: ${result.stats.successful_actions} actions completed`, 'success');
                this.loadRules();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error executing rule: ' + error.message, 'error');
        }
    }

    async executeAllRules() {
        if (!confirm('Are you sure you want to execute all enabled tagging rules? This may affect many ports.')) {
            return;
        }

        try {
            const response = await fetch('/api/tagging-rules/execute-all', { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.showNotification(`All rules executed: ${result.stats.actions_executed} actions completed on ${result.stats.ports_processed} ports`, 'success');
                this.loadRules();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error executing rules: ' + error.message, 'error');
        }
    }

    // Filter functionality
    async loadFilterTags() {
        const select = document.getElementById('filter-tags');
        select.innerHTML = this.tags.map(tag =>
            `<option value="${tag.id}">${tag.name}</option>`
        ).join('');
    }

    async filterPorts() {
        const tagIds = Array.from(document.getElementById('filter-tags').selectedOptions).map(opt => parseInt(opt.value));
        const tagOperator = document.getElementById('filter-tag-operator').value;
        const ipFilter = document.getElementById('filter-ip').value.trim();
        const portFilter = document.getElementById('filter-port').value.trim();
        const descriptionFilter = document.getElementById('filter-description').value.trim();

        const data = {
            tag_ids: tagIds,
            tag_operator: tagOperator,
            ip_filter: ipFilter,
            port_filter: portFilter,
            description_filter: descriptionFilter
        };

        try {
            const response = await fetch('/api/ports/filter', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.displayFilterResults(result.ports);
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error filtering ports: ' + error.message, 'error');
        }
    }

    displayFilterResults(ports) {
        const container = document.getElementById('filtered-ports');
        const resultsDiv = document.getElementById('filter-results');

        if (ports.length === 0) {
            container.innerHTML = '<p class="text-muted">No ports match the filter criteria.</p>';
        } else {
            container.innerHTML = ports.map(port => `
                <div class="port-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong>${port.ip_address}:${port.port_number}</strong>
                            <span class="badge bg-secondary ms-2">${port.port_protocol}</span>
                            ${port.nickname ? `<span class="text-muted ms-2">(${port.nickname})</span>` : ''}
                            <div class="text-muted">${port.description}</div>
                            <div class="port-tags">
                                ${port.tags.map(tag =>
                `<span class="tag-badge" style="background-color: ${tag.color}">${tag.name}</span>`
            ).join('')}
                            </div>
                        </div>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary" onclick="tagManager.showPortTagModal(${port.id})">
                                <i class="fas fa-tags"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        resultsDiv.style.display = 'block';
    }

    clearFilter() {
        document.getElementById('filter-form').reset();
        document.getElementById('filter-results').style.display = 'none';
    }

    // Template Management
    async loadTemplates() {
        try {
            const response = await fetch('/api/tag-templates');
            const data = await response.json();

            if (data.success) {
                this.templates = data.templates;
                this.templateCategories = data.categories;
                this.renderTemplates();
                this.updateTemplateStats();
                this.loadTemplateCategoryFilter();
            } else {
                this.showNotification('Error loading templates: ' + data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error loading templates: ' + error.message, 'error');
        }
    }

    loadTemplateCategoryFilter() {
        const select = document.getElementById('template-category-filter');
        select.innerHTML = '<option value="">All Categories</option>' +
            this.templateCategories.map(category =>
                `<option value="${category}">${category}</option>`
            ).join('');
    }

    filterTemplates(category) {
        this.renderTemplates(category);
    }

    renderTemplates(categoryFilter = null) {
        const container = document.getElementById('templates-list');

        if (!this.templates) {
            container.innerHTML = '<p class="text-muted">Loading templates...</p>';
            return;
        }

        let templatesToRender = Object.entries(this.templates);

        if (categoryFilter) {
            templatesToRender = templatesToRender.filter(([id, template]) =>
                template.category === categoryFilter
            );
        }

        if (templatesToRender.length === 0) {
            container.innerHTML = '<p class="text-muted">No templates found.</p>';
            return;
        }

        container.innerHTML = templatesToRender.map(([templateId, template]) => `
            <div class="template-item mb-3" data-template-id="${templateId}">
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <div class="d-flex align-items-center mb-2">
                                    <h6 class="mb-0 me-2">${template.name}</h6>
                                    <span class="badge bg-info">${template.category}</span>
                                    <span class="badge bg-secondary ms-1">${template.rules.length} rules</span>
                                </div>
                                <p class="text-muted mb-2">${template.description}</p>
                                <div class="small text-muted">
                                    Rules: ${template.rules.map(rule => rule.name).join(', ')}
                                </div>
                            </div>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-success" onclick="tagManager.applyTemplate('${templateId}')" title="Apply Template">
                                    <i class="fas fa-play"></i> Apply
                                </button>
                                <button class="btn btn-outline-primary" onclick="tagManager.previewTemplate('${templateId}')" title="Preview Template">
                                    <i class="fas fa-eye"></i>
                                </button>
                                <button class="btn btn-outline-secondary" onclick="tagManager.exportTemplate('${templateId}')" title="Export Template">
                                    <i class="fas fa-download"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    updateTemplateStats() {
        if (!this.templates) return;

        const totalTemplates = Object.keys(this.templates).length;
        const totalRules = Object.values(this.templates).reduce((sum, template) => sum + template.rules.length, 0);
        const categoryCounts = {};

        Object.values(this.templates).forEach(template => {
            categoryCounts[template.category] = (categoryCounts[template.category] || 0) + 1;
        });

        const mostPopularCategory = Object.entries(categoryCounts).reduce((max, [category, count]) =>
            count > max.count ? { category, count } : max, { category: '', count: 0 });

        document.getElementById('template-stats').innerHTML = `
            <div class="mb-3">
                <h6>Available Templates</h6>
                <div class="h4 text-primary">${totalTemplates}</div>
            </div>
            <div class="mb-3">
                <h6>Total Rules</h6>
                <div class="h4 text-success">${totalRules}</div>
            </div>
            ${mostPopularCategory.category ? `
                <div class="mb-3">
                    <h6>Most Popular Category</h6>
                    <span class="badge bg-info">${mostPopularCategory.category}</span>
                    <div class="text-muted small">${mostPopularCategory.count} templates</div>
                </div>
            ` : ''}
            <div class="mb-3">
                <h6>Categories</h6>
                ${Object.entries(categoryCounts).map(([category, count]) =>
            `<div class="small"><span class="badge bg-outline-secondary me-1">${category}</span> ${count}</div>`
        ).join('')}
            </div>
        `;
    }

    async applyQuickTemplate(templateId) {
        if (!confirm(`Apply the ${templateId.replace('_', ' ')} template? This will create multiple tagging rules.`)) {
            return;
        }

        await this.applyTemplate(templateId);
    }

    async applyTemplate(templateId, customizeOptions = {}) {
        try {
            const response = await fetch(`/api/tag-templates/${templateId}/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ customize_options: customizeOptions })
            });

            const result = await response.json();

            if (result.success) {
                const message = `Template applied successfully! Created ${result.stats.created} rules.`;
                if (result.errors.length > 0) {
                    this.showNotification(message + ` ${result.errors.length} errors occurred.`, 'warning');
                } else {
                    this.showNotification(message, 'success');
                }
                this.loadRules(); // Refresh rules list
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error applying template: ' + error.message, 'error');
        }
    }

    async previewTemplate(templateId) {
        try {
            const response = await fetch(`/api/tag-templates/${templateId}`);
            const data = await response.json();

            if (data.success) {
                this.showTemplatePreviewModal(data.template);
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error loading template: ' + error.message, 'error');
        }
    }

    showTemplatePreviewModal(template) {
        // Create a modal dynamically for template preview
        const modalHtml = `
            <div class="modal fade" id="templatePreviewModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Template Preview: ${template.name}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <strong>Category:</strong> <span class="badge bg-info">${template.category}</span>
                            </div>
                            <div class="mb-3">
                                <strong>Description:</strong> ${template.description}
                            </div>
                            <div class="mb-3">
                                <strong>Rules (${template.rules.length}):</strong>
                            </div>
                            ${template.rules.map(rule => `
                                <div class="card mb-2">
                                    <div class="card-body">
                                        <h6>${rule.name}</h6>
                                        <p class="text-muted small">${rule.description}</p>
                                        <div class="small">
                                            <strong>Priority:</strong> ${rule.priority} |
                                            <strong>Auto-execute:</strong> ${rule.auto_execute ? 'Yes' : 'No'}
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-success" onclick="tagManager.applyTemplate('${template.name.toLowerCase().replace(/\s+/g, '_')}')">
                                Apply Template
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if present
        const existingModal = document.getElementById('templatePreviewModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to DOM and show
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('templatePreviewModal'));
        modal.show();

        // Clean up modal when hidden
        document.getElementById('templatePreviewModal').addEventListener('hidden.bs.modal', function () {
            this.remove();
        });
    }

    async exportTemplate(templateId) {
        try {
            const response = await fetch(`/api/tag-templates/${templateId}/export`);
            const data = await response.json();

            if (data.success) {
                this.downloadFile(`template_${templateId}.json`, data.template_data);
                this.showNotification('Template exported successfully', 'success');
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error exporting template: ' + error.message, 'error');
        }
    }

    async exportConfiguration() {
        try {
            const response = await fetch('/api/tagging-config/export');
            const data = await response.json();

            if (data.success) {
                const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
                this.downloadFile(`portall_tagging_config_${timestamp}.json`, data.config);
                this.showNotification('Configuration exported successfully', 'success');
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error exporting configuration: ' + error.message, 'error');
        }
    }

    async backupConfiguration() {
        if (!confirm('Create a backup of your current tagging configuration?')) {
            return;
        }
        await this.exportConfiguration();
    }

    showImportTemplateModal() {
        const modalHtml = `
            <div class="modal fade" id="importTemplateModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Import Template</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label">Template JSON Data</label>
                                <textarea id="import-template-data" class="form-control" rows="10"
                                    placeholder="Paste template JSON data here..."></textarea>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="tagManager.importTemplate()">
                                Import Template
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if present
        const existingModal = document.getElementById('importTemplateModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to DOM and show
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('importTemplateModal'));
        modal.show();

        // Clean up modal when hidden
        document.getElementById('importTemplateModal').addEventListener('hidden.bs.modal', function () {
            this.remove();
        });
    }

    async importTemplate() {
        const templateData = document.getElementById('import-template-data').value.trim();

        if (!templateData) {
            this.showNotification('Please provide template data', 'error');
            return;
        }

        try {
            const response = await fetch('/api/tag-templates/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ template_data: templateData })
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Template imported successfully', 'success');
                bootstrap.Modal.getInstance(document.getElementById('importTemplateModal')).hide();
                this.loadTemplates(); // Refresh templates
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error importing template: ' + error.message, 'error');
        }
    }

    showImportConfigModal() {
        const modalHtml = `
            <div class="modal fade" id="importConfigModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Import Configuration</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-warning">
                                <i class="fas fa-exclamation-triangle"></i>
                                <strong>Warning:</strong> Importing configuration will add new tags and rules.
                                Enable "Overwrite existing" to replace items with the same name.
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Configuration JSON Data</label>
                                <textarea id="import-config-data" class="form-control" rows="10"
                                    placeholder="Paste configuration JSON data here..."></textarea>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="import-overwrite">
                                <label class="form-check-label" for="import-overwrite">
                                    Overwrite existing tags and rules with same names
                                </label>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-warning" onclick="tagManager.importConfiguration()">
                                Import Configuration
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if present
        const existingModal = document.getElementById('importConfigModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to DOM and show
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('importConfigModal'));
        modal.show();

        // Clean up modal when hidden
        document.getElementById('importConfigModal').addEventListener('hidden.bs.modal', function () {
            this.remove();
        });
    }

    async importConfiguration() {
        const configData = document.getElementById('import-config-data').value.trim();
        const overwrite = document.getElementById('import-overwrite').checked;

        if (!configData) {
            this.showNotification('Please provide configuration data', 'error');
            return;
        }

        if (!confirm('Are you sure you want to import this configuration? This will modify your current setup.')) {
            return;
        }

        try {
            const response = await fetch('/api/tagging-config/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    config_data: configData,
                    overwrite: overwrite
                })
            });

            const result = await response.json();

            if (result.success) {
                const stats = result.stats;
                const message = `Configuration imported! Created: ${stats.tags_created} tags, ${stats.rules_created} rules. Skipped: ${stats.tags_skipped} tags, ${stats.rules_skipped} rules.`;
                this.showNotification(message, 'success');
                bootstrap.Modal.getInstance(document.getElementById('importConfigModal')).hide();

                // Refresh all data
                this.loadTags();
                this.loadRules();
                this.loadTemplates();
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error importing configuration: ' + error.message, 'error');
        }
    }

    downloadFile(filename, content) {
        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Utility functions
    showNotification(message, type = 'info') {
        const container = document.getElementById('notification-area');
        const alertClass = type === 'error' ? 'alert-danger' : type === 'success' ? 'alert-success' : 'alert-info';

        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        container.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize the tag manager when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.tagManager = new TagManager();
});

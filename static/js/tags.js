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

        container.innerHTML = this.rules.map(rule => `
            <div class="rule-item ${!rule.enabled ? 'disabled' : ''}" data-rule-id="${rule.id}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center mb-2">
                            <h6 class="mb-0">${rule.name}</h6>
                            <span class="badge ${rule.enabled ? 'bg-success' : 'bg-secondary'} ms-2">
                                ${rule.enabled ? 'Enabled' : 'Disabled'}
                            </span>
                            <span class="badge bg-info ms-1">Priority: ${rule.priority}</span>
                        </div>
                        ${rule.description ? `<p class="text-muted mb-2">${rule.description}</p>` : ''}
                        <div class="small text-muted">
                            Executed ${rule.execution_count} times, affected ${rule.ports_affected} ports
                            ${rule.last_executed ? `<br>Last executed: ${new Date(rule.last_executed).toLocaleString()}` : ''}
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
        `).join('');
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

        if (Array.isArray(conditions)) {
            conditions.forEach(condition => {
                this.addCondition();
                const conditionItems = document.querySelectorAll('#rule-conditions .condition-item');
                const lastItem = conditionItems[conditionItems.length - 1];
                lastItem.querySelector('.condition-type').value = condition.type;
                lastItem.querySelector('.condition-value').value = condition.value || condition.start || '';
            });
        } else if (conditions.type) {
            this.addCondition();
            const conditionItem = document.querySelector('#rule-conditions .condition-item');
            conditionItem.querySelector('.condition-type').value = conditions.type;
            conditionItem.querySelector('.condition-value').value = conditions.value || conditions.start || '';
        }
    }

    loadRuleActions(actions) {
        this.clearRuleActions();

        actions.forEach(action => {
            this.addAction();
            const actionItems = document.querySelectorAll('#rule-actions .action-item');
            const lastItem = actionItems[actionItems.length - 1];
            lastItem.querySelector('.action-type').value = action.type;
            lastItem.querySelector('.action-tag-name').value = action.tag_name;
            if (action.tag_color) {
                lastItem.querySelector('.action-tag-color').value = action.tag_color;
            }
        });
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

        if (!name) {
            this.showNotification('Rule name is required', 'error');
            return;
        }

        // Collect conditions
        const conditions = [];
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
                conditions.push(conditionData);
            }
        });

        if (conditions.length === 0) {
            this.showNotification('At least one valid condition is required', 'error');
            return;
        }

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

        const data = { name, description, priority, enabled, conditions, actions };
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

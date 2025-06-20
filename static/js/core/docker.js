// static/js/core/docker.js

/**
 * Manages Docker integration functionality for the application.
 * This module handles Docker settings, port scanning, and integration with
 * Portainer and Komodo using the new multi-instance system.
 */

import { showNotification } from '../ui/helpers.js';

/**
 * Initialize Docker integration functionality.
 * Sets up event handlers for Docker-related forms and buttons.
 */
export function init() {
    // Load Docker instances
    loadDockerInstances();

    // Set up button click handlers
    $('#add-docker-instance').click(handleAddInstanceClick);
    $('#refresh-instances').click(loadDockerInstances);

    // Set up delegated event handlers for dynamic content
    $(document).on('click', '.edit-instance-btn', handleEditInstanceClick);
    $(document).on('click', '.delete-instance-btn', handleDeleteInstanceClick);
    $(document).on('click', '.scan-instance-btn', handleScanInstanceClick);
    $(document).on('click', '.test-instance-btn', handleTestInstanceClick);
    $(document).on('submit', '#instance-form', handleInstanceFormSubmit);
    $(document).on('change', '.instance-enabled', handleInstanceEnabledChange);
}

/**
 * Load Docker instances from the server.
 * Populates the instances list with data from the server.
 */
function loadDockerInstances() {
    $.ajax({
        url: '/docker/instances',
        method: 'GET',
        success: function (data) {
            if (data.success) {
                renderInstancesList(data.instances);
            } else {
                showNotification('Error loading Docker instances: ' + data.error, 'error');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error loading Docker instances:', status, error);
            showNotification('Error loading Docker instances.', 'error');
        }
    });
}

/**
 * Render the instances list in the UI.
 *
 * @param {Array} instances - Array of instance objects
 */
function renderInstancesList(instances) {
    const $container = $('#docker-instances-list');
    $container.empty();

    if (instances.length === 0) {
        $container.html(`
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i>
                No Docker instances configured. Click "Add Instance" to get started.
            </div>
        `);
        return;
    }

    instances.forEach(instance => {
        const instanceCard = createInstanceCard(instance);
        $container.append(instanceCard);
    });
}

/**
 * Create an instance card element.
 *
 * @param {Object} instance - Instance object
 * @returns {jQuery} Instance card element
 */
function createInstanceCard(instance) {
    const typeIcon = {
        'docker': 'fab fa-docker',
        'portainer': 'fas fa-ship',
        'komodo': 'fas fa-dragon'
    }[instance.type] || 'fas fa-server';

    const statusBadge = instance.enabled
        ? '<span class="badge badge-success">Enabled</span>'
        : '<span class="badge badge-secondary">Disabled</span>';

    return $(`
        <div class="card mb-3" data-instance-id="${instance.id}">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <i class="${typeIcon}"></i>
                    <strong>${instance.name}</strong>
                    <span class="badge badge-primary ml-2">${instance.type.toUpperCase()}</span>
                    ${statusBadge}
                </div>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary test-instance-btn" data-instance-id="${instance.id}">
                        <i class="fas fa-check-circle"></i> Test
                    </button>
                    <button class="btn btn-outline-success scan-instance-btn" data-instance-id="${instance.id}" ${!instance.enabled ? 'disabled' : ''}>
                        <i class="fas fa-search"></i> Scan
                    </button>
                    <button class="btn btn-outline-secondary edit-instance-btn" data-instance-id="${instance.id}">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn btn-outline-danger delete-instance-btn" data-instance-id="${instance.id}">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <small class="text-muted">Configuration:</small>
                        <div class="mt-1">
                            ${renderInstanceConfig(instance)}
                        </div>
                    </div>
                    <div class="col-md-6">
                        <small class="text-muted">Settings:</small>
                        <div class="mt-1">
                            <div class="form-check form-check-inline">
                                <input class="form-check-input instance-enabled" type="checkbox"
                                       data-instance-id="${instance.id}" ${instance.enabled ? 'checked' : ''}>
                                <label class="form-check-label">Enabled</label>
                            </div>
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="checkbox"
                                       ${instance.auto_detect ? 'checked' : ''} disabled>
                                <label class="form-check-label">Auto-detect</label>
                            </div>
                        </div>
                        <small class="text-muted d-block mt-2">
                            Scan interval: ${instance.scan_interval}s |
                            Services: ${instance.service_count || 0}
                        </small>
                    </div>
                </div>
            </div>
        </div>
    `);
}

/**
 * Render instance configuration details.
 *
 * @param {Object} instance - Instance object
 * @returns {string} HTML string for configuration
 */
function renderInstanceConfig(instance) {
    const config = instance.config || {};

    switch (instance.type) {
        case 'docker':
            return `<code>${config.host || 'unix:///var/run/docker.sock'}</code>`;
        case 'portainer':
            return `<code>${config.url || 'Not configured'}</code>`;
        case 'komodo':
            return `<code>${config.url || 'Not configured'}</code>`;
        default:
            return '<code>Unknown configuration</code>';
    }
}

/**
 * Handle add instance button click.
 */
function handleAddInstanceClick() {
    showInstanceModal();
}

/**
 * Handle edit instance button click.
 *
 * @param {Event} e - Click event
 */
function handleEditInstanceClick(e) {
    const instanceId = $(e.currentTarget).data('instance-id');

    $.ajax({
        url: `/docker/instances/${instanceId}`,
        method: 'GET',
        success: function (data) {
            if (data.success) {
                showInstanceModal(data.instance);
            } else {
                showNotification('Error loading instance: ' + data.error, 'error');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error loading instance:', status, error);
            showNotification('Error loading instance.', 'error');
        }
    });
}

/**
 * Handle delete instance button click.
 *
 * @param {Event} e - Click event
 */
function handleDeleteInstanceClick(e) {
    const instanceId = $(e.currentTarget).data('instance-id');
    const instanceName = $(e.currentTarget).closest('.card').find('strong').text();

    if (confirm(`Are you sure you want to delete the instance "${instanceName}"? This will also delete all associated services and ports.`)) {
        $.ajax({
            url: `/docker/instances/${instanceId}`,
            method: 'DELETE',
            success: function (data) {
                if (data.success) {
                    showNotification('Instance deleted successfully!');
                    loadDockerInstances();
                } else {
                    showNotification('Error deleting instance: ' + data.error, 'error');
                }
            },
            error: function (xhr, status, error) {
                console.error('Error deleting instance:', status, error);
                showNotification('Error deleting instance.', 'error');
            }
        });
    }
}

/**
 * Handle scan instance button click.
 *
 * @param {Event} e - Click event
 */
function handleScanInstanceClick(e) {
    const instanceId = $(e.currentTarget).data('instance-id');
    const $button = $(e.currentTarget);

    $button.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Scanning...');

    $.ajax({
        url: `/docker/instances/${instanceId}/scan`,
        method: 'POST',
        success: function (response) {
            if (response.success) {
                showNotification(response.message);
                loadDockerInstances(); // Refresh to show updated service count
            } else {
                showNotification('Error scanning instance: ' + response.error, 'error');
            }
            $button.prop('disabled', false).html('<i class="fas fa-search"></i> Scan');
        },
        error: function (xhr, status, error) {
            console.error('Error scanning instance:', status, error);
            showNotification('Error scanning instance.', 'error');
            $button.prop('disabled', false).html('<i class="fas fa-search"></i> Scan');
        }
    });
}

/**
 * Handle test instance button click.
 *
 * @param {Event} e - Click event
 */
function handleTestInstanceClick(e) {
    const instanceId = $(e.currentTarget).data('instance-id');
    const $button = $(e.currentTarget);

    $button.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Testing...');

    $.ajax({
        url: `/docker/instances/${instanceId}/test`,
        method: 'POST',
        success: function (response) {
            if (response.success) {
                showNotification('Connection test successful!', 'success');
            } else {
                showNotification('Connection test failed: ' + response.error, 'error');
            }
            $button.prop('disabled', false).html('<i class="fas fa-check-circle"></i> Test');
        },
        error: function (xhr, status, error) {
            console.error('Error testing instance:', status, error);
            showNotification('Error testing instance.', 'error');
            $button.prop('disabled', false).html('<i class="fas fa-check-circle"></i> Test');
        }
    });
}

/**
 * Handle instance enabled checkbox change.
 *
 * @param {Event} e - Change event
 */
function handleInstanceEnabledChange(e) {
    const instanceId = $(e.currentTarget).data('instance-id');
    const enabled = $(e.currentTarget).is(':checked');

    $.ajax({
        url: `/docker/instances/${instanceId}`,
        method: 'PUT',
        contentType: 'application/json',
        data: JSON.stringify({ enabled: enabled }),
        success: function (response) {
            if (response.success) {
                showNotification(`Instance ${enabled ? 'enabled' : 'disabled'} successfully!`);
                loadDockerInstances(); // Refresh to update UI
            } else {
                showNotification('Error updating instance: ' + response.error, 'error');
                // Revert checkbox state
                $(e.currentTarget).prop('checked', !enabled);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error updating instance:', status, error);
            showNotification('Error updating instance.', 'error');
            // Revert checkbox state
            $(e.currentTarget).prop('checked', !enabled);
        }
    });
}

/**
 * Show the instance modal for adding or editing.
 *
 * @param {Object} instance - Instance object for editing (optional)
 */
function showInstanceModal(instance = null) {
    const isEdit = instance !== null;
    const modalTitle = isEdit ? 'Edit Instance' : 'Add New Instance';

    const modalHtml = `
        <div class="modal fade" id="instanceModal" tabindex="-1" role="dialog">
            <div class="modal-dialog modal-lg" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${modalTitle}</h5>
                        <button type="button" class="close" data-dismiss="modal">
                            <span>&times;</span>
                        </button>
                    </div>
                    <form id="instance-form">
                        <div class="modal-body">
                            ${renderInstanceForm(instance)}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
                            <button type="submit" class="btn btn-primary">${isEdit ? 'Update' : 'Create'} Instance</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal and add new one
    $('#instanceModal').remove();
    $('body').append(modalHtml);

    // Show modal
    $('#instanceModal').modal('show');

    // Set up type change handler
    $('#instance-type').change(updateInstanceFormFields);
    updateInstanceFormFields();
}

/**
 * Render the instance form.
 *
 * @param {Object} instance - Instance object for editing (optional)
 * @returns {string} HTML string for the form
 */
function renderInstanceForm(instance = null) {
    const config = instance?.config || {};

    return `
        ${instance ? `<input type="hidden" name="instance_id" value="${instance.id}">` : ''}

        <div class="form-group">
            <label for="instance-name">Instance Name</label>
            <input type="text" class="form-control" id="instance-name" name="name"
                   value="${instance?.name || ''}" required>
        </div>

        <div class="form-group">
            <label for="instance-type">Type</label>
            <select class="form-control" id="instance-type" name="type" required ${instance ? 'disabled' : ''}>
                <option value="">Select type...</option>
                <option value="docker" ${instance?.type === 'docker' ? 'selected' : ''}>Docker</option>
                <option value="portainer" ${instance?.type === 'portainer' ? 'selected' : ''}>Portainer</option>
                <option value="komodo" ${instance?.type === 'komodo' ? 'selected' : ''}>Komodo</option>
            </select>
        </div>

        <div id="config-fields">
            <!-- Configuration fields will be populated based on type -->
        </div>

        <div class="form-row">
            <div class="form-group col-md-6">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="instance-enabled" name="enabled"
                           ${instance?.enabled !== false ? 'checked' : ''}>
                    <label class="form-check-label" for="instance-enabled">Enabled</label>
                </div>
            </div>
            <div class="form-group col-md-6">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="instance-auto-detect" name="auto_detect"
                           ${instance?.auto_detect !== false ? 'checked' : ''}>
                    <label class="form-check-label" for="instance-auto-detect">Auto-detect services</label>
                </div>
            </div>
        </div>

        <div class="form-group">
            <label for="instance-scan-interval">Scan Interval (seconds)</label>
            <input type="number" class="form-control" id="instance-scan-interval" name="scan_interval"
                   value="${instance?.scan_interval || 300}" min="60" max="3600">
        </div>
    `;
}

/**
 * Update instance form fields based on selected type.
 */
function updateInstanceFormFields() {
    const type = $('#instance-type').val();
    const $configFields = $('#config-fields');

    let configHtml = '';

    switch (type) {
        case 'docker':
            configHtml = `
                <div class="form-group">
                    <label for="docker-host">Docker Host</label>
                    <input type="text" class="form-control" id="docker-host" name="host"
                           value="unix:///var/run/docker.sock" placeholder="unix:///var/run/docker.sock">
                    <small class="form-text text-muted">
                        Docker socket path or TCP connection string (e.g., tcp://localhost:2376)
                    </small>
                </div>
                <div class="form-group">
                    <label for="docker-timeout">Timeout (seconds)</label>
                    <input type="number" class="form-control" id="docker-timeout" name="timeout"
                           value="30" min="5" max="300">
                </div>
            `;
            break;

        case 'portainer':
            configHtml = `
                <div class="form-group">
                    <label for="portainer-url">Portainer URL</label>
                    <input type="url" class="form-control" id="portainer-url" name="url"
                           placeholder="https://portainer.example.com" required>
                </div>
                <div class="form-group">
                    <label for="portainer-api-key">API Key</label>
                    <input type="text" class="form-control" id="portainer-api-key" name="api_key"
                           placeholder="ptr_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" required>
                </div>
                <div class="form-group">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="portainer-verify-ssl"
                               name="verify_ssl" checked>
                        <label class="form-check-label" for="portainer-verify-ssl">Verify SSL Certificate</label>
                    </div>
                </div>
            `;
            break;

        case 'komodo':
            configHtml = `
                <div class="form-group">
                    <label for="komodo-url">Komodo URL</label>
                    <input type="url" class="form-control" id="komodo-url" name="url"
                           placeholder="https://komodo.example.com" required>
                </div>
                <div class="form-group">
                    <label for="komodo-api-key">API Key</label>
                    <input type="text" class="form-control" id="komodo-api-key" name="api_key"
                           placeholder="Your Komodo API key" required>
                </div>
                <div class="form-group">
                    <label for="komodo-api-secret">API Secret</label>
                    <input type="password" class="form-control" id="komodo-api-secret" name="api_secret"
                           placeholder="Your Komodo API secret" required>
                </div>
            `;
            break;
    }

    $configFields.html(configHtml);
}

/**
 * Handle instance form submission.
 *
 * @param {Event} e - Form submission event
 */
function handleInstanceFormSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const instanceId = formData.get('instance_id');
    const isEdit = instanceId !== null && instanceId !== '';

    // Build the request data
    const data = {
        name: formData.get('name'),
        type: formData.get('type'),
        enabled: formData.has('enabled'),
        auto_detect: formData.has('auto_detect'),
        scan_interval: parseInt(formData.get('scan_interval')),
        config: {}
    };

    // Build config object based on type
    switch (data.type) {
        case 'docker':
            data.config.host = formData.get('host') || 'unix:///var/run/docker.sock';
            data.config.timeout = parseInt(formData.get('timeout')) || 30;
            break;
        case 'portainer':
            data.config.url = formData.get('url');
            data.config.api_key = formData.get('api_key');
            data.config.verify_ssl = formData.has('verify_ssl');
            break;
        case 'komodo':
            data.config.url = formData.get('url');
            data.config.api_key = formData.get('api_key');
            data.config.api_secret = formData.get('api_secret');
            break;
    }

    const url = isEdit ? `/docker/instances/${instanceId}` : '/docker/instances';
    const method = isEdit ? 'PUT' : 'POST';

    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function (response) {
            if (response.success) {
                showNotification(`Instance ${isEdit ? 'updated' : 'created'} successfully!`);
                $('#instanceModal').modal('hide');
                loadDockerInstances();
            } else {
                showNotification(`Error ${isEdit ? 'updating' : 'creating'} instance: ` + response.error, 'error');
            }
        },
        error: function (xhr, status, error) {
            console.error(`Error ${isEdit ? 'updating' : 'creating'} instance:`, status, error);
            showNotification(`Error ${isEdit ? 'updating' : 'creating'} instance.`, 'error');
        }
    });
}

/**
 * Scan ports for a given IP address.
 *
 * @param {string} ipAddress - The IP address to scan
 * @returns {Promise} A promise that resolves when the scan is complete
 */
export function scanPorts(ipAddress) {
    return new Promise((resolve, reject) => {
        $.ajax({
            url: '/docker/scan_ports',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ ip_address: ipAddress }),
            success: function (response) {
                if (response.success) {
                    // Start polling for scan status
                    pollScanStatus(response.scan_id, resolve, reject);
                } else {
                    reject(new Error(response.message || 'Failed to start port scan'));
                }
            },
            error: function (xhr, status, error) {
                console.error('Error starting port scan:', status, error);
                reject(new Error('Error starting port scan'));
            }
        });
    });
}

/**
 * Poll for scan status.
 *
 * @param {number} scanId - The ID of the scan to check
 * @param {function} resolve - The resolve function for the promise
 * @param {function} reject - The reject function for the promise
 */
function pollScanStatus(scanId, resolve, reject) {
    $.ajax({
        url: `/docker/scan_status/${scanId}`,
        method: 'GET',
        success: function (response) {
            if (response.status === 'completed') {
                resolve(response);
            } else if (response.status === 'failed') {
                reject(new Error('Port scan failed'));
            } else {
                // Continue polling
                setTimeout(() => pollScanStatus(scanId, resolve, reject), 1000);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error checking scan status:', status, error);
            reject(new Error('Error checking scan status'));
        }
    });
}

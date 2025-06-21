// static/js/core/docker.js

/**
 * Manages Docker integration functionality for the application.
 * This module handles Docker settings, port scanning, and integration with
 * Portainer and Komodo using the new multi-instance system.
 */

import { showNotification } from '../ui/helpers.js';
import { showDockerScanAnimation, showDockerScanSuccess, showDockerScanError } from '../ui/dockerAnimation.js';

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
    $('#scan-all-instances').click(handleScanAllInstancesClick);

    // Set up delegated event handlers for dynamic content
    $(document).on('click', '.edit-instance-btn', handleEditInstanceClick);
    $(document).on('click', '.delete-instance-btn', handleDeleteInstanceClick);
    $(document).on('click', '.scan-instance-btn', handleScanInstanceClick);
    $(document).on('click', '.test-instance-btn', handleTestInstanceClick);
    $(document).on('submit', '#instance-form', handleInstanceFormSubmit);
    $(document).on('change', '.instance-enabled', handleInstanceEnabledChange);
    $(document).on('change', '#auto-scan-on-refresh', handleAutoScanSettingChange);

    // Load auto-scan settings
    loadAutoScanSettings();
}

/**
 * Initialize auto-scan functionality for page refresh.
 * This should be called when the ports page loads.
 */
export function initAutoScan() {
    console.log('🔄 Initializing auto-scan functionality');

    // Check if this page load was caused by an auto-scan refresh
    const scanTriggeredRefresh = sessionStorage.getItem('dockerScanTriggeredRefresh');
    if (scanTriggeredRefresh) {
        console.log('⏭️ Skipping auto-scan - page was refreshed due to previous scan');
        sessionStorage.removeItem('dockerScanTriggeredRefresh');
        return;
    }

    // Check if auto-scan on refresh is enabled
    $.ajax({
        url: '/docker/auto_scan_settings',
        method: 'GET',
        success: function (response) {
            if (response.success && response.settings.auto_scan_on_refresh) {
                console.log('✅ Auto-scan on refresh is enabled - starting scan immediately');
                performAutoScan(response.settings);
            } else {
                console.log('❌ Auto-scan on refresh is disabled');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error loading auto-scan settings:', error);
        }
    });
}

/**
 * Perform auto-scan of Docker instances.
 *
 * @param {Object} settings - Auto-scan settings
 */
function performAutoScan(settings) {
    // Show Docker logo animation instead of text notification
    if (settings.show_scan_notifications) {
        showDockerScanAnimation();
    }

    const startTime = Date.now();

    $.ajax({
        url: '/docker/scan_all',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            enabled_only: settings.scan_enabled_only
        }),
        success: function (response) {
            const duration = Math.round((Date.now() - startTime) / 1000);

            if (response.success) {
                console.log('✅ Auto-scan completed successfully:', response.summary);

                // Show success animation with summary
                if (settings.show_scan_notifications) {
                    const summary = response.summary;
                    let message = `Scan completed in ${duration}s`;
                    if (summary.total_added > 0 || summary.total_removed > 0) {
                        message += ` • ${summary.total_added} added, ${summary.total_removed} removed`;
                    }
                    showDockerScanSuccess(message, 2000);
                }

                // Trigger real-time refresh if ports were added or removed
                if (response.summary.total_added > 0 || response.summary.total_removed > 0) {
                    console.log('🔄 Triggering real-time page refresh due to port changes');

                    // Set flag to prevent auto-scan on the next page load
                    sessionStorage.setItem('dockerScanTriggeredRefresh', 'true');

                    // Import and use the refreshPortsForIP function for each IP that had changes
                    import('./portManagement.js').then(portModule => {
                        // For now, do a full page reload to ensure all changes are visible
                        // In the future, we could track which IPs had changes and refresh only those
                        setTimeout(() => {
                            console.log('🔄 Reloading page to show updated ports');
                            window.location.reload();
                        }, 2500); // Longer delay to let the success animation show
                    }).catch(err => {
                        console.log('Port management module not available, doing full reload');
                        setTimeout(() => {
                            window.location.reload();
                        }, 2500);
                    });

                    // Dispatch custom event to notify other parts of the app
                    window.dispatchEvent(new CustomEvent('dockerPortsUpdated', {
                        detail: response.summary
                    }));
                }
            } else {
                console.error('❌ Auto-scan failed:', response.error);
                if (settings.show_scan_notifications) {
                    showDockerScanError(`Scan failed: ${response.error}`);
                }
            }
        },
        error: function (xhr, status, error) {
            console.error('💥 Auto-scan error:', error);

            if (settings.show_scan_notifications) {
                showDockerScanError(`Scan error: ${error}`);
            }
        }
    });
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

    console.log(`Updating instance ${instanceId} enabled status to: ${enabled}`);

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
                console.error('Server error updating instance:', response.error);
                showNotification('Error updating instance: ' + response.error, 'error');
                // Revert checkbox state
                $(e.currentTarget).prop('checked', !enabled);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error updating instance:', status, error, xhr.responseText);
            let errorMessage = 'Error updating instance.';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMessage = xhr.responseJSON.error;
            }
            showNotification(errorMessage, 'error');
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
            configHtml = renderDockerConfigFields();
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

    // Set up connection type change handler for Docker instances
    if (type === 'docker') {
        $('#docker-connection-type').change(updateDockerConnectionFields);
        updateDockerConnectionFields();
    }
}

/**
 * Render Docker configuration fields with connection type selector.
 */
function renderDockerConfigFields() {
    return `
        <div class="form-group">
            <label for="docker-connection-type">Connection Type</label>
            <select class="form-control" id="docker-connection-type" name="connection_type">
                <option value="socket">Local Socket</option>
                <option value="ssh">SSH Connection</option>
                <option value="tcp">TCP Connection</option>
            </select>
            <small class="form-text text-muted">Choose how to connect to the Docker daemon</small>
        </div>

        <div id="docker-connection-fields">
            <!-- Connection-specific fields will be populated here -->
        </div>

        <div class="form-group">
            <label for="docker-timeout">Connection Timeout (seconds)</label>
            <input type="number" class="form-control" id="docker-timeout" name="timeout"
                   value="30" min="5" max="300">
            <small class="form-text text-muted">How long to wait for connection attempts</small>
        </div>
    `;
}

/**
 * Update Docker connection fields based on selected connection type.
 */
function updateDockerConnectionFields() {
    const connectionType = $('#docker-connection-type').val();
    const $connectionFields = $('#docker-connection-fields');

    let fieldsHtml = '';

    switch (connectionType) {
        case 'socket':
            fieldsHtml = renderSocketFields();
            break;
        case 'ssh':
            fieldsHtml = renderSSHFields();
            break;
        case 'tcp':
            fieldsHtml = renderTCPFields();
            break;
    }

    $connectionFields.html(fieldsHtml);

    // Set up TLS toggle handler for TCP connections
    if (connectionType === 'tcp') {
        $('#tcp-tls-enabled').change(updateTLSFields);
        updateTLSFields();
    }
}

/**
 * Render socket connection fields.
 */
function renderSocketFields() {
    return `
        <div class="alert alert-info">
            <i class="fas fa-plug"></i>
            <strong>Local Socket Connection</strong><br>
            Connect to Docker daemon running on the same machine via Unix socket.
        </div>

        <div class="form-group">
            <label for="socket-host">Socket Path</label>
            <input type="text" class="form-control" id="socket-host" name="host"
                   value="unix:///var/run/docker.sock" placeholder="unix:///var/run/docker.sock">
            <small class="form-text text-muted">
                Path to Docker socket file (usually /var/run/docker.sock)
            </small>
        </div>
    `;
}

/**
 * Render SSH connection fields.
 */
function renderSSHFields() {
    return `
        <div class="alert alert-info">
            <i class="fas fa-key"></i>
            <strong>SSH Connection</strong><br>
            Connect to remote Docker daemon via SSH tunnel. Requires SSH access to the remote host.
        </div>

        <div class="form-row">
            <div class="form-group col-md-8">
                <label for="ssh-host">Remote Host</label>
                <input type="text" class="form-control" id="ssh-host" name="host"
                       placeholder="remote-server.example.com" required>
                <small class="form-text text-muted">Hostname or IP address of remote Docker host</small>
            </div>
            <div class="form-group col-md-4">
                <label for="ssh-port">SSH Port</label>
                <input type="number" class="form-control" id="ssh-port" name="ssh_port"
                       value="22" min="1" max="65535">
            </div>
        </div>

        <div class="form-group">
            <label for="ssh-username">SSH Username</label>
            <input type="text" class="form-control" id="ssh-username" name="ssh_username"
                   placeholder="docker-user" required>
            <small class="form-text text-muted">User must be in the docker group on remote host</small>
        </div>

        <div class="form-group">
            <label for="ssh-key-path">SSH Private Key Path (optional)</label>
            <input type="text" class="form-control" id="ssh-key-path" name="ssh_key_path"
                   placeholder="/path/to/private/key">
            <small class="form-text text-muted">
                Leave empty to use default SSH authentication (agent, default keys)
            </small>
        </div>

        <div class="alert alert-warning">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Setup Required:</strong> Ensure SSH access is configured and the user has Docker permissions.
        </div>
    `;
}

/**
 * Render TCP connection fields.
 */
function renderTCPFields() {
    return `
        <div class="alert alert-info">
            <i class="fas fa-network-wired"></i>
            <strong>TCP Connection</strong><br>
            Connect to remote Docker daemon via TCP. Can use TLS for secure connections.
        </div>

        <div class="form-row">
            <div class="form-group col-md-8">
                <label for="tcp-host">Remote Host</label>
                <input type="text" class="form-control" id="tcp-host" name="host"
                       placeholder="remote-server.example.com" required>
                <small class="form-text text-muted">Hostname or IP address of remote Docker host</small>
            </div>
            <div class="form-group col-md-4">
                <label for="tcp-port">Port</label>
                <input type="number" class="form-control" id="tcp-port" name="tcp_port"
                       value="2376" min="1" max="65535">
                <small class="form-text text-muted">2376 for TLS, 2375 for unencrypted</small>
            </div>
        </div>

        <div class="form-group">
            <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" id="tcp-tls-enabled"
                       name="tls_enabled" checked>
                <label class="form-check-label" for="tcp-tls-enabled">
                    <strong>Enable TLS Encryption</strong>
                </label>
            </div>
            <small class="form-text text-muted">Highly recommended for remote connections</small>
        </div>

        <div id="tls-fields">
            <!-- TLS-specific fields will be populated here -->
        </div>

        <div class="alert alert-warning">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Setup Required:</strong> Docker daemon must be configured to accept TCP connections.
        </div>
    `;
}

/**
 * Update TLS fields based on TLS enabled state.
 */
function updateTLSFields() {
    const tlsEnabled = $('#tcp-tls-enabled').is(':checked');
    const $tlsFields = $('#tls-fields');

    if (tlsEnabled) {
        $tlsFields.html(`
            <div class="form-group">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="tls-verify"
                           name="tls_verify" checked>
                    <label class="form-check-label" for="tls-verify">
                        Verify TLS Certificate
                    </label>
                </div>
                <small class="form-text text-muted">Disable only for testing with self-signed certificates</small>
            </div>

            <div class="form-group">
                <label for="tls-ca-path">CA Certificate Path (optional)</label>
                <input type="text" class="form-control" id="tls-ca-path" name="tls_ca_path"
                       placeholder="/path/to/ca.pem">
                <small class="form-text text-muted">Custom CA certificate for verification</small>
            </div>

            <div class="form-row">
                <div class="form-group col-md-6">
                    <label for="tls-cert-path">Client Certificate Path (optional)</label>
                    <input type="text" class="form-control" id="tls-cert-path" name="tls_cert_path"
                           placeholder="/path/to/cert.pem">
                </div>
                <div class="form-group col-md-6">
                    <label for="tls-key-path">Client Key Path (optional)</label>
                    <input type="text" class="form-control" id="tls-key-path" name="tls_key_path"
                           placeholder="/path/to/key.pem">
                </div>
            </div>
            <small class="form-text text-muted">
                Client certificates are required only if the Docker daemon requires client authentication
            </small>
        `);
    } else {
        $tlsFields.html(`
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Warning:</strong> Unencrypted TCP connections are not secure and should only be used in trusted networks.
            </div>
        `);
    }
}

/**
 * Build Docker configuration object from form data.
 *
 * @param {FormData} formData - Form data object
 * @returns {Object} Docker configuration object
 */
function buildDockerConfig(formData) {
    const connectionType = formData.get('connection_type') || 'socket';
    const config = {
        connection_type: connectionType,
        timeout: parseInt(formData.get('timeout')) || 30
    };

    switch (connectionType) {
        case 'socket':
            config.host = formData.get('host') || 'unix:///var/run/docker.sock';
            break;

        case 'ssh':
            config.host = formData.get('host') || '';
            config.ssh_username = formData.get('ssh_username') || '';
            config.ssh_port = parseInt(formData.get('ssh_port')) || 22;

            const sshKeyPath = formData.get('ssh_key_path');
            if (sshKeyPath && sshKeyPath.trim()) {
                config.ssh_key_path = sshKeyPath.trim();
            }
            break;

        case 'tcp':
            config.host = formData.get('host') || '';
            config.tcp_port = parseInt(formData.get('tcp_port')) || 2376;
            config.tls_enabled = formData.has('tls_enabled');

            if (config.tls_enabled) {
                config.tls_verify = formData.has('tls_verify');

                const tlsCaPath = formData.get('tls_ca_path');
                if (tlsCaPath && tlsCaPath.trim()) {
                    config.tls_ca_path = tlsCaPath.trim();
                }

                const tlsCertPath = formData.get('tls_cert_path');
                if (tlsCertPath && tlsCertPath.trim()) {
                    config.tls_cert_path = tlsCertPath.trim();
                }

                const tlsKeyPath = formData.get('tls_key_path');
                if (tlsKeyPath && tlsKeyPath.trim()) {
                    config.tls_key_path = tlsKeyPath.trim();
                }
            }
            break;
    }

    return config;
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
            data.config = buildDockerConfig(formData);
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

/**
 * Handle scan all instances button click.
 */
function handleScanAllInstancesClick() {
    const $button = $('#scan-all-instances');

    $button.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Scanning All...');

    $.ajax({
        url: '/docker/scan_all',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            enabled_only: true
        }),
        success: function (response) {
            if (response.success) {
                showNotification(response.message, 'success');
                loadDockerInstances(); // Refresh to show updated service counts
            } else {
                showNotification('Error scanning instances: ' + response.error, 'error');
            }
            $button.prop('disabled', false).html('<i class="fas fa-search"></i> Scan All');
        },
        error: function (xhr, status, error) {
            console.error('Error scanning all instances:', status, error);
            showNotification('Error scanning instances.', 'error');
            $button.prop('disabled', false).html('<i class="fas fa-search"></i> Scan All');
        }
    });
}

/**
 * Load auto-scan settings from the server.
 */
function loadAutoScanSettings() {
    $.ajax({
        url: '/docker/auto_scan_settings',
        method: 'GET',
        success: function (response) {
            if (response.success) {
                const settings = response.settings;
                $('#auto-scan-on-refresh').prop('checked', settings.auto_scan_on_refresh);
                $('#show-scan-notifications').prop('checked', settings.show_scan_notifications);
                $('#scan-enabled-only').prop('checked', settings.scan_enabled_only);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error loading auto-scan settings:', error);
        }
    });
}

/**
 * Handle auto-scan setting change.
 *
 * @param {Event} e - Change event
 */
function handleAutoScanSettingChange(e) {
    const settings = {
        auto_scan_on_refresh: $('#auto-scan-on-refresh').is(':checked'),
        show_scan_notifications: $('#show-scan-notifications').is(':checked'),
        scan_enabled_only: $('#scan-enabled-only').is(':checked')
    };

    $.ajax({
        url: '/docker/auto_scan_settings',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(settings),
        success: function (response) {
            if (response.success) {
                showNotification('Auto-scan settings saved successfully!', 'success');
            } else {
                showNotification('Error saving auto-scan settings: ' + response.error, 'error');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error saving auto-scan settings:', error);
            showNotification('Error saving auto-scan settings.', 'error');
        }
    });
}

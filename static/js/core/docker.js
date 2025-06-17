// static/js/core/docker.js

/**
 * Manages Docker integration functionality for the application.
 * This module handles Docker settings, port scanning, and integration with
 * Portainer and Komodo.
 */

import { showNotification } from '../ui/helpers.js';

/**
 * Initialize Docker integration functionality.
 * Sets up event handlers for Docker-related forms and buttons.
 */
export function init() {
    // Load Docker settings
    loadDockerSettings();

    // Set up form submission handlers
    $('#docker-settings-form').submit(handleDockerSettingsSubmit);
    $('#portainer-settings-form').submit(handlePortainerSettingsSubmit);
    $('#komodo-settings-form').submit(handleKomodoSettingsSubmit);

    // Set up button click handlers
    $('#docker-scan-button').click(handleDockerScanClick);
    $('#portainer-import-button').click(handlePortainerImportClick);
    $('#komodo-import-button').click(handleKomodoImportClick);

    // Set up checkbox change handlers
    $('#docker-enabled').change(updateDockerFormState);
    $('#portainer-enabled').change(updatePortainerFormState);
    $('#komodo-enabled').change(updateKomodoFormState);
}

/**
 * Load Docker settings from the server.
 * Populates the Docker settings forms with values from the server.
 */
function loadDockerSettings() {
    $.ajax({
        url: '/docker/settings',
        method: 'GET',
        success: function (data) {
            // Docker settings
            $('#docker-enabled').prop('checked', data.docker_enabled === 'true');
            $('#docker-host').val(data.docker_host || 'unix:///var/run/docker.sock');
            $('#docker-auto-detect').prop('checked', data.docker_auto_detect === 'true');
            $('#docker-scan-interval').val(data.docker_scan_interval || '300');

            // Portainer settings
            $('#portainer-enabled').prop('checked', data.portainer_enabled === 'true');
            $('#portainer-url').val(data.portainer_url || '');
            $('#portainer-api-key').val(data.portainer_api_key || '');
            $('#portainer-verify-ssl').prop('checked', data.portainer_verify_ssl !== 'false'); // Default to true
            $('#portainer-auto-detect').prop('checked', data.portainer_auto_detect === 'true');
            $('#portainer-scan-interval').val(data.portainer_scan_interval || '300');

            // Komodo settings
            $('#komodo-enabled').prop('checked', data.komodo_enabled === 'true');
            $('#komodo-url').val(data.komodo_url || '');
            $('#komodo-api-key').val(data.komodo_api_key || '');
            $('#komodo-api-secret').val(data.komodo_api_secret || '');
            $('#komodo-auto-detect').prop('checked', data.komodo_auto_detect === 'true');
            $('#komodo-scan-interval').val(data.komodo_scan_interval || '300');

            // Update form states
            updateDockerFormState();
            updatePortainerFormState();
            updateKomodoFormState();
        },
        error: function (xhr, status, error) {
            console.error('Error loading Docker settings:', status, error);
            showNotification('Error loading Docker settings.', 'error');
        }
    });
}

/**
 * Handle Docker settings form submission.
 * Saves Docker settings to the server.
 *
 * @param {Event} e - The form submission event
 */
function handleDockerSettingsSubmit(e) {
    e.preventDefault();

    const formData = new FormData(this);

    // Add checkbox values (they're only included when checked)
    if (!$('#docker-enabled').is(':checked')) {
        formData.append('docker_enabled', 'false');
    }

    if (!$('#docker-auto-detect').is(':checked')) {
        formData.append('docker_auto_detect', 'false');
    }

    $.ajax({
        url: '/docker/settings',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function (response) {
            if (response.success) {
                showNotification('Docker settings saved successfully!');
                // Reload settings from the server to ensure UI reflects current state
                loadDockerSettings();
                updateDockerFormState();
            } else {
                showNotification('Error saving Docker settings: ' + response.error, 'error');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error saving Docker settings:', status, error);
            showNotification('Error saving Docker settings.', 'error');
        }
    });
}

/**
 * Handle Portainer settings form submission.
 * Saves Portainer integration settings to the server.
 *
 * @param {Event} e - The form submission event
 */
function handlePortainerSettingsSubmit(e) {
    e.preventDefault();

    const formData = new FormData(this);

    // Add checkbox values (they're only included when checked)
    if (!$('#portainer-enabled').is(':checked')) {
        formData.append('portainer_enabled', 'false');
    }

    if (!$('#portainer-verify-ssl').is(':checked')) {
        formData.append('portainer_verify_ssl', 'false');
    }

    if (!$('#portainer-auto-detect').is(':checked')) {
        formData.append('portainer_auto_detect', 'false');
    }

    $.ajax({
        url: '/docker/settings',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function (response) {
            if (response.success) {
                showNotification('Portainer settings saved successfully!');
                // Reload settings from the server to ensure UI reflects current state
                loadDockerSettings();
                updatePortainerFormState();
            } else {
                showNotification('Error saving Portainer settings: ' + response.error, 'error');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error saving Portainer settings:', status, error);
            showNotification('Error saving Portainer settings.', 'error');
        }
    });
}


/**
 * Handle Komodo settings form submission.
 * Saves Komodo integration settings to the server.
 *
 * @param {Event} e - The form submission event
 */
function handleKomodoSettingsSubmit(e) {
    e.preventDefault();

    const formData = new FormData(this);

    // Add checkbox values (they're only included when checked)
    if (!$('#komodo-enabled').is(':checked')) {
        formData.append('komodo_enabled', 'false');
    }

    if (!$('#komodo-auto-detect').is(':checked')) {
        formData.append('komodo_auto_detect', 'false');
    }

    $.ajax({
        url: '/docker/settings',
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function (response) {
            if (response.success) {
                showNotification('Komodo settings saved successfully!');
                // Reload settings from the server to ensure UI reflects current state
                loadDockerSettings();
                updateKomodoFormState();
            } else {
                showNotification('Error saving Komodo settings: ' + response.error, 'error');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error saving Komodo settings:', status, error);
            showNotification('Error saving Komodo settings.', 'error');
        }
    });
}

/**
 * Handle Docker scan button click.
 * Initiates a scan of Docker containers for port mappings.
 */
function handleDockerScanClick() {
    const $button = $(this);
    $button.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Scanning...');

    $.ajax({
        url: '/docker/scan',
        method: 'POST',
        success: function (response) {
            if (response.success) {
                showNotification(response.message);
            } else {
                showNotification('Error scanning Docker containers: ' + response.error, 'error');
            }
            $button.prop('disabled', false).text('Scan Docker Containers Now');
        },
        error: function (xhr, status, error) {
            console.error('Error scanning Docker containers:', status, error);
            showNotification('Error scanning Docker containers.', 'error');
            $button.prop('disabled', false).text('Scan Docker Containers Now');
        }
    });
}

/**
 * Handle Portainer import button click.
 * Imports containers and port mappings from Portainer.
 */
function handlePortainerImportClick() {
    const $button = $(this);
    $button.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Importing...');

    $.ajax({
        url: '/docker/import_from_portainer',
        method: 'POST',
        success: function (response) {
            if (response.success) {
                showNotification(response.message);
            } else {
                showNotification('Error importing from Portainer: ' + response.error, 'error');
            }
            $button.prop('disabled', false).text('Import from Portainer');
        },
        error: function (xhr, status, error) {
            console.error('Error importing from Portainer:', status, error);
            showNotification('Error importing from Portainer.', 'error');
            $button.prop('disabled', false).text('Import from Portainer');
        }
    });
}


/**
 * Handle Komodo import button click.
 * Imports containers and port mappings from Komodo.
 */
function handleKomodoImportClick() {
    const $button = $(this);
    $button.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Importing...');

    $.ajax({
        url: '/docker/import_from_komodo',
        method: 'POST',
        success: function (response) {
            if (response.success) {
                showNotification(response.message);
            } else {
                showNotification('Error importing from Komodo: ' + response.error, 'error');
            }
            $button.prop('disabled', false).text('Import from Komodo');
        },
        error: function (xhr, status, error) {
            console.error('Error importing from Komodo:', status, error);
            showNotification('Error importing from Komodo.', 'error');
            $button.prop('disabled', false).text('Import from Komodo');
        }
    });
}

/**
 * Update Docker form state based on the Docker enabled checkbox.
 * Disables or enables form fields based on the checkbox state.
 */
function updateDockerFormState() {
    const enabled = $('#docker-enabled').is(':checked');

    $('#docker-host').prop('disabled', !enabled);
    $('#docker-auto-detect').prop('disabled', !enabled);
    $('#docker-scan-interval').prop('disabled', !enabled);
    $('#docker-scan-button').prop('disabled', !enabled);
}

/**
 * Update Portainer form state based on the Portainer enabled checkbox.
 * Disables or enables form fields based on the checkbox state.
 */
function updatePortainerFormState() {
    const enabled = $('#portainer-enabled').is(':checked');

    $('#portainer-url').prop('disabled', !enabled);
    $('#portainer-api-key').prop('disabled', !enabled);
    $('#portainer-verify-ssl').prop('disabled', !enabled);
    $('#portainer-auto-detect').prop('disabled', !enabled);
    $('#portainer-scan-interval').prop('disabled', !enabled);
    $('#portainer-import-button').prop('disabled', !enabled);
}


/**
 * Update Komodo form state based on the Komodo enabled checkbox.
 * Disables or enables form fields based on the checkbox state.
 */
function updateKomodoFormState() {
    const enabled = $('#komodo-enabled').is(':checked');

    $('#komodo-url').prop('disabled', !enabled);
    $('#komodo-api-key').prop('disabled', !enabled);
    $('#komodo-api-secret').prop('disabled', !enabled);
    $('#komodo-auto-detect').prop('disabled', !enabled);
    $('#komodo-scan-interval').prop('disabled', !enabled);
    $('#komodo-import-button').prop('disabled', !enabled);
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

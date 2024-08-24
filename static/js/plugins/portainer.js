// static/js/plugins/portainer.js

import { savePortainerConfig, testPortainerConfig, fetchPortainerConfig } from '../api/plugins/portainer-ajax.js';
import { logPluginsConfig } from '../utils/logger.js';

/**
 * Initialize Portainer-related event listeners and UI elements.
 * This function sets up all necessary event listeners for the Portainer plugin
 * and performs initial checks and logging if the plugin is enabled.
 */
export function initPortainerSettings() {
    const saveButton = document.getElementById('save-portainer-settings');
    const testButton = document.getElementById('test-portainer-connection');
    const portainerUrl = document.getElementById('portainer-url');
    const portainerToken = document.getElementById('portainer-token');
    const portainerEnabled = document.getElementById('portainer-enabled');

    if (saveButton) {
        saveButton.addEventListener('click', handleSavePortainerSettings);
    } else {
        console.error('Save button not found');
    }

    if (testButton) {
        testButton.addEventListener('click', handleTestPortainerConnection);
    } else {
        console.error('Test button not found');
    }

    if (portainerUrl && portainerToken) {
        portainerUrl.addEventListener('input', checkPortainerFields);
        portainerToken.addEventListener('input', checkPortainerFields);
    }

    if (portainerEnabled) {
        portainerEnabled.addEventListener('change', handlePortainerEnabledChange);
    } else {
        console.error('Portainer enabled checkbox not found');
    }

    // Load saved configuration
    fetchPortainerConfig((config) => {
        if (config) {
            portainerUrl.value = config.url || '';
            portainerToken.value = config.token || '';
            portainerEnabled.checked = config.enabled;
            checkPortainerFields();
            updateEnabledPlugins();
            if (config.enabled) {
                logPluginsConfig("portainer", { url: config.url, token: config.token });
            }
        }
    });
}

/**
 * Displays a notification message
 * @param {string} message - The message to display
 * @param {string} [type='success'] - The type of notification ('success' or 'error')
 */
function showNotification(message, type = 'success') {
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    const notification = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    $('#notification-area').html(notification);
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        $('.alert').alert('close');
    }, 5000);
}

/**
 * Handle saving Portainer settings.
 * Retrieves URL and token from input fields and calls the savePortainerConfig function.
 */
function handleSavePortainerSettings() {
    const url = document.getElementById('portainer-url').value;
    const token = document.getElementById('portainer-token').value;
    const enabled = document.getElementById('portainer-enabled').checked;

    if (!url || !token) {
        showNotification('Please enter both URL and token', 'error');
        return;
    }

    savePortainerConfig(url, token, enabled);
}

/**
 * Handle testing Portainer connection.
 * Retrieves URL and token from input fields and calls the testPortainerConfig function.
 */
function handleTestPortainerConnection() {
    const url = document.getElementById('portainer-url').value;
    const token = document.getElementById('portainer-token').value;

    if (!url || !token) {
        showNotification('Please enter both URL and token', 'error');
        return;
    }

    testPortainerConfig(url, token);
}

/**
 * Update Portainer connection status in the UI.
 *
 * @param {boolean} isConnected - Whether the Portainer connection is successful.
 */
export function updateConnectionStatus(isConnected) {
    const statusElement = document.getElementById('portainer-connection-status');
    if (statusElement) {
        statusElement.textContent = isConnected ? 'Connected' : 'Disconnected';
        statusElement.className = isConnected ? 'text-success' : 'text-danger';
    }
}

/**
 * Handle changes to the Portainer enabled checkbox.
 */
function handlePortainerEnabledChange() {
    const isEnabled = document.getElementById('portainer-enabled').checked;
    const url = document.getElementById('portainer-url').value;
    const token = document.getElementById('portainer-token').value;

    if (isEnabled && (!url || !token)) {
        showNotification('Please enter both URL and token before enabling Portainer', 'error');
        document.getElementById('portainer-enabled').checked = false;
        updateEnabledPlugins();
        return;
    }

    savePortainerConfig(url, token, isEnabled);
    updateEnabledPlugins();
}

/**
 * Check if Portainer fields are populated and update UI accordingly.
 * This function enables or disables the Portainer checkbox based on whether
 * both the URL and token fields have been filled.
 */
function checkPortainerFields() {
    const url = document.getElementById('portainer-url').value.trim();
    const token = document.getElementById('portainer-token').value.trim();
    const enabledCheckbox = document.getElementById('portainer-enabled');

    if (url && token) {
        enabledCheckbox.disabled = false;
        enabledCheckbox.title = "Enable Portainer integration";
    } else {
        enabledCheckbox.disabled = true;
        enabledCheckbox.checked = false;
        enabledCheckbox.title = "Please configure Portainer first before enabling it";
    }
}

/**
 * Update the list of enabled plugins in the UI.
 * This function updates the UI to reflect the current state of the Portainer plugin
 * (enabled or disabled) and logs the configuration if the plugin is enabled.
 */
function updateEnabledPlugins() {
    const $enabledPlugins = $('#enabled-plugins');
    $enabledPlugins.empty(); // Clear existing entries
    const isEnabled = $('#portainer-enabled').is(':checked');
    if (isEnabled) {
        $enabledPlugins.append(`
            <div class="enabled-plugin">
                <div class="plugin-info">
                    <span class="plugin-name">Portainer</span>: <span class="plugin-description">Connects Portall to your Portainer instance</span>
                </div>
                <button class="btn btn-sm btn-danger disable-plugin" data-plugin="portainer-enabled">Disable</button>
            </div>
        `);

        // Log plugin info when enabled
        const url = document.getElementById('portainer-url').value;
        const token = document.getElementById('portainer-token').value;
        logPluginsConfig("portainer", { url: url, token: token });
    }

    // Add event listener for the disable button
    $('.disable-plugin').off('click').on('click', function () {
        const pluginId = $(this).data('plugin');
        const checkbox = $(`#${pluginId}`);
        checkbox.prop('checked', false);
        checkbox.trigger('change');
        updateEnabledPlugins();
        handlePortainerEnabledChange();
    });
}
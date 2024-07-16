// static/js/plugins/portainer.js

import { savePortainerConfig, testPortainerConfig } from '../api/plugins/portainer-ajax.js';

/**
 * Initialize Portainer-related event listeners and UI elements.
 */
function init() {
    console.log('Initializing Portainer settings...');
    const saveButton = document.getElementById('save-portainer-settings');
    const testButton = document.getElementById('test-portainer-connection');

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
}

/**
 * Displays a notification message
 * @param {string} message - The message to display
 * @param {string} [type='success'] - The type of notification ('success' or 'error')
 */
export function showNotification(message, type = 'success') {
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
    console.log('Save Portainer settings clicked');
    const url = document.getElementById('portainer-url').value;
    const token = document.getElementById('portainer-token').value;

    console.log('URL:', url);
    console.log('Token:', token);

    if (!url || !token) {
        showNotification('Please enter both URL and token', 'error');
        return;
    }

    savePortainerConfig(url, token);
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

// Initialize Portainer functionality when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', init);
// static/js/api/plugins/portainer-ajax.js

import { updateConnectionStatus } from '../../plugins/portainer.js';

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
 * Saves the Portainer configuration to the server.
 *
 * @param {string} url - The Portainer URL.
 * @param {string} token - The Portainer access token.
 */
export function savePortainerConfig(url, token, enabled) {
    $.ajax({
        url: '/save_portainer_config',
        method: 'POST',
        data: JSON.stringify({ url: url, token: token, enabled: enabled }),
        contentType: 'application/json',
        success: function (response) {
            if (response.success) {
                showNotification('Portainer settings saved successfully', 'success');
                updateConnectionStatus(true);
            } else {
                showNotification('Error saving Portainer settings: ' + response.message, 'error');
                updateConnectionStatus(false);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error saving Portainer settings:', error);
            showNotification('Error saving Portainer settings: ' + error, 'error');
            updateConnectionStatus(false);
        }
    });
}

/**
 * Tests the Portainer configuration by attempting to connect to the Portainer instance.
 *
 * @param {string} url - The Portainer URL to test.
 * @param {string} token - The Portainer access token to use for authentication.
 */
export function testPortainerConfig(url, token) {
    $.ajax({
        url: '/test_portainer_config',
        method: 'POST',
        data: JSON.stringify({ url: url, token: token }),
        contentType: 'application/json',
        success: function (response) {
            if (response.success) {
                showNotification('Portainer connection successful', 'success');
                updateConnectionStatus(true);
            } else {
                showNotification('Error connecting to Portainer: ' + response.message, 'error');
                updateConnectionStatus(false);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error connecting to Portainer:', error);
            showNotification('Error connecting to Portainer: ' + error, 'error');
            updateConnectionStatus(false);
        }
    });
}

/**
 * Fetches the current Portainer configuration from the server.
 *
 * @param {function} callback - Function to call with the fetched configuration.
 */
export function fetchPortainerConfig(callback) {
    $.ajax({
        url: '/get_portainer_config',
        method: 'GET',
        success: function (response) {
            if (response.success) {
                callback(response.config);
            } else {
                console.error('Error fetching Portainer config:', response.message);
                showNotification('Error fetching Portainer configuration', 'error');
                callback(null);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error fetching Portainer config:', error);
            showNotification('Error fetching Portainer configuration', 'error');
            callback(null);
        }
    });
}
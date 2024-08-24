// static/js/api/plugins/docker-ajax.js

import { updateConnectionStatus } from '../../plugins/docker.js';

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
 * Checks if the Docker plugin is enabled and updates the tab visibility.
 */
export function updateDockerTabVisibility() {
    $.ajax({
        url: '/get_docker_config',
        method: 'GET',
        success: function (response) {
            if (response.success && response.config) {
                if (response.config.enabled) {
                    $('.docker-tab').removeClass('hidden');
                } else {
                    $('.docker-tab').addClass('hidden');
                }
                updateConnectionStatus(response.config.enabled);
            } else {
                console.error('Error fetching Docker config:', response.message);
                $('.docker-tab').addClass('hidden');
                updateConnectionStatus(false);
            }
        },
        error: function (xhr, status, error) {
            console.log('Error fetching Docker config:', error);

            console.error('Error checking Docker status:', status, error);
            $('.docker-tab').addClass('hidden');
            updateConnectionStatus(false);
        }
    });
}

/**
 * Saves the Docker configuration to the server.
 *
 * @param {string} hostIP - The Docker host IP.
 * @param {string} socketURL - The Docker socket URL.
 * @param {boolean} enabled - Whether the Docker plugin is enabled.
 */
export function saveDockerConfig(hostIP, socketURL, enabled) {
    $.ajax({
        url: '/save_docker_config',
        method: 'POST',
        data: JSON.stringify({ hostIP: hostIP, socketURL: socketURL, enabled: enabled }),
        contentType: 'application/json',
        success: function (response) {
            if (response.success) {
                showNotification('Docker configuration saved successfully', 'success');
                updateConnectionStatus(true);
                updateDockerTabVisibility();
            } else {
                showNotification('Error saving Docker configuration: ' + response.message, 'error');
                updateConnectionStatus(false);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error saving Docker configuration:', error);
            showNotification('Error saving Docker configuration: ' + error, 'error');
            updateConnectionStatus(false);
        }
    });
}

/**
 * Saves the Docker settings to the server.
 *
 * @param {string} dockerIP - The Docker IP address.
 * @param {string} dockerURL - The Docker URL.
 */
export function saveDockerSettings(dockerIP, dockerURL) {
    $.ajax({
        url: '/docker_settings',
        method: 'POST',
        data: {
            docker_ip: dockerIP,
            docker_url: dockerURL
        },
        success: function (response) {
            if (response.success) {
                showNotification('Docker settings saved successfully', 'success');
                updateConnectionStatus(true);
            } else {
                showNotification('Error saving Docker settings: ' + response.message, 'error');
                updateConnectionStatus(false);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error saving Docker settings:', error);
            showNotification('Error saving Docker settings: ' + error, 'error');
            updateConnectionStatus(false);
        }
    });
}

/**
 * Tests the Docker configuration by attempting to connect to the Docker instance.
 *
 * @param {string} hostIP - The Docker host IP to test.
 * @param {string} socketURL - The Docker socket URL to use for connection.
 */
export function testDockerConnection(hostIP, socketURL) {
    $.ajax({
        url: '/test_docker_connection',
        method: 'POST',
        data: JSON.stringify({ hostIP: hostIP, socketURL: socketURL }),
        contentType: 'application/json',
        success: function (response) {
            if (response.success) {
                showNotification('Docker connection successful', 'success');
                updateConnectionStatus(true);
            } else {
                showNotification('Error connecting to Docker: ' + response.message, 'error');
                updateConnectionStatus(false);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error connecting to Docker:', error);
            showNotification('Error connecting to Docker: ' + error, 'error');
            updateConnectionStatus(false);
        }
    });
}

/**
 * Fetches the current Docker configuration from the server.
 *
 * @param {function} callback - Function to call with the fetched configuration.
 */
export function fetchDockerConfig(callback) {
    $.ajax({
        url: '/get_docker_config',
        method: 'GET',
        success: function (response) {
            if (response.success) {
                callback(response.config);
            } else {
                console.error('Error fetching Docker config:', response.message);
                showNotification('Error fetching Docker configuration', 'error');
                callback(null);
            }
        },
        error: function (xhr, status, error) {
            console.error('Error fetching Docker config:', error);
            showNotification('Error fetching Docker configuration', 'error');
            callback(null);
        }
    });
}
// static/js/api/plugins/portainer-ajax.js

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
 * Saves the Portainer configuration to the server.
 *
 * @param {string} url - The Portainer URL.
 * @param {string} token - The Portainer access token.
 */
export function savePortainerConfig(url, token) {
    $.ajax({
        url: '/save_portainer_config',  // Changed to match your naming convention
        method: 'POST',
        data: JSON.stringify({ url: url, token: token }),
        contentType: 'application/json',
        success: function (response) {
            if (response.success) {
                showNotification('Portainer settings saved successfully', 'success');
            } else {
                showNotification('Error saving Portainer settings: ' + response.message, 'error');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error saving Portainer settings:', error);
            showNotification('Error saving Portainer settings: ' + error, 'error');
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
        url: '/test_portainer_config',  // Changed to match your naming convention
        method: 'POST',
        data: JSON.stringify({ url: url, token: token }),
        contentType: 'application/json',
        success: function (response) {
            if (response.success) {
                showNotification('Portainer connection successful', 'success');
            } else {
                showNotification('Error connecting to Portainer: ' + response.message, 'error');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error connecting to Portainer:', error);
            showNotification('Error connecting to Portainer: ' + error, 'error');
        }
    });
}
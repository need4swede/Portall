// static/js/import.js

/**
 * Application: Configuration Import Tool
 * Description: Provides a user interface for importing various types of configuration files.
 * It supports Caddyfile, JSON, and Docker-Compose file formats.
 *
 * Uses jQuery for DOM manipulation and AJAX requests.
 */

$(document).ready(function () {

    /**
     * Placeholder text for different file types.
     * Helps users understand the expected format for each file type.
     */

    const placeholders = {
        'Caddyfile': `service.domain.tld {
    encode gzip
    import /config/security.conf
    reverse_proxy 192.168.0.123:8080
}
jellyfin.domain.tld {
    reverse_proxy 192.168.0.110:8096
}`,
        'JSON': `[
    {
        "ip_address": "192.168.1.100",
        "nickname": "Server1",
        "port_number": 8080,
        "description": "example.domain.com",
        "order": 0
    },
    {
        "ip_address": "192.168.1.101",
        "nickname": "Server2",
        "port_number": 9090,
        "description": "app.domain.com",
        "order": 0
    }
]`,
        'Docker-Compose': `version: '3'
services:
    webapp:
        image: webapp:latest
        ports:
            - "8080:80"
    database:
        image: postgres:12
        ports:
            - "5432:5432"
`
    };

    /**
     * Displays a notification message to the user.
     *
     * @param {string} message - The message to display in the notification.
     * @param {string} [type='success'] - The type of notification ('success' or 'error').
     */
    function showNotification(message, type = 'success') {
        // Determine the appropriate Bootstrap alert class based on the notification type
        const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';

        // Create the notification HTML
        const notification = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;

        // Insert the notification into the DOM
        $('#notification-area').html(notification);

        // Automatically dismiss the notification after 5 seconds
        setTimeout(() => {
            $('.alert').alert('close');
        }, 5000);
    }

    // Event handler for changing the import type
    $('#import-type').change(function () {
        const selectedType = $(this).val();
        // Update the placeholder text based on the selected import type
        $('#file-content').attr('placeholder', placeholders[selectedType]);
    });

    // Set initial placeholder text when the page loads
    $('#file-content').attr('placeholder', placeholders[$('#import-type').val()]);

    // Event handler for form submission
    $('#import-form').submit(function (e) {
        e.preventDefault(); // Prevent the default form submission

        // Send an AJAX POST request to the server
        $.ajax({
            url: '/import',
            method: 'POST',
            data: $(this).serialize(),
            success: function (response) {
                console.log('Import successful:', response);
                showNotification(response.message);
                $('#file-content').val(''); // Clear the textarea after successful import
            },
            error: function (xhr, status, error) {
                console.error('Error importing data:', status, error);
                showNotification('Error importing data.', 'error');
            }
        });
    });
});
$(document).ready(function () {
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
         "ip": "192.168.0.123",
         "port": 8080,
         "description": "My App"
         },
         {
         "ip": "192.168.0.110",
         "port": 8096,
         "description": "Jellyfin Server"
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

    $('#import-type').change(function () {
        const selectedType = $(this).val();
        $('#file-content').attr('placeholder', placeholders[selectedType]);
    });

    // Set initial placeholder
    $('#file-content').attr('placeholder', placeholders[$('#import-type').val()]);

    $('#import-form').submit(function (e) {
        e.preventDefault();
        $.ajax({
            url: '/import',
            method: 'POST',
            data: $(this).serialize(),
            success: function (response) {
                console.log('Import successful:', response);
                showNotification(response.message);
                $('#file-content').val('');  // Clear the textarea
            },
            error: function (xhr, status, error) {
                console.error('Error importing data:', status, error);
                showNotification('Error importing data.', 'error');
            }
        });
    });
});
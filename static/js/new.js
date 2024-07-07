$(document).ready(function() {
    console.log('Document ready');
    const ipSelect = $('#ip-address');
    const newIpModal = new bootstrap.Modal(document.getElementById('newIpModal'));

    $('#add-ip-btn').click(function() {
        console.log('Add IP button clicked');
        $('#new-ip').val('');
        $('#new-nickname').val('');
        newIpModal.show();
    });

    $('#save-new-ip').click(function() {
        console.log('Save new IP clicked');
        const newIp = $('#new-ip').val().trim();
        const newNickname = $('#new-nickname').val().trim();
        if (isValidIpAddress(newIp)) {
            console.log('New IP:', newIp, 'Nickname:', newNickname);
            const optionText = newIp + (newNickname ? ` (${newNickname})` : '');
            if ($(`#ip-address option[value="${newIp}"]`).length === 0) {
                ipSelect.append(new Option(optionText, newIp));
            }
            ipSelect.val(newIp);
            newIpModal.hide();
        } else {
            console.log('Invalid IP');
            alert('Please enter a valid IP address');
        }
    });

    $('#port-form').submit(function(e) {
        e.preventDefault();
        const ipAddress = ipSelect.val();
        const selectedOption = ipSelect.find('option:selected');
        const nickname = selectedOption.text().match(/\((.*?)\)/)?.[1] || '';
        if (!ipAddress) {
            alert('Please select or enter an IP address');
            return;
        }

        $.ajax({
            url: '/generate_port',
            method: 'POST',
            data: {
                ip_address: ipAddress,
                nickname: nickname,
                description: $('#description').val()
            },
            success: function(response) {
                console.log('Port generated successfully:', response);
                $('#result').html(`
                    <div class="alert alert-success" role="alert">
                        Generated URL: ${response.full_url}
                        <button class="btn btn-sm btn-secondary ms-2 copy-btn" data-url="${response.full_url}">Copy</button>
                    </div>
                `);
                $('.copy-btn').click(function() {
                    copyToClipboard($(this).data('url'));
                });
            },
            error: function(xhr, status, error) {
                console.error('Error generating port:', status, error);
                $('#result').html(`
                    <div class="alert alert-danger" role="alert">
                        Error: ${xhr.responseJSON ? xhr.responseJSON.error : 'Unknown error occurred'}
                    </div>
                `);
            }
        });
    });
});

function isValidIpAddress(ip) {
    const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (ipv4Regex.test(ip)) {
        const parts = ip.split('.');
        return parts.every(part => parseInt(part) >= 0 && parseInt(part) <= 255);
    }
    return false;
}

function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        // If the browser supports the Clipboard API and we're in a secure context
        navigator.clipboard.writeText(text).then(function() {
            console.log('Copied to clipboard:', text);
            alert('Copied to clipboard!');
        }, function(err) {
            console.error('Could not copy text: ', err);
            fallbackCopyTextToClipboard(text);
        });
    } else {
        // Fallback for browsers that don't support the Clipboard API or in non-secure contexts
        fallbackCopyTextToClipboard(text);
    }
}

function fallbackCopyTextToClipboard(text) {
    var textArea = document.createElement("textarea");
    textArea.value = text;
    
    // Avoid scrolling to bottom
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        var successful = document.execCommand('copy');
        var msg = successful ? 'successful' : 'unsuccessful';
        console.log('Fallback: Copying text command was ' + msg);
        alert('Copied to clipboard!');
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
        alert('Failed to copy to clipboard. Please copy manually.');
    }

    document.body.removeChild(textArea);
}
// js/core/ipManagement.js

import { showNotification } from '../ui/helpers.js';
import { editIp, deleteIp } from '../api/ajax.js';
import { editIpModal, addIpModal } from '../ui/modals.js';

let deleteIpAddress;

/**
 * Initialize event handlers for IP management.
 * Sets up click event listeners for editing, saving, and deleting IPs,
 * and modal event listeners for delete IP modal.
 */
export function init() {
    $(document).on('click', '.edit-ip', handleEditIpClick);
    $('#save-ip').click(handleSaveIpClick);
    $('#delete-ip').click(handleDeleteIpClick);
    $('#confirm-delete-ip').click(handleConfirmDeleteIpClick);
    $('#deleteIpModal').on('hidden.bs.modal', handleDeleteIpModalHidden);
    $('#add-ip-btn').click(handleAddIpClick);
    $('#save-new-ip').click(handleSaveNewIpClick);
}

/**
 * Handle click event on the edit IP button.
 * Populates and shows the edit IP modal with the current IP and nickname.
 *
 * @param {Event} e - The click event object
 */
function handleEditIpClick(e) {
    e.preventDefault();
    const ip = $(this).data('ip');
    const nickname = $(this).data('nickname');
    $('#old-ip').val(ip);
    $('#new-ip').val(ip);
    $('#new-nickname').val(nickname);
    editIpModal.show();
}

/**
 * Handle click event on the save IP button.
 * Sends an AJAX request to update the IP and updates the UI accordingly.
 */
function handleSaveIpClick() {
    const formData = $('#edit-ip-form').serialize();
    $.ajax({
        url: '/edit_ip',
        method: 'POST',
        data: formData,
        success: function (response) {
            if (response.success) {
                showNotification('IP updated successfully', 'success');
                updateIPLabel(formData);
            } else {
                showNotification('Error updating IP: ' + response.message, 'error');
            }
            editIpModal.hide();
        },
        error: function (xhr, status, error) {
            showNotification('Error updating IP: ' + error, 'error');
            editIpModal.hide();
        }
    });
}

/**
 * Update the IP label in the UI.
 * Modifies the IP and nickname data attributes and updates the displayed label.
 *
 * @param {string} formData - The serialized form data containing the IP information
 */
function updateIPLabel(formData) {
    const data = new URLSearchParams(formData);
    const oldIp = data.get('old_ip');
    const newIp = data.get('new_ip');
    const nickname = data.get('new_nickname');
    const editIpElement = $(`.edit-ip[data-ip="${oldIp}"]`);

    editIpElement.data('ip', newIp).data('nickname', nickname);
    editIpElement.attr('data-ip', newIp).attr('data-nickname', nickname);

    const switchLabel = editIpElement.closest('.switch-label');
    switchLabel.contents().first().replaceWith(newIp + (nickname ? ' (' + nickname + ')' : ''));
}

/**
 * Handle click event on the delete IP button.
 * Stores the IP address to be deleted and shows the delete IP modal.
 */
function handleDeleteIpClick() {
    deleteIpAddress = $('#old-ip').val();
    $('#delete-ip-address').text(deleteIpAddress);
    editIpModal.hide();
    $('#deleteIpModal').modal('show');
}

/**
 * Handle click event on the confirm delete IP button.
 * Sends an AJAX request to delete the IP and updates the UI accordingly.
 */
function handleConfirmDeleteIpClick() {
    $.ajax({
        url: '/delete_ip',
        method: 'POST',
        data: { ip: deleteIpAddress },
        success: function (response) {
            if (response.success) {
                showNotification('IP and all assigned ports deleted successfully', 'success');
                $(`.network-switch:has(.switch-label:contains("${deleteIpAddress}"))`).remove();
            } else {
                showNotification('Error deleting IP: ' + response.message, 'error');
            }
            $('#deleteIpModal').modal('hide');
        },
        error: function (xhr, status, error) {
            showNotification('Error deleting IP: ' + error, 'error');
            $('#deleteIpModal').modal('hide');
        }
    });
}

/**
 * Handle hidden event for the delete IP modal.
 * Resets the stored IP address to be deleted.
 */
function handleDeleteIpModalHidden() {
    deleteIpAddress = null;
}

/**
 * Handle click event on the "Add IP" button.
 * Shows the add IP modal.
 */
function handleAddIpClick() {
    // Reset form fields
    $('#add-ip').val('');
    $('#add-nickname').val('');
    addIpModal.show();
}

/**
 * Handle click event on the "Save New IP" button in the add IP modal.
 * Validates the IP address and sends an AJAX request to add the IP with a default port.
 */
function handleSaveNewIpClick() {
    const ip = $('#add-ip').val().trim();
    const nickname = $('#add-nickname').val().trim();

    if (!ip) {
        showNotification('Please enter an IP address', 'error');
        return;
    }

    // Validate IP address format (simple validation)
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$|^localhost$/;
    if (!ipRegex.test(ip)) {
        showNotification('Please enter a valid IP address', 'error');
        return;
    }

    // Send AJAX request to add the IP with a default port
    console.log('Sending AJAX request to add IP:', { ip: ip, nickname: nickname });

    $.ajax({
        url: '/add_ip',
        method: 'POST',
        data: {
            ip: ip,
            nickname: nickname,
            port_number: 1234,  // Fixed to match the UI message
            description: 'Generic',
            protocol: 'TCP'
        },
        success: function (response) {
            console.log('Add IP response:', response);
            if (response.success) {
                showNotification('IP added successfully with port 1234', 'success');
                location.reload(); // Reload the page to show the new IP
            } else {
                showNotification('Error adding IP: ' + response.message, 'error');
            }
            addIpModal.hide();
        },
        error: function (xhr, status, error) {
            console.error('AJAX error adding IP:', { xhr: xhr, status: status, error: error });
            console.error('Response text:', xhr.responseText);

            let errorMessage = 'Error adding IP: ' + error;
            if (xhr.responseJSON && xhr.responseJSON.message) {
                errorMessage = 'Error adding IP: ' + xhr.responseJSON.message;
            } else if (xhr.responseText) {
                try {
                    const errorData = JSON.parse(xhr.responseText);
                    if (errorData.message) {
                        errorMessage = 'Error adding IP: ' + errorData.message;
                    }
                } catch (e) {
                    // If response is not JSON, use the raw text
                    errorMessage = 'Error adding IP: ' + xhr.responseText;
                }
            }

            showNotification(errorMessage, 'error');
            addIpModal.hide();
        }
    });
}

/**
 * Update the order of IP panels and execute a callback function.
 * Sends an AJAX request to update the IP order on the server.
 *
 * @param {Function} callback - Function to be called after updating the order
 */
export function updateIPPanelOrder(callback) {
    const ipOrder = [];
    $('.network-switch').each(function () {
        ipOrder.push($(this).data('ip'));
    });

    console.log("Sending IP order:", ipOrder);

    $.ajax({
        url: '/update_ip_order',
        method: 'POST',
        data: JSON.stringify({ ip_order: ipOrder }),
        contentType: 'application/json',
        success: function (response) {
            if (response.success) {
                console.log('IP panel order updated successfully');
                if (typeof callback === 'function') {
                    callback();
                }
            } else {
                showNotification('Error updating IP panel order: ' + response.message, 'error');
                location.reload();
            }
        },
        error: function (xhr, status, error) {
            showNotification('Error updating IP panel order: ' + error, 'error');
            location.reload();
        }
    });
}

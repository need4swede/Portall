// js/core/ipManagement.js

import { showNotification } from '../ui/helpers.js';
import { editIp, deleteIp } from '../api/ajax/helpers.js';
import { editIpModal } from '../ui/modals.js';

let deleteIpAddress;

export function init() {
    $('.edit-ip').click(handleEditIpClick);
    $('#save-ip').click(handleSaveIpClick);
    $('#delete-ip').click(handleDeleteIpClick);
    $('#confirm-delete-ip').click(handleConfirmDeleteIpClick);
    $('#deleteIpModal').on('hidden.bs.modal', handleDeleteIpModalHidden);
}

function handleEditIpClick(e) {
    e.preventDefault();
    const ip = $(this).data('ip');
    const nickname = $(this).data('nickname');
    $('#old-ip').val(ip);
    $('#new-ip').val(ip);
    $('#new-nickname').val(nickname);
    editIpModal.show();
}

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

function handleDeleteIpClick() {
    deleteIpAddress = $('#old-ip').val();
    $('#delete-ip-address').text(deleteIpAddress);
    editIpModal.hide();
    $('#deleteIpModal').modal('show');
}

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

function handleDeleteIpModalHidden() {
    deleteIpAddress = null;
}

/**
 * Update the order of IP panels and execute a callback function.
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
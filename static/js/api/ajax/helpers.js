// js/api/ajax/helpers.js

import { showNotification } from '../../ui/helpers.js';
import { cancelDrop } from '../../utils/dragDropUtils.js';

/**
 * Moves a port from one IP to another
 * @param {number} portNumber - The port number being moved
 * @param {string} sourceIp - The source IP address
 * @param {string} targetIp - The target IP address
 * @param {HTMLElement} targetElement - The target element for insertion
 */
export function movePort(portNumber, sourceIp, targetIp, targetElement, draggingElement, updatePortOrder, cancelDropFn) {
    $.ajax({
        url: '/move_port',
        method: 'POST',
        data: {
            port_number: portNumber,
            source_ip: sourceIp,
            target_ip: targetIp
        },
        success: function (response) {
            if (response.success) {
                // Update port order for both source and target IPs
                updatePortOrder(sourceIp);
                if (sourceIp !== targetIp) {
                    updatePortOrder(targetIp);
                }
            } else {
                showNotification('Error moving port: ' + response.message, 'error');
                cancelDropFn();
            }
        },
        error: function (xhr, status, error) {
            showNotification('Error moving port: ' + error, 'error');
            cancelDropFn();
        }
    });
}

export function editIp(formData) {
    $.ajax({
        url: '/edit_ip',
        method: 'POST',
        data: formData,
        success: function (response) {
            if (response.success) {
                showNotification('IP updated successfully', 'success');
                // Update the DOM dynamically
                const oldIp = $('#old-ip').val();
                const newIp = $('#new-ip').val();
                const nickname = $('#new-nickname').val();
                const editIpElement = $(`.edit-ip[data-ip="${oldIp}"]`);

                // Update the data attributes of the edit button
                editIpElement.data('ip', newIp).data('nickname', nickname);
                editIpElement.attr('data-ip', newIp).attr('data-nickname', nickname);

                // Update the IP label
                const switchLabel = editIpElement.closest('.switch-label');
                switchLabel.contents().first().replaceWith(newIp + (nickname ? ' (' + nickname + ')' : ''));
            } else {
                showNotification('Error updating IP: ' + response.message, 'error');
            }
            $('#editIpModal').modal('hide');
        },
        error: function (xhr, status, error) {
            showNotification('Error updating IP: ' + error, 'error');
            $('#editIpModal').modal('hide');
        }
    });
}

export function deleteIp(ip) {
    $.ajax({
        url: '/delete_ip',
        method: 'POST',
        data: { ip: ip },
        success: function (response) {
            if (response.success) {
                showNotification('IP and all assigned ports deleted successfully', 'success');
                // Remove the IP panel from the DOM
                $(`.network-switch:has(.switch-label:contains("${ip}"))`).remove();
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

export function editPort(formData) {
    $.ajax({
        url: '/edit_port',
        method: 'POST',
        data: formData,
        success: function (response) {
            if (response.success) {
                showNotification('Port updated successfully', 'success');
                // Update the DOM dynamically
                const ip = $('#edit-port-ip').val();
                const oldPortNumber = $('#old-port-number').val();
                const newPortNumber = $('#new-port-number').val();
                const description = $('#port-description').val();
                const portElement = $(`.port[data-ip="${ip}"][data-port="${oldPortNumber}"]`);
                portElement.data('port', newPortNumber).data('description', description);
                portElement.attr('data-port', newPortNumber).attr('data-description', description);
                portElement.find('.port-number').text(newPortNumber);
                portElement.find('.port-description').text(description);

                // Refresh the page to ensure all data is correctly displayed
                location.reload();
            } else {
                showNotification('Error updating port: ' + response.message, 'error');
            }
            $('#editPortModal').modal('hide');
        },
        error: function (xhr, status, error) {
            showNotification('Error updating port: ' + error, 'error');
            $('#editPortModal').modal('hide');
        }
    });
}

export function addPort(formData) {
    $.ajax({
        url: '/add_port',
        method: 'POST',
        data: formData,
        success: function (response) {
            if (response.success) {
                showNotification('Port added successfully', 'success');
                location.reload();
            } else {
                showNotification('Error adding port: ' + response.message, 'error');
            }
            $('#addPortModal').modal('hide');
        },
        error: function (xhr, status, error) {
            showNotification('Error adding port: ' + error, 'error');
            $('#addPortModal').modal('hide');
        }
    });
}

export function deletePort(ip, portNumber) {
    $.ajax({
        url: '/delete_port',
        method: 'POST',
        data: { ip: ip, port_number: portNumber },
        success: function (response) {
            if (response.success) {
                showNotification('Port deleted successfully', 'success');
                // Remove the port from the DOM
                $(`.port[data-ip="${ip}"][data-port="${portNumber}"]`).parent().remove();
            } else {
                showNotification('Error deleting port: ' + response.message, 'error');
            }
            $('#deletePortModal').modal('hide');
        },
        error: function (xhr, status, error) {
            showNotification('Error deleting port: ' + error, 'error');
            $('#deletePortModal').modal('hide');
        }
    });
}
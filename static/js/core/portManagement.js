// js/core/portManagement.js

import { showNotification } from '../ui/helpers.js';
import { editPortModal, addPortModal, deletePortModal } from '../ui/modals.js';

let deleteIp, deletePortNumber;
let originalPortNumber;
let originalPortId;

export function init() {
    handlePortNumberInput(true);  // For edit
    handlePortNumberInput(false); // For add
    $('.add-port').click(handleAddPortClick);
    $('#save-port').click(handleSavePortClick);
    $('#save-new-port').click(handleSaveNewPortClick);
    $('#delete-port').click(handleDeletePortClick);
    $('#confirm-delete-port').click(handleConfirmDeletePortClick);
    $('#deletePortModal').on('hidden.bs.modal', handleDeletePortModalHidden);
    $('#new-port-number').on('input', handleNewPortNumberInput);
    $('#add-new-port-number').on('input', handleAddNewPortNumberInput);
}

export function handlePortClick(element) {
    const port = $(element).find('.port');
    const ip = port.data('ip');
    const portNumber = port.data('port');
    const description = port.data('description');
    const portId = port.data('id');

    console.log("Port clicked - ID:", portId);

    // Store the original port number and ID
    originalPortNumber = portNumber;
    originalPortId = portId;

    // Populate the edit port modal
    $('#edit-port-ip').val(ip);
    $('#display-edit-port-ip').text(ip);
    $('#old-port-number').val(portNumber);
    $('#new-port-number').val(portNumber);
    $('#port-description').val(description);
    $('#port-id').val(portId);

    // Disable delete button if it's the last port in the panel
    const isLastPort = $(element).siblings('.port-slot:not(.add-port-slot)').length === 0;
    $('#delete-port').prop('disabled', isLastPort);
    if (isLastPort) {
        $('#delete-port').attr('title', "Can't delete the last port in a panel");
    } else {
        $('#delete-port').removeAttr('title');
    }

    // Clear any existing messages
    $('#edit-port-exists-disclaimer').hide();
    $('#save-port').prop('disabled', false);

    editPortModal.show();
}

function handlePortNumberInput(isEdit) {
    const inputSelector = isEdit ? '#new-port-number' : '#add-new-port-number';
    const ipSelector = isEdit ? '#edit-port-ip' : '#add-port-ip';
    const disclaimerSelector = isEdit ? '#edit-port-exists-disclaimer' : '#port-exists-disclaimer';
    const saveButtonSelector = isEdit ? '#save-port' : '#save-new-port';

    $(inputSelector).on('input', function () {
        console.log("Port number input changed. New value:", this.value);
        const ip = $(ipSelector).val();
        const portNumber = $(this).val().trim();
        const currentPortId = isEdit ? $('#port-id').val() : null;
        const oldPortNumber = isEdit ? $('#old-port-number').val() : null;

        if (portNumber === '') {
            $(disclaimerSelector).hide();
            $(saveButtonSelector).prop('disabled', true);
            return;
        }

        if (isEdit && portNumber === oldPortNumber) {
            $(disclaimerSelector).hide();
            $(saveButtonSelector).prop('disabled', false);
            return;
        }

        const portExists = checkPortExists(ip, portNumber, currentPortId);

        if (portExists) {
            const description = $(`.port[data-ip="${ip}"][data-port="${portNumber}"]`).data('description');
            $(disclaimerSelector).text(`Port ${portNumber} already assigned to ${description}`).show();
            $(saveButtonSelector).prop('disabled', true);
        } else {
            $(disclaimerSelector).hide();
            $(saveButtonSelector).prop('disabled', false);
        }
    });
}

function checkPortExists(ip, portNumber, currentPortId) {
    console.log("Checking if port exists:", ip, portNumber, currentPortId);
    const portElement = $(`.port[data-ip="${ip}"][data-port="${portNumber}"]`);
    console.log("Port element found:", portElement.length > 0);
    console.log("Port element data-id:", portElement.data('id'));
    if (currentPortId) {
        const result = portElement.length > 0 && portElement.data('id') != currentPortId;
        console.log("Check result:", result);
        return result;
    }
    return portElement.length > 0;
}

export function updatePortOrder(ip) {
    const panel = $(`.switch-panel[data-ip="${ip}"]`);
    const portOrder = panel.find('.port-slot:not(.add-port-slot) .port').map(function () {
        return $(this).data('port');
    }).get();

    $.ajax({
        url: '/update_port_order',
        method: 'POST',
        data: JSON.stringify({
            ip: ip,
            port_order: portOrder
        }),
        contentType: 'application/json',
        success: function (response) {
            if (response.success) {
                console.log('Port order updated successfully');
            } else {
                console.error('Error updating port order:', response.message);
                showNotification('Error updating port order: ' + response.message, 'error');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error updating port order:', error);
            showNotification('Error updating port order: ' + error, 'error');
        }
    });
}

function handleAddPortClick() {
    const ip = $(this).data('ip');
    $('#add-port-ip').val(ip);
    $('#display-add-port-ip').text(ip);
    $('#add-new-port-number').val('');
    $('#add-port-description').val('');
    $('#port-exists-disclaimer').hide();
    $('#save-new-port').prop('disabled', false);
    addPortModal.show();
}

function handleSavePortClick() {
    console.log("Save port button clicked");
    const ip = $('#edit-port-ip').val();
    const portNumber = $('#new-port-number').val().trim();
    const description = $('#port-description').val().trim();
    const currentPortId = $('#port-id').val();

    console.log("IP:", ip);
    console.log("Port Number:", portNumber);
    console.log("Description:", description);

    if (portNumber === '') {
        console.log("Port number is empty");
        showNotification('Please enter a port number', 'error');
        return;
    }

    if (description === '') {
        console.log("Description is empty");
        showNotification('Please enter a port description', 'error');
        return;
    }

    if (checkPortExists(ip, portNumber, currentPortId)) {
        console.log("Port already exists");
        showNotification('Port already exists', 'error');
        return;
    }

    console.log("All checks passed, proceeding with AJAX call");
    const formData = $('#edit-port-form').serialize();
    console.log("Form data:", formData);

    $.ajax({
        url: '/edit_port',
        method: 'POST',
        data: formData,
        success: function (response) {
            if (response.success) {
                showNotification('Port updated successfully', 'success');
                const oldPortNumber = $('#old-port-number').val();
                const portElement = $(`.port[data-ip="${ip}"][data-port="${oldPortNumber}"]`);
                portElement.data('port', portNumber).data('description', description);
                portElement.attr('data-port', portNumber).attr('data-description', description);
                portElement.find('.port-number').text(portNumber);
                portElement.find('.port-description').text(description);
                location.reload();
            } else {
                showNotification('Error updating port: ' + response.message, 'error');
            }
            editPortModal.hide();
        },
        error: function (xhr, status, error) {
            showNotification('Error updating port: ' + error, 'error');
            editPortModal.hide();
        }
    });
}

function handleSaveNewPortClick() {
    console.log("Save new port button clicked");

    const ip = $('#add-port-ip').val();
    const portNumber = $('#add-new-port-number').val().trim();
    const description = $('#add-port-description').val().trim();

    console.log("IP:", ip);
    console.log("Port Number:", portNumber);
    console.log("Description:", description);

    if (portNumber === '') {
        console.log("Port number is empty");
        showNotification('Please enter a port number', 'error');
        return;
    }

    if (description === '') {
        console.log("Description is empty");
        showNotification('Please enter a port description', 'error');
        return;
    }

    if (checkPortExists(ip, portNumber)) {
        console.log("Port already exists");
        showNotification('Port already exists', 'error');
        return;
    }

    console.log("All checks passed, proceeding with AJAX call");

    const formData = $('#add-port-form').serialize();
    console.log("Form data:", formData);

    $.ajax({
        url: '/add_port',
        method: 'POST',
        data: formData,
        success: function (response) {
            console.log("AJAX success:", response);
            if (response.success) {
                showNotification('Port added successfully', 'success');
                location.reload();
            } else {
                showNotification('Error adding port: ' + response.message, 'error');
            }
            addPortModal.hide();
        },
        error: function (xhr, status, error) {
            console.log("AJAX error:", status, error);
            showNotification('Error adding port: ' + error, 'error');
            addPortModal.hide();
        }
    });
}

function handleDeletePortClick() {
    deleteIp = $('#edit-port-ip').val();
    deletePortNumber = $('#old-port-number').val();
    editPortModal.hide();
    deletePortModal.show();
}

function handleConfirmDeletePortClick() {
    $.ajax({
        url: '/delete_port',
        method: 'POST',
        data: { ip: deleteIp, port_number: deletePortNumber },
        success: function (response) {
            if (response.success) {
                showNotification('Port deleted successfully', 'success');
                $(`.port[data-ip="${deleteIp}"][data-port="${deletePortNumber}"]`).parent().remove();
            } else {
                showNotification('Error deleting port: ' + response.message, 'error');
            }
            deletePortModal.hide();
        },
        error: function (xhr, status, error) {
            showNotification('Error deleting port: ' + error, 'error');
            deletePortModal.hide();
        }
    });
}

function handleDeletePortModalHidden() {
    deleteIp = null;
    deletePortNumber = null;
}

function handleNewPortNumberInput() {
    const ip = $('#edit-port-ip').val();
    const portNumber = $(this).val().trim();
    const currentPortId = $('#port-id').val();

    console.log('Input event triggered');
    console.log('IP:', ip);
    console.log('Port Number:', portNumber);
    console.log('Original Port Number:', originalPortNumber);
    console.log('Current Port ID:', currentPortId);

    if (portNumber === '') {
        console.log('Port number is empty');
        $('#edit-port-exists-disclaimer').hide();
        $('#save-port').prop('disabled', true);
        return;
    }

    if (portNumber === originalPortNumber) {
        console.log('Port number is the same as original');
        $('#edit-port-exists-disclaimer').hide();
        $('#save-port').prop('disabled', false);
        return;
    }

    const portExists = checkPortExists(ip, portNumber, currentPortId);
    console.log('Port exists:', portExists);

    if (portExists) {
        const existingPortDescription = $(`.port[data-ip="${ip}"][data-port="${portNumber}"]:not([data-id="${currentPortId}"])`).data('description');
        console.log('Existing port description:', existingPortDescription);
        $('#edit-port-exists-disclaimer').text(`Port ${portNumber} already assigned to ${existingPortDescription}`).show();
        $('#save-port').prop('disabled', true);
    } else {
        $('#edit-port-exists-disclaimer').hide();
        $('#save-port').prop('disabled', false);
    }
}

function handleAddNewPortNumberInput() {
    console.log("Port number input changed. New value:", this.value);
    const ip = $('#add-port-ip').val();
    const portNumber = $(this).val().trim();

    if (portNumber === '') {
        $('#port-exists-disclaimer').hide();
        $('#save-new-port').prop('disabled', true);
        return;
    }

    const portExists = checkPortExists(ip, portNumber);

    if (portExists) {
        const description = $(`.port[data-ip="${ip}"][data-port="${portNumber}"]`).data('description');
        $('#port-exists-disclaimer').text(`Port ${portNumber} already assigned to ${description}`).show();
        $('#save-new-port').prop('disabled', true);
    } else {
        $('#port-exists-disclaimer').hide();
        $('#save-new-port').prop('disabled', false);
    }
}
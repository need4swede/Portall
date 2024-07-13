// js/core/portManagement.js

import { showNotification } from '../ui/helpers.js';
import { editPortModal, addPortModal, deletePortModal } from '../ui/modals.js';
import { updatePortOrder as updatePortOrderAjax } from '../api/ajax.js';

/**
 * The IP address of the port to be deleted.
 * @type {string}
 */
let deleteIp;

/**
 * The port number to be deleted.
 * @type {string}
 */
let deletePortNumber;

/**
 * The original port number before editing.
 * @type {string}
 */
let originalPortNumber;

/**
 * The ID of the original port before editing.
 * @type {string}
 */
let originalPortId;

/**
 * The protocol of the original port before editing.
 * @type {string}
 */
let originalProtocol;

/**
 * The current sort type being used.
 * @type {string|null}
 */
let currentSortType = null;

/**
 * The current sort order being used.
 * @type {string|null}
 */
let currentSortOrder = null;


/**
 * Initialize event handlers for port management.
 * Sets up event listeners for port number inputs, and handles add, save, and delete port actions.
 */
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
    $('#add-port-protocol').on('change', handleAddNewPortNumberInput);
    $('#port-protocol').on('change', handleNewPortNumberInput);
    $('#new-port-number').on('input', handleNewPortNumberInput);
    $('#port-protocol').on('change', handleProtocolChange);
    initSortButtons();
}

/**
 * Initialize event handlers for sort buttons.
 * Sets up click event listeners on elements with the class 'sort-btn'.
 */
function initSortButtons() {
    $('.sort-btn').on('click', handleSortButtonClick);
}

/**
 * Handle click event on a sort button.
 * Toggles the sort order or resets it if clicking a different sort type,
 * updates button icons, sorts the ports, and updates the port order in the database.
 *
 * @param {Event} e - The click event object
 */
function handleSortButtonClick(e) {
    const $button = $(e.currentTarget);
    const sortType = $button.data('sort');
    const ip = $button.data('ip');
    const $panel = $button.closest('.network-switch').find('.switch-panel');

    // Toggle sort order or reset if clicking a different sort type
    if (sortType === currentSortType) {
        currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortType = sortType;
        currentSortOrder = 'asc';
    }

    // Update all button icons
    $('.sort-btn').each(function () {
        const $btn = $(this);
        const $icon = $btn.find('i:last-child');
        if ($btn.data('sort') === sortType) {
            $icon.removeClass('fa-sort fa-sort-up fa-sort-down')
                .addClass(currentSortOrder === 'asc' ? 'fa-sort-up' : 'fa-sort-down')
                .show();
        } else {
            $icon.removeClass('fa-sort-up fa-sort-down').addClass('fa-sort').hide();
        }
    });

    // Sort the ports
    const $ports = $panel.find('.port-slot:not(.add-port-slot)').detach().sort((a, b) => {
        const aValue = getSortValue($(a), sortType);
        const bValue = getSortValue($(b), sortType);
        return currentSortOrder === 'asc' ? aValue - bValue : bValue - aValue;
    });

    // Reattach sorted ports
    $panel.prepend($ports);

    // Update port order in the database
    updatePortOrder(ip);
}

/**
 * Get the value to sort by for a given port element and sort type.
 * Retrieves the relevant data attribute based on the sort type.
 *
 * @param {jQuery} $el - The jQuery element representing the port slot
 * @param {string} sortType - The type of sorting ('port' or 'protocol')
 * @returns {number} - The value to sort by
 */
function getSortValue($el, sortType) {
    const $port = $el.find('.port');
    if (sortType === 'port') {
        return parseInt($port.data('port'), 10);
    } else if (sortType === 'protocol') {
        return $port.data('protocol') === 'TCP' ? 0 : 1;
    }
}

/**
 * Handle click event on a port element.
 * Populates and displays the edit port modal with the port's details.
 *
 * @param {HTMLElement} element - The clicked port element
 */
export function handlePortClick(element) {
    const port = $(element).find('.port');
    const ip = port.data('ip');
    const portNumber = port.data('port');
    const description = port.data('description');
    const portId = port.data('id');
    const protocol = port.data('protocol');

    console.log("Port clicked - ID:", portId);

    // Store the original port number and ID
    originalPortNumber = portNumber;
    originalPortId = portId;
    originalProtocol = protocol;

    // Populate the edit port modal
    $('#edit-port-ip').val(ip);
    $('#display-edit-port-ip').text(ip);
    $('#old-port-number').val(portNumber);
    $('#new-port-number').val(portNumber);
    $('#port-description').val(description);
    $('#port-protocol').val(protocol);
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

/**
 * Check if a port number already exists for a given IP address.
 * Validates the existence of the port number and handles current port ID if provided.
 *
 * @param {string} ip - The IP address to check
 * @param {string} portNumber - The port number to check
 * @param {string|null} currentPortId - The current port ID to exclude from the check
 * @returns {boolean} - True if the port exists, false otherwise
 */
export function checkPortExists(ip, portNumber, protocol, currentPortId) {
    console.log("Checking if port exists:", ip, portNumber, protocol, currentPortId);
    const portElement = $(`.port[data-ip="${ip}"][data-port="${portNumber}"][data-protocol="${protocol}"]`);
    console.log("Port element found:", portElement.length > 0);
    console.log("Port element data-id:", portElement.data('id'));
    if (currentPortId) {
        const result = portElement.length > 0 && portElement.data('id') != currentPortId;
        console.log("Check result:", result);
        return result;
    }
    return portElement.length > 0;
}

/**
 * Update the order of ports for a specific IP address.
 * Sends an AJAX request to update the port order on the server.
 *
 * @param {string} ip - The IP address for which to update the port order
 */
export function updatePortOrder(ip) {
    const panel = $(`.switch-panel[data-ip="${ip}"]`);
    const portOrder = panel.find('.port-slot:not(.add-port-slot) .port').map(function () {
        return $(this).data('port');
    }).get();

    updatePortOrderAjax(ip, portOrder);
}

/**
 * Verify port data in the frontend
 * This function logs all port data currently displayed in the frontend
 */
export function verifyPortData() {
    console.log("Verifying frontend port data:");
    $('.port').each(function () {
        const $port = $(this);
        console.log(`Port: ${$port.data('port')}, IP: ${$port.data('ip')}, Protocol: ${$port.data('protocol')}, Description: ${$port.data('description')}`);
    });
}

/**
 * Check for port conflicts when editing a port.
 * Validates the new port number and protocol, checks for existing conflicts,
 * and updates the disclaimer and save button states accordingly.
 */
function checkPortConflict() {
    const ip = $('#edit-port-ip').val();
    const portNumber = $('#new-port-number').val().trim();
    const currentPortId = $('#port-id').val();
    const protocol = $('#port-protocol').val();

    console.log('Checking port conflict');
    console.log('IP:', ip);
    console.log('Port Number:', portNumber);
    console.log('Current Port ID:', currentPortId);
    console.log('Protocol:', protocol);

    if (portNumber === '') {
        console.log('Port number is empty');
        $('#edit-port-exists-disclaimer').hide();
        $('#save-port').prop('disabled', true);
        return;
    }

    if (portNumber === originalPortNumber && protocol === originalProtocol) {
        console.log('Port number and protocol are the same as original');
        $('#edit-port-exists-disclaimer').hide();
        $('#save-port').prop('disabled', false);
        return;
    }

    const portExists = checkPortExists(ip, portNumber, protocol, currentPortId);
    console.log('Port exists:', portExists);

    if (portExists) {
        const existingPortDescription = $(`.port[data-ip="${ip}"][data-port="${portNumber}"][data-protocol="${protocol}"]:not([data-id="${currentPortId}"])`).data('description');
        console.log('Existing port description:', existingPortDescription);
        $('#edit-port-exists-disclaimer').text(`Port ${portNumber} is already assigned to ${existingPortDescription}`).show();
        $('#save-port').prop('disabled', true);
    } else {
        $('#edit-port-exists-disclaimer').hide();
        $('#save-port').prop('disabled', false);
    }
}

/**
 * Handle input event on port number fields.
 * Validates the port number input, checks for port existence,
 * and updates the disclaimer and save button states accordingly.
 *
 * @param {boolean} isEdit - Indicates if the input is for editing an existing port
 */
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

/**
 * Handle click event on the "Add Port" button.
 * Populates the add port modal with the IP address and resets the input fields.
 */
function handleAddPortClick() {
    const ip = $(this).data('ip');
    const $networkSwitch = $(this).closest('.network-switch');
    const ipNickname = $networkSwitch.find('.switch-label').text().trim().match(/\((.*?)\)/)?.[1] || '';
    $('#add-port-ip').val(ip);
    $('#display-add-port-ip').text(ip);
    $('#add-port-ip-nickname').val(ipNickname);
    $('#add-new-port-number').val('');
    $('#add-port-description').val('');
    $('#add-port-protocol').val('TCP');  // Reset to TCP by default
    $('#port-exists-disclaimer').hide();
    $('#save-new-port').prop('disabled', false);
    addPortModal.show();
}

/**
 * Handle click event on the "Save Port" button in the edit port modal.
 * Validates the port details, checks for port existence, and sends an AJAX request to update the port.
 */
function handleSavePortClick() {
    console.log("Save port button clicked");
    const ip = $('#edit-port-ip').val();
    const ipNickname = $('#add-port-ip-nickname').val();
    const portNumber = $('#new-port-number').val().trim();
    const description = $('#port-description').val().trim();
    const currentPortId = $('#port-id').val();
    const protocol = $('#port-protocol').val();

    console.log("IP:", ip);
    console.log("IP Nickname:", ipNickname);
    console.log("Port Number:", portNumber);
    console.log("Description:", description);
    console.log("Protocol:", protocol);

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

    if (checkPortExists(ip, portNumber, protocol, currentPortId)) {
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

/**
 * Handle click event on the "Save New Port" button in the add port modal.
 * Validates the new port details, checks for port existence, and sends an AJAX request to add the port.
 */
function handleSaveNewPortClick() {
    console.log("Save new port button clicked");

    const ip = $('#add-port-ip').val();
    const portNumber = $('#add-new-port-number').val().trim();
    const description = $('#add-port-description').val().trim();
    const protocol = $('#add-port-protocol').val(); // Add this line to get the protocol

    console.log("IP:", ip);
    console.log("Port Number:", portNumber);
    console.log("Description:", description);
    console.log("Protocol:", protocol); // Log the protocol

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

    if (checkPortExists(ip, portNumber, protocol)) { // Include protocol in the check
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

                // Create the new port element
                const newPortElement = `
                <div class="port-slot" draggable="true" data-port="${portNumber}" data-order="${response.order}">
                    <div class="port active" data-ip="${ip}" data-port="${portNumber}" data-description="${description}"
                        data-order="${response.order}" data-id="${response.id}" data-protocol="${protocol}">
                        <span class="port-number">${portNumber}</span>
                        <span class="port-description">${description}</span>
                        <div class="port-tooltip">${description}</div>
                    </div>
                    <p class="port-protocol">${protocol}</p>
                </div>
                `;

                // Insert the new port element before the add-port-slot
                $(`.switch-panel[data-ip="${ip}"] .add-port-slot`).before(newPortElement);

                // Optionally, update the order of other ports if necessary
                updatePortOrder(ip);
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

/**
 * Handle click event on the "Delete Port" button.
 * Stores the IP address and port number for deletion and shows the delete port modal.
 */
function handleDeletePortClick() {
    deleteIp = $('#edit-port-ip').val();
    deletePortNumber = $('#old-port-number').val();
    editPortModal.hide();
    deletePortModal.show();
}

/**
 * Handle click event on the "Confirm Delete Port" button in the delete port modal.
 * Sends an AJAX request to delete the port and updates the UI accordingly.
 */
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

/**
 * Handle the hidden event for the delete port modal.
 * Resets the stored IP address and port number for deletion.
 */
function handleDeletePortModalHidden() {
    deleteIp = null;
    deletePortNumber = null;
}

/**
 * Handle input event on the new port number field in the edit port modal.
 * Validates the new port number, checks for port existence, and updates the disclaimer and save button states.
 */
function handleNewPortNumberInput() {
    checkPortConflict();
}

function handleProtocolChange() {
    checkPortConflict();
}

/**
 * Handle input event on the new port number field in the add port modal.
 * Validates the new port number, checks for port existence, and updates the disclaimer and save button states.
 */
function handleAddNewPortNumberInput() {
    console.log("Port number input changed. New value:", this.value);
    const ip = $('#add-port-ip').val();
    const portNumber = $(this).val().trim();
    const protocol = $('#add-port-protocol').val();  // Get the selected protocol

    console.log("IP:", ip);
    console.log("Port Number:", portNumber);
    console.log("Protocol:", protocol);  // Log the protocol for debugging

    if (portNumber === '') {
        $('#port-exists-disclaimer').hide();
        $('#save-new-port').prop('disabled', true);
        return;
    }

    const portExists = checkPortExists(ip, portNumber, protocol);  // Pass protocol to checkPortExists

    if (portExists) {
        const description = $(`.port[data-ip="${ip}"][data-port="${portNumber}"][data-protocol="${protocol}"]`).data('description');
        $('#port-exists-disclaimer').text(`Port ${portNumber} (${protocol}) already assigned to ${description}`).show();
        $('#save-new-port').prop('disabled', true);
    } else {
        $('#port-exists-disclaimer').hide();
        $('#save-new-port').prop('disabled', false);
    }
}
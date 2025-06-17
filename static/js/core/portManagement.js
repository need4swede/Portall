// js/core/portManagement.js

import { showNotification } from '../ui/helpers.js';
import { editPortModal, addPortModal, deletePortModal } from '../ui/modals.js';
import { updatePortOrder as updatePortOrderAjax } from '../api/ajax.js';
import { showLoadingAnimation, hideLoadingAnimation } from '../ui/loadingAnimation.js';

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
 * Cached app presets data from apps.json
 * @type {Array|null}
 */
let appPresets = null;

/**
 * Flag to track if a port scan has been completed in the current session
 * @type {boolean}
 */
let scanCompletedInSession = false;


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
    $('#generate-port').click(handleGeneratePortClick);
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
    initPortHoverEvents();
    initAppPresets();
    initPortScanning();
    $(document).off('click', '.copy-btn').on('click', '.copy-btn', function () {
        const url = $(this).data('url');
        console.log("Copy button clicked with URL:", url);
        copyToClipboard(url);
    });
}


/**
 * Initialize port hover events for tooltips.
 * The enhanced tooltip system is now initialized in main.js,
 * so we just need to add any port-specific tooltip behavior here.
 */
function initPortHoverEvents() {
    console.log('Enhanced tooltip system loaded for ports');

    // Add port-specific tooltip behavior if needed
    // The main tooltip functionality is now handled by the enhanced tooltip system
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

        // Use appropriate comparison based on value type
        if (typeof aValue === 'string' && typeof bValue === 'string') {
            // String comparison using localeCompare for proper alphabetical sorting
            return currentSortOrder === 'asc'
                ? aValue.localeCompare(bValue)
                : bValue.localeCompare(aValue);
        } else {
            // Numeric comparison for numbers
            return currentSortOrder === 'asc' ? aValue - bValue : bValue - aValue;
        }
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
 * @param {string} sortType - The type of sorting ('port', 'protocol', or 'description')
 * @returns {number|string} - The value to sort by
 */
function getSortValue($el, sortType) {
    const $port = $el.find('.port');
    if (sortType === 'port') {
        return parseInt($port.data('port'), 10);
    } else if (sortType === 'protocol') {
        return $port.data('protocol') === 'TCP' ? 0 : 1;
    } else if (sortType === 'description') {
        return $port.data('description').toLowerCase(); // Case-insensitive sorting
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

    // Add a subtle animation to the port when clicked
    port.addClass('clicked');
    setTimeout(() => {
        port.removeClass('clicked');
    }, 300);

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

    // Check if this port is immutable (imported from Docker integrations)
    // Get the immutable attribute and convert it to a boolean
    const immutableAttr = port.attr('data-immutable');
    console.log("Immutable attribute:", immutableAttr);
    const isImmutable = (immutableAttr === 'true' || immutableAttr === true);
    console.log("Is immutable:", isImmutable);

    // Disable port number and protocol fields for immutable ports
    $('#new-port-number').prop('disabled', isImmutable);
    $('#port-protocol').prop('disabled', isImmutable);

    // Show/hide visual cues for immutable fields
    $('.immutable-field-icon').toggle(isImmutable);
    $('.immutable-field-note').toggle(isImmutable);
    $('#docker-port-note').toggle(isImmutable);

    // Disable delete button for immutable ports
    if (isImmutable) {
        $('#delete-port').prop('disabled', true);
        $('#delete-port').attr('title', "Docker integration ports cannot be deleted");
    } else {
        // Disable delete button if it's the last port in the panel
        const isLastPort = $(element).siblings('.port-slot:not(.add-port-slot)').length === 0;
        $('#delete-port').prop('disabled', isLastPort);
        if (isLastPort) {
            $('#delete-port').attr('title', "Can't delete the last port in a panel");
        } else {
            $('#delete-port').removeAttr('title');
        }
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

    $('#addPortModal').one('shown.bs.modal', function () {
        $('#add-port-description').focus();
    });
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

                // Create the new port element with enhanced tooltip
                const newPortElement = `
                <div class="port-slot active" draggable="true" data-port="${portNumber}" data-order="${response.order}">
                    <div class="port active" data-ip="${ip}" data-port="${portNumber}" data-description="${description}"
                        data-order="${response.order}" data-id="${response.id}" data-protocol="${protocol}">
                        <span class="port-number">${portNumber}</span>
                        <span class="port-description">${description}</span>
                        <div class="port-tooltip">
                            <div class="tooltip-header">
                                <span class="tooltip-title">Port ${portNumber}</span>
                                <span class="tooltip-protocol ${protocol.toLowerCase()}">${protocol}</span>
                            </div>
                            <div class="tooltip-content">
                                <div class="tooltip-label">Description</div>
                                <div class="tooltip-value">${description}</div>

                                <div class="tooltip-label">IP Address</div>
                                <div class="tooltip-value">${ip}</div>
                            </div>
                            <div class="tooltip-footer">
                                <span>Click to edit</span>
                                <span>ID: ${response.id}</span>
                            </div>
                        </div>
                    </div>
                    <p class="port-protocol ${protocol.toLowerCase()}">${protocol}</p>
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
 * Handle click event on the "Generate" button in the add port modal.
 * Collects the necessary data and sends an AJAX request to generate a port.
 * The generated port will follow the rules set in the port generation settings.
 */
function handleGeneratePortClick() {
    console.log("Generate port button clicked");

    const ip = $('#add-port-ip').val();
    const nickname = $('#add-port-ip-nickname').val();
    const description = $('#add-port-description').val().trim();
    const protocol = $('#add-port-protocol').val();

    console.log("IP:", ip);
    console.log("Nickname:", nickname);
    console.log("Description:", description);
    console.log("Protocol:", protocol);

    if (description === '') {
        console.log("Description is empty");
        showNotification('Please enter a port description', 'error');
        return;
    }

    // Create the form data for the generate port number request
    // Only include ip_address and protocol, not description or nickname
    // to ensure we're only generating a port number, not adding it
    const formData = {
        ip_address: ip,
        protocol: protocol
    };

    // Create a result container if it doesn't exist
    if ($('#port-generation-result').length === 0) {
        $('#add-port-form').after('<div id="port-generation-result" class="mt-3"></div>');
    }

    // Clear any previous results
    $('#port-generation-result').empty();

    // Import the generatePortNumber function from ajax.js
    import('../api/ajax.js').then(module => {
        // Use the new generatePortNumber function that only generates a port number without adding it
        module.generatePortNumber(formData);

        // Set up a MutationObserver to watch for changes to the result div
        const resultObserver = new MutationObserver((mutations) => {
            // Check if the result div has been updated with a success message
            if ($('#result .alert-success').length > 0) {
                // Extract the port number from the generated URL
                const fullUrl = $('#result .alert-success').text();
                const portMatch = fullUrl.match(/:(\d+)/);

                if (portMatch && portMatch[1]) {
                    const generatedPort = portMatch[1];

                    // Update the port number field
                    $('#add-new-port-number').val(generatedPort);
                    $('#save-new-port').prop('disabled', false);

                    // Clear the original result
                    $('#result').empty();
                }
            } else if ($('#result .alert-danger').length > 0) {
                // Copy error message to the modal
                const errorMsg = $('#result .alert-danger').text();
                $('#port-generation-result').html(`
                    <div class="alert alert-danger" role="alert">
                        ${errorMsg}
                    </div>
                `);

                // Clear the original result
                $('#result').empty();
            }
        });

        // Start observing the result div
        if (document.getElementById('result')) {
            resultObserver.observe(document.getElementById('result'), { childList: true, subtree: true });
        } else {
            // If the result div doesn't exist, create it
            $('body').append('<div id="result" style="display:none;"></div>');
            resultObserver.observe(document.getElementById('result'), { childList: true, subtree: true });
        }
    });
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

/**
 * Initialize app presets functionality.
 * Loads the app presets data and sets up event handlers for the presets dropdown.
 */
function initAppPresets() {
    console.log('Initializing app presets...');

    // Load app presets when the modal is shown
    $('#addPortModal').on('shown.bs.modal', function () {
        console.log('Add port modal shown, checking if presets need to be loaded...');
        if (!appPresets) {
            console.log('Loading app presets...');
            loadAppPresets();
        } else {
            console.log('App presets already loaded, count:', appPresets.length);
        }
    });

    // Handle preset selection
    $(document).on('click', '.preset-item', handlePresetSelection);

    // Initialize Bootstrap dropdown manually
    $(document).ready(function () {
        console.log('Checking for presets dropdown button...');
        const dropdownBtn = $('#presets-dropdown');
        console.log('Dropdown button found:', dropdownBtn.length > 0);

        // Check if Bootstrap is available
        if (typeof bootstrap !== 'undefined') {
            console.log('Bootstrap is available');

            // Initialize dropdown manually when modal is shown
            $('#addPortModal').on('shown.bs.modal', function () {
                const dropdownElement = document.getElementById('presets-dropdown');
                if (dropdownElement && typeof bootstrap.Dropdown !== 'undefined') {
                    console.log('Initializing Bootstrap dropdown...');
                    new bootstrap.Dropdown(dropdownElement);
                }
            });
        } else {
            console.log('Bootstrap is NOT available');
        }
    });
}

/**
 * Load app presets from the server.
 * Fetches the apps.json data and populates the presets dropdown.
 */
function loadAppPresets() {
    $.ajax({
        url: '/get_app_presets',
        method: 'GET',
        success: function (response) {
            if (response.success) {
                appPresets = response.apps;
                populatePresetDropdown();
                console.log(`Loaded ${appPresets.length} app presets`);
            } else {
                console.error('Failed to load app presets:', response.message);
                showPresetError('Failed to load app presets');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error loading app presets:', error);
            showPresetError('Error loading app presets');
        }
    });
}

/**
 * Populate the presets dropdown with app data.
 * Creates searchable list items for each app in the presets.
 */
function populatePresetDropdown() {
    const $menu = $('#presets-menu');
    $menu.empty();

    // Add search input
    $menu.append(`
        <li class="preset-search-container">
            <input type="text" class="preset-search-input" id="preset-search" placeholder="Search apps...">
        </li>
        <li><hr class="dropdown-divider"></li>
    `);

    // Add app items
    appPresets.forEach(app => {
        $menu.append(`
            <li>
                <a class="preset-item" href="#" data-name="${app.name}" data-port="${app.external_port}">
                    <span class="preset-item-name">${app.name}</span>
                    <span class="preset-item-port">${app.external_port}</span>
                </a>
            </li>
        `);
    });

    // Set up search functionality
    $('#preset-search').on('input', function () {
        const searchTerm = $(this).val().toLowerCase();
        $('.preset-item').each(function () {
            const appName = $(this).data('name').toLowerCase();
            const $listItem = $(this).parent();
            if (appName.includes(searchTerm)) {
                $listItem.show();
            } else {
                $listItem.hide();
            }
        });
    });

    // Focus search input when dropdown opens
    $('#presets-dropdown').on('shown.bs.dropdown', function () {
        $('#preset-search').focus();
    });
}

/**
 * Handle selection of a preset app.
 * Populates the form fields and resolves port conflicts if necessary.
 */
function handlePresetSelection(e) {
    e.preventDefault();

    const appName = $(this).data('name');
    const basePort = parseInt($(this).data('port'));
    const ip = $('#add-port-ip').val();
    const protocol = $('#add-port-protocol').val();

    console.log(`Selected preset: ${appName}, base port: ${basePort}`);

    // Populate description field
    $('#add-port-description').val(appName);

    // Find available port
    const availablePort = findAvailablePort(ip, basePort, protocol);

    if (availablePort !== basePort) {
        // Show notification about port change
        showPortChangeNotification(basePort, availablePort, ip, protocol);
    } else {
        // Hide any existing notification
        hidePresetNotification();
    }

    // Populate port field
    $('#add-new-port-number').val(availablePort);

    // Enable save button
    $('#save-new-port').prop('disabled', false);

    // Close dropdown
    $('#presets-dropdown').dropdown('hide');

    // Clear any port exists disclaimer
    $('#port-exists-disclaimer').hide();
}

/**
 * Find an available port starting from the base port.
 * Increments the port number until an available port is found.
 */
function findAvailablePort(ip, basePort, protocol, maxAttempts = 100) {
    let currentPort = basePort;
    let attempts = 0;

    while (attempts < maxAttempts) {
        if (!checkPortExists(ip, currentPort, protocol)) {
            return currentPort;
        }
        currentPort++;
        attempts++;
    }

    // If no available port found, return the base port and let the user handle it
    console.warn(`No available port found after ${maxAttempts} attempts starting from ${basePort}`);
    return basePort;
}

/**
 * Show notification about port number change due to conflict.
 */
function showPortChangeNotification(originalPort, newPort, ip, protocol) {
    const conflictPorts = [];
    for (let port = originalPort; port < newPort; port++) {
        if (checkPortExists(ip, port, protocol)) {
            conflictPorts.push(port);
        }
    }

    const conflictText = conflictPorts.length > 1
        ? `${conflictPorts[0]}-${conflictPorts[conflictPorts.length - 1]} already in use`
        : `${conflictPorts[0]} already in use`;

    const message = `Port changed from ${originalPort} to ${newPort} (${conflictText})`;

    $('#preset-notification').html(`
        <div class="alert alert-info alert-sm mb-0">
            <i class="fas fa-info-circle"></i> ${message}
        </div>
    `).show();
}

/**
 * Hide the preset notification.
 */
function hidePresetNotification() {
    $('#preset-notification').hide();
}

/**
 * Show error message in the presets dropdown.
 */
function showPresetError(message) {
    $('#presets-menu').html(`
        <li class="px-3 py-2">
            <div class="text-danger">
                <i class="fas fa-exclamation-triangle"></i> ${message}
            </div>
        </li>
    `);
}

/**
 * Initialize port scanning functionality.
 * Sets up event handlers for port scanning buttons and modals.
 */
function initPortScanning() {
    console.log('Initializing port scanning...');

    // Handle scan ports button click
    $(document).on('click', '.scan-ports-btn', handleScanPortsClick);

    // Handle start scan button click
    $('#start-scan-btn').on('click', handleStartScanClick);

    // Load default scan settings when modal is shown
    $('#portScanModal').on('shown.bs.modal', loadScanSettings);

    // Handle modal close after scan completion
    $('#portScanModal').on('hidden.bs.modal', handleScanModalClose);
}

/**
 * Handle click event on the "Scan Ports" button.
 * Opens the port scan modal and populates it with the IP address.
 */
function handleScanPortsClick(e) {
    e.preventDefault();
    const ip = $(this).data('ip');

    console.log('Scan ports clicked for IP:', ip);

    // Populate the modal with IP address
    $('#scan-ip-address').val(ip);
    $('#scan-ip-display').text(ip);

    // Reset form and progress
    resetScanModal();

    // Show the modal
    const scanModal = new bootstrap.Modal(document.getElementById('portScanModal'));
    scanModal.show();
}

/**
 * Load scan settings from the server and populate the form.
 */
function loadScanSettings() {
    $.ajax({
        url: '/port_scanning_settings',
        method: 'GET',
        success: function (data) {
            console.log('Loaded scan settings:', data);

            // Populate form with settings
            $('#scan-port-start').val(data.scan_range_start || '1024');
            $('#scan-port-end').val(data.scan_range_end || '65535');
            $('#scan-excluded-ports').val(data.scan_exclude || '');
            $('#scan-type').val('TCP'); // Default to TCP
        },
        error: function (xhr, status, error) {
            console.error('Error loading scan settings:', error);
            // Use defaults if settings can't be loaded
            $('#scan-port-start').val('1024');
            $('#scan-port-end').val('65535');
            $('#scan-excluded-ports').val('');
            $('#scan-type').val('TCP');
        }
    });
}

/**
 * Reset the scan modal to its initial state.
 */
function resetScanModal() {
    // Hide progress and results
    $('#scan-progress').hide();
    $('#scan-results').hide();

    // Reset progress bar
    $('.progress-bar').css('width', '0%');
    $('#scan-status-text').text('Initializing...');

    // Clear results
    $('#scan-results-content').empty();

    // Enable start button
    $('#start-scan-btn').prop('disabled', false).text('Start Scan');
}

/**
 * Handle click event on the "Start Scan" button.
 * Validates the form and initiates the port scan.
 */
function handleStartScanClick() {
    const ip = $('#scan-ip-address').val();
    const portStart = parseInt($('#scan-port-start').val());
    const portEnd = parseInt($('#scan-port-end').val());
    const excludedPorts = $('#scan-excluded-ports').val();
    const scanType = $('#scan-type').val();

    console.log('Starting port scan:', { ip, portStart, portEnd, excludedPorts, scanType });

    // Validate inputs
    if (!ip) {
        showNotification('IP address is required', 'error');
        return;
    }

    if (portStart < 1 || portStart > 65535 || portEnd < 1 || portEnd > 65535) {
        showNotification('Port range must be between 1 and 65535', 'error');
        return;
    }

    if (portStart > portEnd) {
        showNotification('Start port must be less than or equal to end port', 'error');
        return;
    }

    // Disable start button and show progress
    $('#start-scan-btn').prop('disabled', true).text('Scanning...');
    $('#scan-progress').show();
    $('#scan-results').hide();

    // Start the scan
    startPortScan({
        ip_address: ip,
        port_range_start: portStart,
        port_range_end: portEnd,
        excluded_ports: excludedPorts,
        scan_type: scanType
    });
}

/**
 * Start a port scan with the given parameters.
 * Sends a request to the server to initiate the scan.
 */
function startPortScan(scanParams) {
    $.ajax({
        url: '/start_port_scan',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(scanParams),
        success: function (response) {
            if (response.success) {
                console.log('Scan started successfully:', response);
                showNotification('Port scan started', 'success');

                // Start polling for scan status
                pollScanStatus(response.scan_id);
            } else {
                console.error('Failed to start scan:', response);
                showNotification('Failed to start scan: ' + response.message, 'error');
                resetScanButton();
            }
        },
        error: function (xhr, status, error) {
            console.error('Error starting scan:', error);
            let errorMessage = 'Error starting scan';

            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMessage += ': ' + xhr.responseJSON.error;
            }

            showNotification(errorMessage, 'error');
            resetScanButton();
        }
    });
}

/**
 * Poll the server for scan status updates.
 * Continues polling until the scan is complete or fails.
 */
function pollScanStatus(scanId) {
    const pollInterval = setInterval(() => {
        $.ajax({
            url: `/scan_status/${scanId}`,
            method: 'GET',
            success: function (response) {
                console.log('Scan status:', response);
                updateScanProgress(response);

                if (response.status === 'completed') {
                    clearInterval(pollInterval);
                    handleScanComplete(response);
                } else if (response.status === 'failed') {
                    clearInterval(pollInterval);
                    handleScanFailed(response);
                }
            },
            error: function (xhr, status, error) {
                console.error('Error polling scan status:', error);
                clearInterval(pollInterval);
                showNotification('Error checking scan status', 'error');
                resetScanButton();
            }
        });
    }, 2000); // Poll every 2 seconds
}

/**
 * Update the scan progress display.
 */
function updateScanProgress(scanData) {
    const status = scanData.status;
    let progressPercent = 0;
    let statusText = 'Initializing...';

    if (status === 'in_progress') {
        // Estimate progress based on ports scanned
        if (scanData.ports_scanned > 0) {
            const totalPorts = scanData.port_range_end - scanData.port_range_start + 1;
            progressPercent = Math.min(90, (scanData.ports_scanned / totalPorts) * 100);
            statusText = `Scanning ports... (${scanData.ports_scanned} ports checked)`;
        } else {
            progressPercent = 10;
            statusText = 'Starting scan...';
        }
    } else if (status === 'completed') {
        progressPercent = 100;
        statusText = `Scan completed! Found ${scanData.ports_found} open ports`;
    } else if (status === 'failed') {
        statusText = 'Scan failed';
    }

    $('.progress-bar').css('width', progressPercent + '%');
    $('#scan-status-text').text(statusText);
}

/**
 * Handle scan completion.
 */
function handleScanComplete(scanData) {
    console.log('Scan completed:', scanData);

    // Mark that a scan has been completed in this session
    scanCompletedInSession = true;

    // Update progress to 100%
    $('.progress-bar').css('width', '100%');
    $('#scan-status-text').text(`Scan completed! Found ${scanData.ports_found} open ports in ${scanData.scan_duration?.toFixed(2) || 'N/A'} seconds`);

    // Check if auto-add is enabled and refresh the port display if needed
    checkAutoAddSetting().then(autoAddEnabled => {
        if (autoAddEnabled && scanData.ports_found > 0) {
            // Refresh the ports for this IP to show newly added ports
            refreshPortsForIP(scanData.ip_address);
        }

        // Show results
        displayScanResults(scanData);
    });

    // Reset button
    resetScanButton();

    showNotification(`Port scan completed! Found ${scanData.ports_found} open ports`, 'success');
}

/**
 * Handle scan failure.
 */
function handleScanFailed(scanData) {
    console.log('Scan failed:', scanData);

    $('#scan-status-text').text('Scan failed');
    $('.progress-bar').removeClass('progress-bar-animated').addClass('bg-danger');

    resetScanButton();
    showNotification('Port scan failed', 'error');
}

/**
 * Display scan results in the modal.
 */
function displayScanResults(scanData) {
    const resultsContainer = $('#scan-results-content');
    resultsContainer.empty();

    if (scanData.ports_found === 0) {
        resultsContainer.html(`
            <div class="scan-no-results glass-card">
                <div class="scan-result-icon">
                    <i class="fas fa-search"></i>
                </div>
                <h4>No Open Ports Found</h4>
                <p>No open ports were discovered in the specified range.</p>
            </div>
        `);
    } else {
        let discoveredPorts = [];
        try {
            discoveredPorts = JSON.parse(scanData.discovered_ports || '[]');
        } catch (e) {
            console.error('Error parsing discovered ports:', e);
        }

        // Check if auto-add is enabled
        checkAutoAddSetting().then(autoAddEnabled => {
            let resultsHtml = `
                <div class="scan-results-header glass-card">
                    <div class="scan-result-icon success">
                        <i class="fas fa-check-circle"></i>
                    </div>
                    <h4>Scan Complete</h4>
                    <p>Found ${scanData.ports_found} open ports</p>
                    ${autoAddEnabled ? '<div class="auto-add-notice"><i class="fas fa-magic"></i> Auto-add is enabled</div>' : ''}
                </div>
                <div class="scan-results-grid">
            `;

            discoveredPorts.forEach(portInfo => {
                const portExists = checkPortExists(scanData.ip_address, portInfo.port, portInfo.protocol);

                let statusInfo = {};
                let actionContent = '';

                if (autoAddEnabled) {
                    if (portExists) {
                        statusInfo = {
                            class: 'already-exists',
                            icon: 'fas fa-check-circle',
                            text: 'Already Added',
                            description: 'This port was already in your collection'
                        };
                        actionContent = '<div class="scan-action-disabled">Already Added</div>';
                    } else {
                        statusInfo = {
                            class: 'auto-added',
                            icon: 'fas fa-magic',
                            text: 'Auto-Added',
                            description: 'Automatically added to your collection'
                        };
                        actionContent = '<div class="scan-action-success"><i class="fas fa-check"></i> Added</div>';
                    }
                } else {
                    if (portExists) {
                        statusInfo = {
                            class: 'already-exists',
                            icon: 'fas fa-check-circle',
                            text: 'Already Added',
                            description: 'This port is already in your collection'
                        };
                        actionContent = '<div class="scan-action-disabled">Already Added</div>';
                    } else {
                        statusInfo = {
                            class: 'new-port',
                            icon: 'fas fa-plus-circle',
                            text: 'New Port',
                            description: 'Click to add this port to your collection'
                        };
                        actionContent = `<button class="scan-action-button add-discovered-port" data-ip="${scanData.ip_address}" data-port="${portInfo.port}" data-protocol="${portInfo.protocol}">
                            <i class="fas fa-plus"></i> Add Port
                        </button>`;
                    }
                }

                resultsHtml += `
                    <div class="scan-result-card glass-card ${statusInfo.class}">
                        <div class="scan-result-header">
                            <div class="port-info">
                                <span class="port-number">${portInfo.port}</span>
                                <span class="port-protocol ${portInfo.protocol.toLowerCase()}">${portInfo.protocol}</span>
                            </div>
                            <div class="port-status">
                                <i class="${statusInfo.icon}"></i>
                            </div>
                        </div>
                        <div class="scan-result-body">
                            <div class="status-info">
                                <span class="status-text">${statusInfo.text}</span>
                                <span class="status-description">${statusInfo.description}</span>
                            </div>
                            <div class="scan-result-action">
                                ${actionContent}
                            </div>
                        </div>
                    </div>
                `;
            });

            resultsHtml += '</div>';
            resultsContainer.html(resultsHtml);

            // Handle add discovered port buttons
            $('.add-discovered-port').on('click', handleAddDiscoveredPort);
        });
    }

    $('#scan-results').show();
}

/**
 * Check if auto-add discovered ports is enabled.
 * @returns {Promise<boolean>} Promise that resolves to true if auto-add is enabled
 */
function checkAutoAddSetting() {
    return new Promise((resolve) => {
        $.ajax({
            url: '/port_scanning_settings',
            method: 'GET',
            success: function (data) {
                const autoAddEnabled = data.auto_add_discovered === 'true';
                resolve(autoAddEnabled);
            },
            error: function () {
                // Default to false if we can't get the setting
                resolve(false);
            }
        });
    });
}

/**
 * Handle adding a discovered port.
 */
function handleAddDiscoveredPort(e) {
    const button = $(this);
    const ip = button.data('ip');
    const port = button.data('port');
    const protocol = button.data('protocol');

    console.log('Adding discovered port:', { ip, port, protocol });

    // Disable button
    button.prop('disabled', true).text('Adding...');

    // Add the port
    $.ajax({
        url: '/add_port',
        method: 'POST',
        data: {
            ip: ip,
            ip_nickname: '', // Will be determined by the server
            port_number: port,
            description: 'Discovered',
            protocol: protocol
        },
        success: function (response) {
            if (response.success) {
                showNotification(`Port ${port} added successfully`, 'success');

                // Update the button to show success
                button.text('Added').removeClass('scan-action-button').addClass('scan-action-success');
                button.html('<i class="fas fa-check"></i> Added');

                // Add the port to the UI dynamically
                const portData = {
                    id: response.id || Date.now(), // Use response ID or fallback
                    port_number: port,
                    description: 'Discovered',
                    protocol: protocol,
                    order: response.order || 999,
                    is_immutable: false
                };

                addPortToUI(ip, portData);

                // Update the scan result card to show it's been added
                const $scanCard = button.closest('.scan-result-card');
                $scanCard.removeClass('new-port').addClass('auto-added');
                $scanCard.find('.status-text').text('Added');
                $scanCard.find('.status-description').text('Successfully added to your collection');
                $scanCard.find('.port-status i').removeClass('fa-plus-circle').addClass('fa-check');

            } else {
                showNotification('Error adding port: ' + response.message, 'error');
                button.prop('disabled', false).text('Add Port');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error adding discovered port:', error);
            showNotification('Error adding port', 'error');
            button.prop('disabled', false).text('Add Port');
        }
    });
}

/**
 * Reset the scan button to its initial state.
 */
function resetScanButton() {
    $('#start-scan-btn').prop('disabled', false).text('Start Scan');
    $('.progress-bar').removeClass('bg-danger').addClass('progress-bar-striped progress-bar-animated');
}

/**
 * Refresh the ports display for a specific IP address without refreshing the entire page.
 * This fetches the latest port data and updates the UI dynamically.
 */
function refreshPortsForIP(ipAddress) {
    console.log('Refreshing ports for IP:', ipAddress);

    // Find the network switch panel for this IP
    const $networkSwitch = $(`.network-switch[data-ip="${ipAddress}"]`);
    if ($networkSwitch.length === 0) {
        console.log('Network switch not found for IP:', ipAddress);
        return;
    }

    const $switchPanel = $networkSwitch.find('.switch-panel');

    // Get current ports to compare
    const currentPorts = new Set();
    $switchPanel.find('.port').each(function () {
        const port = $(this).data('port');
        const protocol = $(this).data('protocol');
        currentPorts.add(`${port}-${protocol}`);
    });

    // Fetch updated port data from server
    $.ajax({
        url: '/ports',
        method: 'GET',
        success: function (html) {
            // Parse the returned HTML to extract port data for this IP
            const $tempDiv = $('<div>').html(html);
            const $updatedNetworkSwitch = $tempDiv.find(`.network-switch[data-ip="${ipAddress}"]`);

            if ($updatedNetworkSwitch.length === 0) {
                console.log('Updated network switch not found for IP:', ipAddress);
                return;
            }

            const $updatedSwitchPanel = $updatedNetworkSwitch.find('.switch-panel');
            const newPorts = [];

            // Extract new ports
            $updatedSwitchPanel.find('.port').each(function () {
                const port = $(this).data('port');
                const protocol = $(this).data('protocol');
                const portKey = `${port}-${protocol}`;

                if (!currentPorts.has(portKey)) {
                    newPorts.push($(this).closest('.port-slot')[0].outerHTML);
                }
            });

            // Add new ports to the current panel with animation
            newPorts.forEach((portHtml, index) => {
                setTimeout(() => {
                    const $newPort = $(portHtml);
                    $newPort.css({
                        opacity: 0,
                        transform: 'translateY(20px)'
                    });

                    // Insert before the add-port-slot
                    $switchPanel.find('.add-port-slot').before($newPort);

                    // Animate in
                    $newPort.animate({
                        opacity: 1
                    }, 300).css({
                        transform: 'translateY(0)'
                    });

                    console.log('Added new port to UI:', $newPort.find('.port').data('port'));
                }, index * 100); // Stagger the animations
            });

            if (newPorts.length > 0) {
                showNotification(`${newPorts.length} new port(s) added automatically`, 'success');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error refreshing ports:', error);
        }
    });
}

/**
 * Add a new port element to the UI dynamically.
 * This creates and inserts a new port element with proper styling and event handlers.
 */
function addPortToUI(ipAddress, portData) {
    const $switchPanel = $(`.switch-panel[data-ip="${ipAddress}"]`);
    if ($switchPanel.length === 0) {
        console.log('Switch panel not found for IP:', ipAddress);
        return;
    }

    // Create the new port element
    const newPortElement = `
        <div class="port-slot active" draggable="true" data-port="${portData.port_number}" data-order="${portData.order}">
            <div class="port active" data-ip="${ipAddress}" data-port="${portData.port_number}"
                 data-description="${portData.description}" data-order="${portData.order}"
                 data-id="${portData.id}" data-protocol="${portData.protocol}"
                 data-immutable="${portData.is_immutable || false}">
                <span class="port-number">${portData.port_number}</span>
                <span class="port-description">${portData.description}</span>
                <div class="port-tooltip">
                    <div class="tooltip-header">
                        <span class="tooltip-title">Port ${portData.port_number}</span>
                        <span class="tooltip-protocol ${portData.protocol.toLowerCase()}">${portData.protocol}</span>
                    </div>
                    <div class="tooltip-content">
                        <div class="tooltip-label">Description</div>
                        <div class="tooltip-value">${portData.description}</div>
                        <div class="tooltip-label">IP Address</div>
                        <div class="tooltip-value">${ipAddress}</div>
                    </div>
                    <div class="tooltip-footer">
                        <span>Click to edit</span>
                        <span>ID: ${portData.id}</span>
                    </div>
                </div>
            </div>
            <p class="port-protocol ${portData.protocol.toLowerCase()}">${portData.protocol}</p>
        </div>
    `;

    // Insert the new port element with animation
    const $newPort = $(newPortElement);
    $newPort.css({
        opacity: 0,
        transform: 'translateY(20px)'
    });

    // Insert before the add-port-slot
    $switchPanel.find('.add-port-slot').before($newPort);

    // Animate in
    $newPort.animate({
        opacity: 1
    }, 300).css({
        transform: 'translateY(0)'
    });

    console.log('Added new port to UI:', portData.port_number);
}

/**
 * Handle the port scan modal close event.
 * If a scan was completed in this session, trigger the "Anchors Aweigh" refresh animation.
 */
function handleScanModalClose() {
    console.log('Port scan modal closed. Scan completed in session:', scanCompletedInSession);

    if (scanCompletedInSession) {
        console.log('Triggering Anchors Aweigh refresh animation...');

        // Show the loading animation
        showLoadingAnimation();

        // Wait a moment for the animation to be visible, then refresh the page
        setTimeout(() => {
            location.reload();
        }, 1500); // Give time for the animation to be seen

        // Reset the flag
        scanCompletedInSession = false;
    }
}

// static/js/core/ports.js

/**
 * Main script for network switch management interface.
 * This script handles various functionalities including:
 * - Drag and drop for ports and IP panels
 * - CRUD operations for IPs and ports
 * - Modal interactions for editing and deleting
 * - Dynamic DOM updates
 */

$(document).ready(function () {

    // Initialize Bootstrap modals for various actions
    const editIpModal = new bootstrap.Modal(document.getElementById('editIpModal'));
    const editPortModal = new bootstrap.Modal(document.getElementById('editPortModal'));
    const addPortModal = new bootstrap.Modal(document.getElementById('addPortModal'));
    const deletePortModal = new bootstrap.Modal(document.getElementById('deletePortModal'));

    // Variable to store the IP address being deleted
    let deleteIpAddress;

    // Variables for drag and drop functionality
    let draggingElement = null;
    let placeholder = null;
    let dragStartX, dragStartY, dragStartTime;
    let isDragging = false;
    let sourcePanel = null;
    let sourceIp = null;
    const dragThreshold = 5; // Minimum pixels moved to initiate drag
    const clickThreshold = 200; // Maximum milliseconds for a click

    // Variables for IP panel drag and drop
    let draggingIPPanel = null;
    let ipPanelPlaceholder = null;

    // Variables to store IP and port number for deletion
    let deleteIp, deletePortNumber;
    let originalPortNumber;

    // Initialize port number input handlers
    handlePortNumberInput(true);  // For edit
    handlePortNumberInput(false); // For add

    /**
     * Event listener for mousedown on port slots
     * Initiates the drag process for ports
     */
    $('.port-slot:not(.add-port-slot)').on('mousedown', function (e) {
        if (e.which !== 1) return; // Only respond to left mouse button

        const panel = $(this).closest('.switch-panel');
        if (panel.find('.port-slot:not(.add-port-slot)').length === 1) {
            showNotification("Can't move the last port in a panel", 'error');
            return;
        }

        dragStartX = e.clientX;
        dragStartY = e.clientY;
        dragStartTime = new Date().getTime();
        const element = this;

        // Monitor mouse movement to detect drag
        $(document).on('mousemove.dragdetect', function (e) {
            if (!isDragging &&
                (Math.abs(e.clientX - dragStartX) > dragThreshold ||
                    Math.abs(e.clientY - dragStartY) > dragThreshold)) {

                isDragging = true;
                initiateDrag(e, element);
            }
        });

        // Handle mouseup event
        $(document).on('mouseup.dragdetect', function (e) {
            $(document).off('mousemove.dragdetect mouseup.dragdetect');
            if (!isDragging && new Date().getTime() - dragStartTime < clickThreshold) {
                // This was a click, not a drag
                handlePortClick(element);
            }
            isDragging = false;
        });

        e.preventDefault(); // Prevent text selection
    });

    /**
     * Handles the dragstart event for network switch panels
     * @param {Event} e - The dragstart event object
     */
    $('.network-switch').on('dragstart', function (e) {
        // Store the dragged element
        draggingIPPanel = this;
        e.originalEvent.dataTransfer.effectAllowed = 'move';
        e.originalEvent.dataTransfer.setData('text/html', this.outerHTML);

        // Create and insert a placeholder for the dragged element
        ipPanelPlaceholder = document.createElement('div');
        ipPanelPlaceholder.className = 'network-switch-placeholder';
        ipPanelPlaceholder.style.height = `${this.offsetHeight}px`;
        this.parentNode.insertBefore(ipPanelPlaceholder, this.nextSibling);

        // Hide the original element after a short delay
        setTimeout(() => {
            this.style.display = 'none';
        }, 0);
    });

    /**
     * Handles the dragover event for network switch panels
     * @param {Event} e - The dragover event object
     */
    $('.network-switch').on('dragover', function (e) {
        e.preventDefault();
        e.originalEvent.dataTransfer.dropEffect = 'move';

        // Calculate the midpoint of the current element
        const rect = this.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;

        // Insert the placeholder above or below the current element based on cursor position
        if (e.originalEvent.clientY < midpoint) {
            this.parentNode.insertBefore(ipPanelPlaceholder, this);
        } else {
            this.parentNode.insertBefore(ipPanelPlaceholder, this.nextSibling);
        }
    });

    /**
     * Handles the dragend event for network switch panels
     * @param {Event} e - The dragend event object
     */
    $('.network-switch').on('dragend', function (e) {
        // Restore visibility of the dragged element
        this.style.display = 'block';

        // Insert the dragged element at the placeholder's position and remove the placeholder
        if (ipPanelPlaceholder && ipPanelPlaceholder.parentNode) {
            ipPanelPlaceholder.parentNode.insertBefore(this, ipPanelPlaceholder);
            ipPanelPlaceholder.parentNode.removeChild(ipPanelPlaceholder);
        }

        // Update the order of IP panels after the DOM has been updated
        setTimeout(updateIPPanelOrder, 0);
    });

    /**
     * Handles the drop event on the body element
     * @param {Event} e - The drop event object
     */
    $('body').on('drop', function (e) {
        e.preventDefault();
        if (draggingIPPanel !== null) {
            // Insert the dragged element at the placeholder's position and remove the placeholder
            if (ipPanelPlaceholder && ipPanelPlaceholder.parentNode) {
                ipPanelPlaceholder.parentNode.insertBefore(draggingIPPanel, ipPanelPlaceholder);
                ipPanelPlaceholder.parentNode.removeChild(ipPanelPlaceholder);
            }
            draggingIPPanel = null;
        }
    });

    /**
     * Handles the edit IP button click event
     * @param {Event} e - The click event object
     */
    $('.edit-ip').click(function (e) {
        e.preventDefault();
        const ip = $(this).data('ip');
        const nickname = $(this).data('nickname');
        $('#old-ip').val(ip);
        $('#new-ip').val(ip);
        $('#new-nickname').val(nickname);
        editIpModal.show();
    });

    /**
     * Handles the save IP button click event
     */
    $('#save-ip').click(function () {
        const formData = $('#edit-ip-form').serialize();
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
                editIpModal.hide();
            },
            error: function (xhr, status, error) {
                showNotification('Error updating IP: ' + error, 'error');
                editIpModal.hide();
            }
        });
    });

    /**
     * Handles the delete IP button click event
     */
    $('#delete-ip').click(function () {
        deleteIpAddress = $('#old-ip').val();
        $('#delete-ip-address').text(deleteIpAddress);
        editIpModal.hide();
        $('#deleteIpModal').modal('show');
    });

    /**
     * Handles the confirm delete IP button click event
     */
    $('#confirm-delete-ip').click(function () {
        $.ajax({
            url: '/delete_ip',
            method: 'POST',
            data: { ip: deleteIpAddress },
            success: function (response) {
                if (response.success) {
                    showNotification('IP and all assigned ports deleted successfully', 'success');
                    // Remove the IP panel from the DOM
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
    });

    // Reset deleteIpAddress when delete confirmation modal is closed
    $('#deleteIpModal').on('hidden.bs.modal', function (e) {
        deleteIpAddress = null;
    });

    /**
     * Handles the save port button click event
     */
    $('#save-port').click(function () {
        console.log("Save port button clicked");
        const ip = $('#edit-port-ip').val();
        const portNumber = $('#new-port-number').val().trim();
        const description = $('#port-description').val().trim();
        const currentPortId = $('#port-id').val();

        console.log("IP:", ip);
        console.log("Port Number:", portNumber);
        console.log("Description:", description);

        // Validate input
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
                    // Update the DOM dynamically
                    const oldPortNumber = $('#old-port-number').val();
                    const portElement = $(`.port[data-ip="${ip}"][data-port="${oldPortNumber}"]`);
                    portElement.data('port', portNumber).data('description', description);
                    portElement.attr('data-port', portNumber).attr('data-description', description);
                    portElement.find('.port-number').text(portNumber);
                    portElement.find('.port-description').text(description);

                    // Refresh the page to ensure all data is correctly displayed
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
    });

    /**
     * Handles the add port button click event
     */
    $('.add-port').click(function () {
        const ip = $(this).data('ip');
        $('#add-port-ip').val(ip);
        $('#display-add-port-ip').text(ip);
        $('#add-new-port-number').val('');
        $('#add-port-description').val('');
        $('#port-exists-disclaimer').hide();
        $('#save-new-port').prop('disabled', false);
        addPortModal.show();
    });

    $('#new-port-number').on('input', function () {
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
    });

    /**
     * Handles the input event for the new port number field
     */
    $('#add-new-port-number').on('input', function () {
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
    });

    /**
     * Handles the save new port button click event
     */
    $('#save-new-port').click(function () {
        console.log("Save new port button clicked");

        const ip = $('#add-port-ip').val();
        const portNumber = $('#add-new-port-number').val().trim();
        const description = $('#add-port-description').val().trim();

        console.log("IP:", ip);
        console.log("Port Number:", portNumber);
        console.log("Description:", description);

        // Validate input
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
    });

    /**
     * Handles the delete port button click event
     */
    $('#delete-port').click(function () {
        deleteIp = $('#edit-port-ip').val();
        deletePortNumber = $('#old-port-number').val();
        editPortModal.hide();
        deletePortModal.show();
    });

    /**
     * Handles the confirm delete port button click event
     */
    $('#confirm-delete-port').click(function () {
        $.ajax({
            url: '/delete_port',
            method: 'POST',
            data: { ip: deleteIp, port_number: deletePortNumber },
            success: function (response) {
                if (response.success) {
                    showNotification('Port deleted successfully', 'success');
                    // Remove the port from the DOM
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
    });

    // Reset deleteIp and deletePortNumber when delete confirmation modal is closed
    $('#deletePortModal').on('hidden.bs.modal', function (e) {
        deleteIp = null;
        deletePortNumber = null;
    });

});
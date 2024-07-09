// static/js/ports.js

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
     * Initiates the drag operation for a port
     * @param {Event} e - The event object
     * @param {HTMLElement} element - The element being dragged
     */
    function initiateDrag(e, element) {
        draggingElement = element;
        sourcePanel = $(element).closest('.switch-panel');
        sourceIp = sourcePanel.data('ip');
        console.log('Dragging element:', draggingElement);
        console.log('Source panel:', sourcePanel);
        console.log('Source IP:', sourceIp);

        const rect = draggingElement.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const offsetY = e.clientY - rect.top;

        // Create a placeholder for the dragged element
        placeholder = $(draggingElement).clone().empty().css({
            'height': $(draggingElement).height(),
            'background-color': 'rgba(0, 0, 0, 0.1)',
            'border': '2px dashed #ccc'
        }).insertAfter(draggingElement);

        // Style the dragging element
        $(draggingElement).css({
            'position': 'fixed',
            'zIndex': 1000,
            'pointer-events': 'none',
            'width': $(draggingElement).width() + 'px',
            'height': $(draggingElement).height() + 'px'
        }).appendTo('body');

        // Handle mouse movement during drag
        function mouseMoveHandler(e) {
            $(draggingElement).css({
                'left': e.clientX - offsetX + 'px',
                'top': e.clientY - offsetY + 'px'
            });

            const targetElement = getTargetElement(e.clientX, e.clientY);
            if (targetElement && !$(targetElement).is(placeholder)) {
                if ($(targetElement).index() < $(placeholder).index()) {
                    $(placeholder).insertBefore(targetElement);
                } else {
                    $(placeholder).insertAfter(targetElement);
                }
            }
        }

        // Handle mouse up to end drag
        function mouseUpHandler(e) {
            $(document).off('mousemove', mouseMoveHandler);
            $(document).off('mouseup', mouseUpHandler);

            const targetElement = getTargetElement(e.clientX, e.clientY);
            if (targetElement) {
                finalizeDrop(targetElement);
            } else {
                cancelDrop();
            }

            // Reset the dragging element's style
            $(draggingElement).css({
                'position': '',
                'zIndex': '',
                'left': '',
                'top': '',
                'pointer-events': '',
                'width': '',
                'height': ''
            }).insertBefore(placeholder);
            placeholder.remove();
            draggingElement = null;
            placeholder = null;
        }

        $(document).on('mousemove', mouseMoveHandler);
        $(document).on('mouseup', mouseUpHandler);
    }

    /**
     * Determines the target element for dropping a port
     * @param {number} x - The x-coordinate of the mouse
     * @param {number} y - The y-coordinate of the mouse
     * @returns {HTMLElement|null} The target element or null if invalid
     */
    function getTargetElement(x, y) {
        const elements = document.elementsFromPoint(x, y);
        const potentialTarget = elements.find(el => el.classList.contains('port-slot') && el !== draggingElement && !el.classList.contains('add-port-slot'));

        if (potentialTarget) {
            const sourcePanel = $(draggingElement).closest('.switch-panel');
            const targetPanel = $(potentialTarget).closest('.switch-panel');

            // Prevent moving the last port out of a panel
            if (sourcePanel[0] !== targetPanel[0] && sourcePanel.find('.port-slot:not(.add-port-slot)').length === 1) {
                return null;
            }
        }

        return potentialTarget;
    }

    /**
     * Finalizes the drop operation for a port
     * @param {HTMLElement} targetElement - The element where the port is being dropped
     */
    function finalizeDrop(targetElement) {
        if (!targetElement) {
            showNotification("Can't move the last port in a panel", 'error');
            cancelDrop();
            return;
        }

        const targetPanel = $(targetElement).closest('.switch-panel');
        const targetIp = targetPanel.data('ip');

        console.log('Source panel:', sourcePanel);
        console.log('Target panel:', targetPanel);
        console.log('Source IP:', sourceIp);
        console.log('Target IP:', targetIp);

        if (sourceIp !== targetIp) {
            console.log('Moving port to a different IP group');
            // Moving port to a different IP group
            const portNumber = $(draggingElement).find('.port').data('port');
            movePort(portNumber, sourceIp, targetIp, targetElement);
        } else {
            console.log('Reordering within the same IP group');
            // Reordering within the same IP group
            targetElement.parentNode.insertBefore(draggingElement, targetElement.nextSibling);
            updatePortOrder(sourceIp);
        }

        // Reset source variables
        sourcePanel = null;
        sourceIp = null;
    }

    /**
     * Updates the order of ports for a specific IP address
     * @param {string} ip - The IP address of the ports to reorder
     */
    function updatePortOrder(ip) {
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

    /**
     * Cancels the drop operation and reverts the dragged element to its original position
     */
    function cancelDrop() {
        $(draggingElement).insertBefore(placeholder);
    }

    /**
     * Moves a port from one IP to another
     * @param {number} portNumber - The port number being moved
     * @param {string} sourceIp - The source IP address
     * @param {string} targetIp - The target IP address
     * @param {HTMLElement} targetElement - The target element for insertion
     */
    function movePort(portNumber, sourceIp, targetIp, targetElement) {
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
                    if (document.body.contains(targetElement)) {
                        targetElement.parentNode.insertBefore(draggingElement, targetElement.nextSibling);
                        $(draggingElement).find('.port').attr('data-ip', targetIp);

                        // Update the nickname
                        const targetNickname = $(`.switch-panel[data-ip="${targetIp}"]`).siblings('.switch-label').find('.edit-ip').data('nickname');
                        $(draggingElement).find('.port').attr('data-nickname', targetNickname);
                    } else {
                        $(`.switch-panel[data-ip="${targetIp}"]`).append(draggingElement);
                        $(draggingElement).find('.port').attr('data-ip', targetIp);

                        // Update the nickname
                        const targetNickname = $(`.switch-panel[data-ip="${targetIp}"]`).siblings('.switch-label').find('.edit-ip').data('nickname');
                        $(draggingElement).find('.port').attr('data-nickname', targetNickname);
                    }

                    // Update port order for both source and target IPs
                    updatePortOrder(sourceIp);
                    if (sourceIp !== targetIp) {
                        updatePortOrder(targetIp);
                    }
                } else {
                    showNotification('Error moving port: ' + response.message, 'error');
                    cancelDrop();
                }
            },
            error: function (xhr, status, error) {
                showNotification('Error moving port: ' + error, 'error');
                cancelDrop();
            }
        });
    }

    /**
     * Handles click events on port elements
     * @param {HTMLElement} element - The clicked port element
     */
    function handlePortClick(element) {
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

    /**
     * Handles input events for port number fields
     * @param {boolean} isEdit - True if handling edit mode, false for add mode
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

            // Don't show disclaimer for the current port number when editing
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
     * Updates the order of IP panels on the server
     */
    function updateIPPanelOrder() {
        const ipOrder = [];
        $('.network-switch').each(function () {
            ipOrder.push($(this).data('ip'));
        });

        console.log("Sending IP order:", ipOrder);

        // Send the updated order to the server
        $.ajax({
            url: '/update_ip_order',
            method: 'POST',
            data: JSON.stringify({ ip_order: ipOrder }),
            contentType: 'application/json',
            success: function (response) {
                if (response.success) {
                    // Success notification can be uncommented if needed
                    // showNotification('IP panel order updated successfully', 'success');
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

    /**
     * Checks if a port exists for a given IP address
     * @param {string} ip - The IP address to check
     * @param {string} portNumber - The port number to check
     * @param {string} [currentPortId] - The ID of the current port being edited (optional)
     * @returns {boolean} True if the port exists, false otherwise
     */
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

    /**
     * Displays a notification message
     * @param {string} message - The message to display
     * @param {string} [type='success'] - The type of notification ('success' or 'error')
     */
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
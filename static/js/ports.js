$(document).ready(function () {
    const editIpModal = new bootstrap.Modal(document.getElementById('editIpModal'));
    const editPortModal = new bootstrap.Modal(document.getElementById('editPortModal'));
    const addPortModal = new bootstrap.Modal(document.getElementById('addPortModal'));
    const deletePortModal = new bootstrap.Modal(document.getElementById('deletePortModal'));

    let deleteIpAddress;

    let draggingElement = null;
    let placeholder = null;
    let dragStartX, dragStartY, dragStartTime;
    let isDragging = false;
    const dragThreshold = 5; // pixels
    const clickThreshold = 200; // milliseconds

    // New IP panel drag and drop functionality
    let draggingIPPanel = null;
    let ipPanelPlaceholder = null;


    // Drag and drop functionality
    $('.port-slot:not(.add-port-slot)').on('mousedown', function (e) {
        if (e.which !== 1) return; // Only respond to left mouse button

        dragStartX = e.clientX;
        dragStartY = e.clientY;
        dragStartTime = new Date().getTime();

        const element = this;

        $(document).on('mousemove.dragdetect', function (e) {
            if (!isDragging &&
                (Math.abs(e.clientX - dragStartX) > dragThreshold ||
                    Math.abs(e.clientY - dragStartY) > dragThreshold)) {

                // Check if this is the last port in the panel before initiating drag
                if ($(element).siblings('.port-slot:not(.add-port-slot)').length === 0) {
                    showNotification("Can't move the last port in a panel", 'error');
                    $(document).off('mousemove.dragdetect mouseup.dragdetect');
                    return;
                }

                isDragging = true;
                initiateDrag(e, element);
            }
        });

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

    function initiateDrag(e, element) {
        draggingElement = element;
        const rect = draggingElement.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const offsetY = e.clientY - rect.top;

        placeholder = $(draggingElement).clone().empty().css({
            'height': $(draggingElement).height(),
            'background-color': 'rgba(0, 0, 0, 0.1)',
            'border': '2px dashed #ccc'
        }).insertAfter(draggingElement);

        $(draggingElement).css({
            'position': 'fixed',
            'zIndex': 1000,
            'pointer-events': 'none',
            'width': $(draggingElement).width() + 'px',
            'height': $(draggingElement).height() + 'px'
        }).appendTo('body');

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

        function mouseUpHandler(e) {
            $(document).off('mousemove', mouseMoveHandler);
            $(document).off('mouseup', mouseUpHandler);

            const targetElement = getTargetElement(e.clientX, e.clientY);
            if (targetElement) {
                finalizeDrop(targetElement);
            } else {
                cancelDrop();
            }

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

    function getTargetElement(x, y) {
        const elements = document.elementsFromPoint(x, y);
        const potentialTarget = elements.find(el => el.classList.contains('port-slot') && el !== draggingElement && !el.classList.contains('add-port-slot'));

        if (potentialTarget) {
            const sourcePanel = $(draggingElement).closest('.switch-panel');
            const targetPanel = $(potentialTarget).closest('.switch-panel');

            // If moving to a different panel, check if it's the last port in the source panel
            if (sourcePanel[0] !== targetPanel[0] && sourcePanel.find('.port-slot:not(.add-port-slot)').length === 1) {
                return null; // Prevent drop if it's the last port
            }
        }

        return potentialTarget;
    }

    function finalizeDrop(targetElement) {
        if (!targetElement) {
            showNotification("Can't move the last port in a panel", 'error');
            cancelDrop();
            return;
        }

        const sourcePanel = $(draggingElement).closest('.switch-panel');
        const targetPanel = $(targetElement).closest('.switch-panel');

        if (sourcePanel[0] !== targetPanel[0]) {
            // Moving port to a different IP group
            const portNumber = $(draggingElement).find('.port').data('port');
            const sourceIp = sourcePanel.data('ip');
            const targetIp = targetPanel.data('ip');
            movePort(portNumber, sourceIp, targetIp, targetElement);
        } else {
            // Reordering within the same IP group
            targetElement.parentNode.insertBefore(draggingElement, targetElement.nextSibling);
            updatePortOrder(sourcePanel.data('ip'));
        }
    }

    function cancelDrop() {
        $(draggingElement).insertBefore(placeholder);
    }

    function updateIPPanelOrder() {
        const ipOrder = $('.network-switch').map(function () {
            return $(this).data('ip');
        }).get();

        $.ajax({
            url: '/update_ip_order',
            method: 'POST',
            data: { ip_order: ipOrder },
            success: function (response) {
                if (response.success) {
                    // Reorder the IP panels in the DOM
                    const container = $('.network-switch').parent();
                    ipOrder.forEach(function (ip) {
                        const panel = $(`.network-switch[data-ip="${ip}"]`);
                        container.append(panel);
                    });
                    showNotification('IP panel order updated successfully', 'success');
                } else {
                    showNotification('Error updating IP panel order: ' + response.message, 'error');
                    // Revert to original order if there's an error
                    location.reload();
                }
            },
            error: function (xhr, status, error) {
                showNotification('Error updating IP panel order: ' + error, 'error');
                // Revert to original order if there's an error
                location.reload();
            }
        });
    }

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

    function handlePortClick(element) {
        const port = $(element).find('.port');
        const ip = port.data('ip');
        const portNumber = port.data('port');
        const description = port.data('description');

        $('#edit-port-ip').val(ip);
        $('#display-edit-port-ip').text(ip);
        $('#old-port-number').val(portNumber);
        $('#new-port-number').val(portNumber);
        $('#port-description').val(description);

        // Check if this is the last port in the panel
        const isLastPort = $(element).siblings('.port-slot:not(.add-port-slot)').length === 0;
        $('#delete-port').prop('disabled', isLastPort);
        if (isLastPort) {
            $('#delete-port').attr('title', "Can't delete the last port in a panel");
        } else {
            $('#delete-port').removeAttr('title');
        }

        editPortModal.show();
    }

    $('.network-switch').on('dragstart', function (e) {
        draggingIPPanel = this;
        e.originalEvent.dataTransfer.effectAllowed = 'move';
        e.originalEvent.dataTransfer.setData('text/html', this.outerHTML);

        // Create placeholder
        ipPanelPlaceholder = document.createElement('div');
        ipPanelPlaceholder.className = 'network-switch-placeholder';
        ipPanelPlaceholder.style.height = `${this.offsetHeight}px`;
        this.parentNode.insertBefore(ipPanelPlaceholder, this.nextSibling);

        setTimeout(() => {
            this.style.display = 'none';
        }, 0);
    });

    $('.network-switch').on('dragover', function (e) {
        e.preventDefault();
        e.originalEvent.dataTransfer.dropEffect = 'move';

        const rect = this.getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;

        if (e.originalEvent.clientY < midpoint) {
            this.parentNode.insertBefore(ipPanelPlaceholder, this);
        } else {
            this.parentNode.insertBefore(ipPanelPlaceholder, this.nextSibling);
        }
    });

    $('.network-switch').on('dragend', function (e) {
        this.style.display = 'block';
        if (ipPanelPlaceholder && ipPanelPlaceholder.parentNode) {
            ipPanelPlaceholder.parentNode.insertBefore(this, ipPanelPlaceholder);
            ipPanelPlaceholder.parentNode.removeChild(ipPanelPlaceholder);
        }
        // Wait for the next tick to ensure the DOM has updated
        setTimeout(updateIPPanelOrder, 0);
    });

    $('body').on('drop', function (e) {
        e.preventDefault();
        if (draggingIPPanel !== null) {
            if (ipPanelPlaceholder && ipPanelPlaceholder.parentNode) {
                ipPanelPlaceholder.parentNode.insertBefore(draggingIPPanel, ipPanelPlaceholder);
                ipPanelPlaceholder.parentNode.removeChild(ipPanelPlaceholder);
            }
            draggingIPPanel = null;
        }
    });

    function updateIPPanelOrder() {
        const ipOrder = [];
        $('.network-switch').each(function () {
            ipOrder.push($(this).data('ip'));
        });

        console.log("Sending IP order:", ipOrder); // Add this line for debugging

        $.ajax({
            url: '/update_ip_order',
            method: 'POST',
            data: JSON.stringify({ ip_order: ipOrder }),
            contentType: 'application/json',
            success: function (response) {
                if (response.success) {
                    // showNotification('IP panel order updated successfully', 'success');
                } else {
                    showNotification('Error updating IP panel order: ' + response.message, 'error');
                    // Revert to original order if there's an error
                    location.reload();
                }
            },
            error: function (xhr, status, error) {
                showNotification('Error updating IP panel order: ' + error, 'error');
                // Revert to original order if there's an error
                location.reload();
            }
        });
    }

    // Existing edit IP functionality
    $('.edit-ip').click(function (e) {
        e.preventDefault();
        const ip = $(this).data('ip');
        const nickname = $(this).data('nickname');
        $('#old-ip').val(ip);
        $('#new-ip').val(ip);
        $('#new-nickname').val(nickname);
        editIpModal.show();
    });

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

    // Delete IP functionality
    $('#delete-ip').click(function () {
        deleteIpAddress = $('#old-ip').val();
        $('#delete-ip-address').text(deleteIpAddress);
        editIpModal.hide();
        $('#deleteIpModal').modal('show');
    });

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

    // Edit port functionality
    $('#save-port').click(function () {
        const formData = $('#edit-port-form').serialize();
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
                editPortModal.hide();
            },
            error: function (xhr, status, error) {
                showNotification('Error updating port: ' + error, 'error');
                editPortModal.hide();
            }
        });
    });

    // Function to check if port exists
    function checkPortExists(ip, portNumber) {
        console.log("Checking if port exists:", ip, portNumber);
        const portElement = $(`.port[data-ip="${ip}"][data-port="${portNumber}"]`);
        console.log("Port element found:", portElement.length > 0);
        return portElement.length > 0;
    }

    // Add port functionality
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

    $('#save-new-port').click(function () {
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
    });

    // Delete port functionality
    let deleteIp, deletePortNumber;

    $('#delete-port').click(function () {
        deleteIp = $('#edit-port-ip').val();
        deletePortNumber = $('#old-port-number').val();
        editPortModal.hide();
        deletePortModal.show();
    });

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
});
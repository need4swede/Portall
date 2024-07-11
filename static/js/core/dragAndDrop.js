// js/core/dragAndDrop.js

import { updatePortOrder, handlePortClick, checkPortExists } from './portManagement.js';
import { updateIPPanelOrder } from './ipManagement.js';
import { showNotification } from '../ui/helpers.js';
import { movePort, changePortNumber } from '../api/ajax/helpers.js';
import { cancelDrop as cancelDropUtil } from '../utils/dragDropUtils.js';
import { showLoadingAnimation, hideLoadingAnimation } from '../ui/loadingAnimation.js';

// For dragging ports
let draggingElement = null;
let placeholder = null;
let dragStartX, dragStartY, dragStartTime;
let isDragging = false;
let sourcePanel = null;
let sourceIp = null;
const dragThreshold = 5;
const clickThreshold = 200;

// For dragging IP panels
let draggingIPPanel = null;
let ipPanelPlaceholder = null;

// For port conflict handling
let conflictingPortData = null;

/**
 * Initialize drag-and-drop event handlers.
 * Sets up event listeners for port slots and network switches.
 */
export function init() {
    $('.port-slot:not(.add-port-slot)').on('mousedown', handleMouseDown);
    $('.network-switch').on('dragstart', handleNetworkSwitchDragStart);
    $('.network-switch').on('dragover', handleNetworkSwitchDragOver);
    $('.network-switch').on('dragend', handleNetworkSwitchDragEnd);
    $('body').on('drop', handleBodyDrop);
}

/**
 * Handle mousedown event on a port slot.
 * Initiates drag detection and handles click vs. drag distinction.
 *
 * @param {Event} e - The mousedown event object
 */
function handleMouseDown(e) {
    if (e.which !== 1) return; // Only respond to left mouse button

    const panel = $(this).closest('.switch-panel');
    const isLastPort = panel.find('.port-slot:not(.add-port-slot)').length === 1;

    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragStartTime = new Date().getTime();
    const element = this;

    $(document).on('mousemove.dragdetect', function (e) {
        if (!isDragging &&
            (Math.abs(e.clientX - dragStartX) > dragThreshold ||
                Math.abs(e.clientY - dragStartY) > dragThreshold)) {
            if (isLastPort) {
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
            handlePortClick(element);
        }
        isDragging = false;
    });

    e.preventDefault();
}

/**
 * Handle drag start event for IP panels.
 * Prepares the drag operation and creates a placeholder.
 *
 * @param {Event} e - The dragstart event object
 */
function handleNetworkSwitchDragStart(e) {
    draggingIPPanel = this;
    e.originalEvent.dataTransfer.effectAllowed = 'move';
    e.originalEvent.dataTransfer.setData('text/html', this.outerHTML);

    ipPanelPlaceholder = document.createElement('div');
    ipPanelPlaceholder.className = 'network-switch-placeholder';
    ipPanelPlaceholder.style.height = `${this.offsetHeight}px`;
    this.parentNode.insertBefore(ipPanelPlaceholder, this.nextSibling);

    setTimeout(() => {
        this.style.display = 'none';
    }, 0);
}

/**
 * Handle drag over event for IP panels.
 * Adjusts the placeholder position based on the drag location.
 *
 * @param {Event} e - The dragover event object
 */
function handleNetworkSwitchDragOver(e) {
    e.preventDefault();
    e.originalEvent.dataTransfer.dropEffect = 'move';

    const rect = this.getBoundingClientRect();
    const midpoint = rect.top + rect.height / 2;

    if (e.originalEvent.clientY < midpoint) {
        this.parentNode.insertBefore(ipPanelPlaceholder, this);
    } else {
        this.parentNode.insertBefore(ipPanelPlaceholder, this.nextSibling);
    }
}

/**
 * Handle drag end event for IP panels.
 * Finalizes the drag operation, updates the order of panels,
 * shows a loading animation, and refreshes the page.
 *
 * @param {Event} e - The dragend event object
 */
function handleNetworkSwitchDragEnd(e) {
    this.style.display = 'block';

    if (ipPanelPlaceholder && ipPanelPlaceholder.parentNode) {
        ipPanelPlaceholder.parentNode.insertBefore(this, ipPanelPlaceholder);
        ipPanelPlaceholder.parentNode.removeChild(ipPanelPlaceholder);
    }

    // Update IP panel order
    updateIPPanelOrder(() => {
        // Show loading animation
        showLoadingAnimation();

        // Refresh the page after a short delay
        setTimeout(() => {
            location.reload();
        }, 1500); // 1.5 seconds delay
    });
}

/**
 * Handle drop event on the body element.
 * Completes the drag-and-drop operation for IP panels.
 *
 * @param {Event} e - The drop event object
 */
function handleBodyDrop(e) {
    e.preventDefault();
    if (draggingIPPanel !== null) {
        if (ipPanelPlaceholder && ipPanelPlaceholder.parentNode) {
            ipPanelPlaceholder.parentNode.insertBefore(draggingIPPanel, ipPanelPlaceholder);
            ipPanelPlaceholder.parentNode.removeChild(ipPanelPlaceholder);
        }
        draggingIPPanel = null;
    }
}

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
        'height': $(draggingElement).height() + 10 + 'px'
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
        const portNumber = $(draggingElement).find('.port').data('port');
        const protocol = $(draggingElement).find('.port').data('protocol');

        console.log('Port number:', portNumber);
        console.log('Protocol:', protocol);

        // Check if the port number and protocol combination already exists in the target IP group
        if (checkPortExists(targetIp, portNumber, protocol)) {
            conflictingPortData = {
                sourceIp: sourceIp,
                targetIp: targetIp,
                portNumber: portNumber,
                protocol: protocol,
                targetElement: targetElement,
                draggingElement: draggingElement
            };
            $('#conflictingPortNumber').text(`${portNumber} (${protocol})`);
            $('#portConflictModal').modal('show');
            return;
        }

        // If no conflict, proceed with the move
        proceedWithMove(portNumber, protocol, sourceIp, targetIp, targetElement, draggingElement);
    } else {
        console.log('Reordering within the same IP group');
        targetElement.parentNode.insertBefore(draggingElement, targetElement);
        updatePortOrder(sourceIp);
    }

    // Reset source variables
    sourcePanel = null;
    sourceIp = null;
}

function proceedWithMove(portNumber, protocol, sourceIp, targetIp, targetElement, draggingElement, isConflictResolution = false) {
    console.log(`Proceeding with move: ${portNumber} (${protocol}) from ${sourceIp} to ${targetIp}`);
    console.log('Dragging element:', draggingElement);
    console.log('Target element:', targetElement);

    // Insert the dragged element before the target element
    $(targetElement).before(draggingElement);

    // Move port on the server and update orders
    movePort(portNumber, sourceIp, targetIp, protocol, function (updatedPort) {
        console.log(`Move successful: ${portNumber} (${protocol}) from ${sourceIp} to ${targetIp}`);

        // Update the dragged element with new data
        const $port = $(draggingElement).find('.port');
        $port.attr('data-ip', updatedPort.ip_address);
        $port.attr('data-port', updatedPort.port_number);
        $port.attr('data-protocol', updatedPort.protocol);
        $port.attr('data-description', updatedPort.description);
        $port.attr('data-order', updatedPort.order);
        $port.attr('data-id', updatedPort.id);

        // Update the port's IP and other attributes
        const targetNickname = $(targetElement).closest('.network-switch').find('.edit-ip').data('nickname');
        $port.attr('data-nickname', targetNickname);

        updatePortOrder(sourceIp);
        updatePortOrder(targetIp);
        if (isConflictResolution) {
            refreshPageAfterDelay();
        }
    }, function () {
        console.log(`Move failed: ${portNumber} (${protocol}) from ${sourceIp} to ${targetIp}`);
        cancelDrop();
    });
}

/**
 * Cancels the drop operation and reverts the dragged element to its original position
 */
function cancelDrop() {
    cancelDropUtil(draggingElement, placeholder);
}

/**
 * Event handler for cancelling port conflict.
 * Hides the port conflict modal and reloads the page.
 */
$('#cancelPortConflict').click(function () {
    $('#portConflictModal').modal('hide');
    location.reload();
});

/**
 * Event handler for changing port during conflict resolution.
 * Determines if the migrating or existing port is being changed,
 * hides the port conflict modal, and shows the port change modal.
 */
$('#changeMigratingPort, #changeExistingPort').click(function () {
    const isChangingMigrating = $(this).attr('id') === 'changeMigratingPort';
    $('#portChangeType').text(isChangingMigrating ? 'migrating' : 'existing');
    $('#portConflictModal').modal('hide');
    $('#portChangeModal').modal('show');
});

/**
 * Event handler for confirming port change during conflict resolution.
 * Retrieves the new port number and updates the port based on whether
 * the migrating or existing port is being changed.
 * Proceeds with the port move and hides the port change modal.
 */
$('#confirmPortChange').click(function () {
    const newPortNumber = $('#newPortNumber').val();
    const isChangingMigrating = $('#portChangeType').text() === 'migrating';

    if (isChangingMigrating) {
        changePortNumber(conflictingPortData.sourceIp, conflictingPortData.portNumber, newPortNumber, function () {
            proceedWithMove(newPortNumber, conflictingPortData.protocol, conflictingPortData.sourceIp, conflictingPortData.targetIp, conflictingPortData.targetElement, conflictingPortData.draggingElement, true);
        });
    } else {
        changePortNumber(conflictingPortData.targetIp, conflictingPortData.portNumber, newPortNumber, function () {
            proceedWithMove(conflictingPortData.portNumber, conflictingPortData.protocol, conflictingPortData.sourceIp, conflictingPortData.targetIp, conflictingPortData.targetElement, conflictingPortData.draggingElement, true);
        });
    }

    $('#portChangeModal').modal('hide');
});

/**
 * Refresh the page after a delay.
 * Shows a loading animation and reloads the page after 1.5 seconds.
 */
function refreshPageAfterDelay() {
    showLoadingAnimation();
    setTimeout(function () {
        location.reload();
    }, 1500);
}

$(document).ready(init);

export { initiateDrag, getTargetElement, finalizeDrop, proceedWithMove, cancelDrop };
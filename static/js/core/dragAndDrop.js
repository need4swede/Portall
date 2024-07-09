// js/core/dragAndDrop.js

import { updatePortOrder } from './portManagement.js';
import { updateIPPanelOrder } from './ipManagement.js';
import { showNotification } from '../ui/helpers.js';
import { movePort } from '../api/ajax/helpers.js';
import { cancelDrop as cancelDropUtil } from '../utils/dragDropUtils.js';

let draggingElement = null;
let placeholder = null;
let dragStartX, dragStartY, dragStartTime;
let isDragging = false;
let sourcePanel = null;
let sourceIp = null;
const dragThreshold = 5;
const clickThreshold = 200;

let draggingIPPanel = null;
let ipPanelPlaceholder = null;

export function init() {
    $('.port-slot:not(.add-port-slot)').on('mousedown', handleMouseDown);
    $('.network-switch').on('dragstart', handleNetworkSwitchDragStart);
    $('.network-switch').on('dragover', handleNetworkSwitchDragOver);
    $('.network-switch').on('dragend', handleNetworkSwitchDragEnd);
    $('body').on('drop', handleBodyDrop);
}

function handleMouseDown(e) {
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

    $(document).on('mousemove.dragdetect', function (e) {
        if (!isDragging &&
            (Math.abs(e.clientX - dragStartX) > dragThreshold ||
                Math.abs(e.clientY - dragStartY) > dragThreshold)) {
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

function handleNetworkSwitchDragEnd(e) {
    this.style.display = 'block';

    if (ipPanelPlaceholder && ipPanelPlaceholder.parentNode) {
        ipPanelPlaceholder.parentNode.insertBefore(this, ipPanelPlaceholder);
        ipPanelPlaceholder.parentNode.removeChild(ipPanelPlaceholder);
    }

    setTimeout(updateIPPanelOrder, 0);
}

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
        const portNumber = $(draggingElement).find('.port').data('port');

        // Insert the dragged element before the target element
        $(targetElement).before(draggingElement);

        // Update the port's IP and other attributes
        $(draggingElement).find('.port').attr('data-ip', targetIp);
        const targetNickname = targetPanel.siblings('.switch-label').find('.edit-ip').data('nickname');
        $(draggingElement).find('.port').attr('data-nickname', targetNickname);

        // Move port on the server and update orders
        movePort(portNumber, sourceIp, targetIp, targetElement, draggingElement, updatePortOrder, cancelDrop);
    } else {
        console.log('Reordering within the same IP group');
        targetElement.parentNode.insertBefore(draggingElement, targetElement);
        updatePortOrder(sourceIp);
    }

    // Reset source variables
    sourcePanel = null;
    sourceIp = null;
}

/**
 * Cancels the drop operation and reverts the dragged element to its original position
 */
function cancelDrop() {
    cancelDropUtil(draggingElement, placeholder);
}

$(document).ready(init);

export { initiateDrag, getTargetElement, finalizeDrop, cancelDrop };
// js/core/dragAndDrop.js

import { updatePortOrder, handlePortClick, checkPortExists } from './portManagement.js';
import { updateIPPanelOrder } from './ipManagement.js';
import { showNotification } from '../ui/helpers.js';
import { movePort, changePortNumber } from '../api/ajax.js';
import { cancelDrop as cancelDropUtil } from '../utils/dragDropUtils.js';
import { showLoadingAnimation, hideLoadingAnimation } from '../ui/loadingAnimation.js';

/**
 * Add this at the top of dragAndDrop.js, right after your imports and before
 * variable declarations
 */

// Global variable to store port data during drag
let draggedPortData = null;

// Debug mode flag - set to true for detailed logging
const DEBUG = true;

// Debug logger function
function debug(...args) {
    if (DEBUG) {
        console.log('[DragDrop Debug]', ...args);
    }
}

/**
 * Cancels the drop operation and reverts the dragged element to its original position
 */
function cancelDrop() {
    console.log('[DragDrop Debug] Cancelling drop operation');

    // If draggingElement is null, nothing to do
    if (!draggingElement) {
        console.log('[DragDrop Debug] No dragging element to cancel');
        return;
    }

    // Try to safely remove the element's dragging styles and positioning
    try {
        $(draggingElement).removeClass('dragging');
        $(draggingElement).css({
            'position': '',
            'zIndex': '',
            'left': '',
            'top': '',
            'pointer-events': '',
            'width': '',
            'height': '',
            'opacity': '1',
            'animation': 'none',
            'transform': 'scale(1) rotate(0deg)',
            'box-shadow': '',
            'transition': 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
            'cursor': ''
        });

        // Only try to insert the element back if placeholder exists
        if (placeholder && placeholder.parentNode) {
            placeholder.parentNode.insertBefore(draggingElement, placeholder);
        }
    } catch (e) {
        console.error('Error while cancelling drop:', e);
    }

    // Remove the placeholder if it exists
    if (placeholder) {
        try {
            $(placeholder).remove();
        } catch (e) {
            console.error('Error removing placeholder:', e);
        }
    }

    // Use the utility function for cancelling the drop
    try {
        cancelDropUtil(draggingElement, placeholder);
    } catch (e) {
        console.error('Error in cancelDropUtil:', e);
    }

    // Clear the stored draggedPortData
    draggedPortData = null;

    // Reset all variables
    draggingElement = null;
    placeholder = null;
    sourcePanel = null;
    sourceIp = null;
}

/**
 * Refresh the page after a delay.
 * Shows a loading animation and reloads the page after 1.5 seconds.
 */
function refreshPageAfterDelay(delay = 1500) {
    console.log('[DragDrop Debug] Refreshing page after delay');
    showLoadingAnimation();
    setTimeout(function () {
        window.location.reload();
    }, delay);
}


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
let ipDragStartX, ipDragStartY, ipDragStartTime;
let isIPDragging = false;
const ipDragThreshold = 5;
const ipClickThreshold = 200;

// For port conflict handling
let conflictingPortData = null;

/**
 * Initialize drag-and-drop event handlers.
 * Sets up event listeners for port slots and network switches using event delegation.
 * This ensures that dynamically added elements will automatically have event handlers.
 */
export function init() {
    $(document).on('mousedown', '.port-slot:not(.add-port-slot)', handleMouseDown);
    $(document).on('mousedown', '.network-switch', handleNetworkSwitchMouseDown);
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

    // Check if the port is immutable
    const portElement = $(this).find('.port');
    const isImmutable = portElement.attr('data-immutable') === 'true';

    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragStartTime = new Date().getTime();
    const element = this;

    $(document).on('mousemove.dragdetect', function (e) {
        if (!isDragging &&
            (Math.abs(e.clientX - dragStartX) > dragThreshold ||
                Math.abs(e.clientY - dragStartY) > dragThreshold)) {

            // For immutable ports, allow limited dragging with snap-back
            if (isImmutable) {
                isDragging = true;
                initiateImmutableDrag(e, element);
                return;
            }

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
    e.stopPropagation(); // Stop event from bubbling up to parent elements
}

/**
 * Handle mousedown event on a network switch.
 * Initiates drag detection and handles click vs. drag distinction.
 *
 * @param {Event} e - The mousedown event object
 */
function handleNetworkSwitchMouseDown(e) {
    if (e.which !== 1) return; // Only respond to left mouse button
    if ($(e.target).closest('.edit-ip, .sort-btn').length) return; // Don't initiate drag if clicking on buttons

    ipDragStartX = e.clientX;
    ipDragStartY = e.clientY;
    ipDragStartTime = new Date().getTime();
    const element = this;

    $(document).on('mousemove.ipdragdetect', function (e) {
        if (!isIPDragging &&
            (Math.abs(e.clientX - ipDragStartX) > ipDragThreshold ||
                Math.abs(e.clientY - ipDragStartY) > ipDragThreshold)) {
            isIPDragging = true;
            initiateIPDrag(e, element);
        }
    });

    $(document).on('mouseup.ipdragdetect', function (e) {
        $(document).off('mousemove.ipdragdetect mouseup.ipdragdetect');
        isIPDragging = false;
    });

    e.preventDefault();
    e.stopPropagation(); // Stop event from bubbling up to parent elements
}

/**
 * Initiates the drag operation for a network switch (IP panel)
 * @param {Event} e - The event object
 * @param {HTMLElement} element - The element being dragged
 */
function initiateIPDrag(e, element) {
    draggingIPPanel = element;
    console.log('Dragging IP panel:', draggingIPPanel);

    // Stop event propagation to prevent interference with other drag operations
    e.stopPropagation();

    const rect = draggingIPPanel.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;

    // Get the exact dimensions of the element before cloning
    const originalWidth = $(draggingIPPanel).outerWidth();
    const originalHeight = $(draggingIPPanel).outerHeight();

    // Create a placeholder for the dragged element with exact same dimensions
    ipPanelPlaceholder = document.createElement('div');
    ipPanelPlaceholder.className = 'network-switch-placeholder';
    ipPanelPlaceholder.style.width = originalWidth + 'px';
    ipPanelPlaceholder.style.height = originalHeight + 'px';
    ipPanelPlaceholder.style.backgroundColor = 'rgba(0, 0, 0, 0.1)';
    ipPanelPlaceholder.style.border = '2px dashed #ccc';
    ipPanelPlaceholder.style.borderRadius = '16px';
    ipPanelPlaceholder.style.margin = '0 0 30px 0';
    draggingIPPanel.parentNode.insertBefore(ipPanelPlaceholder, draggingIPPanel.nextSibling);

    // Style the dragging element
    $(draggingIPPanel).css({
        'position': 'fixed',
        'zIndex': 1000,
        'pointer-events': 'none',
        'width': originalWidth + 'px',
        'height': originalHeight + 'px',
        'opacity': '0.8',
        'transform': 'scale(1.02)',
        'box-shadow': 'var(--hover-shadow)'
    }).addClass('dragging');

    // Handle mouse movement during drag
    function mouseMoveHandler(e) {
        $(draggingIPPanel).css({
            'left': e.clientX - offsetX + 'px',
            'top': e.clientY - offsetY + 'px'
        });

        const targetElement = getIPTargetElement(e.clientX, e.clientY);
        if (targetElement && targetElement !== draggingIPPanel) {
            const targetRect = targetElement.getBoundingClientRect();
            const targetMidpoint = targetRect.top + targetRect.height / 2;

            if (e.clientY < targetMidpoint) {
                targetElement.parentNode.insertBefore(ipPanelPlaceholder, targetElement);
            } else {
                targetElement.parentNode.insertBefore(ipPanelPlaceholder, targetElement.nextSibling);
            }
        }
    }

    // Handle mouse up to end drag
    function mouseUpHandler(e) {
        $(document).off('mousemove', mouseMoveHandler);
        $(document).off('mouseup', mouseUpHandler);

        finalizeIPDrop();
    }

    $(document).on('mousemove', mouseMoveHandler);
    $(document).on('mouseup', mouseUpHandler);
}

/**
 * Determines the target element for dropping an IP panel
 * @param {number} x - The x-coordinate of the mouse
 * @param {number} y - The y-coordinate of the mouse
 * @returns {HTMLElement|null} The target element or null if invalid
 */
function getIPTargetElement(x, y) {
    const elements = document.elementsFromPoint(x, y);
    return elements.find(el => el.classList.contains('network-switch') && el !== draggingIPPanel);
}

/**
 * Finalizes the drop operation for an IP panel
 */
function finalizeIPDrop() {
    // Reset the dragging element's style
    $(draggingIPPanel).css({
        'position': '',
        'zIndex': '',
        'left': '',
        'top': '',
        'pointer-events': '',
        'width': '',
        'height': '',
        'opacity': '',
        'transform': '',
        'box-shadow': ''
    }).removeClass('dragging');

    // Move the dragging element to the placeholder position
    if (ipPanelPlaceholder && ipPanelPlaceholder.parentNode) {
        ipPanelPlaceholder.parentNode.insertBefore(draggingIPPanel, ipPanelPlaceholder);
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

    draggingIPPanel = null;
    ipPanelPlaceholder = null;
}

/**
 * Handle drop event on the body element.
 * Completes the drag-and-drop operation for IP panels.
 *
 * @param {Event} e - The drop event object
 */
function handleBodyDrop(e) {
    e.preventDefault();
}

/**
 * Initiates a limited drag operation for immutable ports with snap-back effect
 * @param {Event} e - The event object
 * @param {HTMLElement} element - The immutable port element being dragged
 */
function initiateImmutableDrag(e, element) {
    const $element = $(element);
    const originalPosition = $element.position();
    const rect = element.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;

    // Create and show the immutable tooltip
    const immutableTooltip = document.createElement('div');
    immutableTooltip.className = 'port-tooltip immutable-tooltip';
    immutableTooltip.innerHTML = `
        <div class="tooltip-header">
            <span class="tooltip-title">Immutable Port</span>
            <span class="tooltip-protocol"><i class="fas fa-lock"></i></span>
        </div>
        <div class="tooltip-content">
            <div class="tooltip-value">This port cannot be moved because it's from a Docker integration</div>
        </div>
    `;

    // Get the enhanced tooltip if it exists
    const portTooltip = document.querySelector('.enhanced-tooltip');

    // Default tooltip dimensions
    const tooltipWidth = 250;
    const tooltipHeight = 100;
    const tooltipOffset = 15;

    // Calculate available space in each direction
    const spaceTop = rect.top;
    const spaceBottom = window.innerHeight - rect.bottom;
    const spaceLeft = rect.left;
    const spaceRight = window.innerWidth - rect.right;

    // Default to best position based on available space
    let bestPosition = 'top';
    let maxSpace = spaceTop;

    if (spaceBottom > maxSpace) {
        bestPosition = 'bottom';
        maxSpace = spaceBottom;
    }

    if (spaceLeft > maxSpace) {
        bestPosition = 'left';
        maxSpace = spaceLeft;
    }

    if (spaceRight > maxSpace) {
        bestPosition = 'right';
        maxSpace = spaceRight;
    }

    // If there's a visible port tooltip, use the opposite position
    if (portTooltip) {
        const portTooltipPosition = portTooltip.getAttribute('data-position') || 'top';

        // Use the opposite position
        switch (portTooltipPosition) {
            case 'top': bestPosition = 'bottom'; break;
            case 'bottom': bestPosition = 'top'; break;
            case 'left': bestPosition = 'right'; break;
            case 'right': bestPosition = 'left'; break;
        }

        // If opposite position has very little space, choose another direction
        const minRequiredSpace = {
            top: tooltipHeight + tooltipOffset,
            bottom: tooltipHeight + tooltipOffset,
            left: tooltipWidth + tooltipOffset,
            right: tooltipWidth + tooltipOffset
        };

        const availableSpace = {
            top: spaceTop,
            bottom: spaceBottom,
            left: spaceLeft,
            right: spaceRight
        };

        if (availableSpace[bestPosition] < minRequiredSpace[bestPosition]) {
            // Find next best position
            const positions = ['top', 'right', 'bottom', 'left'].filter(pos => pos !== portTooltipPosition);
            bestPosition = positions.reduce((best, pos) =>
                availableSpace[pos] > availableSpace[best] ? pos : best, positions[0]);
        }
    }

    // Set the immutable tooltip's position attribute
    $(immutableTooltip).attr('data-position', bestPosition);

    // Calculate position based on the determined direction
    let top, left;

    switch (bestPosition) {
        case 'top':
            top = rect.top - tooltipHeight - tooltipOffset;
            left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
            break;
        case 'bottom':
            top = rect.bottom + tooltipOffset;
            left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
            break;
        case 'left':
            top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
            left = rect.left - tooltipWidth - tooltipOffset;
            break;
        case 'right':
            top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
            left = rect.right + tooltipOffset;
            break;
    }

    // Ensure tooltip stays within viewport
    top = Math.max(10, Math.min(window.innerHeight - tooltipHeight - 10, top));
    left = Math.max(10, Math.min(window.innerWidth - tooltipWidth - 10, left));

    // Style the tooltip
    $(immutableTooltip).css({
        'position': 'fixed', // Use fixed instead of absolute to ensure proper positioning
        'zIndex': 1001,
        'background-color': 'var(--bg-card)',
        'color': 'var(--text-primary)',
        'border-radius': '8px',
        'padding': '10px',
        'box-shadow': '0 4px 8px rgba(0, 0, 0, 0.2)',
        'width': `${tooltipWidth}px`, // Set explicit width
        'pointer-events': 'none',
        'opacity': '0',
        'backdrop-filter': 'blur(50px)',
        'transition': 'opacity 0.2s ease-in-out',
        'top': top + 'px',
        'left': left + 'px'
    });

    document.body.appendChild(immutableTooltip);

    // Fade in the tooltip
    setTimeout(() => {
        $(immutableTooltip).css('opacity', '1');
    }, 10);

    // Style the dragging element
    $element.css({
        'position': 'relative',
        'zIndex': 1000,
        'transition': 'none',
        'transform': 'scale(1.02)',
        'box-shadow': 'var(--hover-shadow)'
    }).addClass('dragging-immutable');

    // Handle mouse movement during drag - limited to a small area
    function mouseMoveHandler(e) {
        // Calculate new position with a maximum distance constraint
        const maxDistance = 30; // Maximum pixels the port can be dragged
        const deltaX = e.clientX - dragStartX;
        const deltaY = e.clientY - dragStartY;

        // Calculate distance from start point
        const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

        // If distance exceeds max, scale it down
        let newDeltaX = deltaX;
        let newDeltaY = deltaY;
        if (distance > maxDistance) {
            const scale = maxDistance / distance;
            newDeltaX = deltaX * scale;
            newDeltaY = deltaY * scale;
        }

        // Apply the constrained movement
        $element.css({
            'left': newDeltaX + 'px',
            'top': newDeltaY + 'px'
        });

        // Update tooltip position based on its data-position attribute
        const tooltipPosition = $(immutableTooltip).attr('data-position');

        let newTop, newLeft;

        switch (tooltipPosition) {
            case 'top':
                newTop = rect.top - tooltipHeight - tooltipOffset + newDeltaY;
                newLeft = rect.left + (rect.width / 2) - (tooltipWidth / 2) + newDeltaX;
                break;
            case 'bottom':
                newTop = rect.bottom + tooltipOffset + newDeltaY;
                newLeft = rect.left + (rect.width / 2) - (tooltipWidth / 2) + newDeltaX;
                break;
            case 'left':
                newTop = rect.top + (rect.height / 2) - (tooltipHeight / 2) + newDeltaY;
                newLeft = rect.left - tooltipWidth - tooltipOffset + newDeltaX;
                break;
            case 'right':
                newTop = rect.top + (rect.height / 2) - (tooltipHeight / 2) + newDeltaY;
                newLeft = rect.right + tooltipOffset + newDeltaX;
                break;
        }

        // Ensure tooltip stays within viewport
        newTop = Math.max(10, Math.min(window.innerHeight - tooltipHeight - 10, newTop));
        newLeft = Math.max(10, Math.min(window.innerWidth - tooltipWidth - 10, newLeft));

        $(immutableTooltip).css({
            'top': newTop + 'px',
            'left': newLeft + 'px'
        });
    }

    // Handle mouse up to end drag with snap-back animation
    function mouseUpHandler(e) {
        $(document).off('mousemove', mouseMoveHandler);
        $(document).off('mouseup', mouseUpHandler);

        // Animate snap back to original position with elastic effect
        $element.css({
            'transition': 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
            'left': '0',
            'top': '0'
        });

        // Add elastic snap animation
        setTimeout(() => {
            $element.css('animation', 'elastic-snap 0.6s ease-out');
        }, 300);

        // Remove dragging class and reset styles after animations complete
        setTimeout(() => {
            $element.css({
                'position': '',
                'zIndex': '',
                'transition': '',
                'transform': '',
                'box-shadow': '',
                'animation': ''
            }).removeClass('dragging-immutable');

            // Fade out and remove the tooltip
            $(immutableTooltip).css('opacity', '0');
            setTimeout(() => {
                if (immutableTooltip.parentNode) {
                    immutableTooltip.parentNode.removeChild(immutableTooltip);
                }
            }, 300);
        }, 900); // Increased timeout to allow elastic animation to complete

        isDragging = false;
    }

    $(document).on('mousemove', mouseMoveHandler);
    $(document).on('mouseup', mouseUpHandler);
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

    // Store the port data at the beginning of the drag operation
    // This ensures we have the data even if DOM structure changes during drag
    const $portElement = $(element).find('.port');
    draggedPortData = {
        portNumber: $portElement.data('port'),
        protocol: $portElement.data('protocol'),
        description: $portElement.data('description'),
        id: $portElement.data('id'),
        immutable: $portElement.attr('data-immutable') === 'true'
    };

    console.log('Dragging element:', draggingElement);
    console.log('Source panel:', sourcePanel);
    console.log('Source IP:', sourceIp);
    console.log('Stored port data:', draggedPortData);

    // Stop event propagation to prevent interference with other drag operations
    e.stopPropagation();

    const rect = draggingElement.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;

    // Get the exact dimensions of the element before cloning
    const originalWidth = $(draggingElement).outerWidth();
    const originalHeight = $(draggingElement).outerHeight();

    // Create a placeholder for the dragged element with exact same dimensions
    placeholder = $(draggingElement).clone().empty().css({
        'width': originalWidth + 'px',
        'height': originalHeight + 'px',
        'background-color': 'rgba(0, 0, 0, 0.1)',
        'border': '2px dashed #ccc',
        'border-radius': '22px', // Match the port-slot border radius
        'transition': 'all 0.2s ease'
    }).insertAfter(draggingElement);

    // Update placeholder for dark mode if needed
    if ($('body').attr('data-theme') === 'dark') {
        placeholder.css({
            'background-color': 'rgba(255, 255, 255, 0.1)',
            'border': '2px dashed #444'
        });
    }

    // Hide any visible tooltips
    $(draggingElement).find('.port-tooltip').css({
        'visibility': 'hidden',
        'opacity': '0'
    });

    // Style the dragging element with exact dimensions - make it feel lighter
    $(draggingElement).css({
        'position': 'fixed',
        'zIndex': 1000,
        'pointer-events': 'none',
        'width': originalWidth + 'px',
        'height': originalHeight + 'px',
        'opacity': '0.85',
        'transform': 'scale(1.05) rotate(2deg)', // Slight rotate and scale up
        'transition': 'transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)', // Bouncy, springy effect
        'box-shadow': '0 12px 24px rgba(0, 0, 0, 0.12)', // Elevated shadow
        'cursor': 'grabbing'
    }).addClass('dragging').appendTo('body');

    // Add subtle floating animation
    $(draggingElement).css('animation', 'float 1.5s infinite alternate ease-in-out');

    // Define the float animation if it doesn't exist
    if (!document.getElementById('float-animation')) {
        const styleEl = document.createElement('style');
        styleEl.id = 'float-animation';
        styleEl.innerHTML = `
            @keyframes float {
                0% { transform: scale(1.05) rotate(2deg) translateY(0px); }
                100% { transform: scale(1.05) rotate(2deg) translateY(-5px); }
            }
        `;
        document.head.appendChild(styleEl);
    }

    // Handle mouse movement during drag
    function mouseMoveHandler(e) {
        $(draggingElement).css({
            'left': (e.clientX - offsetX) + 'px',
            'top': (e.clientY - offsetY) + 'px'
        });

        const targetElement = getTargetElement(e.clientX, e.clientY);
        if (targetElement && !$(targetElement).is(placeholder)) {
            // Add visual indicator for drop location
            $('.port-slot').removeClass('potential-drop-target');
            $(targetElement).addClass('potential-drop-target');

            // Animate the placeholder to the new position rather than jumping
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

        // Remove the float animation style if it exists
        const floatStyle = document.getElementById('float-animation');
        if (floatStyle) {
            floatStyle.remove();
        }

        $('.port-slot').removeClass('potential-drop-target');

        const targetElement = getTargetElement(e.clientX, e.clientY);
        if (targetElement) {
            // Return the element to normal with an elastic effect
            $(draggingElement).css({
                'animation': 'none',
                'transform': 'scale(1) rotate(0deg)',
                'transition': 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)' // Elastic transition
            });

            setTimeout(() => {
                finalizeDrop(targetElement);
            }, 150); // Small delay to allow the transform to complete
        } else {
            cancelDrop();
        }

        // Reset the dragging element's style with a nice transition back
        $(draggingElement).css({
            'position': '',
            'zIndex': '',
            'left': '',
            'top': '',
            'pointer-events': '',
            'width': '',
            'height': '',
            'opacity': '1',
            'animation': 'none',
            'transform': 'scale(1) rotate(0deg)',
            'box-shadow': '',
            'transition': 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)', // Elastic transition
            'cursor': ''
        }).removeClass('dragging').insertBefore(placeholder);

        placeholder.remove();
        draggingElement = null;
        placeholder = null;

        // Keep draggedPortData available for finalizeDrop
        // It will be cleared after the drop is finalized or canceled
    }

    $(document).on('mousemove', mouseMoveHandler);
    $(document).on('mouseup', mouseUpHandler);
}

/**
 * Fallback function to get the IP address for a network switch
 * This is used when the data-ip attribute is not available directly
 * @param {jQuery} $networkSwitch - jQuery object representing the network switch
 * @returns {string|null} - The IP address or null if not found
 */
function getNetworkSwitchIp($networkSwitch) {
    // First try: get from the switch-panel data-ip attribute
    const $panel = $networkSwitch.find('.switch-panel');
    if ($panel.length && $panel.data('ip')) {
        return $panel.data('ip');
    }

    // Second try: extract from the switch-label text content
    const switchLabel = $networkSwitch.find('.switch-label').text().trim();
    const ipMatch = switchLabel.match(/^([\d.]+)/);
    if (ipMatch && ipMatch[1]) {
        return ipMatch[1];
    }

    // Third try: look for port elements with data-ip
    const $port = $networkSwitch.find('.port[data-ip]').first();
    if ($port.length) {
        return $port.data('ip');
    }

    // If all else fails, return null
    return null;
}

/**
 * Determines the target element for dropping a port
 * @param {number} x - The x-coordinate of the mouse
 * @param {number} y - The y-coordinate of the mouse
 * @returns {HTMLElement|null} The target element or null if invalid
 */
function getTargetElement(x, y) {
    // Get all elements at the current mouse position
    const elements = document.elementsFromPoint(x, y);
    console.log('Elements at drop position:', elements);

    // First try to find a port-slot directly
    const portSlot = elements.find(el =>
        el.classList.contains('port-slot') &&
        el !== draggingElement &&
        !el.classList.contains('add-port-slot')
    );

    if (portSlot) {
        // Log the found port slot for debugging
        console.log('Found port slot:', portSlot);

        // Check if we're in the same panel or a different one
        const sourcePanel = $(draggingElement).closest('.switch-panel');
        const targetPanel = $(portSlot).closest('.switch-panel');
        const targetIp = targetPanel.data('ip');

        console.log('Port slot target panel:', targetPanel);
        console.log('Target IP from panel:', targetIp);

        // Store target IP directly on the element for later retrieval
        $(portSlot).attr('data-temp-target-ip', targetIp);

        // Prevent moving the last port out of a panel
        if (sourcePanel.length && targetPanel.length &&
            sourcePanel[0] !== targetPanel[0] &&
            sourcePanel.find('.port-slot:not(.add-port-slot)').length === 1) {
            console.log("Can't move the last port out of a panel");
            return null;
        }

        // Check if the dragging element is immutable using stored data
        if (draggedPortData && draggedPortData.immutable) {
            console.log("Can't move an immutable port");
            return null;
        }

        return portSlot;
    }

    // If we couldn't find a port slot, look for a switch-panel
    // This handles the case where we're dropping onto an empty area of a panel
    const switchPanel = elements.find(el => el.classList.contains('switch-panel'));
    if (switchPanel) {
        console.log('Found switch panel:', switchPanel);
        const targetIp = $(switchPanel).data('ip');
        console.log('Target IP from switch panel:', targetIp);

        // Store target IP directly on the element for later retrieval
        $(switchPanel).attr('data-temp-target-ip', targetIp);

        // Check if this is the source panel and it only has one port
        const sourcePanel = $(draggingElement).closest('.switch-panel');
        if (sourcePanel.length && sourcePanel[0] !== switchPanel &&
            sourcePanel.find('.port-slot:not(.add-port-slot)').length === 1) {
            console.log("Can't move the last port out of a panel");
            return null;
        }

        // Check if the dragging element is immutable using stored data
        if (draggedPortData && draggedPortData.immutable) {
            console.log("Can't move an immutable port");
            return null;
        }

        // Find the last port slot in this panel (excluding the add-port-slot)
        const lastPortSlot = $(switchPanel).find('.port-slot:not(.add-port-slot)').last()[0];
        if (lastPortSlot) {
            // Also store target IP on this element
            $(lastPortSlot).attr('data-temp-target-ip', targetIp);
            console.log('Using last port slot as target:', lastPortSlot);
            return lastPortSlot;
        }

        // If no port slots, use the add-port-slot as the target
        const addPortSlot = $(switchPanel).find('.add-port-slot')[0];
        if (addPortSlot) {
            // Also store target IP on this element
            $(addPortSlot).attr('data-temp-target-ip', targetIp);
            console.log('Using add-port-slot as target:', addPortSlot);
            return addPortSlot;
        }
    }

    // If we still haven't found a valid target, try to find the closest network switch
    const networkSwitch = elements.find(el => el.classList.contains('network-switch'));
    if (networkSwitch) {
        console.log('Found network switch:', networkSwitch);

        // Make sure we can get a valid IP from this network switch
        const $networkSwitch = $(networkSwitch);
        const switchIp = getNetworkSwitchIp($networkSwitch);

        if (!switchIp) {
            console.log('No valid IP found for network switch');
            return null;
        }

        console.log('Target IP from network switch:', switchIp);

        // Store target IP directly on the element for later retrieval
        $networkSwitch.attr('data-temp-target-ip', switchIp);

        // Find the switch-panel within this network switch
        const panel = $networkSwitch.find('.switch-panel')[0];
        if (panel) {
            // Also store target IP on the panel
            $(panel).attr('data-temp-target-ip', switchIp);
            console.log('Found panel in network switch:', panel);

            // Check if this is the source panel and it only has one port
            const sourcePanel = $(draggingElement).closest('.switch-panel');
            if (sourcePanel.length && sourcePanel[0] !== panel &&
                sourcePanel.find('.port-slot:not(.add-port-slot)').length === 1) {
                console.log("Can't move the last port out of a panel");
                return null;
            }

            // Check if the dragging element is immutable using stored data
            if (draggedPortData && draggedPortData.immutable) {
                console.log("Can't move an immutable port");
                return null;
            }

            // Find the last port slot in this panel (excluding the add-port-slot)
            const lastPortSlot = $(panel).find('.port-slot:not(.add-port-slot)').last()[0];
            if (lastPortSlot) {
                // Also store target IP on this element
                $(lastPortSlot).attr('data-temp-target-ip', switchIp);
                console.log('Using last port slot as target:', lastPortSlot);
                return lastPortSlot;
            }

            // If no port slots, use the add-port-slot as the target
            const addPortSlot = $(panel).find('.add-port-slot')[0];
            if (addPortSlot) {
                // Also store target IP on this element
                $(addPortSlot).attr('data-temp-target-ip', switchIp);
                console.log('Using add-port-slot as target:', addPortSlot);
                return addPortSlot;
            }
        }

        // If we still can't find a valid target within the network switch,
        // but we know it has a valid IP, create a new port slot as target
        console.log('Creating fallback target for network switch with IP:', switchIp);

        // Find or create a panel
        let switchPanel = $networkSwitch.find('.switch-panel');
        if (!switchPanel.length) {
            // In the rare case the panel doesn't exist, create it
            switchPanel = $('<div class="switch-panel"></div>').attr('data-ip', switchIp);
            $networkSwitch.append(switchPanel);
        }

        // Use the add-port-slot if it exists, otherwise return the panel itself
        const addPortSlot = switchPanel.find('.add-port-slot')[0];
        if (addPortSlot) {
            // Also store target IP on this element
            $(addPortSlot).attr('data-temp-target-ip', switchIp);
            return addPortSlot;
        } else {
            // Also store target IP on the panel
            switchPanel.attr('data-temp-target-ip', switchIp);
            return switchPanel[0];
        }
    }

    console.log('No valid drop target found');
    return null;
}

/**
 * Finalizes the drop operation for a port
 * @param {HTMLElement} targetElement - The element where the port is being dropped
 */
function finalizeDrop(targetElement) {
    if (!targetElement) {
        console.log("No valid target element provided");
        showNotification("Can't move the port - no valid drop target", 'error');
        cancelDrop();
        return;
    }

    // Use the stored draggedPortData from initiateDrag
    console.log('Using stored port data:', draggedPortData);

    // Enhanced target IP detection - first try to get the stored temp target IP
    let targetIp = $(targetElement).attr('data-temp-target-ip');
    console.log('Target IP from data-temp-target-ip attribute:', targetIp);

    let targetPanel = null;

    // If we didn't get an IP from our temp attribute, try the normal methods
    if (!targetIp) {
        // First try to get the target panel directly from the element
        targetPanel = $(targetElement).closest('.switch-panel');

        if (targetPanel.length) {
            targetIp = targetPanel.data('ip');
            console.log('Found target panel with data-ip:', targetIp);
        } else {
            // If we couldn't find a panel, try to get the IP from the network switch
            const networkSwitch = $(targetElement).closest('.network-switch');
            if (networkSwitch.length) {
                // Try to find the switch-panel within the network switch
                targetPanel = networkSwitch.find('.switch-panel');
                if (targetPanel.length) {
                    targetIp = targetPanel.data('ip');
                    console.log('Found target panel within network switch, IP:', targetIp);
                }

                // If still no IP, try to extract it from the switch label
                if (!targetIp) {
                    // Use our getNetworkSwitchIp helper function
                    targetIp = getNetworkSwitchIp(networkSwitch);
                    console.log('Got target IP from getNetworkSwitchIp:', targetIp);
                }
            }

            // Last resort - check if we're somehow dropping back on the source panel
            if (!targetIp && sourcePanel && sourcePanel.length) {
                // We might be dropping back onto our source panel
                targetIp = sourceIp;
                targetPanel = sourcePanel;
                console.log('Using source panel as target (same-panel drop):', targetIp);
            }
        }
    } else {
        // If we found a targetIp from the temp attribute, try to find the associated panel
        targetPanel = $(`.switch-panel[data-ip="${targetIp}"]`);
        console.log('Found target panel using targetIp:', targetPanel.length ? 'yes' : 'no');
    }

    console.log('Source panel:', sourcePanel);
    console.log('Target panel:', targetPanel);
    console.log('Source IP:', sourceIp);
    console.log('Target IP:', targetIp);

    // Make sure we have valid source and target IPs
    if (!sourceIp || !targetIp) {
        console.error('Invalid source or target IP');
        showNotification("Couldn't identify source or target IP address", 'error');
        cancelDrop();
        return;
    }

    // Make sure we have valid port data
    if (!draggedPortData || !draggedPortData.portNumber || !draggedPortData.protocol) {
        console.error('Missing port data in draggedPortData object');
        showNotification('Error moving port: Missing port data', 'error');
        cancelDrop();
        return;
    }

    // Check if the port is immutable
    if (draggedPortData.immutable) {
        console.log("Can't move an immutable port");
        showNotification("This port cannot be moved because it's from a Docker integration", 'error');
        cancelDrop();
        return;
    }

    if (sourceIp !== targetIp) {
        console.log('Moving port to a different IP group');

        console.log('Port number:', draggedPortData.portNumber);
        console.log('Protocol:', draggedPortData.protocol);

        // Check if the port number and protocol combination already exists in the target IP group
        if (checkPortExists(targetIp, draggedPortData.portNumber, draggedPortData.protocol)) {
            conflictingPortData = {
                sourceIp: sourceIp,
                targetIp: targetIp,
                portNumber: draggedPortData.portNumber,
                protocol: draggedPortData.protocol,
                targetElement: targetElement,
                draggingElement: draggingElement
            };
            $('#conflictingPortNumber').text(`${draggedPortData.portNumber} (${draggedPortData.protocol})`);
            $('#portConflictModal').modal('show');
            return;
        }

        // If no conflict, proceed with the move
        proceedWithMove(
            draggedPortData.portNumber,
            draggedPortData.protocol,
            sourceIp,
            targetIp,
            targetElement,
            draggingElement
        );
    } else {
        console.log('Reordering within the same IP group');

        // Make sure the target element is still in the DOM
        if (targetElement.parentNode) {
            targetElement.parentNode.insertBefore(draggingElement, targetElement);
            updatePortOrder(sourceIp);
        } else {
            // If the target element is no longer in the DOM, just append to the panel
            if (targetPanel && targetPanel.length) {
                // Find the add-port-slot and insert before it
                const addPortSlot = targetPanel.find('.add-port-slot');
                if (addPortSlot.length) {
                    addPortSlot.before(draggingElement);
                } else {
                    // Just append to the panel
                    targetPanel.append(draggingElement);
                }
                updatePortOrder(sourceIp);
            } else {
                console.error('Target element parent node not found');
                cancelDrop();
                return;
            }
        }
    }

    // Remove any temp target IP attributes we added
    $('.switch-panel, .port-slot, .network-switch').removeAttr('data-temp-target-ip');

    // Show success message
    showNotification('Port order updated', 'success');

    // Reset source variables
    sourcePanel = null;
    sourceIp = null;

    // Clear draggedPortData after successful drop
    draggedPortData = null;
}

/**
 * Proceed with moving a port from one IP address to another.
 * Inserts the dragged element before the target element, updates the server,
 * and adjusts the port order.
 *
 * @param {number} portNumber - The port number being moved
 * @param {string} protocol - The protocol of the port (e.g., 'TCP', 'UDP')
 * @param {string} sourceIp - The source IP address
 * @param {string} targetIp - The target IP address
 * @param {HTMLElement} targetElement - The target element for insertion
 * @param {HTMLElement} draggingElement - The element being dragged
 * @param {boolean} [isConflictResolution=false] - Flag indicating if this is part of conflict resolution
 */
function proceedWithMove(portNumber, protocol, sourceIp, targetIp, targetElement, draggingElement, isConflictResolution = false) {
    console.log(`Proceeding with move: ${portNumber} (${protocol}) from ${sourceIp} to ${targetIp}`);
    console.log('Dragging element:', draggingElement);
    console.log('Target element:', targetElement);

    // Validation checks
    if (!portNumber || !protocol || !sourceIp || !targetIp) {
        console.error('Missing required parameters for proceedWithMove');
        console.log('Port number:', portNumber);
        console.log('Protocol:', protocol);
        console.log('Source IP:', sourceIp);
        console.log('Target IP:', targetIp);

        showNotification('Error moving port: Missing required data', 'error');
        cancelDrop();
        return;
    }

    // Make sure targetElement is still valid
    if (!targetElement || !document.body.contains(targetElement)) {
        console.warn('Target element is no longer in the DOM');

        // Try to find a valid target element based on the targetIp
        const $panel = $(`.switch-panel[data-ip="${targetIp}"]`);
        if ($panel.length) {
            const addPortSlot = $panel.find('.add-port-slot')[0];
            if (addPortSlot) {
                console.log('Found alternative target (add-port-slot)');
                targetElement = addPortSlot;
            } else {
                console.log('Using panel as target');
                targetElement = $panel[0];
            }
        } else {
            console.error('Cannot find a valid target panel for IP:', targetIp);
            showNotification('Error moving port: Target panel not found', 'error');
            cancelDrop();
            return;
        }
    }

    // Show loading animation
    showLoadingAnimation();

    // Make sure the dragging element is still valid
    if (!draggingElement || !document.body.contains(draggingElement)) {
        console.warn('Dragging element is no longer in the DOM - using draggedPortData for the move');

        // We'll continue with the server-side move, but we'll need to refresh afterward
        const forceRefresh = true;

        // Move port on the server
        movePort(portNumber, sourceIp, targetIp, protocol, function (updatedPort) {
            console.log(`Move successful: ${portNumber} (${protocol}) from ${sourceIp} to ${targetIp}`);
            console.log('Updated port data:', updatedPort);

            // Hide loading animation
            hideLoadingAnimation();

            // Show success notification
            showNotification(`Port ${portNumber} moved successfully to ${targetIp}`, 'success');

            // Force a page refresh to update the UI
            refreshPageAfterDelay();
        }, function (errorMessage) {
            console.log(`Move failed: ${portNumber} (${protocol}) from ${sourceIp} to ${targetIp}`);
            console.error('Error message:', errorMessage);

            // Hide loading animation
            hideLoadingAnimation();

            // Show error notification
            showNotification(`Error moving port: ${errorMessage || 'Unknown error'}`, 'error');

            cancelDrop();
        });

        return;
    }

    // Insert the dragged element before the target element or into the panel
    try {
        if (targetElement.classList.contains('switch-panel')) {
            // Append to panel
            targetElement.appendChild(draggingElement);
        } else {
            // Insert before target element
            targetElement.parentNode.insertBefore(draggingElement, targetElement);
        }
    } catch (e) {
        console.error('Error inserting dragging element:', e);
        // Continue with the server-side move but prepare for a refresh
    }

    // Move port on the server and update orders
    movePort(portNumber, sourceIp, targetIp, protocol, function (updatedPort) {
        console.log(`Move successful: ${portNumber} (${protocol}) from ${sourceIp} to ${targetIp}`);
        console.log('Updated port data:', updatedPort);

        // Update the dragged element with new data if it's still in the DOM
        if (draggingElement && document.body.contains(draggingElement)) {
            const $port = $(draggingElement).find('.port');

            // Safety check - make sure we found the port element
            if ($port.length === 0) {
                console.error('Error: Could not find .port element within dragging element');
                showNotification('Error updating port data after move', 'error');
                refreshPageAfterDelay();
                return;
            }

            $port.attr('data-ip', updatedPort.ip_address);
            $port.attr('data-port', updatedPort.port_number);
            $port.attr('data-protocol', updatedPort.protocol);
            $port.attr('data-description', updatedPort.description);
            $port.attr('data-order', updatedPort.order);
            $port.attr('data-id', updatedPort.id);
            $port.attr('data-nickname', updatedPort.nickname);  // Update the nickname

            // Update the port's IP and other attributes
            const targetNickname = updatedPort.nickname;
            $port.attr('data-nickname', targetNickname);

            // Update the visual representation of the port
            $port.find('.port-number').text(updatedPort.port_number);
            $port.find('.port-description').text(updatedPort.description);
            $port.closest('.port-slot').find('.port-protocol').text(updatedPort.protocol);
        }

        // Update the order of ports for both source and target IPs
        try {
            updatePortOrder(sourceIp);
            updatePortOrder(targetIp);
        } catch (e) {
            console.error('Error updating port order:', e);
        }

        // Hide loading animation
        hideLoadingAnimation();

        // Show success notification
        showNotification(`Port ${portNumber} moved successfully to ${targetIp}`, 'success');

        if (isConflictResolution || sourceIp !== targetIp) {
            // Always refresh after cross-IP moves to ensure consistency
            refreshPageAfterDelay();
        }
    }, function (errorMessage) {
        console.log(`Move failed: ${portNumber} (${protocol}) from ${sourceIp} to ${targetIp}`);
        console.error('Error message:', errorMessage);

        // Hide loading animation
        hideLoadingAnimation();

        // Show error notification
        showNotification(`Error moving port: ${errorMessage || 'Unknown error'}`, 'error');

        cancelDrop();
    });
}

/**
 * Event handler for cancelling port conflict.
 * Hides the port conflict modal and reloads the page.
 */
$('#cancelPortConflict').click(function () {
    // Clear conflictingPortData to prevent the modal dismiss handler from triggering
    // since the user has explicitly chosen to cancel
    conflictingPortData = null;

    $('#portConflictModal').modal('hide');
    location.reload();
});

/**
 * Event handler for when the port conflict modal is dismissed without resolution.
 * This handles cases where the user clicks the "X" button, presses Escape, or clicks outside the modal.
 * Reverts the visual drag operation to match the backend state.
 */
$('#portConflictModal').on('hidden.bs.modal', function () {
    // Only call cancelDrop if we have conflicting port data (meaning the modal was shown for a conflict)
    // and the modal wasn't hidden due to a user choosing an action (which would clear conflictingPortData)
    if (conflictingPortData) {
        console.log('[DragDrop Debug] Port conflict modal dismissed without resolution - reverting drag operation');

        // Call cancelDrop to revert the visual changes
        cancelDrop();

        // Clear the conflicting port data
        conflictingPortData = null;
    }
});

/**
 * Event handler for changing port during conflict resolution.
 * Determines if the migrating or existing port is being changed,
 * hides the port conflict modal, and shows the port change modal.
 */
$('#changeMigratingPort, #changeExistingPort').click(function () {
    const isChangingMigrating = $(this).attr('id') === 'changeMigratingPort';
    $('#portChangeType').text(isChangingMigrating ? 'migrating' : 'existing');

    // Clear conflictingPortData to prevent the modal dismiss handler from triggering
    // since the user has chosen a resolution path
    conflictingPortData = null;

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

$(document).ready(init);

export { initiateDrag, getTargetElement, finalizeDrop, proceedWithMove, cancelDrop };

// static/js/ui/tooltip.js

/**
 * Enhanced Tooltip System
 *
 * A modern, animated tooltip system that ensures tooltips are always
 * on top of other elements and provides smooth animations.
 */

class EnhancedTooltip {
    constructor() {
        this.activeTooltip = null;
        this.tooltipContainer = null;
        this.tooltipZIndex = 9999;
        this.animationDuration = 300; // ms
        this.tooltipOffset = 15; // px
        this.tooltipClass = 'enhanced-tooltip';
        this.tooltipArrowClass = 'enhanced-tooltip-arrow';
        this.tooltipVisibleClass = 'enhanced-tooltip-visible';
        this.tooltipHiddenClass = 'enhanced-tooltip-hidden';
        this.tooltipPositions = ['top', 'bottom', 'left', 'right'];
        this.defaultPosition = 'top';
        this.initialized = false;
    }

    /**
     * Initialize the tooltip system
     */
    init() {
        if (this.initialized) return;

        // Create a container for all tooltips at the document root level
        this.tooltipContainer = document.createElement('div');
        this.tooltipContainer.className = 'tooltip-container';
        this.tooltipContainer.style.position = 'fixed';
        this.tooltipContainer.style.top = '0';
        this.tooltipContainer.style.left = '0';
        this.tooltipContainer.style.width = '100%';
        this.tooltipContainer.style.height = '100%';
        this.tooltipContainer.style.pointerEvents = 'none';
        this.tooltipContainer.style.zIndex = this.tooltipZIndex;
        document.body.appendChild(this.tooltipContainer);

        // Add necessary styles to the document
        this.addStyles();

        // Set up event delegation for tooltip triggers
        this.setupEventListeners();

        this.initialized = true;
        console.log('Enhanced tooltip system initialized');
    }

    /**
     * Add the necessary styles for the tooltip system
     */
    addStyles() {
        const styleElement = document.createElement('style');
        styleElement.textContent = `
            .tooltip-container {
                overflow: hidden;
            }

            .${this.tooltipClass} {
                position: absolute;
                background-color: var(--bg-card);
                color: var(--text-primary);
                border-radius: 12px;
                padding: 15px;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid var(--border-color);
                max-width: 280px;
                width: max-content;
                pointer-events: none;
                opacity: 0;
                transform-origin: center center;
                z-index: ${this.tooltipZIndex};
                transition: opacity ${this.animationDuration}ms var(--ease-out),
                            transform ${this.animationDuration}ms var(--ease-out);
            }

            .${this.tooltipVisibleClass} {
                opacity: 1;
                transform: scale(1) translateY(0);
            }

            .${this.tooltipHiddenClass} {
                opacity: 0;
                transform: scale(0.95) translateY(10px);
            }

            .${this.tooltipArrowClass} {
                position: absolute;
                width: 0;
                height: 0;
                border-style: solid;
            }

            .${this.tooltipClass}[data-position="top"] .${this.tooltipArrowClass} {
                bottom: -8px;
                left: 50%;
                margin-left: -8px;
                border-width: 8px 8px 0 8px;
                border-color: var(--bg-card) transparent transparent transparent;
            }

            .${this.tooltipClass}[data-position="bottom"] .${this.tooltipArrowClass} {
                top: -8px;
                left: 50%;
                margin-left: -8px;
                border-width: 0 8px 8px 8px;
                border-color: transparent transparent var(--bg-card) transparent;
            }

            .${this.tooltipClass}[data-position="left"] .${this.tooltipArrowClass} {
                right: -8px;
                top: 50%;
                margin-top: -8px;
                border-width: 8px 0 8px 8px;
                border-color: transparent transparent transparent var(--bg-card);
            }

            .${this.tooltipClass}[data-position="right"] .${this.tooltipArrowClass} {
                left: -8px;
                top: 50%;
                margin-top: -8px;
                border-width: 8px 8px 8px 0;
                border-color: transparent var(--bg-card) transparent transparent;
            }
        `;
        document.head.appendChild(styleElement);
    }

    /**
     * Set up event listeners for tooltip triggers
     */
    setupEventListeners() {
        // Use event delegation for port elements
        document.addEventListener('mouseover', (event) => {
            try {
                // Find the port element (either the target or a parent)
                let portElement = null;
                if (event.target.classList && event.target.classList.contains('port')) {
                    portElement = event.target;
                } else if (event.target.parentElement && event.target.parentElement.classList &&
                    event.target.parentElement.classList.contains('port')) {
                    portElement = event.target.parentElement;
                }

                // If we found a port element with a tooltip, show it
                if (portElement) {
                    const tooltipContent = portElement.querySelector('.port-tooltip');
                    if (tooltipContent) {
                        this.showTooltip(portElement, tooltipContent);
                    }
                }
            } catch (error) {
                console.error('Error in tooltip mouseover handler:', error);
            }
        });

        document.addEventListener('mouseout', (event) => {
            try {
                // Find if we're leaving a port element
                let isLeavingPort = false;

                if (event.target.classList && event.target.classList.contains('port')) {
                    isLeavingPort = true;
                } else if (event.target.parentElement && event.target.parentElement.classList &&
                    event.target.parentElement.classList.contains('port')) {
                    isLeavingPort = true;
                }

                if (isLeavingPort) {
                    this.hideTooltip();
                }
            } catch (error) {
                console.error('Error in tooltip mouseout handler:', error);
            }
        });

        // Handle scroll and resize events to reposition active tooltip
        window.addEventListener('scroll', () => {
            if (this.activeTooltip) {
                this.positionTooltip(this.activeTooltip.trigger, this.activeTooltip.tooltip);
            }
        }, { passive: true });

        window.addEventListener('resize', () => {
            if (this.activeTooltip) {
                this.positionTooltip(this.activeTooltip.trigger, this.activeTooltip.tooltip);
            }
        }, { passive: true });
    }

    /**
     * Get tooltip content from an element
     * @param {HTMLElement} element - The element to check for tooltip content
     * @returns {HTMLElement|null} - The tooltip content element or null
     */
    getTooltipContent(element) {
        if (!element || !element.classList) {
            return null;
        }

        // Check if the element is a port with a tooltip
        if (element.classList.contains('port')) {
            return element.querySelector('.port-tooltip');
        }

        // Check if the element is a child of a port
        const portParent = element.closest('.port');
        if (portParent) {
            return portParent.querySelector('.port-tooltip');
        }

        return null;
    }

    /**
     * Show a tooltip for a trigger element
     * @param {HTMLElement} triggerElement - The element triggering the tooltip
     * @param {HTMLElement} contentElement - The element containing the tooltip content
     */
    showTooltip(triggerElement, contentElement) {
        // Hide any existing tooltip
        this.hideTooltip();

        // Create a new tooltip element
        const tooltip = document.createElement('div');
        tooltip.className = `${this.tooltipClass} ${this.tooltipHiddenClass}`;
        tooltip.setAttribute('data-position', this.defaultPosition);

        // Clone the content
        const content = contentElement.cloneNode(true);
        content.style.display = 'block';
        content.style.visibility = 'visible';
        content.style.opacity = '1';
        content.style.transform = 'none';
        tooltip.appendChild(content);

        // Add arrow
        const arrow = document.createElement('div');
        arrow.className = this.tooltipArrowClass;
        tooltip.appendChild(arrow);

        // Add to container
        this.tooltipContainer.appendChild(tooltip);

        // Position the tooltip
        this.positionTooltip(triggerElement, tooltip);

        // Store the active tooltip
        this.activeTooltip = {
            trigger: triggerElement,
            tooltip: tooltip,
            content: contentElement
        };

        // Trigger animation after a small delay to ensure proper positioning
        setTimeout(() => {
            tooltip.classList.remove(this.tooltipHiddenClass);
            tooltip.classList.add(this.tooltipVisibleClass);
        }, 10);
    }

    /**
     * Hide the active tooltip
     */
    hideTooltip() {
        if (!this.activeTooltip) return;

        const { tooltip } = this.activeTooltip;

        // Trigger hide animation
        tooltip.classList.remove(this.tooltipVisibleClass);
        tooltip.classList.add(this.tooltipHiddenClass);

        // Remove from DOM after animation completes
        setTimeout(() => {
            if (tooltip.parentNode) {
                tooltip.parentNode.removeChild(tooltip);
            }
            if (this.activeTooltip && this.activeTooltip.tooltip === tooltip) {
                this.activeTooltip = null;
            }
        }, this.animationDuration);
    }

    /**
     * Position a tooltip relative to its trigger element
     * @param {HTMLElement} triggerElement - The element triggering the tooltip
     * @param {HTMLElement} tooltipElement - The tooltip element to position
     */
    positionTooltip(triggerElement, tooltipElement) {
        const triggerRect = triggerElement.getBoundingClientRect();
        const tooltipRect = tooltipElement.getBoundingClientRect();

        // Calculate available space in each direction
        const spaceTop = triggerRect.top;
        const spaceBottom = window.innerHeight - triggerRect.bottom;
        const spaceLeft = triggerRect.left;
        const spaceRight = window.innerWidth - triggerRect.right;

        // Determine best position based on available space
        let bestPosition = this.defaultPosition;
        let maxSpace = spaceTop;

        if (spaceBottom > maxSpace) {
            bestPosition = 'bottom';
            maxSpace = spaceBottom;
        }

        if (spaceLeft > maxSpace && tooltipRect.width < spaceLeft) {
            bestPosition = 'left';
            maxSpace = spaceLeft;
        }

        if (spaceRight > maxSpace && tooltipRect.width < spaceRight) {
            bestPosition = 'right';
            maxSpace = spaceRight;
        }

        // Set position attribute
        tooltipElement.setAttribute('data-position', bestPosition);

        // Calculate position based on best direction
        let top, left;

        switch (bestPosition) {
            case 'top':
                top = triggerRect.top - tooltipRect.height - this.tooltipOffset;
                left = triggerRect.left + (triggerRect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'bottom':
                top = triggerRect.bottom + this.tooltipOffset;
                left = triggerRect.left + (triggerRect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'left':
                top = triggerRect.top + (triggerRect.height / 2) - (tooltipRect.height / 2);
                left = triggerRect.left - tooltipRect.width - this.tooltipOffset;
                break;
            case 'right':
                top = triggerRect.top + (triggerRect.height / 2) - (tooltipRect.height / 2);
                left = triggerRect.right + this.tooltipOffset;
                break;
        }

        // Ensure tooltip stays within viewport
        top = Math.max(10, Math.min(window.innerHeight - tooltipRect.height - 10, top));
        left = Math.max(10, Math.min(window.innerWidth - tooltipRect.width - 10, left));

        // Apply position
        tooltipElement.style.top = `${top}px`;
        tooltipElement.style.left = `${left}px`;
    }
}

// Create and export a singleton instance
const enhancedTooltip = new EnhancedTooltip();
export default enhancedTooltip;

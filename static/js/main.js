// static/js/main.js

import * as DragAndDrop from "./core/dragAndDrop.js";
import * as IpManagement from "./core/ipManagement.js";
import * as PortManagement from "./core/portManagement.js";
import * as Modals from "./ui/modals.js";
import enhancedTooltip from "./ui/tooltip.js";
import * as Docker from "./core/docker.js";
import { initDockerAnimationStyles } from "./ui/dockerAnimation.js";

// Import tags functionality if we're on the tags page
let TagsModule = null;
if (window.location.pathname === '/tags') {
    import('./tags.js').then(module => {
        TagsModule = module;
        if (TagsModule.init) {
            TagsModule.init();
        }
    }).catch(err => {
        console.log('Tags module not needed on this page');
    });
}

function init() {
    Modals.init();  // Initialize modals first
    enhancedTooltip.init(); // Initialize enhanced tooltip system
    initDockerAnimationStyles(); // Initialize Docker animation styles
    DragAndDrop.init();
    IpManagement.init();
    PortManagement.init();

    // Initialize Docker auto-scan functionality if we're on the ports page
    if (window.location.pathname === '/' || window.location.pathname === '/ports') {
        console.log('Initializing Docker auto-scan for ports page');
        Docker.initAutoScan();
    }

    // Initialize tag loading for port tooltips
    initPortTagLoading();

    console.log("Document ready");
}

// Function to load and display tags for ports
function initPortTagLoading() {
    // Load tags for all port tooltips
    const portTagContainers = document.querySelectorAll('.port-tags[data-port-id]');

    portTagContainers.forEach(container => {
        const portId = container.getAttribute('data-port-id');
        loadPortTags(portId, container);
    });

    // Add event listeners for port tag management
    document.addEventListener('click', function (e) {
        if (e.target.closest('.port')) {
            const port = e.target.closest('.port');
            const portId = port.getAttribute('data-id');

            // Right-click to open tag management modal
            if (e.button === 2 || e.ctrlKey) {
                e.preventDefault();
                openPortTagModal(portId, port);
            }
        }
    });

    // Add context menu for tag management
    document.addEventListener('contextmenu', function (e) {
        if (e.target.closest('.port')) {
            e.preventDefault();
            const port = e.target.closest('.port');
            const portId = port.getAttribute('data-id');
            openPortTagModal(portId, port);
        }
    });
}

// Load tags for a specific port
async function loadPortTags(portId, container) {
    try {
        const response = await fetch(`/api/ports/${portId}/tags`);
        if (response.ok) {
            const data = await response.json();
            // Extract tags array from the response
            const tags = data.success ? data.tags : [];
            displayPortTags(tags, container);
        } else {
            container.innerHTML = '<span class="text-muted">No tags</span>';
        }
    } catch (error) {
        console.error('Error loading port tags:', error);
        container.innerHTML = '<span class="text-muted">Error loading tags</span>';
    }
}

// Display tags in the container
function displayPortTags(tags, container) {
    if (tags.length === 0) {
        container.innerHTML = '<span class="text-muted">No tags</span>';
        return;
    }

    const tagElements = tags.map(tag =>
        `<span class="tag-badge" style="background-color: ${tag.color}">${tag.name}</span>`
    ).join('');

    container.innerHTML = tagElements;
}

// Open port tag management modal
async function openPortTagModal(portId, portElement) {
    const modal = document.getElementById('portTagModal');
    if (!modal) {
        console.error('Port tag modal not found');
        return;
    }

    // Set port information
    document.getElementById('port-tag-port-id').value = portId;
    const portNumber = portElement.getAttribute('data-port');
    const portDescription = portElement.getAttribute('data-description');
    const portIp = portElement.getAttribute('data-ip');

    document.getElementById('port-tag-port-info').textContent =
        `${portNumber} (${portDescription}) on ${portIp}`;

    // Load current tags and available tags
    await loadCurrentPortTags(portId);
    await loadAvailableTags();

    // Show modal
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
}

// Load current tags for the port
async function loadCurrentPortTags(portId) {
    try {
        const response = await fetch(`/api/ports/${portId}/tags`);
        if (response.ok) {
            const data = await response.json();
            // Extract tags array from the response
            const tags = data.success ? data.tags : [];
            const container = document.getElementById('current-port-tags');

            if (tags.length === 0) {
                container.innerHTML = '<span class="text-muted">No tags assigned</span>';
            } else {
                const tagElements = tags.map(tag =>
                    `<span class="tag-badge" style="background-color: ${tag.color}">
                        ${tag.name}
                        <button type="button" class="tag-remove-btn" data-tag-id="${tag.id}">×</button>
                    </span>`
                ).join('');
                container.innerHTML = tagElements;

                // Add remove tag event listeners
                container.querySelectorAll('.tag-remove-btn').forEach(btn => {
                    btn.addEventListener('click', function () {
                        const tagId = this.getAttribute('data-tag-id');
                        removeTagFromPort(portId, tagId);
                    });
                });
            }
        }
    } catch (error) {
        console.error('Error loading current port tags:', error);
    }
}

// Load available tags for selection
async function loadAvailableTags() {
    try {
        const response = await fetch('/api/tags');
        if (response.ok) {
            const tags = await response.json();
            const select = document.getElementById('available-tags');

            select.innerHTML = tags.map(tag =>
                `<option value="${tag.id}" style="background-color: ${tag.color}; color: white;">
                    ${tag.name}
                </option>`
            ).join('');
        }
    } catch (error) {
        console.error('Error loading available tags:', error);
    }
}

// Remove tag from port
async function removeTagFromPort(portId, tagId) {
    try {
        const response = await fetch(`/api/ports/${portId}/tags/${tagId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Reload current tags
            await loadCurrentPortTags(portId);
            // Refresh the port tooltip tags
            const container = document.querySelector(`.port-tags[data-port-id="${portId}"]`);
            if (container) {
                await loadPortTags(portId, container);
            }
        }
    } catch (error) {
        console.error('Error removing tag from port:', error);
    }
}

// Add event listeners for tag management modal
document.addEventListener('DOMContentLoaded', function () {
    // Quick add tag button
    const quickAddBtn = document.getElementById('quick-add-tag-btn');
    if (quickAddBtn) {
        quickAddBtn.addEventListener('click', async function () {
            const name = document.getElementById('quick-tag-name').value.trim();
            const color = document.getElementById('quick-tag-color').value;

            if (!name) {
                alert('Please enter a tag name');
                return;
            }

            try {
                const response = await fetch('/api/tags', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ name, color, description: '' })
                });

                if (response.ok) {
                    // Clear inputs
                    document.getElementById('quick-tag-name').value = '';
                    document.getElementById('quick-tag-color').value = '#007bff';

                    // Reload available tags
                    await loadAvailableTags();
                }
            } catch (error) {
                console.error('Error creating tag:', error);
            }
        });
    }

    // Save port tags button
    const saveTagsBtn = document.getElementById('save-port-tags-btn');
    if (saveTagsBtn) {
        saveTagsBtn.addEventListener('click', async function () {
            const portId = document.getElementById('port-tag-port-id').value;
            const selectedTags = Array.from(document.getElementById('available-tags').selectedOptions)
                .map(option => option.value);

            try {
                const response = await fetch(`/api/ports/${portId}/tags`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ tag_ids: selectedTags })
                });

                if (response.ok) {
                    // Reload current tags
                    await loadCurrentPortTags(portId);
                    // Refresh the port tooltip tags
                    const container = document.querySelector(`.port-tags[data-port-id="${portId}"]`);
                    if (container) {
                        await loadPortTags(portId, container);
                    }

                    // Close modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('portTagModal'));
                    if (modal) {
                        modal.hide();
                    }
                }
            } catch (error) {
                console.error('Error saving port tags:', error);
            }
        });
    }
});

document.addEventListener('DOMContentLoaded', init);

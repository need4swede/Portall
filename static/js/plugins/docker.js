// static/js/plugins/docker.js

import { saveDockerConfig, testDockerConnection, fetchDockerConfig, updateDockerTabVisibility, discoverDockerPorts } from '../api/plugins/docker-ajax.js';
import { logPluginsConfig } from '../utils/logger.js';

let isInitialized = false;

/**
 * Initialize Docker-related event listeners and UI elements.
 * This function sets up all necessary event listeners for the Docker plugin
 * and performs initial checks and logging if the plugin is enabled.
 */
export function initDockerSettings() {
    const saveButton = document.getElementById('save-docker-settings');
    const configureButton = document.getElementById('configure-docker');
    const dockerHostIp = document.getElementById('docker-host-ip');
    const dockerSocketUrl = document.getElementById('docker-socket-url');
    const dockerEnabledButton = document.getElementById('docker-enabled');
    const discoverPortsButton = document.getElementById('discover-docker-ports');
    const addDockerSettingButton = document.getElementById('docker-add-btn');

    if (saveButton) {
        saveButton.addEventListener('click', handleSaveDockerSettings);
    } else {
        console.error('Save button not found');
    }

    if (configureButton) {
        configureButton.addEventListener('click', handleConfigureDocker);
    } else {
        console.error('Configure button not found');
    }

    if (dockerHostIp && dockerSocketUrl) {
        dockerHostIp.addEventListener('input', checkDockerFields);
        dockerSocketUrl.addEventListener('input', checkDockerFields);
    }

    if (dockerEnabledButton) {
        dockerEnabledButton.addEventListener('change', handleDockerEnabledChange);
    } else {
        console.error('Docker enabled checkbox not found');
    }

    if (discoverPortsButton) {
        discoverPortsButton.addEventListener('click', handleDiscoverDockerPorts);
    } else {
        console.error('Discover ports button not found');
    }

    if (addDockerSettingButton) {
        addDockerSettingButton.addEventListener('click', handleAddDockerSetting);
    } else {
        console.error('Add Docker setting button not found');
    }

    // Add event listener for tab changes
    const tabLinks = document.querySelectorAll('#settingsTabs button[data-bs-toggle="tab"]');
    tabLinks.forEach(tabLink => {
        tabLink.addEventListener('shown.bs.tab', (event) => {
            if (event.target.id !== 'docker-tab') {
                hideDockerConfig();
            }
        });
    });

    // Add event listener for window location changes
    window.addEventListener('hashchange', hideDockerConfig);

    // Load saved configuration
    fetchDockerConfig((config) => {
        if (config) {
            document.getElementById('docker-host-ip').value = config.hostIP || '';
            document.getElementById('docker-socket-url').value = config.socketURL || '';
            document.getElementById('docker-enabled').checked = config.enabled;
            checkDockerFields();
            if (config.enabled) {
                logPluginsConfig("docker", { hostIP: config.hostIP, socketURL: config.socketURL });
            }
            populateDockerSettingsTable(config.settings || []);
        }
    });

    // Initial update of Docker tab visibility
    updateDockerTabVisibility();
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
 * Handle saving Docker settings.
 * Retrieves Host IP and Socket URL from input fields and calls the saveDockerConfig function.
 */
function handleSaveDockerSettings() {
    const hostIP = document.getElementById('docker-host-ip').value;
    const socketURL = document.getElementById('docker-socket-url').value;
    const enabled = document.getElementById('docker-enabled').checked;

    if (!hostIP || !socketURL) {
        showNotification('Please enter both Host IP and Socket URL', 'error');
        return;
    }

    saveDockerSettings();
}

/**
 * Handle testing Docker connection.
 * Retrieves Host IP and Socket URL from input fields and calls the testDockerConnection function.
 */
function handleTestDockerConnection() {
    const hostIP = document.getElementById('docker-host-ip').value;
    const socketURL = document.getElementById('docker-socket-url').value;

    if (!hostIP || !socketURL) {
        showNotification('Please enter both Host IP and Socket URL', 'error');
        return;
    }

    testDockerConnection(hostIP, socketURL);
}

/**
 * Update Docker connection status in the UI.
 *
 * @param {boolean} isConnected - Whether the Docker connection is successful.
 */
export function updateConnectionStatus(isConnected) {
    const statusElement = document.getElementById('docker-connection-status');
    if (statusElement) {
        statusElement.textContent = isConnected ? 'Connected' : 'Disconnected';
        statusElement.className = isConnected ? 'text-success' : 'text-danger';
    }
}

/**
 * Handle changes to the Docker enabled checkbox.
 */
export function handleDockerEnabledChange() {
    const isEnabled = document.getElementById('docker-enabled').checked;
    const hostIP = document.getElementById('docker-host-ip').value;
    const socketURL = document.getElementById('docker-socket-url').value;

    if (isEnabled && (!hostIP || !socketURL)) {
        showNotification('Please enter both Host IP and Socket URL before enabling Docker', 'error');
        document.getElementById('docker-enabled').checked = false;
        return;
    }

    saveDockerSettings();
}

/**
 * Check if Docker fields are populated and update UI accordingly.
 * This function enables or disables the Docker checkbox based on whether
 * both the Host IP and Socket URL fields have been filled.
 */
function checkDockerFields() {
    const hostIP = document.getElementById('docker-host-ip').value.trim();
    const socketURL = document.getElementById('docker-socket-url').value.trim();
    const enabledCheckbox = document.getElementById('docker-enabled');

    if (hostIP && socketURL) {
        enabledCheckbox.disabled = false;
        enabledCheckbox.title = "Enable Docker integration";
    } else {
        enabledCheckbox.disabled = true;
        enabledCheckbox.checked = false;
        enabledCheckbox.title = "Please configure Docker first before enabling it";
    }
}

/**
 * Handle discovering Docker ports.
 * Calls the discoverDockerPorts function when the discover ports button is clicked.
 */
function handleDiscoverDockerPorts() {
    discoverDockerPorts();
}

/**
 * Handle the Configure Docker button click.
 * Toggles the visibility of the Docker configuration section.
 */
function handleConfigureDocker() {
    const dockerConfig = document.getElementById('docker-config');
    if (dockerConfig) {
        dockerConfig.classList.toggle('hidden');
        const configureButton = document.getElementById('configure-docker');
        configureButton.textContent = dockerConfig.classList.contains('hidden') ? 'Configure' : 'Hide Configuration';
    } else {
        console.error('Docker configuration section not found');
    }
}

/**
 * Hide the Docker configuration section.
 */
function hideDockerConfig() {
    const dockerConfig = document.getElementById('docker-config');
    if (dockerConfig && !dockerConfig.classList.contains('hidden')) {
        dockerConfig.classList.add('hidden');
        const configureButton = document.getElementById('configure-docker');
        if (configureButton) {
            configureButton.textContent = 'Configure';
        }
    }
}

/**
 * Handle adding a new Docker setting.
 * Adds a new row to the Docker settings table and saves the settings.
 */
function handleAddDockerSetting() {
    const hostIP = document.getElementById('new-docker-host-ip').value;
    const socketURL = document.getElementById('new-docker-socket-url').value;

    if (hostIP && socketURL) {
        addDockerSettingToTable(hostIP, socketURL);
        document.getElementById('new-docker-host-ip').value = '';
        document.getElementById('new-docker-socket-url').value = '';
        saveDockerSettings();
    } else {
        showNotification('Please enter both Host IP and Socket URL', 'error');
    }
}

/**
 * Add a new Docker setting to the table.
 * @param {string} hostIP - The Docker host IP.
 * @param {string} socketURL - The Docker socket URL.
 */
function addDockerSettingToTable(hostIP, socketURL) {
    const table = document.getElementById('docker-settings-table').getElementsByTagName('tbody')[0];
    const newRow = table.insertRow();
    newRow.innerHTML = `
        <td>${hostIP}</td>
        <td>${socketURL}</td>
        <td>
            <button class="btn btn-sm btn-danger delete-docker-setting">Delete</button>
        </td>
    `;
    newRow.querySelector('.delete-docker-setting').addEventListener('click', function () {
        table.removeChild(newRow);
        saveDockerSettings();
    });
}

/**
 * Populate the Docker settings table with saved settings.
 * @param {Array} settings - Array of saved Docker settings.
 */
function populateDockerSettingsTable(settings) {
    const table = document.getElementById('docker-settings-table').getElementsByTagName('tbody')[0];
    table.innerHTML = '';
    settings.forEach(setting => addDockerSettingToTable(setting.hostIP, setting.socketURL));
}

/**
 * Save all Docker settings, including the main settings and the table of additional settings.
 */
function saveDockerSettings() {
    const settings = [];
    const rows = document.getElementById('docker-settings-table').getElementsByTagName('tbody')[0].rows;
    for (let row of rows) {
        settings.push({
            hostIP: row.cells[0].textContent,
            socketURL: row.cells[1].textContent
        });
    }
    saveDockerConfig(
        document.getElementById('docker-host-ip').value,
        document.getElementById('docker-socket-url').value,
        document.getElementById('docker-enabled').checked,
        settings
    );
}

export { saveDockerConfig, updateDockerTabVisibility };
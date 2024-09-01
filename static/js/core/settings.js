// static/js/core/settings.js

/**
 * Manages the settings page functionality for a web application.
 * This script handles custom CSS editing, form submissions, port settings,
 * and various UI interactions.
 */

// Imports
import { exportEntries, purgeEntries } from '../api/ports-ajax.js';
import { saveThemeSettings, loadPortSettings, savePortSettings, loadAboutContent } from '../api/settings-ajax.js';
import { initDockerSettings, saveDockerConfig } from '../plugins/docker.js';
import { initPortainerSettings, savePortainerConfig } from '../plugins/portainer.js';
import { logPluginsConfig } from '../utils/logger.js';

// Global variables
let cssEditor;

// Main function
$(document).ready(function () {
    // Initialize UI components
    initializeUIComponents();

    // Initialize Plugin settings
    initializePluginSettings();

    // Initialize CodeMirror
    initializeCodeMirror();

    // Load initial settings
    loadInitialSettings();

    // Set up event listeners
    setupEventListeners();
});

// Function definitions

/**
 * Initializes UI components such as Bootstrap modals and tooltips.
 */
function initializeUIComponents() {
    // Initialize Bootstrap modal for confirmation dialogs
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));

    // Initialize tooltips
    let tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    let tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })
}

/**
 * Initializes settings for various plugins.
 */
function initializePluginSettings() {
    initPortainerSettings();
    initDockerSettings();
}

/**
 * Updates the UI to reflect the currently enabled plugins.
 * This function also sets up event listeners for enabling/disabling plugins.
 */
function updateEnabledPlugins() {
    const $enabledPlugins = $('#enabled-plugins');
    $enabledPlugins.empty(); // Clear existing entries

    const plugins = [
        {
            id: 'docker-enabled',
            name: 'Docker',
            description: 'Connects Portall to your Docker instance',
            saveConfig: saveDockerConfig,
            getConfig: () => ({
                hostIP: $('#docker-host-ip').val(),
                socketURL: $('#docker-socket-url').val()
            })
        },
        {
            id: 'portainer-enabled',
            name: 'Portainer',
            description: 'Connects Portall to your Portainer instance',
            saveConfig: savePortainerConfig,
            getConfig: () => ({
                url: $('#portainer-url').val(),
                token: $('#portainer-token').val()
            })
        }
    ];

    plugins.forEach(plugin => {
        const $checkbox = $(`#${plugin.id}`);
        $checkbox.off('change').on('change', function () {
            const isEnabled = $(this).is(':checked');
            const config = plugin.getConfig();

            if (isEnabled && Object.values(config).some(value => !value)) {
                showNotification(`Please enter all required fields for ${plugin.name} before enabling it`, 'error');
                $(this).prop('checked', false);
            } else {
                plugin.saveConfig(...Object.values(config), isEnabled);
                if (isEnabled) {
                    logPluginsConfig(plugin.name.toLowerCase(), config);
                }
            }
            updateEnabledPlugins();
        });

        if ($checkbox.is(':checked')) {
            $enabledPlugins.append(`
                <div class="enabled-plugin">
                    <div class="plugin-info">
                        <span class="plugin-name">${plugin.name}</span>: <span class="plugin-description">${plugin.description}</span>
                    </div>
                    <button class="btn btn-sm btn-danger disable-plugin" data-plugin="${plugin.id}">Disable</button>
                </div>
            `);
        }
    });

    $('.disable-plugin').off('click').on('click', function () {
        const pluginId = $(this).data('plugin');
        $(`#${pluginId}`).prop('checked', false).trigger('change');
    });
}

/**
 * Initializes CodeMirror for custom CSS editing.
 */
function initializeCodeMirror() {
    cssEditor = CodeMirror(document.getElementById("custom-css-editor"), {
        value: $('#custom-css').val(),
        mode: "text/css",
        theme: "monokai",
        lineNumbers: true,
        autoCloseBrackets: true,
        matchBrackets: true,
        indentUnit: 4,
        tabSize: 4,
        indentWithTabs: false,
        lineWrapping: true,
        extraKeys: { "Ctrl-Space": "autocomplete" },
        smartIndent: true
    });

    // Force a refresh after a short delay to ensure proper rendering
    setTimeout(function () {
        cssEditor.refresh();
    }, 100);

    // Update hidden input when CodeMirror content changes
    cssEditor.on("change", function () {
        $('#custom-css').val(cssEditor.getValue());
    });
}

/**
 * Loads initial settings including port settings, custom CSS, and enabled plugins.
 */
function loadInitialSettings() {
    // Load port settings on page load
    loadPortSettings(updatePortLengthStatus);

    // Apply custom CSS on page load
    applyCustomCSS($('#custom-css').val());

    // Call updateEnabledPlugins on page load
    updateEnabledPlugins();
}

/**
 * Displays a notification message to the user.
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

    // Remove any existing alerts
    const existingAlerts = document.querySelectorAll('#notification-area .alert');
    existingAlerts.forEach(alert => {
        if (bootstrap.Alert.getInstance(alert)) {
            bootstrap.Alert.getInstance(alert).dispose();
        }
    });

    // Add the new alert
    const notificationArea = document.getElementById('notification-area');
    notificationArea.innerHTML = notification;

    // Get the alert element
    const alertElement = notificationArea.querySelector('.alert');

    // Create a new Alert instance
    const alert = new bootstrap.Alert(alertElement);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (document.body.contains(alertElement)) {
            alert.close();
        }
    }, 5000);
}

/**
 * Updates the UI to reflect the current port length status.
 * Disables port length radio buttons if start/end values are set.
 */
function updatePortLengthStatus() {
    const portStart = $('#port-start').val();
    const portEnd = $('#port-end').val();
    const portLengthRadios = $('input[name="port_length"]');
    const portLengthControls = $('#port-length-controls');
    const portLengthHelp = $('#port-length-help');

    if (portStart || portEnd) {
        portLengthRadios.prop('disabled', true);
        portLengthControls.addClass('text-muted');
        portLengthRadios.closest('.form-check-label').css('text-decoration', 'line-through');
        portLengthHelp.show();

        // Add tooltip to the disabled radio buttons
        portLengthRadios.attr('title', 'Disabled: Port length is determined by Start/End values');
        portLengthRadios.tooltip();
    } else {
        portLengthRadios.prop('disabled', false);
        portLengthControls.removeClass('text-muted');
        portLengthRadios.closest('.form-check-label').css('text-decoration', 'none');
        portLengthHelp.hide();

        // Remove tooltip from the enabled radio buttons
        portLengthRadios.removeAttr('title');
        portLengthRadios.tooltip('dispose');
    }
}

/**
 * Applies custom CSS to the page.
 * @param {string} css - The CSS string to apply
 */
function applyCustomCSS(css) {
    let styleElement = $('#custom-style');
    if (styleElement.length === 0) {
        styleElement = $('<style id="custom-style"></style>');
        $('head').append(styleElement);
    }
    styleElement.text(css);
}

/**
 * Activates the tab corresponding to the current URL hash.
 */
function activateTabFromHash() {
    let hash = window.location.hash;
    if (hash) {
        $('.nav-tabs button[data-bs-target="' + hash + '"]').tab('show');
    }
}

/**
 * Updates the Docker tab visibility based on the enabled state.
 */
function updateDockerTabVisibility() {
    const isEnabled = $('#docker-enabled').is(':checked');
    if (isEnabled) {
        $('.docker-tab').removeClass('hidden');
    } else {
        $('.docker-tab').addClass('hidden');
        // If Docker tab is currently active, switch to Plugins tab
        if ($('#docker-tab').hasClass('active')) {
            $('#settingsTabs button[data-bs-target="#plugins"]').tab('show');
        }
    }
}

/**
 * Sets up all event listeners for the settings page.
 */
function setupEventListeners() {
    // Handle settings and theme form submissions
    $('#settings-form, #theme-form').submit(function (e) {
        e.preventDefault();
        // Update hidden input with latest CodeMirror content before submitting
        $('#custom-css').val(cssEditor.getValue());
        saveThemeSettings(e, applyCustomCSS);
    });

    // Handle purge button click
    $('#purge-button').click(function () {
        const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
        confirmModal.show();
    });

    // Handle export button click
    $('#export-entries-button').on('click', function () {
        exportEntries();
    });

    // Handle confirmation of purge action
    $('#confirm-purge').click(function () {
        const confirmModalElement = document.getElementById('confirmModal');
        purgeEntries(confirmModalElement);
    });

    // Handle tab navigation
    $('#settingsTabs button').on('click', function (e) {
        e.preventDefault();
        $(this).tab('show');
    });

    // Change hash for page-reload
    $('.nav-tabs a').on('shown.bs.tab', function (e) {
        window.location.hash = e.target.hash;
    });

    // Call on page load
    activateTabFromHash();

    // Call when hash changes
    $(window).on('hashchange', activateTabFromHash);

    // Refresh CodeMirror when its tab becomes visible
    $('button[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
        if (e.target.getAttribute('data-bs-target') === '#appearance') {
            if (cssEditor) {
                cssEditor.refresh();
            } else {
                initializeCodeMirror();
            }
        }
    });

    // Handle port settings form submission
    $('#port-settings-form').submit(function (e) {
        e.preventDefault();
        var formData = $(this).serializeArray();

        // Filter out empty values
        formData = formData.filter(function (item) {
            return item.value !== "";
        });

        savePortSettings(formData, loadPortSettings, updatePortLengthStatus);
    });

    // Add event listeners for Port Start and Port End inputs
    $('#port-start, #port-end').on('input', updatePortLengthStatus);

    // Handle clear port settings button
    $('#clear-port-settings').click(function () {
        // Clear all input fields
        $('#port-start, #port-end, #port-exclude').val('');

        // Uncheck all radio buttons
        $('input[name="port_length"]').prop('checked', false);

        // Check the default radio button (assuming 4 digits is default)
        $('#port-length-4').prop('checked', true);

        // Update the port length status
        updatePortLengthStatus();

        // Show a notification
        showNotification('Port settings cleared.');
    });

    // Call this function when the About tab is shown
    $('button[data-bs-target="#about"]').on('shown.bs.tab', function (e) {
        loadAboutContent();
    });

    // Force a refresh on window load
    $(window).on('load', function () {
        if (cssEditor) {
            cssEditor.refresh();
        }
    });

    // Handle Docker configuration button
    $('#configure-docker').on('click', function (e) {
        e.preventDefault();
        $('#settingsTabs button[data-bs-target="#docker"]').tab('show');
    });

    // Handle returning to Plugins tab when leaving Docker tab
    $('#settingsTabs button').on('shown.bs.tab', function (e) {
        if (e.relatedTarget && e.relatedTarget.id === 'docker-tab') {
            $('.docker-tab').addClass('hidden');
        }
    });

    // Handle Docker enabled checkbox
    $('#docker-enabled').on('change', function () {
        updateDockerTabVisibility();
    });
}
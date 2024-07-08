// static/js/settings.js

/**
 * Manages the settings page functionality for a web application.
 * This script handles custom CSS editing, form submissions, port settings,
 * and various UI interactions.
 */

let cssEditor;

$(document).ready(function () {
    // Initialize Bootstrap modal for confirmation dialogs
    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));

    /**
     * Initializes the CodeMirror editor for custom CSS editing.
     * Sets up the editor with specific options and event listeners.
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

    // Initialize CodeMirror on page load
    initializeCodeMirror();

    // Load port settings on page load
    loadPortSettings();

    // Apply custom CSS on page load
    applyCustomCSS($('#custom-css').val());

    /**
     * Displays a notification message to the user.
     * @param {string} message - The message to display.
     * @param {string} [type='success'] - The type of notification ('success' or 'error').
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

    // Handle settings and theme form submissions
    $('#settings-form, #theme-form').submit(function (e) {
        e.preventDefault();
        // Update hidden input with latest CodeMirror content before submitting
        $('#custom-css').val(cssEditor.getValue());
        $.ajax({
            url: '/settings',
            method: 'POST',
            data: $(this).serialize(),
            success: function (response) {
                console.log('Settings saved successfully:', response);
                showNotification('Settings saved successfully!');
                // Apply custom CSS immediately
                applyCustomCSS($('#custom-css').val());
                // Reload the page to apply the new theme
                location.reload();
            },
            error: function (xhr, status, error) {
                console.error('Error saving settings:', status, error);
                showNotification('Error saving settings.', 'error');
            }
        });
    });

    // Handle purge button click
    $('#purge-button').click(function () {
        confirmModal.show();
    });

    // Handle confirmation of purge action
    $('#confirm-purge').click(function () {
        $.ajax({
            url: '/api/purge_entries',
            method: 'POST',
            success: function (response) {
                console.log('Entries purged successfully:', response);
                showNotification(response.message);
                confirmModal.hide();
            },
            error: function (xhr, status, error) {
                console.error('Error purging entries:', status, error);
                showNotification('Error purging entries: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Unknown error occurred'), 'error');
            }
        });
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

    /**
     * Activates the correct tab based on the URL hash.
     */
    function activateTabFromHash() {
        let hash = window.location.hash;
        if (hash) {
            $('.nav-tabs button[data-bs-target="' + hash + '"]').tab('show');
        }
    }

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

    // Load port settings on page load
    $.ajax({
        url: '/api/port_settings',
        method: 'GET',
        success: function (data) {
            $('#port-start').val(data.port_start || '');
            $('#port-end').val(data.port_end || '');
            $('#port-exclude').val(data.port_exclude || '');
            if (data.port_length) {
                $(`input[name="port_length"][value="${data.port_length}"]`).prop('checked', true);
            }
            updatePortLengthStatus();
        },
        error: function (xhr, status, error) {
            console.error('Error loading port settings:', status, error);
            showNotification('Error loading port settings.', 'error');
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

        $.ajax({
            url: '/api/port_settings',
            method: 'POST',
            data: $.param(formData),
            success: function (response) {
                console.log('Port settings saved successfully:', response);
                showNotification('Port settings saved successfully!');
                loadPortSettings();
                updatePortLengthStatus();
            },
            error: function (xhr, status, error) {
                console.error('Error saving port settings:', status, error);
                showNotification('Error saving port settings: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Unknown error occurred'), 'error');
            }
        });
    });

    /**
     * Loads and updates the port settings UI.
     */
    function loadPortSettings() {
        $.ajax({
            url: '/api/port_settings',
            method: 'GET',
            success: function (data) {
                console.log("Received port settings:", data);  // Add this line for debugging

                // Clear all fields first
                $('#port-start, #port-end, #port-exclude').val('');
                $('input[name="port_length"]').prop('checked', false);
                $('input[name="copy_format"]').prop('checked', false);

                // Then set values only if they exist in the data
                if (data.port_start) $('#port-start').val(data.port_start);
                if (data.port_end) $('#port-end').val(data.port_end);
                if (data.port_exclude) $('#port-exclude').val(data.port_exclude);
                if (data.port_length) {
                    $(`input[name="port_length"][value="${data.port_length}"]`).prop('checked', true);
                }

                // Always set a value for copy_format
                const copyFormat = data.copy_format || 'port_only';
                $(`input[name="copy_format"][value="${copyFormat}"]`).prop('checked', true);

                console.log("Copy format set to:", copyFormat);  // Add this line for debugging

                updatePortLengthStatus();
            },
            error: function (xhr, status, error) {
                console.error('Error loading port settings:', status, error);
                showNotification('Error loading port settings.', 'error');
            }
        });
    }

    /**
     * Updates the UI state of port length controls based on start/end port values.
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

    // Add event listeners for Port Start and Port End inputs
    $('#port-start, #port-end').on('input', updatePortLengthStatus);

    // Initial call to set the correct state
    updatePortLengthStatus();

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

    /**
     * Applies custom CSS to the page.
     * @param {string} css - The CSS string to apply.
     */
    function applyCustomCSS(css) {
        let styleElement = $('#custom-style');
        if (styleElement.length === 0) {
            styleElement = $('<style id="custom-style"></style>');
            $('head').append(styleElement);
        }
        styleElement.text(css);
    }

    // Force a refresh on window load
    $(window).on('load', function () {
        if (cssEditor) {
            cssEditor.refresh();
        }
    });
});
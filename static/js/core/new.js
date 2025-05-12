// static/js/new.js

/**
 * Application: New Port / IP Address Generator
 * Description: AJAX requests for managing IP addresses and
 * generating ports based on user input.
 */

import { showNotification } from '../ui/helpers.js';
import { generatePort } from '../api/ajax.js';

$(document).ready(function () {
    console.log('Document ready');
    const ipSelect = $('#ip-address');
    const newIpModal = new bootstrap.Modal(document.getElementById('newIpModal'));

    /**
     * Event handler for the "Add IP" button.
     * Opens a modal for adding a new IP address and nickname.
     */
    $('#add-ip-btn').click(function () {
        console.log('Add IP button clicked');
        $('#new-ip').val('');
        $('#new-nickname').val('');
        newIpModal.show();
    });

    /**
     * Event handler for saving a new IP address.
     * Validates the IP, adds it to the select dropdown, and closes the modal.
     */
    $('#save-new-ip').click(function () {
        console.log('Save new IP clicked');
        const newIp = $('#new-ip').val().trim();
        const newNickname = $('#new-nickname').val().trim();
        if (isValidIpAddress(newIp)) {
            console.log('New IP:', newIp, 'Nickname:', newNickname);
            const optionText = newIp + (newNickname ? ` (${newNickname})` : '');
            // Add the new IP to the dropdown if it doesn't already exist
            if ($(`#ip-address option[value="${newIp}"]`).length === 0) {
                ipSelect.append(new Option(optionText, newIp));
            }
            ipSelect.val(newIp);
            newIpModal.hide();
        } else {
            console.log('Invalid IP');
            alert('Please enter a valid IP address');
        }
    });

    /**
     * Event handler for form submission.
     * Prevents default form submission, validates input, and sends an AJAX request
     * to generate a port based on the selected IP address and other inputs.
     */
    $('#port-form').submit(function (e) {
        e.preventDefault();
        const ipAddress = ipSelect.val();
        const selectedOption = ipSelect.find('option:selected');
        const nickname = selectedOption.text().match(/\((.*?)\)/)?.[1] || '';
        const portProtocol = $('#protocol').val();
        if (!ipAddress) {
            alert('Please select or enter an IP address');
            return;
        }

        // Send AJAX request to generate port
        const formData = {
            ip_address: ipAddress,
            nickname: nickname,
            description: $('#description').val(),
            protocol: portProtocol
        }
        generatePort(formData)
    });
});

/**
 * Validates an IP address.
 * @param {string} ip - The IP address to validate.
 * @returns {boolean} True if the IP address is valid, false otherwise.
 */
function isValidIpAddress(ip) {
    const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (ipv4Regex.test(ip)) {
        const parts = ip.split('.');
        return parts.every(part => parseInt(part) >= 0 && parseInt(part) <= 255);
    }
    return false;
}

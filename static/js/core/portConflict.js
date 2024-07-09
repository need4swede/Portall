// In js/core/portConflict.js

import { showNotification } from '../ui/helpers.js';

export function handlePortConflict(sourcePort, destinationPort, onResolve) {
    const modal = new bootstrap.Modal(document.getElementById('portConflictModal'));

    $('#sourcePortInfo').text(`${sourcePort.ip}:${sourcePort.number}`);
    $('#destinationPortInfo').text(`${destinationPort.ip}:${destinationPort.number}`);

    $('#changeSourcePort').val(sourcePort.number);
    $('#changeDestinationPort').val(destinationPort.number);

    $('#resolveConflict').off('click').on('click', function () {
        const newSourcePort = $('#changeSourcePort').val();
        const newDestinationPort = $('#changeDestinationPort').val();

        if (newSourcePort === newDestinationPort) {
            showNotification('Port numbers must be different', 'error');
            return;
        }

        if (newSourcePort !== sourcePort.number) {
            // Change source port number
            onResolve('changeSource', newSourcePort);
        } else if (newDestinationPort !== destinationPort.number) {
            // Change destination port number
            onResolve('changeDestination', newDestinationPort);
        } else {
            // Delete destination port
            onResolve('deleteDestination');
        }

        modal.hide();
    });

    modal.show();
}
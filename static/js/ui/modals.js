// static/js/ui/modals.js

export let editIpModal, editPortModal, addPortModal, deletePortModal;

export function init() {
    editIpModal = new bootstrap.Modal(document.getElementById('editIpModal'));
    editPortModal = new bootstrap.Modal(document.getElementById('editPortModal'));
    addPortModal = new bootstrap.Modal(document.getElementById('addPortModal'));
    deletePortModal = new bootstrap.Modal(document.getElementById('deletePortModal'));
}
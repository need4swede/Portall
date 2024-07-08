// static/js/animations.js

/**
 * Application: Animation Logic
 * Description: Handles animations and transitions for the application.
 *
 * Uses jQuery for DOM manipulation and Bootstrap for animations.
 */

$(document).ready(function () {

    // Animate buttons on hover
    $('.btn').hover(
        function () { $(this).addClass('animate__animated animate__pulse'); },
        function () { $(this).removeClass('animate__animated animate__pulse'); }
    );

    // Show modals
    $('.modal').on('show.bs.modal', function (e) {
        $(this).find('.modal-dialog').attr('class', 'modal-dialog animate__animated');
    });

    // Hide modals
    $('.modal').on('hide.bs.modal', function (e) {
        $(this).find('.modal-dialog').attr('class', 'modal-dialog animate__animated');
    });

    // Show dropdown menus
    $('.dropdown-toggle').on('show.bs.dropdown', function () {
        $(this).find('.dropdown-menu').first().stop(true, true).slideDown(200);
    });

    // Hide dropdown menus
    $('.dropdown-toggle').on('hide.bs.dropdown', function () {
        $(this).find('.dropdown-menu').first().stop(true, true).slideUp(200);
    });

});
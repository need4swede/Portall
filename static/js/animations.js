$(document).ready(function () {
    // Animate navbar items
    // $('.navbar-nav .nav-link').each(function (index) {
    //     $(this).css('animation-delay', `${index * 0.1}s`);
    // });

    // // Animate content on page load
    // $('.container.mt-5').children().addClass('animate__animated animate__fadeIn');

    // Animate buttons on hover
    $('.btn').hover(
        function () { $(this).addClass('animate__animated animate__pulse'); },
        function () { $(this).removeClass('animate__animated animate__pulse'); }
    );

    // Animate modals
    $('.modal').on('show.bs.modal', function (e) {
        $(this).find('.modal-dialog').attr('class', 'modal-dialog animate__animated');
    });

    $('.modal').on('hide.bs.modal', function (e) {
        $(this).find('.modal-dialog').attr('class', 'modal-dialog animate__animated');
    });

    // Animate dropdown menus
    $('.dropdown-toggle').on('show.bs.dropdown', function () {
        $(this).find('.dropdown-menu').first().stop(true, true).slideDown(200);
    });

    $('.dropdown-toggle').on('hide.bs.dropdown', function () {
        $(this).find('.dropdown-menu').first().stop(true, true).slideUp(200);
    });
});
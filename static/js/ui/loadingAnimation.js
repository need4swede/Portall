// js/ui/loadingAnimation.js

export function showLoadingAnimation() {
    const loadingHTML = `
        <div id="loading-overlay" class="position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center" style="background-color: rgba(0,0,0,0.5); z-index: 9999;">
            <div class="text-center">
                <div class="spinner-border text-light" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="mt-2 text-light">
                    <i class="fas fa-anchor fa-2x"></i>
                    <p class="mt-2">Anchors aweigh! Refreshing Portall...</p>
                </div>
            </div>
        </div>
    `;
    $('body').append(loadingHTML);
}

export function hideLoadingAnimation() {
    $('#loading-overlay').remove();
}
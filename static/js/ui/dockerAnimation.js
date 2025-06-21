// static/js/ui/dockerAnimation.js

/**
 * Docker logo animation system for auto-scan feedback.
 * Provides visual feedback during Docker scanning operations.
 */

/**
 * Show Docker logo animation during scanning.
 * The logo fades in and pulses with a blue color during the scan.
 */
export function showDockerScanAnimation() {
    // Remove any existing animation
    hideDockerScanAnimation();

    // Create the Docker logo animation container
    const animationHtml = `
        <div id="docker-scan-animation" class="docker-scan-overlay">
            <div class="docker-scan-container">
                <div class="docker-logo-wrapper">
                    <svg class="docker-logo" viewBox="0 0 24 24" width="48" height="48">
                        <path fill="currentColor" d="M13.983 11.078h2.119a.186.186 0 00.186-.185V9.006a.186.186 0 00-.186-.186h-2.119a.185.185 0 00-.185.185v1.888c0 .102.083.185.185.185m-2.954-5.43h2.118a.186.186 0 00.186-.186V3.574a.186.186 0 00-.186-.185h-2.118a.185.185 0 00-.185.185v1.888c0 .102.082.185.185.186m0 2.716h2.118a.187.187 0 00.186-.186V6.29a.186.186 0 00-.186-.185h-2.118a.185.185 0 00-.185.185v1.887c0 .102.082.185.185.186m-2.93 0h2.12a.186.186 0 00.185-.186V6.29a.185.185 0 00-.185-.185H8.1a.185.185 0 00-.185.185v1.887c0 .102.083.185.185.186m-2.964 0h2.119a.186.186 0 00.185-.186V6.29a.185.185 0 00-.185-.185H5.136a.186.186 0 00-.186.185v1.887c0 .102.084.185.186.186m5.893 2.715h2.118a.186.186 0 00.186-.185V9.006a.186.186 0 00-.186-.186h-2.118a.185.185 0 00-.185.185v1.888c0 .102.082.185.185.185m-2.93 0h2.12a.185.185 0 00.185-.185V9.006a.185.185 0 00-.185-.186H8.1a.185.185 0 00-.185.185v1.888c0 .102.083.185.185.185m-2.964 0h2.119a.185.185 0 00.185-.185V9.006a.185.185 0 00-.185-.186H5.136a.186.186 0 00-.186.186v1.887c0 .102.084.185.186.185m-2.92 0h2.12a.185.185 0 00.185-.185V9.006a.185.185 0 00-.185-.186h-2.12a.185.185 0 00-.185.185v1.888c0 .102.083.185.185.185M23.763 9.89c-.065-.051-.672-.51-1.954-.51-.338 0-.676.033-1.01.099-.663-1.998-2.639-2.676-2.762-2.725l-.203-.065-.135.175c-.316.406-.684 1.213-.684 1.213c-.133.58-.17 1.197-.17 1.197c.013.581.123 1.139.3 1.658a2.543 2.543 0 01-.762.106H.157a.186.186 0 00-.186.186 9.67 9.67 0 00.084 1.518 6.466 6.466 0 001.525 3.312c.915 1.07 2.458 1.618 4.59 1.618 4.337 0 7.548-2.018 9.298-5.842a7.35 7.35 0 001.858.24c1.254 0 2.043-.494 2.043-.494.692-.319 1.268-.824 1.268-.824a.185.185 0 00.055-.157v-.039a.186.186 0 00-.129-.154"/>
                    </svg>
                </div>
                <div class="docker-scan-text">Scanning containers...</div>
            </div>
        </div>
    `;

    // Add to body
    $('body').append(animationHtml);

    // Trigger animation
    setTimeout(() => {
        $('#docker-scan-animation').addClass('active');
    }, 10);
}

/**
 * Show success animation - transforms Docker logo into a green checkmark.
 *
 * @param {string} message - Success message to display
 * @param {number} duration - How long to show the success state (default: 2000ms)
 */
export function showDockerScanSuccess(message = 'Scan completed!', duration = 2000) {
    const $animation = $('#docker-scan-animation');
    if ($animation.length === 0) return;

    // Update to success state
    $animation.addClass('success');

    // Update the logo to a checkmark
    const $logoWrapper = $animation.find('.docker-logo-wrapper');
    $logoWrapper.html(`
        <svg class="success-check" viewBox="0 0 24 24" width="48" height="48">
            <path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
        </svg>
    `);

    // Update text
    $animation.find('.docker-scan-text').text(message);

    // Hide after duration
    setTimeout(() => {
        hideDockerScanAnimation();
    }, duration);
}

/**
 * Show error animation - transforms Docker logo into a red X.
 *
 * @param {string} message - Error message to display
 * @param {number} duration - How long to show the error state (default: 3000ms)
 */
export function showDockerScanError(message = 'Scan failed!', duration = 3000) {
    const $animation = $('#docker-scan-animation');
    if ($animation.length === 0) return;

    // Update to error state
    $animation.addClass('error');

    // Update the logo to an X
    const $logoWrapper = $animation.find('.docker-logo-wrapper');
    $logoWrapper.html(`
        <svg class="error-x" viewBox="0 0 24 24" width="48" height="48">
            <path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
        </svg>
    `);

    // Update text
    $animation.find('.docker-scan-text').text(message);

    // Hide after duration
    setTimeout(() => {
        hideDockerScanAnimation();
    }, duration);
}

/**
 * Hide the Docker scan animation.
 */
export function hideDockerScanAnimation() {
    const $animation = $('#docker-scan-animation');
    if ($animation.length === 0) return;

    $animation.removeClass('active');

    setTimeout(() => {
        $animation.remove();
    }, 300);
}

/**
 * Initialize Docker animation styles.
 * This should be called once when the page loads.
 */
export function initDockerAnimationStyles() {
    // Check if styles are already added
    if ($('#docker-animation-styles').length > 0) return;

    const styles = `
        <style id="docker-animation-styles">
            .docker-scan-overlay {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                opacity: 0;
                transform: translateY(-20px);
                transition: all 0.3s ease-in-out;
                pointer-events: none;
            }

            .docker-scan-overlay.active {
                opacity: 1;
                transform: translateY(0);
            }

            .docker-scan-container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(0, 123, 255, 0.2);
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 12px;
                min-width: 200px;
            }

            .docker-logo-wrapper {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, #007bff, #0056b3);
                color: white;
                animation: dockerPulse 2s ease-in-out infinite;
                transition: all 0.3s ease-in-out;
            }

            .docker-logo {
                transition: all 0.3s ease-in-out;
            }

            .docker-scan-text {
                font-size: 14px;
                font-weight: 500;
                color: #333;
                text-align: center;
                margin: 0;
            }

            /* Success state */
            .docker-scan-overlay.success .docker-logo-wrapper {
                background: linear-gradient(135deg, #28a745, #1e7e34);
                animation: successBounce 0.6s ease-out;
            }

            .docker-scan-overlay.success .docker-scan-text {
                color: #28a745;
            }

            /* Error state */
            .docker-scan-overlay.error .docker-logo-wrapper {
                background: linear-gradient(135deg, #dc3545, #c82333);
                animation: errorShake 0.6s ease-out;
            }

            .docker-scan-overlay.error .docker-scan-text {
                color: #dc3545;
            }

            /* Animations */
            @keyframes dockerPulse {
                0%, 100% {
                    transform: scale(1);
                    box-shadow: 0 0 0 0 rgba(0, 123, 255, 0.4);
                }
                50% {
                    transform: scale(1.05);
                    box-shadow: 0 0 0 10px rgba(0, 123, 255, 0);
                }
            }

            @keyframes successBounce {
                0% { transform: scale(1); }
                50% { transform: scale(1.2); }
                100% { transform: scale(1); }
            }

            @keyframes errorShake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-5px); }
                75% { transform: translateX(5px); }
            }

            /* Dark theme support */
            @media (prefers-color-scheme: dark) {
                .docker-scan-container {
                    background: rgba(33, 37, 41, 0.95);
                    border-color: rgba(0, 123, 255, 0.3);
                }

                .docker-scan-text {
                    color: #f8f9fa;
                }

                .docker-scan-overlay.success .docker-scan-text {
                    color: #28a745;
                }

                .docker-scan-overlay.error .docker-scan-text {
                    color: #dc3545;
                }
            }

            /* Mobile responsive */
            @media (max-width: 768px) {
                .docker-scan-overlay {
                    top: 10px;
                    right: 10px;
                    left: 10px;
                    right: 10px;
                }

                .docker-scan-container {
                    padding: 16px;
                    min-width: auto;
                }

                .docker-logo-wrapper {
                    width: 50px;
                    height: 50px;
                }

                .docker-scan-text {
                    font-size: 13px;
                }
            }
        </style>
    `;

    $('head').append(styles);
}

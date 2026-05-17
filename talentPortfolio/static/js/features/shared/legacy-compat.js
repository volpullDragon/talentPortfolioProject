/* Legacy compatibility behaviors that preserve older template interactions without forcing those templates to be rewritten immediately.
   This module keeps password visibility toggles and old file-input label updates working while the codebase moves toward more structured components.
   New interaction patterns should prefer route-specific modules instead of growing this compatibility layer. */
(function (window, document) {
    'use strict';

    // Toggle password field visibility and switch the eye icon state.
    // Swap a password field between masked and visible states for older forms.
    function togglePasswordVisibility(button) {
        if (!button) {
            return;
        }

        var targetId = button.getAttribute('data-target');
        if (!targetId) {
            return;
        }

        var input = document.getElementById(targetId);
        if (!input) {
            return;
        }

        var isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';

        var icon = button.querySelector('i');
        if (icon) {
            icon.className = isPassword ? 'bi bi-eye-slash' : 'bi bi-eye';
        }
    }

    // Attach legacy helpers that older templates still expect from the shell.
    function initLegacyInteractions() {
        var fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(function (input) {
            if (input.hasAttribute('data-upload-input') || input.closest('[data-add-project-page]')) {
                return;
            }

            input.addEventListener('change', function () {
                var files = this.files;
                var label = this.previousElementSibling;
                if (!label || !files || files.length === 0) {
                    return;
                }

                var baseText = label.textContent.split(' (')[0];
                label.textContent = baseText + ' (' + files.length + ' file' + (files.length > 1 ? 's' : '') + ' selected)';
            });
        });
    }

    window.LegacyCompat = Object.assign({}, window.LegacyCompat, {
        initLegacyInteractions: initLegacyInteractions,
        togglePasswordVisibility: togglePasswordVisibility,
    });

    // Backward-compatible global used by settings templates.
    window.togglePasswordVisibility = togglePasswordVisibility;

    var bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : function (fn) { document.addEventListener('DOMContentLoaded', fn, { once: true }); };

    bindReady(initLegacyInteractions);
}(window, document));

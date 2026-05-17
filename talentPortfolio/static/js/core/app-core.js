/* Shared application core helpers for DOM ready binding, CSRF lookup, and global alert rendering.
   Other JS modules use this as the thin compatibility layer that bridges newer namespaced helpers and older globals.
   Keep this file small and dependency-free so it can bootstrap the rest of the client-side code safely. */
(function (window, document) {
    'use strict';

    function bindDomReady(callback) {
        if (typeof callback !== 'function') {
            return;
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback, { once: true });
            return;
        }

        callback();
    }

    function getGlobalCsrfToken() {
        var tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (tokenInput && tokenInput.value) {
            return tokenInput.value;
        }

        var tokenCookie = document.cookie.split('; ').find(function (row) {
            return row.indexOf('csrftoken=') === 0;
        });

        return tokenCookie ? tokenCookie.split('=')[1] : '';
    }

    function showGlobalSystemAlert(message, level) {
        var alertLevel = level || 'success';
        if (!message) {
            return;
        }

        var container = document.querySelector('.content-wrapper');
        if (!container) {
            return;
        }

        var alert = document.createElement('div');
        alert.className = 'alert alert-' + alertLevel + ' alert-dismissible fade show';
        alert.setAttribute('role', 'alert');
        alert.appendChild(document.createTextNode(message));

        var closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('data-bs-dismiss', 'alert');
        closeButton.setAttribute('aria-label', 'Close');
        alert.appendChild(closeButton);

        container.prepend(alert);
    }
    var confirmModalEl = null;
    var confirmModalInstance = null;
    var confirmModalTitleEl = null;
    var confirmModalMessageEl = null;
    var confirmModalCancelEl = null;
    var confirmModalAcceptEl = null;
    var confirmResolve = null;
    var confirmGuardsBound = false;
    var approvedSubmitForms = new WeakSet();

    function ensureConfirmModal() {
        if (confirmModalEl) {
            return confirmModalInstance;
        }

        confirmModalEl = document.querySelector('[data-global-confirm-modal]');
        if (!confirmModalEl) {
            return null;
        }

        confirmModalTitleEl = confirmModalEl.querySelector('#globalConfirmModalTitle');
        confirmModalMessageEl = confirmModalEl.querySelector('[data-global-confirm-message]');
        confirmModalCancelEl = confirmModalEl.querySelector('[data-global-confirm-cancel]');
        confirmModalAcceptEl = confirmModalEl.querySelector('[data-global-confirm-accept]');

        if (window.bootstrap && window.bootstrap.Modal) {
            confirmModalInstance = window.bootstrap.Modal.getOrCreateInstance(confirmModalEl, { backdrop: 'static', keyboard: true });
        }

        if (confirmModalAcceptEl) {
            confirmModalAcceptEl.addEventListener('click', function () {
                if (confirmResolve) {
                    confirmResolve(true);
                    confirmResolve = null;
                }
                if (confirmModalInstance) {
                    confirmModalInstance.hide();
                }
            });
        }

        if (confirmModalCancelEl) {
            confirmModalCancelEl.addEventListener('click', function () {
                if (confirmResolve) {
                    confirmResolve(false);
                    confirmResolve = null;
                }
                if (confirmModalInstance) {
                    confirmModalInstance.hide();
                }
            });
        }

        confirmModalEl.addEventListener('hidden.bs.modal', function () {
            if (confirmResolve) {
                confirmResolve(false);
                confirmResolve = null;
            }
        });

        return confirmModalInstance;
    }

    function confirmAction(message, options) {
        var confirmOptions = options || {};
        var fallbackMessage = message || 'Are you sure?';
        var modalInstance = ensureConfirmModal();

        if (!modalInstance || !confirmModalEl || !confirmModalMessageEl) {
            return Promise.resolve(false);
        }

        if (confirmResolve) {
            confirmResolve(false);
            confirmResolve = null;
        }

        if (confirmModalTitleEl) {
            confirmModalTitleEl.textContent = confirmOptions.title || 'Please confirm';
        }
        confirmModalMessageEl.textContent = fallbackMessage;
        if (confirmModalAcceptEl) {
            confirmModalAcceptEl.textContent = confirmOptions.confirmText || 'Continue';
            confirmModalAcceptEl.className = 'btn ' + (confirmOptions.confirmClass || 'btn-danger');
        }
        if (confirmModalCancelEl) {
            confirmModalCancelEl.textContent = confirmOptions.cancelText || 'Cancel';
        }

        return new Promise(function (resolve) {
            confirmResolve = resolve;
            modalInstance.show();
        });
    }

    function bindConfirmGuards(root) {
        if (confirmGuardsBound) {
            return;
        }
        confirmGuardsBound = true;

        var scope = root || document;

        scope.addEventListener('submit', function (event) {
            var form = event.target;
            if (!form || !form.matches || !form.matches('form[data-confirm-message]')) {
                return;
            }

            if (approvedSubmitForms.has(form)) {
                approvedSubmitForms.delete(form);
                return;
            }

            event.preventDefault();
            confirmAction(form.getAttribute('data-confirm-message'), {
                title: form.getAttribute('data-confirm-title') || 'Please confirm',
                confirmText: form.getAttribute('data-confirm-confirm-text') || 'Continue',
                confirmClass: form.getAttribute('data-confirm-confirm-class') || 'btn-danger'
            }).then(function (approved) {
                if (!approved) {
                    return;
                }

                approvedSubmitForms.add(form);
                if (typeof form.requestSubmit === 'function') {
                    form.requestSubmit();
                } else {
                    HTMLFormElement.prototype.submit.call(form);
                }
            });
        }, true);

        scope.addEventListener('click', function (event) {
            var link = event.target && event.target.closest ? event.target.closest('a[data-confirm-message]') : null;
            if (!link) {
                return;
            }

            event.preventDefault();
            confirmAction(link.getAttribute('data-confirm-message'), {
                title: link.getAttribute('data-confirm-title') || 'Please confirm',
                confirmText: link.getAttribute('data-confirm-confirm-text') || 'Continue',
                confirmClass: link.getAttribute('data-confirm-confirm-class') || 'btn-danger'
            }).then(function (approved) {
                if (approved) {
                    window.location.assign(link.href);
                }
            });
        }, true);
    }


    window.AppCore = Object.assign({}, window.AppCore, {
        bindDomReady: bindDomReady,
        confirmAction: confirmAction,
        getGlobalCsrfToken: getGlobalCsrfToken,
        showGlobalSystemAlert: showGlobalSystemAlert
    });

    // Backward-compatible globals used elsewhere in legacy scripts.
    window.getGlobalCsrfToken = getGlobalCsrfToken;
    window.showGlobalSystemAlert = showGlobalSystemAlert;
    window.confirmAction = confirmAction;

    bindDomReady(bindConfirmGuards);
}(window, document));

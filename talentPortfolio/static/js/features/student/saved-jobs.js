/* Student saved jobs interactions for unsaving items, updating counts, and maintaining the empty state.
   This module keeps the saved-jobs route synchronized with the server response and removes cards from the list when the save state changes.
   It should remain narrowly focused on the saved-jobs page instead of handling generic bookmark behavior. */
(function (window, document) {
    'use strict';

    // Show the result of an unsave action using the shared alert styling.
    function showAlert(message, level) {
        if (window.AppCore && typeof window.AppCore.showGlobalSystemAlert === 'function') {
            window.AppCore.showGlobalSystemAlert(message, level);
            return;
        }
        if (typeof window.showGlobalSystemAlert === 'function') {
            window.showGlobalSystemAlert(message, level);
        }
    }

    // Read the CSRF token used by the saved-jobs unsave request.
    function getCsrf() {
        if (window.AppCore && typeof window.AppCore.getGlobalCsrfToken === 'function') {
            return window.AppCore.getGlobalCsrfToken();
        }
        if (typeof window.getGlobalCsrfToken === 'function') {
            return window.getGlobalCsrfToken();
        }
        return '';
    }

    // Use the shared confirmation modal when available before unsaving a job.
    function requestDeleteConfirmation(button) {
        const message = button.getAttribute('data-confirm-message') || 'Remove this saved job?';
        const options = {
            title: button.getAttribute('data-confirm-title') || 'Please confirm',
            confirmText: button.getAttribute('data-confirm-confirm-text') || 'Continue',
            confirmClass: button.getAttribute('data-confirm-confirm-class') || 'btn-danger',
        };

        if (window.AppCore && typeof window.AppCore.confirmAction === 'function') {
            return window.AppCore.confirmAction(message, options);
        }

        if (typeof window.confirmAction === 'function') {
            return window.confirmAction(message, options);
        }

        return Promise.resolve(window.confirm(message));
    }

    // Keep the saved-jobs list and empty state in sync after unsaving.
    function initStudentSavedJobsInteractions() {
        const root = document.querySelector('[data-student-saved-jobs]');
        if (!root) {
            return;
        }

        const saveUrlTemplate = root.getAttribute('data-save-url-template') || '';
        const countNode = root.querySelector('[data-saved-jobs-count]');
        const listNode = root.querySelector('[data-saved-jobs-list]');

        // Update the saved-job counter so the empty-state logic stays accurate.
        const syncCount = () => {
            if (!countNode || !listNode) {
                return;
            }

            const total = listNode.querySelectorAll('[data-saved-job-card]').length;
            countNode.textContent = String(total);

            let emptyNode = listNode.querySelector('[data-saved-jobs-empty]');
            if (total === 0 && !emptyNode) {
                emptyNode = document.createElement('div');
                emptyNode.className = 'student-empty-card';
                emptyNode.setAttribute('data-saved-jobs-empty', '1');
                emptyNode.textContent = 'No saved jobs yet. Save jobs from the dashboard or job detail page.';
                listNode.appendChild(emptyNode);
            }

            if (total > 0 && emptyNode) {
                emptyNode.remove();
            }
        };

        root.querySelectorAll('[data-student-unsave-job]').forEach((button) => {
            button.addEventListener('click', async () => {
                if (button.dataset.pending === '1') {
                    return;
                }

                const jobId = button.getAttribute('data-job-id');
                if (!jobId || !saveUrlTemplate.includes('/0/')) {
                    return;
                }

                const approved = await requestDeleteConfirmation(button);
                if (!approved) {
                    return;
                }

                button.dataset.pending = '1';
                const url = saveUrlTemplate.replace('/0/', `/${jobId}/`);

                try {
                    const response = await fetch(url, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCsrf(),
                            'X-Requested-With': 'XMLHttpRequest',
                        },
                        credentials: 'same-origin',
                    });
                    const payload = await response.json();
                    if (!response.ok || payload.success !== true) {
                        throw new Error(payload.error || payload.message || 'Unable to update saved job.');
                    }

                    if (payload.saved === false) {
                        const card = button.closest('[data-saved-job-card]');
                        if (card) {
                            card.remove();
                        }
                        syncCount();
                    }

                    showAlert(payload.message || 'Saved jobs updated.');
                } catch (error) {
                    showAlert(error?.message || 'Unable to update saved job.', 'danger');
                } finally {
                    button.dataset.pending = '0';
                }
            });
        });
    }

    window.StudentSavedJobs = Object.assign({}, window.StudentSavedJobs, {
        init: initStudentSavedJobsInteractions,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initStudentSavedJobsInteractions);
}(window, document));

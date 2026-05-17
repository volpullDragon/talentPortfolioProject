/* Student job board interactions for searching, filtering, and saving jobs from the listings page.
   This module owns the page-level AJAX and navigation behavior that keeps the search results responsive without reloading the whole app shell logic.
   Keep it focused on job board actions so the student detail and saved-job screens can maintain their own interaction layers. */
(function (window, document) {
    'use strict';

    // Resolve the CSRF token for the job board's form submissions and AJAX actions.
    function getCsrf() {
        if (window.AppCore && typeof window.AppCore.getGlobalCsrfToken === 'function') {
            return window.AppCore.getGlobalCsrfToken();
        }

        if (typeof window.getGlobalCsrfToken === 'function') {
            return window.getGlobalCsrfToken();
        }

        return '';
    }

    // Surface a consistent alert message through the shared alert container.
    function showAlert(message, level) {
        if (window.AppCore && typeof window.AppCore.showGlobalSystemAlert === 'function') {
            window.AppCore.showGlobalSystemAlert(message, level);
            return;
        }

        if (typeof window.showGlobalSystemAlert === 'function') {
            window.showGlobalSystemAlert(message, level);
        }
    }

    // Bind search, filter, save, and apply behavior for the student job board.
    function initStudentJobBoardInteractions() {
        var root = document.querySelector('[data-student-job-board]');
        if (!root) {
            return;
        }

        var applyUrlTemplate = root.getAttribute('data-apply-url-template') || '';
        var saveUrlTemplate = root.getAttribute('data-save-url-template') || '';
        var searchInput = root.querySelector('#jobSearch, .search-input');
        var searchButton = root.querySelector('[data-student-search-submit]');
        var searchTarget = root.getAttribute('data-search-target') || window.location.pathname;

        // Rebuild the query string so the job search can navigate with filters intact.
        var redirectStudentSearch = function () {
            if (!searchInput) {
                return;
            }

            var params = new URLSearchParams(window.location.search);
            var query = (searchInput.value || '').trim();

            if (query) {
                params.set('q', query);
            } else {
                params.delete('q');
            }
            params.delete('page');

            var queryString = params.toString();
            window.location.assign(queryString ? (searchTarget + '?' + queryString) : searchTarget);
        };

        if (searchButton && searchInput) {
            searchButton.addEventListener('click', redirectStudentSearch);

            searchInput.addEventListener('keydown', function (event) {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    redirectStudentSearch();
                }
            });
        }

        var fieldFilterControl = root.querySelector('[data-student-field-filter]');
        if (fieldFilterControl) {
            fieldFilterControl.addEventListener('change', function () {
                var selectedField = (fieldFilterControl.value || 'all').trim();
                var params = new URLSearchParams(window.location.search);

                if (selectedField && selectedField !== 'all') {
                    params.set('field', selectedField);
                } else {
                    params.delete('field');
                }
                params.delete('page');

                var queryString = params.toString();
                window.location.assign(queryString ? (searchTarget + '?' + queryString) : searchTarget);
            });
        }

        root.querySelectorAll('[data-student-save-job]').forEach(function (button) {
            var icon = button.querySelector('i.bi');

            // Toggle the saved-state icon so the button reflects the current server state.
            var syncSavedIcon = function (isSaved) {
                button.classList.toggle('saved', isSaved);
                button.setAttribute('aria-pressed', isSaved ? 'true' : 'false');
                if (icon) {
                    icon.classList.toggle('bi-bookmark-fill', isSaved);
                    icon.classList.toggle('bi-bookmark', !isSaved);
                }
            };

            syncSavedIcon(button.classList.contains('saved'));

            button.addEventListener('click', async function () {
                if (button.dataset.pending === '1') {
                    return;
                }

                var jobId = button.getAttribute('data-job-id');
                if (!jobId || saveUrlTemplate.indexOf('/0/') === -1) {
                    return;
                }

                button.dataset.pending = '1';
                var url = saveUrlTemplate.replace('/0/', '/' + jobId + '/');

                try {
                    var response = await fetch(url, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCsrf(),
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        credentials: 'same-origin'
                    });
                    var payload = await response.json();
                    if (!response.ok || payload.success !== true) {
                        throw new Error(payload.error || payload.message || 'Unable to update saved job.');
                    }

                    syncSavedIcon(Boolean(payload.saved));
                    showAlert(payload.message || 'Saved jobs updated.');
                } catch (error) {
                    showAlert(error && error.message ? error.message : 'Unable to update saved job.', 'danger');
                } finally {
                    button.dataset.pending = '0';
                }
            });
        });

        root.querySelectorAll('[data-student-apply-job]').forEach(function (button) {
            button.addEventListener('click', async function () {
                if (button.dataset.pending === '1' || button.disabled) {
                    return;
                }

                var jobId = button.getAttribute('data-job-id');
                if (!jobId || applyUrlTemplate.indexOf('/0/') === -1) {
                    return;
                }

                button.dataset.pending = '1';
                var url = applyUrlTemplate.replace('/0/', '/' + jobId + '/');

                try {
                    var response = await fetch(url, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCsrf(),
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        credentials: 'same-origin'
                    });
                    var payload = await response.json();
                    if (!response.ok || payload.success !== true) {
                        throw new Error(payload.error || payload.message || 'Unable to submit application.');
                    }

                    button.disabled = true;
                    button.textContent = 'Applied';
                    showAlert(payload.message || 'Application submitted successfully.');
                } catch (error) {
                    showAlert(error && error.message ? error.message : 'Unable to submit application.', 'danger');
                } finally {
                    button.dataset.pending = '0';
                }
            });
        });
    }

    window.StudentJobBoard = Object.assign({}, window.StudentJobBoard, {
        init: initStudentJobBoardInteractions
    });

    if (window.AppCore && typeof window.AppCore.bindDomReady === 'function') {
        window.AppCore.bindDomReady(initStudentJobBoardInteractions);
    } else if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initStudentJobBoardInteractions, { once: true });
    } else {
        initStudentJobBoardInteractions();
    }
}(window, document));

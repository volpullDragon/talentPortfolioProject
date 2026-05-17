/* Student job detail interactions for application and save actions plus the match meter display.
   The module owns the detail-page AJAX flows, button state updates, and progress visualization for a single job listing.
   It should stay separate from the broader job board so the detail view can evolve independently. */
(function (window, document) {
    'use strict';

    // Display the apply/save result on the job detail page.
    function showAlert(message, level) {
        if (window.AppCore && typeof window.AppCore.showGlobalSystemAlert === 'function') {
            window.AppCore.showGlobalSystemAlert(message, level);
            return;
        }
        if (typeof window.showGlobalSystemAlert === 'function') {
            window.showGlobalSystemAlert(message, level);
        }
    }

    // Retrieve the CSRF token for job detail form actions.
    function getCsrf() {
        if (window.AppCore && typeof window.AppCore.getGlobalCsrfToken === 'function') {
            return window.AppCore.getGlobalCsrfToken();
        }
        if (typeof window.getGlobalCsrfToken === 'function') {
            return window.getGlobalCsrfToken();
        }
        return '';
    }

    // Wire up save and apply controls on the single job detail page.
    function initStudentJobDetailInteractions() {
        const root = document.querySelector('[data-student-job-detail]');
        if (!root) {
            return;
        }

        const applyButton = root.querySelector('[data-student-apply-btn]');
        const saveButton = root.querySelector('[data-student-save-btn]');
        const applyUrl = root.getAttribute('data-apply-url') || '';
        const saveUrl = root.getAttribute('data-save-url') || '';

        const matchCard = root.querySelector('[data-match-score]');
        const meterFill = root.querySelector('[data-student-match-meter-fill]');
        if (matchCard && meterFill) {
            const rawScore = Number.parseInt(matchCard.getAttribute('data-match-score') || '0', 10);
            const safeScore = Number.isFinite(rawScore) ? Math.max(0, Math.min(100, rawScore)) : 0;
            meterFill.style.width = `${safeScore}%`;
        }

        if (saveButton && saveUrl) {
            saveButton.addEventListener('click', async () => {
                if (saveButton.dataset.pending === '1') {
                    return;
                }

                saveButton.dataset.pending = '1';
                try {
                    const response = await fetch(saveUrl, {
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

                    const isSaved = Boolean(payload.saved);
                    saveButton.classList.toggle('is-saved', isSaved);
                    saveButton.setAttribute('aria-pressed', isSaved ? 'true' : 'false');

                    const icon = saveButton.querySelector('i.bi');
                    if (icon) {
                        icon.classList.toggle('bi-bookmark-fill', isSaved);
                        icon.classList.toggle('bi-bookmark', !isSaved);
                    }

                    const label = saveButton.querySelector('span');
                    if (label) {
                        label.textContent = isSaved ? 'Saved' : 'Save for Later';
                    }

                    showAlert(payload.message || 'Saved jobs updated.');
                } catch (error) {
                    showAlert(error?.message || 'Unable to update saved job.', 'danger');
                } finally {
                    saveButton.dataset.pending = '0';
                }
            });
        }

        if (applyButton && applyUrl) {
            applyButton.addEventListener('click', async () => {
                if (applyButton.dataset.pending === '1' || applyButton.disabled) {
                    return;
                }

                applyButton.dataset.pending = '1';
                try {
                    const response = await fetch(applyUrl, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCsrf(),
                            'X-Requested-With': 'XMLHttpRequest',
                        },
                        credentials: 'same-origin',
                    });
                    const payload = await response.json();
                    if (!response.ok || payload.success !== true) {
                        throw new Error(payload.error || payload.message || 'Unable to submit application.');
                    }

                    applyButton.disabled = true;
                    const textNode = applyButton.querySelector('span');
                    if (textNode) {
                        textNode.textContent = 'Application Submitted';
                    } else {
                        applyButton.textContent = 'Application Submitted';
                    }

                    showAlert(payload.message || 'Application submitted successfully.');
                } catch (error) {
                    showAlert(error?.message || 'Unable to submit application.', 'danger');
                } finally {
                    applyButton.dataset.pending = '0';
                }
            });
        }
    }

    window.StudentJobDetail = Object.assign({}, window.StudentJobDetail, {
        init: initStudentJobDetailInteractions,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initStudentJobDetailInteractions);
}(window, document));

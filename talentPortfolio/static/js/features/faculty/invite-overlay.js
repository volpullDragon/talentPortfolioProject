/* Faculty invite overlay interactions for opening the invitation modal, syncing the selected job, and managing submit state.
   This module owns the message draft, character counter, hidden job ID, and modal lifecycle so the invitation flow remains self-contained.
   Keep it focused on invite composition and submission rather than generic modal behavior. */
(function (window, document) {
    'use strict';

    // Initialize the faculty invite modal, counters, and selected job state.
    function initFacultyInviteOverlay() {
        const page = document.querySelector('[data-faculty-dashboard-page]');
        if (!page) {
            return;
        }

        const overlay = document.querySelector('[data-invite-overlay]');
        const inviteForm = overlay ? overlay.querySelector('[data-invite-form]') : null;
        const inviteButtons = page.querySelectorAll('[data-open-invite-overlay]');
        const closeButtons = overlay ? overlay.querySelectorAll('[data-close-invite-overlay]') : [];
        const jobSelect = overlay ? overlay.querySelector('[data-invite-job-select]') : null;
        const messageField = overlay ? overlay.querySelector('#invite-message') : null;
        const charCount = overlay ? overlay.querySelector('[data-char-count]') : null;
        const hiddenJobId = overlay ? overlay.querySelector('[data-hidden-job-id]') : null;
        const submitButton = inviteForm ? inviteForm.querySelector('button[type="submit"]') : null;
        const inviteUrlTemplate = page.getAttribute('data-invite-url-template') || '';

        if (!overlay || !inviteForm || !inviteButtons.length || !messageField || !charCount || !hiddenJobId || !submitButton) {
            return;
        }

        let isSubmitting = false;

        // Update the remaining-character counter as the invite message changes.
        const syncCounter = () => {
            charCount.textContent = `${messageField.value.length} / 1000 characters`;
        };

        // Mirror the currently chosen job into the hidden form field.
        const syncJobSelection = () => {
            hiddenJobId.value = jobSelect ? jobSelect.value : '';
        };

        // Hide the modal and reset the controls to their default state.
        const closeOverlay = () => {
            overlay.hidden = true;
            overlay.classList.remove('is-open');
            document.body.classList.remove('invite-overlay-open');

            inviteForm.removeAttribute('action');
            messageField.value = '';
            if (jobSelect) {
                jobSelect.value = '';
            }
            hiddenJobId.value = '';
            isSubmitting = false;
            submitButton.disabled = false;
            submitButton.textContent = 'Send Invitation';
            syncCounter();
        };

        // Pre-fill the modal from the clicked invite button before showing it.
        const openOverlay = (button) => {
            const studentId = button.getAttribute('data-student-id');
            const studentName = button.getAttribute('data-student-name') || 'there';
            if (!studentId || !inviteUrlTemplate.includes('/0/')) {
                return;
            }

            inviteForm.action = inviteUrlTemplate.replace('/0/', `/${studentId}/`);
            messageField.value = `Hi ${studentName}, we reviewed your profile and believe you'd be a great fit for this opportunity. We'd love to discuss it with you.`;

            syncJobSelection();
            syncCounter();

            overlay.hidden = false;
            overlay.classList.add('is-open');
            document.body.classList.add('invite-overlay-open');
            messageField.focus();
            messageField.setSelectionRange(messageField.value.length, messageField.value.length);
        };

        inviteButtons.forEach((button) => {
            button.addEventListener('click', () => {
                openOverlay(button);
            });
        });

        closeButtons.forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                closeOverlay();
            });
        });

        const backdrop = overlay.querySelector('.invite-overlay-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', closeOverlay);
        }

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && overlay.classList.contains('is-open')) {
                closeOverlay();
            }
        });

        messageField.addEventListener('input', syncCounter);
        if (jobSelect) {
            jobSelect.addEventListener('change', syncJobSelection);
        }

        inviteForm.addEventListener('submit', (event) => {
            if (isSubmitting) {
                event.preventDefault();
                return;
            }

            isSubmitting = true;
            submitButton.disabled = true;
            submitButton.textContent = 'Sending...';
        });

        syncCounter();
    }

    window.FacultyInviteOverlay = Object.assign({}, window.FacultyInviteOverlay, {
        init: initFacultyInviteOverlay,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initFacultyInviteOverlay);
}(window, document));

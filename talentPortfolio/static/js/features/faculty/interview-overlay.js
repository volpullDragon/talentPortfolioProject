/* Faculty interview overlay interactions for opening, closing, and pre-filling the scheduling modal.
   The module coordinates the overlay state with the trigger data attributes and keeps the interview type fields visible or hidden as needed.
   Because the overlay is reused across schedule flows, keep its responsibilities limited to modal orchestration. */
(function (window, document) {
    'use strict';

    // Initialize the interview scheduling modal and keep its fields in sync.
    function initInterviewScheduleOverlay() {
        const pageRoot = document.querySelector('[data-interview-schedule-root]');
        const overlay = document.querySelector('[data-interview-overlay]');

        if (!pageRoot || !overlay) {
            return;
        }

        const panel = overlay.querySelector('.interview-overlay-panel');
        const form = overlay.querySelector('form');
        const closeButtons = overlay.querySelectorAll('[data-interview-overlay-close]');
        const openButtons = document.querySelectorAll('[data-open-interview-modal]');

        if (!form) {
            return;
        }

        const jobField = form.querySelector("[name='job_listing']");
        const studentField = form.querySelector("[name='student_portfolio']");
        const typeField = form.querySelector("[name='interview_type']");
        const dateField = form.querySelector("[name='scheduled_date']");
        const timeField = form.querySelector("[name='scheduled_time']");
        const locationField = form.querySelector("[name='location']");
        const teamsField = form.querySelector("[name='teams_meeting_link']");
        const descriptionField = form.querySelector("[name='description']");

        const locationRow = overlay.querySelector('[data-interview-location-row]');
        const teamsRow = overlay.querySelector('[data-interview-teams-row]');

        // Set a field value without breaking the modal's existing state.
        const setFieldValue = (field, value) => {
            if (!field || value === undefined || value === null || value === '') {
                return;
            }
            field.value = String(value);
        };

        // Show or hide date and time inputs based on the chosen interview type.
        const updateInterviewTypeFields = () => {
            if (!typeField) {
                return;
            }

            const selectedType = typeField.value;
            const showTeams = selectedType === 'video';
            const showLocation = selectedType === 'in_person';

            if (teamsRow) {
                teamsRow.style.display = showTeams ? 'block' : 'none';
            }

            if (locationRow) {
                locationRow.style.display = showLocation ? 'block' : 'none';
            }
        };

        // Close the overlay and clear any transient trigger state.
        const closeOverlay = () => {
            overlay.classList.remove('is-open');
            overlay.setAttribute('aria-hidden', 'true');
            document.body.classList.remove('interview-overlay-open');
        };

        // Populate the form from the clicked trigger before showing the overlay.
        const openOverlay = (trigger) => {
            if (trigger && trigger.dataset) {
                setFieldValue(jobField, trigger.dataset.jobId);
                setFieldValue(studentField, trigger.dataset.studentId);
                setFieldValue(typeField, trigger.dataset.interviewType);
                setFieldValue(dateField, trigger.dataset.date);
                setFieldValue(timeField, trigger.dataset.time);
                setFieldValue(locationField, trigger.dataset.location);
                setFieldValue(teamsField, trigger.dataset.teamsLink);
                setFieldValue(descriptionField, trigger.dataset.description);
            }

            updateInterviewTypeFields();

            overlay.classList.add('is-open');
            overlay.setAttribute('aria-hidden', 'false');
            document.body.classList.add('interview-overlay-open');

            const focusTarget = studentField || jobField || panel;
            if (focusTarget && typeof focusTarget.focus === 'function') {
                focusTarget.focus();
            }
        };

        openButtons.forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                openOverlay(button);
            });
        });

        closeButtons.forEach((button) => {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                closeOverlay();
            });
        });

        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) {
                closeOverlay();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && overlay.classList.contains('is-open')) {
                closeOverlay();
            }
        });

        if (typeField) {
            typeField.addEventListener('change', updateInterviewTypeFields);
        }

        updateInterviewTypeFields();

        const shouldAutoOpen = pageRoot.dataset.openSchedule === '1' || pageRoot.dataset.formInvalid === '1';
        if (shouldAutoOpen) {
            openOverlay(null);
        }
    }

    window.FacultyInterviewOverlay = Object.assign({}, window.FacultyInterviewOverlay, {
        init: initInterviewScheduleOverlay,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initInterviewScheduleOverlay);
}(window, document));

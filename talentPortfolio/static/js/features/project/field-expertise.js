/* Field expertise page interactions for confidence selection, autosave, and skill pill rendering.
   The module ties the confidence slider to its displayed label and the field-specific styling variables that drive the route theme.
   It should keep the confidence workflow self-contained so other project pages can reuse only the generic helper functions. */
(function (window, document) {
    'use strict';

    // Initialize the confidence slider, auto-save, and skill rendering workflow.
    function initFieldExpertisePage() {
        const page = document.querySelector('[data-field-projects-page]');
        if (!page) {
            return;
        }

        const fieldName = page.getAttribute('data-field-name') || '';
        const confidenceText = page.getAttribute('data-confidence-source') || '';

        const theme = typeof window.getFieldThemeFromName === 'function'
            ? window.getFieldThemeFromName(fieldName)
            : { accentStart: '#2563eb', accentEnd: '#1d4ed8', accent: '#1d4ed8', soft: '#dbeafe', deep: '#1e3a8a' };

        page.style.setProperty('--field-accent-start', theme.accentStart);
        page.style.setProperty('--field-accent-end', theme.accentEnd);
        page.style.setProperty('--field-accent', theme.accent);
        page.style.setProperty('--field-accent-soft', theme.soft);
        page.style.setProperty('--field-accent-deep', theme.deep);

        const parsePercent = typeof window.parseConfidencePercent === 'function'
            ? window.parseConfidencePercent
            : () => 0;
        const normalizePercent = typeof window.normalizeConfidencePercent === 'function'
            ? window.normalizeConfidencePercent
            : (value) => value;
        const getLabelForPercent = typeof window.getConfidenceLabelForPercent === 'function'
            ? window.getConfidenceLabelForPercent
            : () => 'Moderate Confidence';

        const split = typeof window.splitSkills === 'function'
            ? window.splitSkills
            : (raw) => Array.from(new Set((raw || '').split(/[,\n;/|]+/).map((item) => item.trim()).filter(Boolean)));

        const confidenceFill = page.querySelector('[data-confidence-fill]');
        const confidenceValue = page.querySelector('[data-confidence-value]');
        const confidenceTrack = page.querySelector('.field-confidence-track');
        const confidenceLabel = page.querySelector('[data-confidence-label]');
        const confidenceSlider = page.querySelector('[data-confidence-slider]');
        const confidenceHidden = page.querySelector('[data-confidence-hidden]');
        const confidenceSelected = page.querySelector('[data-confidence-selected]');
        const confidenceForm = page.querySelector('[data-confidence-form]');

        const initialPercent = parsePercent(confidenceText);
        const initialSliderPercent = initialPercent < 20 ? 60 : normalizePercent(initialPercent);

        // Map the stored slider value to the visible percentage scale.
        const getSliderVisualPercent = (value) => {
            if (!confidenceSlider) {
                return value;
            }

            const min = Number.parseInt(confidenceSlider.min || '0', 10);
            const max = Number.parseInt(confidenceSlider.max || '100', 10);

            if (Number.isNaN(min) || Number.isNaN(max) || max <= min) {
                return value;
            }

            return ((value - min) / (max - min)) * 100;
        };

        // Apply the chosen confidence level to the slider and supporting labels.
        const applyConfidencePercent = (percent) => {
            const normalizedPercent = normalizePercent(percent);
            const label = getLabelForPercent(normalizedPercent);

            if (confidenceValue) {
                confidenceValue.textContent = `${normalizedPercent}%`;
            }
            if (confidenceTrack) {
                confidenceTrack.setAttribute('aria-valuenow', String(normalizedPercent));
            }
            if (confidenceFill) {
                const visualPercent = getSliderVisualPercent(normalizedPercent);
                confidenceFill.style.width = `${visualPercent}%`;
            }
            if (confidenceLabel) {
                confidenceLabel.textContent = label;
            }
            if (confidenceSelected) {
                confidenceSelected.textContent = `${label} (${normalizedPercent}%)`;
            }
            if (confidenceSlider) {
                confidenceSlider.value = String(normalizedPercent);
            }
            if (confidenceHidden) {
                confidenceHidden.value = label;
            }
        };

        // Submit the confidence form and update the UI from the returned HTML.
        const submitConfidenceForm = async () => {
            if (!confidenceForm) {
                return;
            }

            const formData = new FormData(confidenceForm);

            try {
                await fetch(window.location.href, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: formData,
                    credentials: 'same-origin',
                });
            } catch (error) {
                console.error('Confidence autosave failed:', error);
            }
        };

        let autoSaveTimer = null;

        // Debounce autosave so rapid slider changes do not spam the server.
        const scheduleAutoSave = () => {
            if (!confidenceForm) {
                return;
            }

            if (autoSaveTimer) {
                window.clearTimeout(autoSaveTimer);
            }

            autoSaveTimer = window.setTimeout(async () => {
                await submitConfidenceForm();
            }, 450);
        };

        applyConfidencePercent(initialSliderPercent);

        if (confidenceForm) {
            confidenceForm.addEventListener('submit', (event) => {
                event.preventDefault();
            });
        }

        if (confidenceSlider) {
            const onSliderInput = () => {
                const sliderPercent = Number.parseInt(confidenceSlider.value || '0', 10);
                applyConfidencePercent(sliderPercent);
                scheduleAutoSave();
            };

            const onSliderChange = () => {
                const sliderPercent = Number.parseInt(confidenceSlider.value || '0', 10);
                applyConfidencePercent(sliderPercent);

                if (autoSaveTimer) {
                    window.clearTimeout(autoSaveTimer);
                }
                void submitConfidenceForm();
            };

            confidenceSlider.addEventListener('input', onSliderInput);
            confidenceSlider.addEventListener('change', onSliderChange);
        }

        const skillsRows = page.querySelectorAll('[data-skill-pills]');
        skillsRows.forEach((row) => {
            const source = row.getAttribute('data-skills-source') || '';
            const skills = split(source);

            if (!skills.length) {
                const fallback = document.createElement('span');
                fallback.className = 'field-skill-pill';
                fallback.textContent = 'No skills listed';
                row.replaceChildren(fallback);
                return;
            }

            const fragment = document.createDocumentFragment();
            skills.forEach((skill) => {
                const pill = document.createElement('span');
                pill.className = row.classList.contains('field-project-placeholder-row') ? 'field-project-placeholder-pill' : 'field-skill-pill';
                pill.textContent = skill;
                fragment.appendChild(pill);
            });

            row.replaceChildren(fragment);
        });
    }

    window.FieldExpertisePage = Object.assign({}, window.FieldExpertisePage, {
        init: initFieldExpertisePage,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initFieldExpertisePage);
}(window, document));

/* Faculty job detail interactions for pill editors and delete confirmation on the job detail route.
   This module turns freeform inputs into pill lists, syncs hidden form values, and guards destructive actions with a confirmation prompt.
   It is intentionally route-specific because the faculty job detail screen has its own editing workflow. */
(function (window, document) {
    'use strict';

    // Initialize the faculty job detail page and its editable pill lists.
    function initFacultyJobDetailPage() {
        const page = document.querySelector('[data-faculty-job-detail-page]');
        if (!page) {
            return;
        }

        const split = typeof window.splitSkills === 'function'
            ? window.splitSkills
            : (raw) => Array.from(new Set((raw || '').split(/[,\n;/|]+/).map((item) => item.trim()).filter(Boolean)));

        const editors = page.querySelectorAll('[data-pill-editor]');
        editors.forEach((editor) => {
            const hiddenInput = editor.querySelector('[data-pill-hidden-input]');
            const pillGrid = editor.querySelector('[data-pill-grid]');
            const textInput = editor.querySelector('[data-pill-input]');
            const addButton = editor.querySelector('[data-pill-add]');

            if (!hiddenInput || !pillGrid || !textInput || !addButton) {
                return;
            }

            const addDefaultLabel = addButton.textContent && addButton.textContent.trim()
                ? addButton.textContent.trim()
                : 'Add';
            const statusKey = `facultyJobPillStatus:${hiddenInput.name || hiddenInput.id || 'editor'}`;

            const setAddButtonState = (label, disabled) => {
                addButton.textContent = label;
                addButton.disabled = Boolean(disabled);
                addButton.setAttribute('aria-busy', disabled ? 'true' : 'false');
            };

            const showSavedState = () => {
                setAddButtonState('Saved', false);
                window.setTimeout(() => {
                    setAddButtonState(addDefaultLabel, false);
                }, 900);
            };

            try {
                if (window.sessionStorage.getItem(statusKey) === 'saved') {
                    window.sessionStorage.removeItem(statusKey);
                    showSavedState();
                }
            } catch (error) {
                // Ignore storage access issues in restrictive browser modes.
            }

            const submitEditor = (source = 'remove') => {
                try {
                    window.sessionStorage.setItem(statusKey, 'saved');
                } catch (error) {
                    // Ignore storage access issues in restrictive browser modes.
                }

                if (source === 'add') {
                    setAddButtonState('Saving...', true);
                }

                if (typeof editor.requestSubmit === 'function') {
                    editor.requestSubmit();
                    return;
                }

                editor.submit();
            };

            const entries = split(hiddenInput.value);

            // Keep the hidden pill input aligned with the rendered entries.
            const syncHidden = () => {
                hiddenInput.value = entries.join('\n');
            };

            // Rebuild the visible pill list after edits or removals.
            const renderPills = () => {
                pillGrid.replaceChildren();

                if (!entries.length) {
                    const empty = document.createElement('p');
                    empty.className = 'portfolio-strength-empty';
                    empty.textContent = 'No items yet. Add your first one.';
                    pillGrid.appendChild(empty);
                    return;
                }

                entries.forEach((entry, index) => {
                    const item = document.createElement('div');
                    item.className = 'portfolio-strength-item';

                    const remove = document.createElement('button');
                    remove.type = 'button';
                    remove.className = 'portfolio-strength-remove-btn';
                    remove.setAttribute('aria-label', `Remove ${entry}`);
                    remove.innerHTML = '<i class="bi bi-x-lg"></i>';
                    remove.addEventListener('click', () => {
                        entries.splice(index, 1);
                        syncHidden();
                        renderPills();
                        submitEditor('remove');
                    });

                    const pill = document.createElement('span');
                    pill.className = 'portfolio-strength-pill';
                    pill.textContent = entry;

                    item.appendChild(remove);
                    item.appendChild(pill);
                    pillGrid.appendChild(item);
                });
            };

            // Add a new pill from the text box and clear the input for the next entry.
            const addEntry = () => {
                const raw = (textInput.value || '').trim();
                if (!raw) {
                    return;
                }

                if (entries.some((value) => value.toLowerCase() === raw.toLowerCase())) {
                    textInput.value = '';
                    textInput.focus();
                    return;
                }

                entries.push(raw);
                textInput.value = '';
                syncHidden();
                renderPills();
                submitEditor('add');
            };

            addButton.addEventListener('click', addEntry);
            textInput.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    addEntry();
                }
            });

            syncHidden();
            renderPills();
        });

    }

    window.FacultyJobDetailPage = Object.assign({}, window.FacultyJobDetailPage, {
        init: initFacultyJobDetailPage,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initFacultyJobDetailPage);
}(window, document));

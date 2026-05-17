/* Project creation interactions for word counts, chip-style inputs, file selection, and drag-and-drop uploads.
   This module enhances the add-project form with client-side feedback so authors can see what will be submitted before posting the form.
   Route-specific upload and validation behavior belongs here, not in the shared utilities. */
(function (window, document) {
    'use strict';

    // Initialize the add-project page enhancements once the DOM is available.
    function initAddProjectPage() {
        const page = document.querySelector('[data-add-project-page]');
        if (!page) {
            return;
        }

        // Count words so the textarea counters can show progress against the 500-word cap.
        const countWords = (value) => {
            const trimmed = (value || '').trim();
            if (!trimmed) {
                return 0;
            }
            return trimmed.split(/\s+/).length;
        };

        const summaryInput = document.getElementById('id_project_summary');
        const learnedInput = document.getElementById('id_what_i_learnd');
        const summaryCounter = page.querySelector('[data-word-count-for="id_project_summary"]');
        const learnedCounter = page.querySelector('[data-word-count-for="id_what_i_learnd"]');

        // Update the live counter element and flag when the word limit is exceeded.
        const updateCounter = (input, counterEl) => {
            if (!input || !counterEl) {
                return;
            }

            const words = countWords(input.value);
            counterEl.textContent = `${words} / 500 words`;
            counterEl.classList.toggle('is-over', words > 500);
        };

        if (summaryInput && summaryCounter) {
            summaryInput.addEventListener('input', () => updateCounter(summaryInput, summaryCounter));
            updateCounter(summaryInput, summaryCounter);
        }

        if (learnedInput && learnedCounter) {
            learnedInput.addEventListener('input', () => updateCounter(learnedInput, learnedCounter));
            updateCounter(learnedInput, learnedCounter);
        }

        // Turn hidden comma-separated values into editable chip lists.
        const setupChips = (groupName, hiddenId) => {
            const group = page.querySelector(`[data-chip-group="${groupName}"]`);
            const hiddenInput = document.getElementById(hiddenId);

            if (!group || !hiddenInput) {
                return;
            }

            const input = group.querySelector('[data-chip-input]');
            const addBtn = group.querySelector('[data-chip-add]');
            const list = group.querySelector('[data-chip-list]');

            if (!input || !addBtn || !list) {
                return;
            }

            const values = new Set(
                (hiddenInput.value || '')
                    .split(',')
                    .map((item) => item.trim())
                    .filter((item) => item.length > 0),
            );

            // Keep the hidden field in sync with the visible chip values.
            const syncHidden = () => {
                hiddenInput.value = Array.from(values).join(', ');
            };

            // Re-render the chip list after every add or remove action.
            const render = () => {
                list.innerHTML = '';
                values.forEach((value) => {
                    const chip = document.createElement('span');
                    chip.className = 'add-project-chip';
                    chip.textContent = value;

                    const removeBtn = document.createElement('button');
                    removeBtn.type = 'button';
                    removeBtn.className = 'add-project-chip-remove';
                    removeBtn.setAttribute('aria-label', `Remove ${value}`);
                    removeBtn.textContent = 'x';
                    removeBtn.addEventListener('click', () => {
                        values.delete(value);
                        syncHidden();
                        render();
                    });

                    chip.appendChild(removeBtn);
                    list.appendChild(chip);
                });
            };

            // Add a new chip value from the text input, then clear the field.
            const addValue = () => {
                const next = (input.value || '').trim();
                if (!next) {
                    return;
                }
                values.add(next);
                input.value = '';
                syncHidden();
                render();
                input.focus();
            };

            addBtn.addEventListener('click', addValue);
            input.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    addValue();
                }
            });

            syncHidden();
            render();
        };

        setupChips('skills', 'id_skills_demonstrated');
        setupChips('tech', 'id_tech_n_tools_used');

        const uploadInput = page.querySelector('[data-upload-input]');
        const uploadZone = page.querySelector('[data-upload-zone]');
        const uploadSelected = page.querySelector('[data-upload-selected]');

        const selectedMedia = [];

        const mediaKey = (file) => `${file.name}::${file.size}::${file.lastModified}`;

        // Mirror the selected files back into the file input so form submission stays correct.
        const syncUploadInput = () => {
            if (!uploadInput) {
                return;
            }

            const dataTransfer = new DataTransfer();
            selectedMedia.forEach((file) => dataTransfer.items.add(file));
            uploadInput.files = dataTransfer.files;
        };

        // Render a short file summary for the user-friendly upload status line.
        const renderSelected = () => {
            if (!uploadSelected) {
                return;
            }

            if (!selectedMedia.length) {
                uploadSelected.textContent = 'No files selected';
                return;
            }

            const names = selectedMedia.map((f) => f.name);
            const summary = names.length <= 3 ? names.join(', ') : `${names.slice(0, 3).join(', ')} +${names.length - 3} more`;
            uploadSelected.textContent = `${selectedMedia.length} file${selectedMedia.length === 1 ? '' : 's'} selected: ${summary}`;
        };

        // Merge newly chosen files with the existing selection without duplicating items.
        const addSelectedFiles = (files) => {
            if (!files || !files.length) {
                return;
            }

            const existing = new Set(selectedMedia.map(mediaKey));
            Array.from(files).forEach((file) => {
                const key = mediaKey(file);
                if (!existing.has(key)) {
                    selectedMedia.push(file);
                    existing.add(key);
                }
            });

            syncUploadInput();
            renderSelected();
        };

        if (uploadInput) {
            uploadInput.addEventListener('change', () => addSelectedFiles(uploadInput.files));
        }

        if (uploadZone && uploadInput) {
            ['dragenter', 'dragover'].forEach((eventName) => {
                uploadZone.addEventListener(eventName, (event) => {
                    event.preventDefault();
                    uploadZone.classList.add('is-dragging');
                });
            });

            ['dragleave', 'drop'].forEach((eventName) => {
                uploadZone.addEventListener(eventName, (event) => {
                    event.preventDefault();
                    uploadZone.classList.remove('is-dragging');
                });
            });

            uploadZone.addEventListener('drop', (event) => {
                if (!event.dataTransfer || !event.dataTransfer.files) {
                    return;
                }
                addSelectedFiles(event.dataTransfer.files);
            });
        }

        const form = page.querySelector('.add-project-form');
        const skillsHidden = document.getElementById('id_skills_demonstrated');
        if (form && skillsHidden) {
            form.addEventListener('submit', (event) => {
                if (!(skillsHidden.value || '').trim()) {
                    event.preventDefault();
                    if (window.AppCore && typeof window.AppCore.showGlobalSystemAlert === 'function') {
                        window.AppCore.showGlobalSystemAlert('Please add at least one skill before creating the project.', 'danger');
                    }
                }
            });
        }
    }

    window.AddProjectPage = Object.assign({}, window.AddProjectPage, {
        init: initAddProjectPage,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initAddProjectPage);
}(window, document));

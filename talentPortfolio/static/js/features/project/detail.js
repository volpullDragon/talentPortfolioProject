/* Project detail interactions for field theme application, skill pill rendering, and inline editing of project content.
   This module coordinates multiple editable regions and media-related controls on the project detail route, so it intentionally contains more orchestration than the smaller shared helpers.
   Keep the logic here tied to the project detail screen instead of leaking it into global utilities. */
(function (window, document) {
    'use strict';

    // Explain the page-level init entry point before any DOM work begins.
    function initProjectDetailPage() {
        const page = document.querySelector('[data-project-detail-page]');
        if (!page) {
            return;
        }

        const fieldName = page.getAttribute('data-field-name') || '';
        const theme = typeof window.getFieldThemeFromName === 'function'
            ? window.getFieldThemeFromName(fieldName)
            : { accentStart: '#2563eb', accentEnd: '#1d4ed8', accent: '#1d4ed8', soft: '#dbeafe', deep: '#1e3a8a' };

        page.style.setProperty('--field-accent-start', theme.accentStart);
        page.style.setProperty('--field-accent-end', theme.accentEnd);
        page.style.setProperty('--field-accent', theme.accent);
        page.style.setProperty('--field-accent-soft', theme.soft);
        page.style.setProperty('--field-accent-deep', theme.deep);

        const split = typeof window.splitSkills === 'function'
            ? window.splitSkills
            : (raw) => Array.from(new Set((raw || '').split(/[,\n;/|]+/).map((item) => item.trim()).filter(Boolean)));

        const techRows = page.querySelectorAll('[data-project-tech-row]');
        techRows.forEach((row) => {
            const skills = split(row.getAttribute('data-skills-source') || '');
            const fragment = document.createDocumentFragment();

            if (!skills.length) {
                const empty = document.createElement('span');
                empty.className = 'project-detail-pill';
                empty.textContent = 'No tools listed';
                fragment.appendChild(empty);
            } else {
                skills.forEach((skill) => {
                    const pill = document.createElement('span');
                    pill.className = 'project-detail-pill';
                    pill.textContent = skill;
                    fragment.appendChild(pill);
                });
            }

            row.replaceChildren(fragment);
        });

        const skillOpenBtn = page.querySelector('[data-project-skill-open]');
        const skillForm = page.querySelector('[data-project-skill-form]');
        const skillCancelBtn = page.querySelector('[data-project-skill-cancel]');
        const skillInput = page.querySelector('[data-project-skill-input]');
        const skillSaveBtn = page.querySelector('[data-project-skill-save]');

        if (skillOpenBtn && skillForm && skillCancelBtn && skillInput && skillSaveBtn) {
            const syncSkillState = () => {
                skillSaveBtn.disabled = skillInput.value.trim().length === 0;
            };

            skillOpenBtn.addEventListener('click', () => {
                skillForm.classList.remove('is-hidden');
                skillOpenBtn.classList.add('is-hidden');
                skillInput.focus();
                syncSkillState();
            });

            skillCancelBtn.addEventListener('click', () => {
                skillForm.classList.add('is-hidden');
                skillOpenBtn.classList.remove('is-hidden');
                skillInput.value = '';
                syncSkillState();
            });

            skillInput.addEventListener('input', syncSkillState);
            syncSkillState();
        }

        // Wrap POST submission so edits and add/remove actions share the same AJAX path.
        const postProjectDetailForm = async (formDataOrForm, options = {}) => {
            const actionName = options.actionName || null;
            const formData = formDataOrForm instanceof FormData ? formDataOrForm : new FormData(formDataOrForm);

            if (actionName && !formData.has(actionName)) {
                formData.append(actionName, '1');
            }

            return fetch(window.location.href, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: formData,
                credentials: 'same-origin',
            });
        };

        const editableButtons = page.querySelectorAll('[data-project-edit-toggle]');
        editableButtons.forEach((button) => {
            const card = button.closest('.project-detail-card');
            const target = card ? card.querySelector('[data-project-edit-content]') : null;
            if (!target) {
                return;
            }

            const icon = button.querySelector('i');
            const label = button.querySelector('span');

            // Toggle the inline editor state and keep the button label/icon aligned with the current mode.
            const setEditMode = (isEditing) => {
                target.setAttribute('contenteditable', isEditing ? 'true' : 'false');
                target.classList.toggle('is-editing', isEditing);

                if (icon) {
                    icon.className = isEditing ? 'bi bi-check2' : 'bi bi-pencil';
                }
                if (label) {
                    label.textContent = isEditing ? 'Save' : 'Edit';
                }

                if (isEditing) {
                    target.focus();
                }
            };

            button.addEventListener('click', async () => {
                const isEditing = target.getAttribute('contenteditable') === 'true';

                if (!isEditing) {
                    target.dataset.projectOriginalValue = (target.textContent || '').trim();
                    setEditMode(true);
                    return;
                }

                if (button.dataset.saving === '1') {
                    return;
                }

                const editableField = (target.getAttribute('data-project-edit-field') || '').trim();
                const editableValue = (target.textContent || '').trim();
                const csrfInput = page.querySelector("input[name='csrfmiddlewaretoken']");

                button.dataset.saving = '1';

                try {
                    const formData = new FormData();
                    if (csrfInput && csrfInput.value) {
                        formData.append('csrfmiddlewaretoken', csrfInput.value);
                    }
                    formData.append('project_text_save', '1');
                    formData.append('project_text_field', editableField);
                    formData.append('project_text_value', editableValue);

                    const response = await postProjectDetailForm(formData);

                    const payload = await response.json().catch(() => ({}));
                    if (!response.ok || payload.ok === false) {
                        const errorMessage = (payload && payload.message) ? payload.message : 'Unable to save project details.';
                        throw new Error(errorMessage);
                    }

                    const updatedValue = (payload && typeof payload.updated_value === 'string') ? payload.updated_value : editableValue;
                    target.textContent = updatedValue;
                    target.dataset.projectOriginalValue = updatedValue;
                    setEditMode(false);
                } catch (error) {
                    const originalValue = target.dataset.projectOriginalValue || '';
                    if ((target.textContent || '').trim().length === 0 && originalValue) {
                        target.textContent = originalValue;
                    }
                    if (window.AppCore && typeof window.AppCore.showGlobalSystemAlert === 'function') {
                        window.AppCore.showGlobalSystemAlert(error && error.message ? error.message : 'Unable to save project details.', 'danger');
                    }
                    setEditMode(true);
                } finally {
                    delete button.dataset.saving;
                }
            });
        });

        const techOpenBtn = page.querySelector('[data-project-tech-open]');
        const techForm = page.querySelector('[data-project-tech-form]');
        const techCancelBtn = page.querySelector('[data-project-tech-cancel]');
        const techInput = page.querySelector('[data-project-tech-input]');
        const techSaveBtn = page.querySelector('[data-project-tech-save]');

        if (techOpenBtn && techForm && techCancelBtn && techInput && techSaveBtn) {
            const syncTechState = () => {
                techSaveBtn.disabled = techInput.value.trim().length === 0;
            };

            techOpenBtn.addEventListener('click', () => {
                techForm.classList.remove('is-hidden');
                techOpenBtn.classList.add('is-hidden');
                techInput.focus();
                syncTechState();
            });

            techCancelBtn.addEventListener('click', () => {
                techForm.classList.add('is-hidden');
                techOpenBtn.classList.remove('is-hidden');
                techInput.value = '';
                syncTechState();
            });

            techInput.addEventListener('input', syncTechState);
            syncTechState();
        }

        const skillGrid = page.querySelector('[data-project-skill-grid]');
        const techGrid = page.querySelector('[data-project-tech-grid]');

        // Build a removable pill form so delete actions can submit without rebuilding the whole card.
        const buildRemoveItem = (value, fieldName, pillClass, ariaLabel, dataAttrName) => {
            const form = document.createElement('form');
            form.method = 'post';
            form.className = 'project-detail-pill-item';
            form.setAttribute(dataAttrName, '');

            const tokenSource = skillForm || techForm;
            const tokenInput = tokenSource ? tokenSource.querySelector("input[name='csrfmiddlewaretoken']") : null;

            const csrf = document.createElement('input');
            csrf.type = 'hidden';
            csrf.name = 'csrfmiddlewaretoken';
            csrf.value = tokenInput ? tokenInput.value : '';

            const hidden = document.createElement('input');
            hidden.type = 'hidden';
            hidden.name = fieldName;
            hidden.value = value;

            const removeButton = document.createElement('button');
            removeButton.type = 'submit';
            removeButton.className = 'project-detail-pill-remove';
            removeButton.setAttribute('aria-label', ariaLabel);
            removeButton.innerHTML = '<i class="bi bi-x-lg"></i>';

            const pill = document.createElement('span');
            pill.className = pillClass;
            pill.textContent = value;

            form.appendChild(csrf);
            form.appendChild(hidden);
            form.appendChild(removeButton);
            form.appendChild(pill);
            return form;
        };

        // Rebuild the skill grid from server data after edits so the UI stays in sync.
        const renderSkillGrid = (items) => {
            if (!skillGrid) {
                return;
            }

            const fragment = document.createDocumentFragment();

            if (!items.length) {
                const empty = document.createElement('p');
                empty.className = 'project-detail-skill-empty';
                empty.textContent = 'No key skills yet. Add your first one.';
                fragment.appendChild(empty);
            } else {
                items.forEach((skill) => {
                    fragment.appendChild(buildRemoveItem(skill, 'project_skill_remove', 'field-skill-pill project-detail-skill-pill', 'Remove skill', 'data-project-skill-remove-form'));
                });
            }

            if (skillOpenBtn) {
                fragment.appendChild(skillOpenBtn);
            }

            skillGrid.replaceChildren(fragment);
        };

        // Rebuild the technology grid using the same server response as the skill list.
        const renderTechGrid = (items) => {
            if (!techGrid) {
                return;
            }

            const fragment = document.createDocumentFragment();

            if (!items.length) {
                const empty = document.createElement('p');
                empty.className = 'project-detail-skill-empty';
                empty.textContent = 'No tools listed.';
                fragment.appendChild(empty);
            } else {
                items.forEach((tech) => {
                    fragment.appendChild(buildRemoveItem(tech, 'project_tech_remove', 'project-detail-pill', 'Remove technology', 'data-project-tech-remove-form'));
                });
            }

            techGrid.replaceChildren(fragment);
        };

        // Submit the relevant form via fetch, then re-render both grids from the returned payload.
        const submitProjectAjax = async (form, actionName = null) => {
            try {
                const response = await postProjectDetailForm(form, { actionName });

                const payload = await response.json();
                if (!payload || !Array.isArray(payload.project_skill_items) || !Array.isArray(payload.project_tech_items)) {
                    throw new Error('Invalid response payload');
                }

                renderSkillGrid(payload.project_skill_items);
                renderTechGrid(payload.project_tech_items);

                if (form === skillForm && response.ok) {
                    skillInput.value = '';
                    skillForm.classList.add('is-hidden');
                    skillOpenBtn.classList.remove('is-hidden');
                    skillSaveBtn.disabled = true;
                }

                if (form === techForm && response.ok) {
                    techInput.value = '';
                    techForm.classList.add('is-hidden');
                    techOpenBtn.classList.remove('is-hidden');
                    techSaveBtn.disabled = true;
                }
            } catch (error) {
                form.submit();
            }
        };

        if (skillForm) {
            skillForm.addEventListener('submit', (event) => {
                event.preventDefault();
                void submitProjectAjax(skillForm, 'project_skill_submit');
            });
        }

        if (techForm) {
            techForm.addEventListener('submit', (event) => {
                event.preventDefault();
                void submitProjectAjax(techForm, 'project_tech_submit');
            });
        }

        if (skillGrid) {
            skillGrid.addEventListener('submit', (event) => {
                const targetForm = event.target.closest('form[data-project-skill-remove-form]');
                if (!targetForm) {
                    return;
                }
                event.preventDefault();
                void submitProjectAjax(targetForm);
            });
        }

        if (techGrid) {
            techGrid.addEventListener('submit', (event) => {
                const targetForm = event.target.closest('form[data-project-tech-remove-form]');
                if (!targetForm) {
                    return;
                }
                event.preventDefault();
                void submitProjectAjax(targetForm);
            });
        }
    }

    window.ProjectDetailPage = Object.assign({}, window.ProjectDetailPage, {
        init: initProjectDetailPage,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initProjectDetailPage);
}(window, document));

/* Faculty dashboard interactions for candidate search, skill filtering, save actions, and dashboard alerts.
   This module powers the faculty search and save workflows that sit on top of the shared dashboard shell, including AJAX actions and local filtering logic.
   It should remain focused on faculty candidate review rather than general shell behavior. */
(function (window, document) {
    'use strict';

    // Surface a success or error message using the shared alert system when possible.
    function showAlert(message, level = 'success') {
        if (window.AppCore && typeof window.AppCore.showGlobalSystemAlert === 'function') {
            window.AppCore.showGlobalSystemAlert(message, level);
            return;
        }

        const container = document.querySelector('.content-wrapper');
        if (!container || !message) {
            return;
        }

        const alert = document.createElement('div');
        alert.className = `alert alert-${level} alert-dismissible fade show`;
        alert.setAttribute('role', 'alert');
        alert.appendChild(document.createTextNode(message));

        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('data-bs-dismiss', 'alert');
        closeButton.setAttribute('aria-label', 'Close');
        alert.appendChild(closeButton);

        container.prepend(alert);
    }

    // Resolve the CSRF token from the shared helper or the fallback page-level sources.
    function getCsrfToken() {
        if (window.AppCore && typeof window.AppCore.getGlobalCsrfToken === 'function') {
            return window.AppCore.getGlobalCsrfToken();
        }

        return (
            document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
            document.cookie.split('; ').find((row) => row.startsWith('csrftoken='))?.split('=')[1] ||
            ''
        );
    }

    // Boot the faculty dashboard after the shell and card markup are available.
    function initFacultyDashboardPage() {
        const page = document.querySelector('[data-faculty-dashboard-page]');
        if (!page) {
            return;
        }

        const candidateCards = Array.from(page.querySelectorAll('[data-candidate-card]'));
        const skillFilterButtons = Array.from(page.querySelectorAll('button[data-skill-filter], button[data-faculty-search-skill-filter]'));
        const searchInput = page.querySelector('#facultyCandidateSearch');
        const searchButton = page.querySelector('[data-faculty-candidate-search-btn]');
        const countLabel = page.querySelector('[data-faculty-candidate-count]');
        const jobFilter = page.querySelector('[data-faculty-job-filter]');
        const courseFilter = page.querySelector('[data-faculty-course-filter]');
        const campusFilter = page.querySelector('[data-faculty-campus-filter]');
        const yearFilter = page.querySelector('[data-faculty-year-filter]');
        const minScoreFilter = page.querySelector('[data-faculty-min-score-filter]');

        // Normalize the serialized skill list into lowercase tokens for filtering.
        const splitCardSkills = (raw) => {
            return (raw || '')
                .split(/[;,\n/|]+/)
                .map((item) => item.trim().toLowerCase())
                .filter((item) => item.length > 0);
        };

        // Toggle the visual state of the active skill filter button.
        const setActiveFilterButton = (targetButton) => {
            skillFilterButtons.forEach((button) => {
                const isActive = button === targetButton;
                button.classList.toggle('active', isActive);
                button.classList.toggle('inactive', !isActive);
            });
        };

        // Read the current filter value from whichever button is active.
        const getActiveSkillFilter = () => {
            const active = skillFilterButtons.find((button) => button.classList.contains('active'));
            return active ? (active.getAttribute('data-skill-filter') || active.getAttribute('data-faculty-search-skill-filter') || 'all').toLowerCase() : 'all';
        };

        const searchResultsMode = page.hasAttribute('data-faculty-search-results-page');

        // Hide cards that do not match the search text or the selected skill filter.
        const applyCandidateFilters = () => {
            const searchTerm = (searchInput?.value || '').trim().toLowerCase();
            const activeSkill = getActiveSkillFilter();
            let visibleCount = 0;

            candidateCards.forEach((card) => {
                const searchText = (card.getAttribute('data-search-text') || '').toLowerCase();
                const cardSkills = splitCardSkills(card.getAttribute('data-skills-source') || '');

                const matchesSearch = !searchTerm || searchText.includes(searchTerm);
                const matchesSkill = activeSkill === 'all' || cardSkills.some((skill) => skill.includes(activeSkill));
                const shouldShow = matchesSearch && matchesSkill;

                card.style.display = shouldShow ? '' : 'none';
                if (shouldShow) {
                    visibleCount += 1;
                }
            });

            if (countLabel) {
                countLabel.textContent = `Showing ${visibleCount} student${visibleCount === 1 ? '' : 's'}`;
            }
        };

        skillFilterButtons.forEach((button) => {
            button.addEventListener('click', () => {
                if (button.hasAttribute('disabled')) {
                    return;
                }

                if (searchResultsMode) {
                    const params = new URLSearchParams(window.location.search);
                    const skill = (button.getAttribute('data-faculty-search-skill-filter') || button.getAttribute('data-skill-filter') || 'all').toLowerCase();

                    if (skill && skill !== 'all') {
                        params.set('skill', skill);
                        params.delete('q');
                    } else {
                        params.delete('skill');
                    }
                    params.delete('page');

                    const queryString = params.toString();
                    window.location.assign(queryString ? `${facultySearchTarget}?${queryString}` : facultySearchTarget);
                    return;
                }

                setActiveFilterButton(button);
                applyCandidateFilters();
            });
        });

        const facultySearchTarget = page.getAttribute('data-faculty-search-target') || window.location.pathname;

        // Rebuild the search URL and navigate to the search results page.
        const redirectFacultySearch = () => {
            if (!searchInput) {
                return;
            }

            const params = new URLSearchParams(window.location.search);
            const query = (searchInput.value || '').trim();

            if (query) {
                params.set('q', query);
            } else {
                params.delete('q');
            }

            const jobValue = (jobFilter?.value || 'all').trim();
            if (jobValue && jobValue.toLowerCase() !== 'all') {
                params.set('job_listing', jobValue);
            } else {
                params.delete('job_listing');
            }

            const courseValue = (courseFilter?.value || 'all').trim();
            if (courseValue && courseValue.toLowerCase() !== 'all') {
                params.set('course', courseValue);
            } else {
                params.delete('course');
            }

            const campusValue = (campusFilter?.value || 'all').trim();
            if (campusValue && campusValue.toLowerCase() !== 'all') {
                params.set('campus', campusValue);
            } else {
                params.delete('campus');
            }

            const yearValue = (yearFilter?.value || 'all').trim();
            if (yearValue && yearValue.toLowerCase() !== 'all') {
                params.set('year', yearValue);
            } else {
                params.delete('year');
            }

            const minScoreValue = (minScoreFilter?.value || '0').trim();
            if (minScoreValue && minScoreValue !== '0') {
                params.set('min_score', minScoreValue);
            } else {
                params.delete('min_score');
            }

            params.delete('page');

            const queryString = params.toString();
            window.location.assign(queryString ? `${facultySearchTarget}?${queryString}` : facultySearchTarget);
        };

        if (searchInput) {
            searchInput.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    redirectFacultySearch();
                }
            });
        }

        if (searchButton) {
            searchButton.addEventListener('click', redirectFacultySearch);
        }

        [jobFilter, courseFilter, campusFilter, yearFilter, minScoreFilter].forEach((control) => {
            if (!control) {
                return;
            }
            control.addEventListener('change', redirectFacultySearch);
        });

        const saveButtons = page.querySelectorAll('button[data-faculty-save-student]');
        const saveStudentUrlTemplate = page.getAttribute('data-save-student-url-template') || '';

        saveButtons.forEach((button) => {
            button.addEventListener('click', async () => {
                if (button.dataset.pending === '1') {
                    return;
                }

                const card = button.closest('[data-candidate-card]');
                const studentId = card ? card.getAttribute('data-student-id') : null;
                if (!studentId || !saveStudentUrlTemplate.includes('/0/')) {
                    return;
                }

                const targetUrl = saveStudentUrlTemplate.replace('/0/', `/${studentId}/`);
                button.dataset.pending = '1';
                button.disabled = true;

                try {
                    const response = await fetch(targetUrl, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCsrfToken(),
                            'X-Requested-With': 'XMLHttpRequest',
                        },
                        credentials: 'same-origin',
                    });

                    const payload = await response.json();
                    if (!response.ok || payload.success !== true) {
                        throw new Error(payload.error || payload.message || 'Unable to save applicant.');
                    }

                    const isSaved = Boolean(payload.saved);
                    button.classList.toggle('saved', isSaved);
                    button.dataset.isSaved = isSaved ? 'true' : 'false';
                    button.setAttribute('aria-pressed', isSaved ? 'true' : 'false');

                    const icon = button.querySelector('i.bi');
                    if (icon) {
                        icon.classList.toggle('bi-bookmark-fill', isSaved);
                        icon.classList.toggle('bi-bookmark', !isSaved);
                    }

                    showAlert(payload.message || (isSaved ? 'Student saved!' : 'Student removed from saved'), 'success');
                } catch (error) {
                    console.error('Save student failed:', error);
                    showAlert(error?.message || 'Unable to save applicant.', 'danger');
                } finally {
                    button.dataset.pending = '0';
                    button.disabled = false;
                }
            });
        });

        const skillRows = page.querySelectorAll('[data-faculty-candidate-skill-pills]');
        skillRows.forEach((row) => {
            const skills = typeof window.splitSkills === 'function'
                ? window.splitSkills(row.getAttribute('data-skills-source') || '')
                : splitCardSkills(row.getAttribute('data-skills-source') || '');
            const fragment = document.createDocumentFragment();

            if (!skills.length) {
                const fallback = document.createElement('span');
                fallback.className = 'faculty-candidate-skill-pill';
                fallback.textContent = 'No overlapping skills';
                fragment.appendChild(fallback);
            } else {
                skills.slice(0, 6).forEach((skill) => {
                    const pill = document.createElement('span');
                    pill.className = 'faculty-candidate-skill-pill';
                    pill.textContent = skill;
                    fragment.appendChild(pill);
                });
            }

            row.replaceChildren(fragment);
        });

        applyCandidateFilters();
    }

    window.FacultyDashboard = Object.assign({}, window.FacultyDashboard, {
        init: initFacultyDashboardPage,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initFacultyDashboardPage);
}(window, document));

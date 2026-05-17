/* Faculty profile interactions for required-skill pill rendering and delete confirmation on the profile page.
   The script keeps the profile route in sync with its serialized skill data while protecting job deletions from accidental submits.
   Add faculty profile-only behavior here instead of folding it into the broader dashboard modules. */
(function (window, document) {
    'use strict';

    // Initialize the faculty profile page's skill rendering and delete guards.
    function initFacultyProfilePage() {
        const page = document.querySelector('[data-faculty-profile-page]');
        if (!page) {
            return;
        }

        const split = typeof window.splitSkills === 'function'
            ? window.splitSkills
            : (raw) => Array.from(new Set((raw || '').split(/[,\n;/|]+/).map((item) => item.trim()).filter(Boolean)));

        const rows = page.querySelectorAll('[data-faculty-job-skill-pills]');
        rows.forEach((row) => {
            const source = row.getAttribute('data-skills-source') || '';
            const skills = split(source);
            const fragment = document.createDocumentFragment();

            if (!skills.length) {
                const empty = document.createElement('span');
                empty.className = 'faculty-job-skill-pill';
                empty.textContent = 'No required skills listed';
                fragment.appendChild(empty);
            } else {
                skills.forEach((skill) => {
                    const pill = document.createElement('span');
                    pill.className = 'faculty-job-skill-pill';
                    pill.textContent = skill;
                    fragment.appendChild(pill);
                });
            }

            row.replaceChildren(fragment);
        });

    }

    window.FacultyProfilePage = Object.assign({}, window.FacultyProfilePage, {
        init: initFacultyProfilePage,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initFacultyProfilePage);
}(window, document));

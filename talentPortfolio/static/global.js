// Student Dashboard JavaScript

// Lightweight module loader for progressively splitting global.js by feature.
(function initGlobalModuleLoader() {
    const currentScript = document.currentScript || Array.from(document.querySelectorAll('script[src]')).find((tag) => (tag.getAttribute('src') || '').includes('global.js'));
    const currentSrc = currentScript ? (currentScript.getAttribute('src') || '') : '';
    const staticBase = (currentSrc.split('global.js')[0] || '/static/').replace(/\?[^]*$/, '');

    const modulePaths = [
        `${staticBase}js/core/app-core.js`,
        `${staticBase}js/shared/field-utils.js`,
        `${staticBase}js/features/shared/dropdowns.js`,
        `${staticBase}js/features/shared/page-inits.js`,
        `${staticBase}js/features/shared/legacy-compat.js`,
        `${staticBase}js/features/student-job-board.js`,
        `${staticBase}js/features/student/job-detail.js`,
        `${staticBase}js/features/student/saved-jobs.js`,
        `${staticBase}js/features/portfolio/editors.js`,
        `${staticBase}js/features/project/detail.js`,
        `${staticBase}js/features/project/field-expertise.js`,
        `${staticBase}js/features/project/add.js`,
        `${staticBase}js/features/faculty/profile.js`,
        `${staticBase}js/features/faculty/job-detail.js`,
        `${staticBase}js/features/faculty/dashboard.js`,
        `${staticBase}js/features/faculty/interview-overlay.js`,
        `${staticBase}js/features/faculty/invite-overlay.js`,
    ];

    modulePaths.forEach((src) => {
        if (document.querySelector(`script[data-global-module="${src}"]`)) {
            return;
        }

        const tag = document.createElement('script');
        tag.src = src;
        tag.async = false;
        tag.setAttribute('data-global-module', src);
        document.head.appendChild(tag);
    });
})();

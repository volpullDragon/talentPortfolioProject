/* Portfolio editing interactions for about text, strengths, featured cards, and scroll persistence.
   The module coordinates inline editing state, lightweight autosave-adjacent behavior, and card ordering so the portfolio page feels editable without a full form reload.
   When these controls are expanded, prefer adding helpers here rather than scattering edit logic across templates. */
(function (window, document) {
    'use strict';

    // Manage the portfolio about-section editor and its word-count feedback.
    function initPortfolioAboutEditor() {
        const editBtn = document.querySelector('[data-about-edit]');
        const displayBlock = document.querySelector('[data-about-display]');
        const formBlock = document.querySelector('[data-about-form]');
        const cancelBtn = document.querySelector('[data-about-cancel]');
        const aboutInput = document.querySelector('[data-about-input]');
        const saveBtn = document.querySelector('[data-about-save]');
        const counter = document.querySelector('[data-about-word-count]');

        if (!editBtn || !displayBlock || !formBlock || !cancelBtn || !aboutInput || !saveBtn || !counter) {
            return;
        }

        const countWords = (text) => {
            const value = (text || '').trim();
            if (!value) {
                return 0;
            }
            return value.split(/\s+/).length;
        };

        const syncWordCount = () => {
            const words = countWords(aboutInput.value);
            counter.textContent = words + ' / 500 words';
            const overLimit = words > 500;
            counter.classList.toggle('is-over-limit', overLimit);
            saveBtn.disabled = overLimit;
        };

        editBtn.addEventListener('click', () => {
            displayBlock.classList.add('is-hidden');
            formBlock.classList.remove('is-hidden');
            editBtn.classList.add('is-hidden');
            aboutInput.focus();
            syncWordCount();
        });

        cancelBtn.addEventListener('click', () => {
            formBlock.classList.add('is-hidden');
            displayBlock.classList.remove('is-hidden');
            editBtn.classList.remove('is-hidden');
        });

        aboutInput.addEventListener('input', syncWordCount);
        syncWordCount();
    }

    // Keep the strength selector and preview state synchronized.
    function initPortfolioStrengthEditor() {
        const openBtn = document.querySelector('[data-strength-open]');
        const formBlock = document.querySelector('[data-strength-form]');
        const cancelBtn = document.querySelector('[data-strength-cancel]');
        const strengthInput = document.querySelector('[data-strength-input]');
        const saveBtn = document.querySelector('[data-strength-save]');

        if (!openBtn || !formBlock || !cancelBtn || !strengthInput || !saveBtn) {
            return;
        }

        const syncStrengthState = () => {
            saveBtn.disabled = strengthInput.value.trim().length === 0;
        };

        openBtn.addEventListener('click', () => {
            formBlock.classList.remove('is-hidden');
            openBtn.classList.add('is-hidden');
            strengthInput.focus();
            syncStrengthState();
        });

        cancelBtn.addEventListener('click', () => {
            formBlock.classList.add('is-hidden');
            openBtn.classList.remove('is-hidden');
            strengthInput.value = '';
            syncStrengthState();
        });

        strengthInput.addEventListener('input', syncStrengthState);
        syncStrengthState();
    }

    // Preserve scroll position while the portfolio editors re-render.
    function initPortfolioScrollPersistence() {
        const forms = document.querySelectorAll('form[data-preserve-scroll]');

        forms.forEach((form) => {
            form.addEventListener('submit', () => {
                const input = form.querySelector('[data-scroll-position]');
                if (input) {
                    input.value = String(Math.max(0, Math.round(window.scrollY || window.pageYOffset || 0)));
                }
            });
        });

        const params = new URLSearchParams(window.location.search);
        const raw = params.get('scroll');
        if (raw === null) {
            return;
        }

        const y = Number.parseInt(raw, 10);
        if (isNaN(y) === false && y >= 0) {
            if ('scrollRestoration' in window.history) {
                window.history.scrollRestoration = 'manual';
            }

            const applyScroll = () => {
                window.scrollTo(0, y);
            };

            applyScroll();
            requestAnimationFrame(applyScroll);
            setTimeout(applyScroll, 50);
            setTimeout(applyScroll, 150);
            window.addEventListener('load', applyScroll, { once: true });
        }

        params.delete('scroll');
        const next = params.toString();
        const cleanUrl = next ? (window.location.pathname + '?' + next + window.location.hash) : (window.location.pathname + window.location.hash);
        window.history.replaceState({}, '', cleanUrl);
    }

    // Move featured cards to the top of the grid so they read as prioritized items.
    function reorderCardsByFeatured() {
        const grid = document.querySelector('.portfolio-card-grid');
        if (!grid) {
            return;
        }

        const addCard = grid.querySelector('.experience-card-add');
        const addCardAnchor = addCard ? addCard.closest('.experience-card-anchor') : null;

        const containers = Array.from(grid.querySelectorAll('.experience-card-container'));
        const featured = containers.filter((c) => c.querySelector('.experience-card-star-toggle')?.dataset.featured === 'true');
        const notFeatured = containers.filter((c) => c.querySelector('.experience-card-star-toggle')?.dataset.featured !== 'true');

        [...featured, ...notFeatured].forEach((container) => {
            grid.appendChild(container);
        });

        if (addCardAnchor) {
            grid.appendChild(addCardAnchor);
        }
    }

    // Persist the featured flag, then refresh the card order from the server response.
    function toggleFieldFeatured(fieldId, newStatus, buttonElement) {
        const csrf = typeof window.getGlobalCsrfToken === 'function'
            ? window.getGlobalCsrfToken()
            : (document.querySelector('[name=csrfmiddlewaretoken]')?.value || document.cookie.split('; ').find((row) => row.startsWith('csrftoken='))?.split('=')[1]);

        fetch('/dashboard/toggle-field-featured/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf,
            },
            body: JSON.stringify({
                field_id: fieldId,
                is_featured: newStatus,
            }),
        })
            .then(async (response) => {
                const data = await response.json();
                return { ok: response.ok, status: response.status, data };
            })
            .then(({ ok, status, data }) => {
                if (!ok || !data.success) {
                    console.error('Featured toggle failed:', status, data);
                    return;
                }
                buttonElement.dataset.featured = newStatus ? 'true' : 'false';
                const icon = buttonElement.querySelector('i');
                if (icon) {
                    icon.classList.toggle('bi-star', !newStatus);
                    icon.classList.toggle('bi-star-fill', newStatus);
                }
                const cardContainer = buttonElement.closest('.experience-card-container');
                const card = cardContainer ? cardContainer.querySelector('.experience-card') : null;
                if (card) {
                    card.classList.toggle('experience-card-featured', newStatus);
                }
                reorderCardsByFeatured();
            })
            .catch((error) => console.error('Error:', error));
    }

    // Bind featured-star controls on each portfolio field card.
    function initFeaturedToggle() {
        const starButtons = document.querySelectorAll('.experience-card-star-toggle');
        starButtons.forEach((btn) => {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                const fieldId = this.dataset.fieldId;
                const isFeatured = this.dataset.featured === 'true';
                toggleFieldFeatured(fieldId, !isFeatured, this);
            });
        });
    }

    // Render portfolio skills into pill rows and keep delete actions local.
    function initPortfolioSkillPills() {
        const rows = document.querySelectorAll('[data-card-skill-pills]');
        if (rows.length === 0) {
            return;
        }

        const split = typeof window.splitSkills === 'function'
            ? window.splitSkills
            : (raw) => Array.from(new Set((raw || '').split(/[,\n;/|]+/).map((item) => item.trim()).filter(Boolean)));

        rows.forEach((row) => {
            const source = row.getAttribute('data-skills-source') || '';
            const skills = split(source);
            const fragment = document.createDocumentFragment();

            if (skills.length === 0) {
                const empty = document.createElement('span');
                empty.className = 'experience-card-skill-pill';
                empty.textContent = 'No skills yet';
                fragment.appendChild(empty);
            } else {
                skills.forEach((skill) => {
                    const pill = document.createElement('span');
                    pill.className = 'experience-card-skill-pill';
                    pill.textContent = skill;
                    fragment.appendChild(pill);
                });
            }

            row.replaceChildren(fragment);

            window.requestAnimationFrame(() => {
                const overflowing = row.scrollHeight > row.clientHeight + 1;
                row.classList.toggle('is-truncated', overflowing);
            });
        });
    }

    window.PortfolioEditors = Object.assign({}, window.PortfolioEditors, {
        initPortfolioAboutEditor,
        initPortfolioStrengthEditor,
        initPortfolioScrollPersistence,
        initFeaturedToggle,
        initPortfolioSkillPills,
        toggleFieldFeatured,
        reorderCardsByFeatured,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initPortfolioAboutEditor);
    bindReady(initPortfolioStrengthEditor);
    bindReady(initPortfolioScrollPersistence);
    bindReady(initFeaturedToggle);
    bindReady(initPortfolioSkillPills);
}(window, document));

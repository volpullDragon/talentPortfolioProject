/* Shared dropdown interactions for the notification and profile menus in the application shell.
   The module owns open/close behavior, outside-click dismissal, and Escape-key handling for the shared navbar controls.
   Page-specific menus should not be added here unless they follow the same shell-level pattern. */
(function (window, document) {
    'use strict';

    function initNotificationsDropdown() {
        const notificationsToggle = document.querySelector('.notifications-toggle');
        const notificationsMenu = document.getElementById('notificationsMenu');

        if (!notificationsToggle || !notificationsMenu) {
            return;
        }

        const closeMenu = () => {
            notificationsMenu.classList.remove('is-open');
            notificationsToggle.setAttribute('aria-expanded', 'false');
            notificationsMenu.setAttribute('aria-hidden', 'true');
        };

        notificationsToggle.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();
            const willOpen = !notificationsMenu.classList.contains('is-open');
            notificationsMenu.classList.toggle('is-open', willOpen);
            notificationsToggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
            notificationsMenu.setAttribute('aria-hidden', willOpen ? 'false' : 'true');
        });

        notificationsMenu.addEventListener('click', function (event) {
            event.stopPropagation();
        });

        document.addEventListener('click', function () {
            closeMenu();
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                closeMenu();
            }
        });
    }

    function initProfileDropdown() {
        const profileToggle = document.querySelector('.profile-toggle');
        const profileMenu = document.getElementById('profileMenu');

        if (!profileToggle || !profileMenu) {
            return;
        }

        const closeProfileMenu = () => {
            profileMenu.classList.remove('is-open');
            profileToggle.setAttribute('aria-expanded', 'false');
            profileMenu.setAttribute('aria-hidden', 'true');
        };

        profileToggle.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();

            const willOpen = !profileMenu.classList.contains('is-open');
            profileMenu.classList.toggle('is-open', willOpen);
            profileToggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
            profileMenu.setAttribute('aria-hidden', willOpen ? 'false' : 'true');
        });

        profileMenu.addEventListener('click', function (event) {
            event.stopPropagation();
        });

        document.addEventListener('click', function () {
            closeProfileMenu();
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                closeProfileMenu();
            }
        });
    }

    window.SharedDropdowns = Object.assign({}, window.SharedDropdowns, {
        initNotificationsDropdown: initNotificationsDropdown,
        initProfileDropdown: initProfileDropdown,
    });

    const bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : (fn) => document.addEventListener('DOMContentLoaded', fn, { once: true });

    bindReady(initNotificationsDropdown);
    bindReady(initProfileDropdown);
}(window, document));

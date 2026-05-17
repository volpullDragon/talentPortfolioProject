/* Shared page initializers for cross-page behaviors that are not specific to one route.
   This module handles things like conversation scrolling, settings search hydration, and staged reveal effects for field project cards.
   It acts as a shared bootstrap layer for small page enhancements that do not warrant a full feature module. */
(function (window, document) {
    'use strict';

    // Keep the latest conversation content visible when the page or form updates.
    function initConversationAutoScroll() {
        var scrollArea = document.querySelector('.conversation-scroll-area');
        var composeForm = document.querySelector('.conversation-compose-form');

        if (scrollArea === null) {
            return;
        }

        var storageKey = 'conversationScroll:' + window.location.pathname;

        // Scroll the message pane to the bottom using the requested animation style.
        var scrollToLatest = function (behavior) {
            scrollArea.scrollTo({
                top: scrollArea.scrollHeight,
                behavior: behavior,
            });
        };

        var shouldSmoothScroll = false;
        try {
            shouldSmoothScroll = sessionStorage.getItem(storageKey) === 'smooth';
            sessionStorage.removeItem(storageKey);
        } catch (error) {
            shouldSmoothScroll = false;
        }

        scrollToLatest(shouldSmoothScroll ? 'smooth' : 'auto');

        if (composeForm !== null) {
            composeForm.addEventListener('submit', function () {
                try {
                    sessionStorage.setItem(storageKey, 'smooth');
                } catch (error) {
                }
            });
        }
    }

    // Load matching course options from the JSON endpoint as the user types.
    function initSettingsCourseSearch() {
        var courseInputs = Array.from(document.querySelectorAll('input[data-course-source][list]'));
        if (!courseInputs.length) {
            return;
        }

        var sourceUrl = courseInputs[0].dataset.courseSource;
        if (!sourceUrl) {
            return;
        }

        fetch(sourceUrl)
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Unable to load course list');
                }
                return response.json();
            })
            .then(function (data) {
                var courses = Array.isArray(data.courses) ? data.courses : [];

                courseInputs.forEach(function (courseInput) {
                    var listId = courseInput.getAttribute('list');
                    var courseList = listId ? document.getElementById(listId) : null;
                    if (!courseList) {
                        return;
                    }

                    var fragment = document.createDocumentFragment();
                    courses.forEach(function (course) {
                        var option = document.createElement('option');
                        option.value = course;
                        fragment.appendChild(option);
                    });

                    courseList.replaceChildren(fragment);
                });
            })
            .catch(function (error) {
                console.error('Failed to load Westminster courses:', error);
            });
    }

    // Stagger the placeholder reveal so field project cards animate in sequence.
    function initFieldProjectPlaceholders() {
        var cards = document.querySelectorAll('[data-field-project-card]');
        if (!cards.length) {
            return;
        }

        cards.forEach(function (card, index) {
            window.setTimeout(function () {
                card.classList.add('is-ready');
            }, index * 45);
        });
    }

    window.SharedPageInits = Object.assign({}, window.SharedPageInits, {
        initConversationAutoScroll: initConversationAutoScroll,
        initSettingsCourseSearch: initSettingsCourseSearch,
        initFieldProjectPlaceholders: initFieldProjectPlaceholders,
    });

    var bindReady = window.AppCore && typeof window.AppCore.bindDomReady === 'function'
        ? window.AppCore.bindDomReady
        : function (fn) { document.addEventListener('DOMContentLoaded', fn, { once: true }); };

    bindReady(initConversationAutoScroll);
    bindReady(initSettingsCourseSearch);
    bindReady(initFieldProjectPlaceholders);
}(window, document));

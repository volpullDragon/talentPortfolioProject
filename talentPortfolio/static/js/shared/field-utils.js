/* Shared field utilities for slug normalization, theme selection, confidence parsing, and skill tokenization.
   These helpers are intentionally generic because multiple student, project, and faculty features reuse the same field logic.
   Avoid adding page-specific behavior here so the utilities stay predictable and easy to test. */
(function (window) {
    'use strict';

    function normalizeFieldSlug(fieldName) {
        return (fieldName || '')
            .toLowerCase()
            .trim()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '');
    }

    function getFieldThemeFromName(fieldName) {
        var slug = normalizeFieldSlug(fieldName);

        var fieldThemes = {
            'artificial-intelligence': { accentStart: 'hsl(60 80% 52%)', accentEnd: 'hsl(76 78% 46%)', accent: 'hsl(76 78% 46%)', soft: 'hsl(60 80% 92%)', deep: 'hsl(90 70% 35%)' },
            'cloud-computing': { accentStart: 'hsl(200 80% 52%)', accentEnd: 'hsl(216 78% 46%)', accent: 'hsl(216 78% 46%)', soft: 'hsl(200 80% 92%)', deep: 'hsl(230 70% 35%)' },
            'computer-networks': { accentStart: 'hsl(165 80% 52%)', accentEnd: 'hsl(181 78% 46%)', accent: 'hsl(181 78% 46%)', soft: 'hsl(165 80% 92%)', deep: 'hsl(195 70% 35%)' },
            'cyber-security': { accentStart: 'hsl(24 90% 54%)', accentEnd: 'hsl(36 86% 46%)', accent: 'hsl(36 86% 46%)', soft: 'hsl(30 90% 92%)', deep: 'hsl(20 72% 34%)' },
            'data-science': { accentStart: 'hsl(305 80% 52%)', accentEnd: 'hsl(321 78% 46%)', accent: 'hsl(321 78% 46%)', soft: 'hsl(305 80% 92%)', deep: 'hsl(335 70% 35%)' },
            'database-systems': { accentStart: 'hsl(210 32% 52%)', accentEnd: 'hsl(220 36% 42%)', accent: 'hsl(220 36% 42%)', soft: 'hsl(210 36% 90%)', deep: 'hsl(228 40% 30%)' },
            'machine-learning': { accentStart: 'hsl(340 80% 52%)', accentEnd: 'hsl(356 78% 46%)', accent: 'hsl(356 78% 46%)', soft: 'hsl(340 80% 92%)', deep: 'hsl(10 70% 35%)' },
            'mobile-app-development': { accentStart: 'hsl(30 80% 52%)', accentEnd: 'hsl(46 78% 46%)', accent: 'hsl(46 78% 46%)', soft: 'hsl(30 80% 92%)', deep: 'hsl(60 70% 35%)' },
            'operating-systems': { accentStart: 'hsl(270 80% 52%)', accentEnd: 'hsl(286 78% 46%)', accent: 'hsl(286 78% 46%)', soft: 'hsl(270 80% 92%)', deep: 'hsl(300 70% 35%)' },
            'software-engineering': { accentStart: 'hsl(235 80% 52%)', accentEnd: 'hsl(251 78% 46%)', accent: 'hsl(251 78% 46%)', soft: 'hsl(235 80% 92%)', deep: 'hsl(265 70% 35%)' },
            'web-development': { accentStart: 'hsl(130 80% 52%)', accentEnd: 'hsl(146 78% 46%)', accent: 'hsl(146 78% 46%)', soft: 'hsl(130 80% 92%)', deep: 'hsl(160 70% 35%)' }
        };

        return fieldThemes[slug] || {
            accentStart: '#2563eb',
            accentEnd: '#1d4ed8',
            accent: '#1d4ed8',
            soft: '#dbeafe',
            deep: '#1e3a8a'
        };
    }

    function parseConfidencePercent(confidenceText) {
        var raw = (confidenceText || '').trim();
        if (!raw) {
            return 0;
        }

        var numericMatch = raw.match(/\d+/);
        if (numericMatch) {
            var value = Number.parseInt(numericMatch[0], 10);
            return Number.isNaN(value) ? 0 : Math.max(0, Math.min(100, value));
        }

        var normalized = raw.toLowerCase();
        var labelToPercent = {
            'low confidence': 20,
            'developing confidence': 40,
            'moderate confidence': 60,
            'high confidence': 80,
            'advanced confidence': 100
        };

        if (Object.prototype.hasOwnProperty.call(labelToPercent, normalized)) {
            return labelToPercent[normalized];
        }

        if (normalized.includes('very high')) {
            return 100;
        }
        if (normalized.includes('high')) {
            return 80;
        }
        if (normalized.includes('moderate') || normalized.includes('medium') || normalized.includes('intermediate')) {
            return 60;
        }
        if (normalized.includes('developing') || normalized.includes('learning') || normalized.includes('low')) {
            return 40;
        }

        return 0;
    }

    var CONFIDENCE_SCALE = [
        { label: 'Low Confidence', percent: 20 },
        { label: 'Developing Confidence', percent: 40 },
        { label: 'Moderate Confidence', percent: 60 },
        { label: 'High Confidence', percent: 80 },
        { label: 'Advanced Confidence', percent: 100 }
    ];

    function normalizeConfidencePercent(percent) {
        var numericPercent = Number.isFinite(percent) ? percent : 0;
        var clamped = Math.max(20, Math.min(100, numericPercent));
        return Math.round(clamped / 10) * 10;
    }

    function getConfidenceLabelForPercent(percent) {
        var normalized = normalizeConfidencePercent(percent);
        return CONFIDENCE_SCALE.reduce(function (currentLabel, step) {
            return normalized >= step.percent ? step.label : currentLabel;
        }, CONFIDENCE_SCALE[0].label);
    }

    function splitSkills(rawSkills) {
        var parts = (rawSkills || '')
            .split(/[\,\n;\/|]+/)
            .map(function (item) { return item.trim(); })
            .filter(function (item) { return item.length > 0; });

        return Array.from(new Set(parts));
    }

    window.FieldUtils = Object.assign({}, window.FieldUtils, {
        normalizeFieldSlug: normalizeFieldSlug,
        getFieldThemeFromName: getFieldThemeFromName,
        parseConfidencePercent: parseConfidencePercent,
        normalizeConfidencePercent: normalizeConfidencePercent,
        getConfidenceLabelForPercent: getConfidenceLabelForPercent,
        splitSkills: splitSkills
    });

    // Legacy global names retained for compatibility with existing feature modules.
    window.normalizeFieldSlug = normalizeFieldSlug;
    window.getFieldThemeFromName = getFieldThemeFromName;
    window.parseConfidencePercent = parseConfidencePercent;
    window.normalizeConfidencePercent = normalizeConfidencePercent;
    window.getConfidenceLabelForPercent = getConfidenceLabelForPercent;
    window.splitSkills = splitSkills;
}(window));

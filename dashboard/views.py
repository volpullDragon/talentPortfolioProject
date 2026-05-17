from django.shortcuts import render
from django.http import JsonResponse
import json
import re
import hashlib
from datetime import timedelta
from django.shortcuts import redirect, get_object_or_404
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from . import forms
from .models import FieldOfExpertise, Project, Picture, Video, Files, JobListing, SavedStudent, Interview, SavedJob, JobApplication
from django.contrib import messages
from functools import wraps
import shutil
import subprocess
from pathlib import Path
from django.conf import settings
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.cache import cache
from userManagement.models import Message, Notification, Student, Portfolio
from urllib.parse import urlencode


def get_user_portfolio(user): 
    """Get the user's portfolio. 
    Returns None if the user does not have a student portfolio.
    """
    student = getattr(user, 'student', None)
    return getattr(student, 'portfolio', None)


def get_user_student(user):
    """Get the user's student record. Returns None if unavailable."""
    return getattr(user, 'student', None)


def get_user_faculty(user):
    """Get the user's faculty record. Returns None if unavailable."""
    return getattr(user, 'faculty', None)


def get_user_faculty_profile(user):
    """Get the user's faculty profile. Returns None if unavailable."""
    faculty = get_user_faculty(user)
    return getattr(faculty, 'profile', None)

def get_user_project(user, project_id):
    """Get a project from the user's portfolio.
    Returns None if the project does not exist or does not belong to the user's portfolio.
    """
    return get_object_or_404(
        Project, 
        id=project_id, 
        field_of_expertise__portfolio=get_user_portfolio(user)
    )


def parse_text_entries(raw_text):
    """Split comma/newline/semi-colon separated text into distinct entries.
    Also performs cleaning such as trimming whitespace, removing empty entries, and filtering out common non-entry phrases.
    """
    segments = re.split(r"[,;\n]+", raw_text or "")
    cleaned = []
    for segment in segments:
        value = segment.strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in {'skills demonstrated', 'key skills', 'technologies and tools used', 'no tools listed'}:
            continue
        if value not in cleaned:
            cleaned.append(value)
    return cleaned



def _normalize_skill_token(value):
    token = re.sub(r"[^a-z0-9+#]+", "", (value or "").strip().lower())
    return token


def _split_skill_text(raw_text):
    # Split on common list separators while keeping tokens like CI/CD intact.
    return [segment.strip() for segment in re.split(r"[,;\n|]+|\s+/\s+", raw_text or "") if segment.strip()]


def _filter_student_jobs(queryset, search_query, active_category):
    query = (search_query or '').strip()
    category = (active_category or 'all').strip().lower()

    valid_categories = {'all', 'frontend', 'backend', 'design', 'fullstack', 'devops'}
    if category not in valid_categories:
        category = 'all'

    filtered = queryset

    if query:
        filtered = filtered.filter(
            Q(job_title__icontains=query)
            | Q(required_skills_and_tools__icontains=query)
            | Q(description__icontains=query)
            | Q(profile__faculty__first_name__icontains=query)
            | Q(profile__faculty__last_name__icontains=query)
        )

    category_keywords = {
        'frontend': ['frontend', 'front-end', 'react', 'vue', 'angular', 'html', 'css', 'javascript'],
        'backend': ['backend', 'back-end', 'api', 'django', 'flask', 'fastapi', 'database', 'sql'],
        'design': ['ui', 'ux', 'design', 'figma', 'prototype'],
        'fullstack': ['fullstack', 'full stack'],
        'devops': ['devops', 'docker', 'kubernetes', 'aws', 'azure', 'ci/cd', 'deployment', 'cloud'],
    }

    if category != 'all':
        keyword_filter = Q()
        for keyword in category_keywords.get(category, []):
            keyword_filter |= (
                Q(job_title__icontains=keyword)
                | Q(required_skills_and_tools__icontains=keyword)
                | Q(description__icontains=keyword)
            )
        filtered = filtered.filter(keyword_filter)

    return filtered, category


def _extract_course_keywords(course_name):
    stop_words = {
        'bsc', 'ba', 'msc', 'ma', 'hons', 'honours', 'with', 'foundation',
        'degree', 'course', 'the', 'and', 'for', 'in', 'of', 'to', 'year',
    }
    tokens = []
    for token in re.split(r'[^a-z0-9]+', (course_name or '').lower()):
        if len(token) < 3 or token in stop_words:
            continue
        if token not in tokens:
            tokens.append(token)
    return tokens


def _build_related_course_keywords(student_course):
    base_keywords = set(_extract_course_keywords(student_course))
    lowered = (student_course or '').lower()

    domain_aliases = [
        (
            {'computer', 'computing', 'science', 'software'},
            {
                'software', 'developer', 'engineering', 'backend', 'frontend',
                'fullstack', 'cyber', 'network', 'cloud', 'devops', 'data',
            },
        ),
        (
            {'data', 'analytics', 'statistics', 'machine', 'learning'},
            {
                'data', 'analytics', 'machine', 'learning', 'ai', 'python',
                'sql', 'business', 'intelligence', 'cloud',
            },
        ),
        (
            {'business', 'management', 'marketing', 'finance'},
            {
                'business', 'management', 'marketing', 'finance', 'operations',
                'strategy', 'analytics', 'project',
            },
        ),
        (
            {'design', 'ux', 'ui', 'architecture'},
            {
                'design', 'ux', 'ui', 'figma', 'prototype', 'creative',
                'architecture', 'visual',
            },
        ),
    ]

    for triggers, related in domain_aliases:
        if any(trigger in base_keywords or trigger in lowered for trigger in triggers):
            base_keywords.update(related)

    return sorted(base_keywords)


def _filter_jobs_by_course_scope(queryset, student_course, active_scope):
    scope = (active_scope or 'all').strip().lower()
    valid_scopes = {'all', 'my_course', 'related'}
    if scope not in valid_scopes:
        scope = 'all'

    if scope == 'all':
        return queryset, scope

    course_text = (student_course or '').strip()
    if not course_text:
        return queryset, 'all'

    if scope == 'my_course':
        course_keywords = _extract_course_keywords(course_text)
        keyword_filter = Q(profile__faculty__professor_of__icontains=course_text)
        for keyword in course_keywords:
            keyword_filter |= Q(profile__faculty__professor_of__icontains=keyword)
            keyword_filter |= Q(job_title__icontains=keyword)
            keyword_filter |= Q(required_skills_and_tools__icontains=keyword)
            keyword_filter |= Q(description__icontains=keyword)
        return queryset.filter(keyword_filter), scope

    related_keywords = _build_related_course_keywords(course_text)
    if not related_keywords:
        return queryset, scope

    related_filter = Q()
    for keyword in related_keywords:
        related_filter |= Q(profile__faculty__professor_of__icontains=keyword)
        related_filter |= Q(job_title__icontains=keyword)
        related_filter |= Q(required_skills_and_tools__icontains=keyword)
        related_filter |= Q(description__icontains=keyword)

    return queryset.filter(related_filter), scope


def _collect_job_required_skill_tokens(job):
    tokens = []
    for item in _split_skill_text(getattr(job, 'required_skills_and_tools', '') or ''):
        normalized = _normalize_skill_token(item)
        if normalized and normalized not in tokens:
            tokens.append(normalized)
    return tokens


def _job_matches_skill_filter(job, active_skill_filter):
    skill = (active_skill_filter or '').strip().lower()
    if not skill or skill == 'all':
        return True

    required_tokens = _collect_job_required_skill_tokens(job)
    if any(skill == token or skill in token or token in skill for token in required_tokens):
        return True

    search_sources = ' '.join([
        getattr(job, 'required_skills_and_tools', '') or '',
        getattr(job, 'job_title', '') or '',
        getattr(job, 'description', '') or '',
    ]).lower()
    return skill in search_sources


_FIELD_OF_EXPERTISE_FILTER_CACHE = {}


def _slugify_course_name(course_name):
    if not course_name:
        return ''

    slug = str(course_name).lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    return slug.strip('_')


def _load_field_of_expertise_filters(student_course=''):
    global _FIELD_OF_EXPERTISE_FILTER_CACHE

    course_slug = _slugify_course_name(student_course)
    cache_key = course_slug or '__all__'
    if cache_key in _FIELD_OF_EXPERTISE_FILTER_CACHE:
        return _FIELD_OF_EXPERTISE_FILTER_CACHE[cache_key]

    folder = settings.BASE_DIR / 'static' / 'course_fields.json'
    label_lookup = {}
    token_map = {}

    source_paths = []
    if course_slug:
        source_path = folder / f'{course_slug}_fields.json'
        if source_path.exists():
            source_paths = [source_path]
    if not source_paths:
        _FIELD_OF_EXPERTISE_FILTER_CACHE[cache_key] = ([], {})
        return _FIELD_OF_EXPERTISE_FILTER_CACHE[cache_key]

    for source_path in source_paths:
        try:
            payload = json.loads(source_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            continue

        groups = payload.get('groups') if isinstance(payload, dict) else None
        fields = payload.get('fields') if isinstance(payload, dict) else None

        if not isinstance(fields, list):
            continue

        group_token_sets = []
        if isinstance(groups, dict):
            for values in groups.values():
                if not isinstance(values, list):
                    continue
                normalized_values = [
                    _normalize_skill_token(item)
                    for item in values
                    if isinstance(item, str) and _normalize_skill_token(item)
                ]
                if normalized_values:
                    group_token_sets.append(set(normalized_values))

        for item in fields:
            if not isinstance(item, str):
                continue

            normalized = _normalize_skill_token(item)
            if not normalized:
                continue

            if normalized not in label_lookup:
                label_lookup[normalized] = item.strip()

            token_set = token_map.setdefault(normalized, set())
            token_set.add(normalized)

            for group_tokens in group_token_sets:
                if normalized in group_tokens:
                    token_set.update(group_tokens)

            # Add split-word tokens so partial but meaningful matches can still work.
            for part in re.split(r'[^a-z0-9]+', item.lower()):
                part_token = _normalize_skill_token(part)
                if part_token and len(part_token) > 2:
                    token_set.add(part_token)

    filters = [
        {
            'raw': token,
            'label': label,
        }
        for token, label in label_lookup.items()
    ]

    filters.sort(key=lambda entry: entry['label'].lower())

    _FIELD_OF_EXPERTISE_FILTER_CACHE[cache_key] = (filters, token_map)
    return _FIELD_OF_EXPERTISE_FILTER_CACHE[cache_key]


def _job_matches_field_filter(job, field_token_set, field_filter_token):
    required_tokens = set(_collect_job_required_skill_tokens(job))
    if required_tokens.intersection(field_token_set):
        return True

    search_text = ' '.join([
        getattr(job, 'required_skills_and_tools', '') or '',
        getattr(job, 'job_title', '') or '',
        getattr(job, 'description', '') or '',
    ]).lower()

    if field_filter_token in search_text:
        return True

    return any(token in search_text for token in field_token_set if len(token) > 2)


def _format_skill_label(value):
    normalized = _normalize_skill_token(value)
    label_map = {
        'frontend': 'Front End',
        'backend': 'Back End',
        'fullstack': 'Full Stack',
        'devops': 'DevOps',
        'ui': 'UI',
        'ux': 'UX',
        'uiux': 'UI/UX',
        'api': 'API',
        'sql': 'SQL',
        'aws': 'AWS',
        'css': 'CSS',
        'html': 'HTML',
        'javascript': 'JavaScript',
        'typescript': 'TypeScript',
        'django': 'Django',
        'flask': 'Flask',
        'fastapi': 'FastAPI',
        'react': 'React',
        'vue': 'Vue',
        'angular': 'Angular',
        'docker': 'Docker',
        'kubernetes': 'Kubernetes',
        'figma': 'Figma',
        'prototype': 'Prototype',
        'database': 'Database',
        'deployment': 'Deployment',
        'cloud': 'Cloud',
        'cicd': 'CI/CD',
    }

    if normalized in label_map:
        return label_map[normalized]

    if not value:
        return ''

    cleaned = re.sub(r'[_-]+', ' ', str(value)).strip()
    cleaned = re.sub(r'(?<!^)(?=[A-Z])', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title()


_SKILL_LABEL_LOOKUP = None


def _build_skill_label_lookup():
    lookup = {
        'frontend': 'Front End',
        'backend': 'Back End',
        'fullstack': 'Full Stack',
        'devops': 'DevOps',
        'ui': 'UI',
        'ux': 'UX',
        'uiux': 'UI/UX',
        'api': 'API',
        'sql': 'SQL',
        'aws': 'AWS',
        'css': 'CSS',
        'html': 'HTML',
        'javascript': 'JavaScript',
        'typescript': 'TypeScript',
        'django': 'Django',
        'flask': 'Flask',
        'fastapi': 'FastAPI',
        'react': 'React',
        'vue': 'Vue',
        'angular': 'Angular',
        'docker': 'Docker',
        'kubernetes': 'Kubernetes',
        'figma': 'Figma',
        'prototype': 'Prototype',
        'database': 'Database',
        'deployment': 'Deployment',
        'cloud': 'Cloud',
        'cicd': 'CI/CD',
        'cavendish': 'Cavendish',
        'cavendishcampus': 'Cavendish Campus',
        'harrowcampus': 'Harrow Campus',
        'marylebonecampus': 'Marylebone Campus',
        'regentcampus': 'Regent Campus',
        'agilemethodologiesandcrossfunctionalcollaboration': 'Agile methodologies and cross-functional collaboration',
        'architecturaltechnologybschonours': 'Architectural Technology BSc Honours',
        'architecturaltechnologywithfoundationbschonours': 'Architectural Technology with Foundation BSc Honours',
        'artificialintelligence': 'Artificial Intelligence',
        'cloudcomputing': 'Cloud Computing',
        'computernetworks': 'Computer Networks',
        'computerscience': 'Computer Science',
        'computersciencewithfoundationbschonours': 'Computer Science with Foundation BSc Honours',
        'datascience': 'Data Science',
        'machinelearning': 'Machine Learning',
        'softwareengineering': 'Software Engineering',
        'mobileappdevelopment': 'Mobile App Development',
        'webdevelopment': 'Web Development',
        'databasesystems': 'Database Systems',
        'operatingsystems': 'Operating Systems',
        'cybersecurity': 'Cyber Security',
    }

    static_sources = [
        settings.BASE_DIR / 'static' / 'course_fields.json' / 'computer_science_fields.json',
        settings.BASE_DIR / 'static' / 'westminster_courses.json',
    ]

    for source_path in static_sources:
        try:
            data = json.loads(source_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            continue

        if isinstance(data, dict):
            values = []
            for value in data.values():
                if isinstance(value, list):
                    values.extend(value)
        elif isinstance(data, list):
            values = data
        else:
            values = []

        for value in values:
            if not isinstance(value, str):
                continue
            normalized = _normalize_skill_token(value)
            if normalized and normalized not in lookup:
                lookup[normalized] = value.strip()

    return lookup


def _skill_display_label(value):
    global _SKILL_LABEL_LOOKUP

    if value is None:
        return ''

    if _SKILL_LABEL_LOOKUP is None:
        _SKILL_LABEL_LOOKUP = _build_skill_label_lookup()

    normalized = _normalize_skill_token(value)
    if normalized in _SKILL_LABEL_LOOKUP:
        return _SKILL_LABEL_LOOKUP[normalized]

    cleaned = re.sub(r'[_-]+', ' ', str(value)).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    if not cleaned:
        return ''

    if re.search(r'[\s/\-]', cleaned):
        return cleaned

    if cleaned.isupper() or any(char.isupper() for char in cleaned[1:]):
        cleaned = re.sub(r'(?<!^)(?=[A-Z])', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    return cleaned

def _candidate_matches_query(candidate, query):
    q = (query or '').strip().lower()
    if not q:
        return True

    student = candidate.get('student')
    best_job = candidate.get('best_job')

    haystack = ' '.join([
        getattr(student, 'first_name', '') or '',
        getattr(student, 'last_name', '') or '',
        getattr(student, 'username', '') or '',
        getattr(student, 'current_course', '') or '',
        getattr(student, 'campus', '') or '',
        candidate.get('matched_skills_source', '') or '',
        getattr(best_job, 'job_title', '') if best_job else '',
    ]).lower()

    return q in haystack


def _candidate_matches_skill_filter(candidate, active_skill_filter):
    skill = (active_skill_filter or '').strip().lower()
    if not skill or skill == 'all':
        return True

    student_tokens = [token.lower() for token in (candidate.get('student_skill_tokens') or [])]
    if any(skill == token or skill in token or token in skill for token in student_tokens):
        return True

    search_sources = ' '.join([
        candidate.get('student_skills_source', '') or '',
        candidate.get('matched_skills_source', '') or '',
    ]).lower()
    return skill in search_sources


_CONFIDENCE_TO_WEIGHT = {
    'lowconfidence': 0.40,
    'developingconfidence': 0.60,
    'moderateconfidence': 0.75,
    'highconfidence': 0.90,
    'advancedconfidence': 1.00,
    'veryhighconfidence': 1.00,
}


def _build_student_scoring_context(student):
    context = {
        'project_tokens': set(),
        'profile_tokens': set(),
        'confidence_by_token': {},
        'course_name': (getattr(student, 'current_course', '') or '').strip(),
        'all_tokens': set(),
    }

    portfolio = getattr(student, 'portfolio', None)
    if not portfolio:
        return context

    def _apply_confidence(tokens, confidence_text):
        confidence_token = _normalize_skill_token(confidence_text)
        weight = _CONFIDENCE_TO_WEIGHT.get(confidence_token, 0.70)
        for token in tokens:
            current = context['confidence_by_token'].get(token, 0.0)
            if weight > current:
                context['confidence_by_token'][token] = weight

    for item in _split_skill_text(portfolio.what_I_bring or ''):
        token = _normalize_skill_token(item)
        if not token:
            continue
        context['profile_tokens'].add(token)
        context['all_tokens'].add(token)

    fields = portfolio.fields_of_expertise.all()
    for field in fields:
        field_tokens = set()
        for value in [field.field_of_expertise, field.skills]:
            for item in _split_skill_text(value or ''):
                token = _normalize_skill_token(item)
                if not token:
                    continue
                field_tokens.add(token)
                context['profile_tokens'].add(token)
                context['all_tokens'].add(token)

        _apply_confidence(field_tokens, field.level_of_confidence)

        for project in field.projects.all():
            project_tokens = set()
            for value in [project.skills_demonstrated, project.tech_n_tools_used]:
                for item in _split_skill_text(value or ''):
                    token = _normalize_skill_token(item)
                    if not token:
                        continue
                    project_tokens.add(token)
                    context['project_tokens'].add(token)
                    context['all_tokens'].add(token)

            _apply_confidence(project_tokens or field_tokens, field.level_of_confidence)

    return context


def _score_student_against_job(student, job, student_tokens=None, scoring_context=None, job_tokens=None):
    tokens = student_tokens if student_tokens is not None else _collect_student_skill_tokens(student)
    context = scoring_context if scoring_context is not None else _build_student_scoring_context(student)

    required_tokens = set(job_tokens) if job_tokens is not None else {
        _normalize_skill_token(skill)
        for skill in _split_skill_text(job.required_skills_and_tools or '')
    }
    required_tokens.discard('')

    student_course = (context.get('course_name') or '').strip()
    faculty_course = (
        getattr(getattr(job, 'profile', None), 'faculty', None)
        and getattr(job.profile.faculty, 'professor_of', '')
    ) or ''

    relevance_score = 0.50
    student_course_lower = student_course.lower()
    faculty_course_lower = faculty_course.lower()
    if student_course_lower and faculty_course_lower:
        if student_course_lower == faculty_course_lower:
            relevance_score = 1.00
        else:
            student_keywords = set(_extract_course_keywords(student_course_lower))
            faculty_keywords = set(_extract_course_keywords(faculty_course_lower))
            if student_keywords and faculty_keywords:
                shared = student_keywords.intersection(faculty_keywords)
                if shared:
                    relevance_score = min(0.95, 0.55 + (0.40 * (len(shared) / max(len(student_keywords), 1))))
                else:
                    relevance_score = 0.25

    if not required_tokens:
        breakdown = {
            'required': 0,
            'proficiency': 0,
            'relevance': int(round(relevance_score * 100)),
        }
        return 0, set(), breakdown, 0.0

    overlap = tokens.intersection(required_tokens)
    if not overlap:
        breakdown = {
            'required': 0,
            'proficiency': 0,
            'relevance': int(round(relevance_score * 100)),
        }
        return 0, set(), breakdown, 0.0

    required_score = len(overlap) / max(len(required_tokens), 1)

    proficiency_values = [context['confidence_by_token'].get(token, 0.70) for token in overlap]
    avg_proficiency = sum(proficiency_values) / len(proficiency_values) if proficiency_values else 0.70
    min_proficiency = min(proficiency_values) if proficiency_values else 0.70
    proficiency_score = (0.70 * avg_proficiency) + (0.30 * min_proficiency)

    final_score = (
        (0.45 * required_score)
        + (0.45 * proficiency_score)
        + (0.10 * relevance_score)
    ) * 100

    breakdown = {
        'required': int(round(required_score * 100)),
        'proficiency': int(round(proficiency_score * 100)),
        'relevance': int(round(relevance_score * 100)),
    }

    normalized_final_score = max(0.0, min(100.0, final_score))
    floored_score = int(normalized_final_score)

    return floored_score, overlap, breakdown, normalized_final_score


def _calculate_student_job_match_score(student, job):
    score, _, _, _ = _score_student_against_job(student, job)
    return score


def _collect_student_skill_tokens(student):
    tokens = set()

    # Include explicit course context so course-specific jobs can still match.
    for seed in [student.current_course, student.campus, student.current_year]:
        normalized = _normalize_skill_token(seed)
        if normalized:
            tokens.add(normalized)

    portfolio = getattr(student, 'portfolio', None)
    if not portfolio:
        return tokens

    for item in _split_skill_text(portfolio.what_I_bring or ""):
        normalized = _normalize_skill_token(item)
        if normalized:
            tokens.add(normalized)

    fields = portfolio.fields_of_expertise.all()
    for field in fields:
        for value in [field.field_of_expertise, field.skills, field.level_of_confidence]:
            for item in _split_skill_text(value or ""):
                normalized = _normalize_skill_token(item)
                if normalized:
                    tokens.add(normalized)

        for project in field.projects.all():
            for value in [project.skills_demonstrated, project.tech_n_tools_used]:
                for item in _split_skill_text(value or ""):
                    normalized = _normalize_skill_token(item)
                    if normalized:
                        tokens.add(normalized)

    return tokens


def _dedupe_candidate_cards_by_student(candidate_cards):
    """Keep only the first card per student ID to avoid duplicate search entries."""
    unique_cards = []
    seen_student_ids = set()

    for card in candidate_cards:
        student = card.get('student') if isinstance(card, dict) else None
        student_id = getattr(student, 'id', None)
        if student_id is None:
            unique_cards.append(card)
            continue
        if student_id in seen_student_ids:
            continue
        seen_student_ids.add(student_id)
        unique_cards.append(card)

    return unique_cards


_FACULTY_MATCH_CACHE_TTL_SECONDS = 120


def _get_faculty_match_cache_key(faculty_profile_id, job_ids):
    token = f"{faculty_profile_id}:{','.join(str(job_id) for job_id in sorted(job_ids))}"
    digest = hashlib.md5(token.encode('utf-8')).hexdigest()
    return f"faculty:candidate-matches:v1:{digest}"


def _get_cached_faculty_candidate_matches(faculty_profile, jobs):
    profile_id = getattr(faculty_profile, 'id', None) or 0
    job_ids = [job.id for job in jobs if getattr(job, 'id', None)]
    cache_key = _get_faculty_match_cache_key(profile_id, job_ids)

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    computed = _build_faculty_candidate_matches(jobs)
    cache.set(cache_key, computed, _FACULTY_MATCH_CACHE_TTL_SECONDS)
    return computed


def _build_faculty_candidate_matches(faculty_jobs):
    job_entries = []
    required_tokens_union = set()
    required_skill_labels = []
    required_skill_label_keys = set()

    for job in faculty_jobs:
        raw_skills = _split_skill_text(job.required_skills_and_tools or "")
        token_set = set()
        for skill in raw_skills:
            normalized = _normalize_skill_token(skill)
            if not normalized:
                continue
            token_set.add(normalized)
            if normalized not in required_skill_label_keys:
                required_skill_label_keys.add(normalized)
                required_skill_labels.append({
                    'raw': normalized,
                    'label': _skill_display_label(skill) or _format_skill_label(skill),
                })
        required_tokens_union.update(token_set)
        job_entries.append({
            'job': job,
            'skill_tokens': token_set,
        })

    students = Student.objects.select_related('portfolio').prefetch_related('portfolio__fields_of_expertise__projects').all()
    candidate_cards = []

    for student in students:
        skill_tokens = _collect_student_skill_tokens(student)
        skill_label_map = {}
        portfolio = getattr(student, 'portfolio', None)
        if portfolio:
            raw_skill_sources = [portfolio.what_I_bring or '']
            fields = portfolio.fields_of_expertise.all()
            for field in fields:
                raw_skill_sources.extend([field.field_of_expertise or '', field.skills or '', field.level_of_confidence or ''])
                for project in field.projects.all():
                    raw_skill_sources.extend([project.skills_demonstrated or '', project.tech_n_tools_used or '', project.project_title or ''])

            for raw_source in raw_skill_sources:
                for item in _split_skill_text(raw_source):
                    normalized = _normalize_skill_token(item)
                    if normalized and normalized not in skill_label_map:
                        skill_label_map[normalized] = _skill_display_label(item) or _format_skill_label(item)

        overlap_union = required_tokens_union.intersection(skill_tokens) if required_tokens_union else set()

        best_job = None
        best_overlap = set()
        best_score = 0
        best_score_precise = 0.0
        best_score_breakdown = {
            'required': 0,
            'proficiency': 0,
            'relevance': 0,
        }

        scoring_context = _build_student_scoring_context(student)

        for entry in job_entries:
            job_tokens = entry['skill_tokens']
            if not job_tokens:
                continue

            score, overlap, score_breakdown, score_precise = _score_student_against_job(
                student,
                entry['job'],
                student_tokens=skill_tokens,
                scoring_context=scoring_context,
                job_tokens=job_tokens,
            )
            if not overlap:
                continue

            if score_precise > best_score_precise:
                best_score = score
                best_score_precise = score_precise
                best_overlap = overlap
                best_job = entry['job']
                best_score_breakdown = score_breakdown

        if best_job is None:
            best_score = int(round((len(overlap_union) / max(len(required_tokens_union), 1)) * 100)) if required_tokens_union else 0
            best_score_precise = float(best_score)
            best_overlap = overlap_union
            best_score_breakdown = {
                'required': best_score,
                'proficiency': 0,
                'relevance': 0,
            }

        readable_overlap = sorted(best_overlap)
        student_skill_tokens = sorted(skill_tokens)
        student_skill_labels = [skill_label_map.get(token, _format_skill_label(token)) for token in student_skill_tokens]

        candidate_cards.append({
            'student': student,
            'match_score': max(0, min(100, best_score)),
            'match_score_precise': max(0.0, min(100.0, round(best_score_precise, 1))),
            'best_job': best_job,
            'matched_tokens': readable_overlap,
            'matched_skills_source': ", ".join(readable_overlap),
            'student_skills_source': ", ".join(student_skill_tokens),
            'student_skill_tokens': student_skill_tokens,
            'student_skill_labels': student_skill_labels,
            'matched_count': len(readable_overlap),
            'score_breakdown': best_score_breakdown,
        })

    candidate_cards.sort(
        key=lambda item: (
            item.get('match_score_precise', item['match_score']),
            item['match_score'],
            item['matched_count'],
            (item['student'].first_name or '').lower(),
            (item['student'].last_name or '').lower(),
        ),
        reverse=True,
    )

    return candidate_cards, required_skill_labels


def save_project_skill_entries(project, entries):
    project.skills_demonstrated = "\n".join(entries)
    project.save(update_fields=['skills_demonstrated'])


def save_project_tech_entries(project, entries):
    project.tech_n_tools_used = "\n".join(entries)
    project.save(update_fields=['tech_n_tools_used'])


def try_generate_word_preview_pdf(file_record):
    """Attempt to convert DOC/DOCX into PDF preview using LibreOffice."""
    if not file_record.file:
        return False

    suffix = Path(file_record.file.name).suffix.lower()
    if suffix not in {'.doc', '.docx'}:
        return False

    soffice = shutil.which('soffice')
    if not soffice:
        return False

    input_path = Path(file_record.file.path)
    output_pdf = input_path.with_suffix('.pdf')

    if output_pdf.exists():
        return True

    try:
        subprocess.run(
            [
                soffice,
                '--headless',
                '--convert-to',
                'pdf:writer_pdf_Export',
                '--outdir',
                str(input_path.parent),
                str(input_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (subprocess.SubprocessError, OSError):
        return False

    return output_pdf.exists()


def student_required(view_func):
    """Require a student account."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'student'):
            messages.error(request, 'Access denied. Students only.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def faculty_required(view_func):
    """Require a faculty account."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'faculty'):
            messages.error(request, 'Access denied. Faculty only.')
            return redirect('faculty-login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view



@login_required
def dashboard_home(request):
    """Show dashboard content by user type."""
    
    # Student dashboard.
    if hasattr(request.user, 'student'):
        try:
            portfolio = get_user_portfolio(request.user)
            if portfolio is None:
                messages.warning(request, 'Please complete your portfolio setup.')
                return redirect('users-portfolio')
            fields = portfolio.fields_of_expertise.all()
            student = get_user_student(request.user)
            student_course = (getattr(student, 'current_course', '') or '').strip()
            all_jobs = JobListing.objects.all().select_related('profile__faculty').order_by('-posted_date', '-id')

            search_query = (request.GET.get('q') or '').strip()
            active_skill_filter = (request.GET.get('skill') or 'all').strip().lower()

            all_jobs, _ = _filter_student_jobs(all_jobs, search_query, 'all')

            _, field_token_map = _load_field_of_expertise_filters(student_course)

            if field_token_map:
                course_field_tokens = {token for token in field_token_map.keys() if token}
                student_course_keywords = set(_extract_course_keywords(student_course))

                scoped_jobs = []
                for job in list(all_jobs):
                    required_tokens = set(_collect_job_required_skill_tokens(job))
                    faculty_course_text = (
                        getattr(getattr(getattr(job, 'profile', None), 'faculty', None), 'professor_of', '')
                        or ''
                    )
                    faculty_course_token = _normalize_skill_token(faculty_course_text)
                    faculty_course_keywords = set(_extract_course_keywords(faculty_course_text))

                    matches_course_fields = bool(required_tokens.intersection(course_field_tokens))
                    matches_faculty_course_field = bool(
                        faculty_course_token
                        and any(
                            len(token) > 4 and token in faculty_course_token
                            for token in course_field_tokens
                        )
                    )
                    matches_same_course = bool(student_course_keywords.intersection(faculty_course_keywords))

                    if matches_course_fields or matches_faculty_course_field or matches_same_course:
                        scoped_jobs.append(job)

                all_jobs = scoped_jobs
            elif student_course:
                all_jobs, _ = _filter_jobs_by_course_scope(all_jobs, student_course, 'my_course')
                all_jobs = list(all_jobs)
            else:
                all_jobs = []

            skill_match_counts = {}
            skill_label_map = {}
            for job in all_jobs:
                tokens = _collect_job_required_skill_tokens(job)
                labels = [_skill_display_label(token) for token in tokens]
                for index, token in enumerate(tokens):
                    if not token:
                        continue
                    skill_match_counts[token] = skill_match_counts.get(token, 0) + 1
                    if token not in skill_label_map:
                        skill_label_map[token] = labels[index] if index < len(labels) else _skill_display_label(token)

            base_query_params = request.GET.copy()
            base_query_params.pop('page', None)

            required_skill_filters = []
            for token, count in skill_match_counts.items():
                query_params_for_skill = base_query_params.copy()
                query_params_for_skill['skill'] = token
                required_skill_filters.append({
                    'raw': token,
                    'label': skill_label_map.get(token) or _skill_display_label(token),
                    'count': count,
                    'querystring': query_params_for_skill.urlencode(),
                })

            required_skill_filters = sorted(
                required_skill_filters,
                key=lambda item: (-item.get('count', 0), (item.get('label') or '').lower()),
            )[:12]

            all_jobs_querystring = base_query_params.copy()
            all_jobs_querystring.pop('skill', None)

            if active_skill_filter != 'all':
                filtered_jobs = [job for job in all_jobs if _job_matches_skill_filter(job, active_skill_filter)]
            else:
                filtered_jobs = list(all_jobs)

            total_jobs_count = len(filtered_jobs)
            dashboard_jobs = filtered_jobs[:5]

            for job in dashboard_jobs:
                job.match_score = _calculate_student_job_match_score(student, job)

            recent_unread_messages = Message.objects.filter(recipient=request.user, is_read=False).select_related('sender')[:5]
            recent_unread_notifications = Notification.objects.filter(user=request.user, is_read=False)[:5]

            application_qs = JobApplication.objects.filter(student_portfolio=portfolio).select_related('job_listing')
            saved_job_ids = set(SavedJob.objects.filter(student_portfolio=portfolio).values_list('job_listing_id', flat=True))
            applied_job_ids = set(application_qs.values_list('job_listing_id', flat=True))
            application_status_map = {item.job_listing.pk: item.status for item in application_qs}

            interviews_count = Interview.objects.filter(
                student_portfolio=portfolio,
                scheduled_date__gte=timezone.now().date(),
            ).count()

            offers_count = application_qs.filter(status__in=[JobApplication.STATUS_OFFER, JobApplication.STATUS_ACCEPTED]).count()

            context = {
                'fields': fields,
                'jobs': dashboard_jobs,
                'total_jobs_count': total_jobs_count,
                'user_type': 'student',
                'recent_unread_messages': recent_unread_messages,
                'recent_unread_notifications': recent_unread_notifications,
                'applications_count': application_qs.count(),
                'interviews_count': interviews_count,
                'offers_count': offers_count,
                'saved_job_ids': saved_job_ids,
                'applied_job_ids': applied_job_ids,
                'application_status_map': application_status_map,
                'active_search_query': search_query,
                'active_skill_filter': active_skill_filter,
                'required_skill_filters': required_skill_filters,
                'all_jobs_querystring': all_jobs_querystring.urlencode(),
            }
            return render(request, 'student_dashboard/dashboard.html', context)
        except AttributeError:
            messages.warning(request, 'Please complete your portfolio setup.')
            return redirect('users-portfolio')
    
    # Faculty dashboard.
    elif hasattr(request.user, 'faculty'):
        try:
            faculty_profile = get_user_faculty_profile(request.user)
            jobs = list(JobListing.objects.filter(profile=faculty_profile).order_by('-posted_date', '-id'))
            candidate_cards, required_skill_filters = _get_cached_faculty_candidate_matches(faculty_profile, jobs)
            total_candidates_count = len(candidate_cards)
            dashboard_candidates = candidate_cards[:5]
            strong_matches = sum(1 for item in candidate_cards if item['match_score'] >= 60)

            token_match_counts = {}
            token_label_map = {}
            for candidate in candidate_cards:
                labels = candidate.get('student_skill_labels', [])
                for index, token in enumerate(candidate.get('student_skill_tokens', [])):
                    token = (token or '').strip().lower()
                    if not token:
                        continue
                    token_match_counts[token] = token_match_counts.get(token, 0) + 1
                    if token not in token_label_map:
                        token_label_map[token] = labels[index] if index < len(labels) else _format_skill_label(token)

            dashboard_skill_filters = []
            for item in (required_skill_filters or []):
                token = (item.get('raw') or '').strip().lower()
                if not token:
                    continue
                count = token_match_counts.get(token, 0)
                if count <= 0:
                    continue
                dashboard_skill_filters.append({
                    'raw': token,
                    'label': item.get('label') or token_label_map.get(token) or _format_skill_label(token),
                    'count': count,
                    'querystring': urlencode({'skill': token}),
                })

            if not dashboard_skill_filters:
                for token, count in token_match_counts.items():
                    dashboard_skill_filters.append({
                        'raw': token,
                        'label': token_label_map.get(token) or _format_skill_label(token),
                        'count': count,
                        'querystring': urlencode({'skill': token}),
                    })

            dashboard_skill_filters = sorted(
                dashboard_skill_filters,
                key=lambda entry: (-entry.get('count', 0), (entry.get('label') or '').lower()),
            )[:10]

            application_filter = Q()
            interview_filter = Q()
            for job in jobs:
                application_filter |= Q(related_url__icontains=f'/dashboard/job/{job.pk}/')
                interview_filter |= Q(related_url__icontains=f'/dashboard/job/{job.pk}/')

            if jobs:
                applications_received = Notification.objects.filter(
                    Q(user=request.user),
                    Q(kind=Notification.KIND_APPLICATION),
                    application_filter,
                ).count()
                interviews_scheduled = Notification.objects.filter(
                    Q(user=request.user),
                    Q(kind=Notification.KIND_INTERVIEW),
                    interview_filter,
                ).count()
            else:
                applications_received = 0
                interviews_scheduled = 0

            saved_student_ids = set(
                SavedStudent.objects.filter(
                    faculty_profile=faculty_profile
                ).values_list('student_portfolio__student_id', flat=True)
            )

            context = {
                'jobs': jobs,
                'invite_jobs': jobs,
                'saved_student_ids': saved_student_ids,
                'candidates': dashboard_candidates,
                'total_candidates_count': total_candidates_count,
                'applications_received': applications_received,
                'interviews_scheduled': interviews_scheduled,
                'strong_matches': strong_matches,
                'required_skill_filters': dashboard_skill_filters,
                'all_students_querystring': '',
            }
            return render(request, 'faculty_dashboard/dashboard.html', context)
        except AttributeError:
            messages.warning(request, 'Please complete your profile setup.')
            return redirect('faculty-profile')
    
    # Unknown account type.
    else:
        messages.error(request, 'Account type not recognized. Please contact support.')
        return redirect('login')



@login_required
def add_field_of_expertise(request):
    if request.method == 'POST':
        form = forms.FieldOfExpertiseForm(request.POST, student=get_user_student(request.user))
        if form.is_valid():
            field = form.save(commit=False)
            # Include portfolio link.
            field.portfolio = get_user_portfolio(request.user)
            field.save()
            return redirect('users-portfolio')  
    else:
        form = forms.FieldOfExpertiseForm(student=get_user_student(request.user))
    return render(request, 'student_dashboard/add_field_of_expertise.html', {'form': form})

@login_required
def see_field_of_expertise(request):
    portfolio = get_user_portfolio(request.user)
    if portfolio is None:
        messages.warning(request, 'Please complete your portfolio setup.')
        return redirect('users-portfolio')

    fields = portfolio.fields_of_expertise.all()
    return render(request, 'student_dashboard/field_of_expertise.html', {'fields': fields})




@login_required
def add_project(request, field_id):
    field_of_expertise = get_object_or_404(
        FieldOfExpertise,
        id=field_id,
        portfolio=get_user_portfolio(request.user)
    )

    if request.method == 'POST':
        form = forms.ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.field_of_expertise = field_of_expertise
            project.save()

            uploaded_media = request.FILES.getlist('project_media')
            errors = []
            upload_count = 0

            image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
            video_exts = {'.mp4', '.avi', '.mov', '.wmv'}
            doc_exts = {'.pdf', '.doc', '.docx', '.txt', '.zip', '.xlsx'}
            max_bytes = 1000 * 1024 * 1024

            for media in uploaded_media:
                ext = Path(media.name).suffix.lower()

                if media.size > max_bytes:
                    errors.append(f"{media.name}: exceeds 1000MB limit")
                    continue

                if ext in image_exts:
                    Picture.objects.create(project=project, image=media)
                    upload_count += 1
                elif ext in video_exts:
                    Video.objects.create(project=project, video=media)
                    upload_count += 1
                elif ext in doc_exts:
                    Files.objects.create(project=project, file=media)
                    upload_count += 1
                else:
                    errors.append(f"{media.name}: unsupported file type")

            if errors:
                messages.warning(request, 'Project created. Some files were skipped: ' + '; '.join(errors))
            elif upload_count:
                messages.success(request, f'Project added with {upload_count} media file(s)!')
            else:
                messages.success(request, 'Project added successfully!')

            return redirect('see-field-projects', field_id=project.field_of_expertise.pk)
    else:
        form = forms.ProjectForm()

    context = {
        'form': form,
        'field_of_expertise': field_of_expertise,
    }
    return render(request, 'student_dashboard/add_projects.html', context)



@login_required
def see_field_projects(request, field_id):
    # Load the selected field.
    field_of_expertise = get_object_or_404(
        FieldOfExpertise,
        id=field_id,
        portfolio=get_user_portfolio(request.user)
    )

    confidence_choices = forms.CONFIDENCE_SCALE_CHOICES

    if request.method == 'POST' and ('update_confidence_submit' in request.POST or 'auto_confidence_update' in request.POST):
        is_auto_save = 'auto_confidence_update' in request.POST
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        selected_confidence = (request.POST.get('level_of_confidence') or '').strip()
        allowed_values = {value for value, _label in confidence_choices}

        if selected_confidence in allowed_values:
            field_of_expertise.level_of_confidence = selected_confidence
            field_of_expertise.save(update_fields=['level_of_confidence'])

            if is_ajax:
                return JsonResponse({'ok': True, 'level_of_confidence': selected_confidence})

            if not is_auto_save:
                messages.success(request, 'Confidence level updated successfully.')
        else:
            if is_ajax:
                return JsonResponse({'ok': False, 'error': 'Invalid confidence level.'}, status=400)

            if not is_auto_save:
                messages.error(request, 'Please choose a valid confidence level.')

        return redirect('see-field-projects', field_id=field_of_expertise.pk)

    # Load projects for this field.
    projects = Project.objects.filter(field_of_expertise=field_of_expertise)

    # Aggregate all project skills for a single skills-only pill cloud.
    aggregated_skills = "\n".join(
        skill_text.strip()
        for skill_text in (project.skills_demonstrated or "" for project in projects)
        if skill_text and skill_text.strip() and skill_text.strip().lower() != "skills demonstrated"
    )


    context = {
        'projects': projects,
        'field_of_expertise': field_of_expertise,
        'confidence_choices': confidence_choices,
        'aggregated_skills': aggregated_skills,
    }
    return render(request, 'student_dashboard/field_of_expertise.html', context)



@login_required
def see_project_files(request, project_id):
    # Load the selected project.
    project = get_object_or_404(Project, id=project_id, field_of_expertise__portfolio=get_user_portfolio(request.user))
    is_async_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def post_response(success, message, status=200, non_ajax_level='error', payload=None):
        if is_async_request:
            response_payload = {
                'ok': success,
                'message': message,
                'project_skill_items': parse_text_entries(project.skills_demonstrated),
                'project_tech_items': parse_text_entries(project.tech_n_tools_used),
            }
            if payload:
                response_payload.update(payload)
            return JsonResponse(response_payload, status=status)

        if success:
            messages.success(request, message)
        else:
            level = getattr(messages, non_ajax_level, messages.error)
            level(request, message)
        return redirect('see-project-files', project_id=project.pk)

    if request.method == 'POST' and 'project_text_save' in request.POST:
        editable_field = request.POST.get('project_text_field', '').strip()
        editable_value = request.POST.get('project_text_value', '').strip()
        allowed_fields = {'project_summary', 'what_i_learnd'}

        if editable_field not in allowed_fields:
            return post_response(False, 'Invalid project text field.', status=400)

        if not editable_value:
            return post_response(False, 'Project details cannot be empty.', status=400)

        setattr(project, editable_field, editable_value)
        project.save(update_fields=[editable_field])
        return post_response(True, 'Project details saved.', payload={'updated_field': editable_field, 'updated_value': editable_value})

    if request.method == 'POST' and 'project_skill_remove' in request.POST:
        remove_entry = request.POST.get('project_skill_remove', '').strip()
        current_entries = parse_text_entries(project.skills_demonstrated)
        updated_entries = [entry for entry in current_entries if entry != remove_entry]

        if len(updated_entries) != len(current_entries):
            save_project_skill_entries(project, updated_entries)
            return post_response(True, 'Skill removed successfully.')

        return post_response(False, 'Skill was not found.', status=404, non_ajax_level='info')

    if request.method == 'POST' and 'project_skill_submit' in request.POST:
        skill_entry = request.POST.get('project_skill_entry', '').strip()

        if not skill_entry:
            return post_response(False, 'Please enter a skill before submitting.', status=400)

        if len(skill_entry) > 80:
            return post_response(False, 'Skills must be 80 characters or fewer.', status=400)

        current_entries = parse_text_entries(project.skills_demonstrated)
        if skill_entry not in current_entries:
            current_entries.append(skill_entry)
            save_project_skill_entries(project, current_entries)
            return post_response(True, 'Skill added successfully.')

        return post_response(False, 'That skill already exists.', status=409, non_ajax_level='info')

    if request.method == 'POST' and 'project_tech_remove' in request.POST:
        remove_entry = request.POST.get('project_tech_remove', '').strip()
        current_entries = parse_text_entries(project.tech_n_tools_used)
        updated_entries = [entry for entry in current_entries if entry != remove_entry]

        if len(updated_entries) != len(current_entries):
            save_project_tech_entries(project, updated_entries)
            return post_response(True, 'Technology removed successfully.')

        return post_response(False, 'Technology was not found.', status=404, non_ajax_level='info')

    if request.method == 'POST' and 'project_tech_submit' in request.POST:
        tech_entry = request.POST.get('project_tech_entry', '').strip()

        if not tech_entry:
            return post_response(False, 'Please enter a technology before submitting.', status=400)

        if len(tech_entry) > 80:
            return post_response(False, 'Technology entries must be 80 characters or fewer.', status=400)

        current_entries = parse_text_entries(project.tech_n_tools_used)
        if tech_entry not in current_entries:
            current_entries.append(tech_entry)
            save_project_tech_entries(project, current_entries)
            return post_response(True, 'Technology added successfully.')

        return post_response(False, 'That technology already exists.', status=409, non_ajax_level='info')

    project_files = list(Files.objects.filter(project=project))

    # Load previews and provide a dedicated preview URL.
    for project_file in project_files:
        preview_text = None
        preview_url = None
        word_preview_available = False

        if project_file.is_text and project_file.file:
            try:
                with project_file.file.open("rb") as file_handle:
                    raw_content = file_handle.read(40 * 1024)
                preview_text = raw_content.decode("utf-8", errors="replace")
                if len(raw_content) == 40 * 1024:
                    preview_text += "\n\n[Preview truncated]"
            except OSError:
                preview_text = "Preview unavailable for this text file."

        if project_file.is_pdf:
            preview_url = reverse("preview-media-file", args=[project_file.pk])

        if project_file.is_word and project_file.file:
            try:
                word_pdf_path = Path(project_file.file.path).with_suffix(".pdf")
                word_preview_available = word_pdf_path.exists() or try_generate_word_preview_pdf(project_file)
                if word_preview_available:
                    preview_url = reverse("preview-media-file", args=[project_file.pk])
            except OSError:
                word_preview_available = False

        setattr(project_file, 'preview_text', preview_text)
        setattr(project_file, 'preview_url', preview_url)
        setattr(project_file, 'word_preview_available', word_preview_available)

    context = {
        "project": project,
        "pictures": Picture.objects.filter(project=project),
        "videos": Video.objects.filter(project=project),
        "files": project_files,
        "project_skill_items": parse_text_entries(project.skills_demonstrated),
        "project_tech_items": parse_text_entries(project.tech_n_tools_used),
        "sibling_projects": Project.objects.filter(field_of_expertise=project.field_of_expertise).exclude(pk=project.pk)[:2],
    }
    return render(request, "student_dashboard/project.html", context)


@login_required
@student_required
@xframe_options_sameorigin
def preview_media_file(request, file_id):
    """Serve previewable files with SAMEORIGIN frame policy."""
    portfolio = get_user_portfolio(request.user)
    file_record = get_object_or_404(
        Files,
        id=file_id,
        project__field_of_expertise__portfolio=portfolio,
    )

    if not file_record.file:
        raise Http404("No file available for preview.")

    source_path = Path(file_record.file.path)
    preview_path = source_path

    if file_record.is_word:
        preview_path = source_path.with_suffix(".pdf")
        if not preview_path.exists() and not try_generate_word_preview_pdf(file_record):
            raise Http404("Word preview is unavailable for this file.")
    elif not file_record.is_pdf:
        raise Http404("Preview is only available for PDF and converted Word files.")

    if not preview_path.exists():
        raise Http404("Preview file not found.")

    response = FileResponse(open(preview_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = f"inline; filename=\"{preview_path.name}\""
    return response


@student_required
def upload_project_media(request, project_id):
    """Upload multiple media files for a project"""
    project = get_user_project(request.user, project_id)
    
    if request.method == 'POST':
        form = forms.MediaUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    upload_count = 0
                    
                    # Save uploaded images.
                    images = request.FILES.getlist('images')
                    for image in images:
                        Picture.objects.create(project=project, image=image)
                        upload_count += 1
                    
                    # Save uploaded videos.
                    videos = request.FILES.getlist('videos')
                    for video in videos:
                        Video.objects.create(project=project, video=video)
                        upload_count += 1
                    
                    # Save uploaded files.
                    files = request.FILES.getlist('documents')
                    word_preview_unavailable = False
                    for file in files:
                        created_file = Files.objects.create(project=project, file=file)
                        upload_count += 1

                        if created_file.is_word:
                            converted = try_generate_word_preview_pdf(created_file)
                            if not converted:
                                word_preview_unavailable = True

                    if word_preview_unavailable:
                        messages.info(request, 'Word files uploaded. Install LibreOffice (soffice) on the server to enable inline Word previews.')
                    
                    if upload_count > 0:
                        messages.success(request, f'{upload_count} file(s) uploaded successfully!')
                    else:
                        messages.warning(request, 'No files were selected for upload.')
                        
                    return redirect('see-project-files', project_id=project.pk)
                    
            except Exception as e:
                messages.error(request, 'An error occurred while uploading files. Please try again.')
        else:
            messages.error(request, 'Please check your file selections and try again.')
    else:
        form = forms.MediaUploadForm()
    
    context = {
        'form': form,
        'project': project,
    }
    return render(request, 'student_dashboard/upload_media.html', context)

@student_required
def delete_media_file(request, file_type, file_id):
    """Delete a media file"""
    portfolio = get_user_portfolio(request.user)
    
    try:
        if file_type == 'image':
            media_file = get_object_or_404(
                Picture, 
                id=file_id, 
                project__field_of_expertise__portfolio=portfolio
            )
        elif file_type == 'video':
            media_file = get_object_or_404(
                Video, 
                id=file_id, 
                project__field_of_expertise__portfolio=portfolio
            )
        elif file_type == 'file':
            media_file = get_object_or_404(
                Files, 
                id=file_id, 
                project__field_of_expertise__portfolio=portfolio
            )
        else:
            messages.error(request, 'Invalid file type.')
            return redirect('dashboard-home')
        
        project_id = media_file.project.pk
        media_file.delete()
        messages.success(request, 'File deleted successfully!')
        return redirect('see-project-files', project_id=project_id)
        
    except Exception as e:
        messages.error(request, 'An error occurred while deleting the file.')
        return redirect('dashboard-home')


@login_required
@faculty_required
def create_job_listing(request):
    if request.method == 'POST':
        form = forms.JobListingForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            # Include portfolio link.
            field.profile = get_user_faculty_profile(request.user)
            field.save()

            student_ids = list(Student.objects.values_list('pk', flat=True))
            if student_ids:
                Notification.objects.bulk_create([
                    Notification(
                        user_id=student_id,
                        kind=Notification.KIND_JOB_POSTED,
                        title='New job listing posted',
                        body=f'{field.job_title} in {field.location}',
                        related_url=f'/dashboard/job/{field.id}/',
                    )
                    for student_id in student_ids
                ])

            messages.success(request, 'Job listing created successfully!')
            return redirect('faculty-profile')
    else:
        form = forms.JobListingForm()
    return render(request, 'faculty_dashboard/create_job_listing.html', {'form': form})

@login_required
@faculty_required
def see_job_listings(request):
    """Show the current faculty user's job listings."""
    try:
        profile = get_user_faculty_profile(request.user)
        jobs = JobListing.objects.filter(profile=profile).order_by('-posted_date', '-id')
        
        # Debug output.
        print(f"User: {request.user}")
        print(f"Profile: {profile}")
        print(f"Number of jobs found: {jobs.count()}")
        print(f"Jobs: {list(jobs)}")
        
    except AttributeError as e:
        print(f"Error accessing faculty profile: {e}")
        jobs = []
    
    context = {
        'jobs': jobs,
    }
    return render(request, 'faculty/profile.html', context)

@login_required
@faculty_required
def faculty_student_field_projects(request, student_id, field_id):
    student = get_object_or_404(Student, id=student_id)
    portfolio = get_object_or_404(Portfolio, student=student)

    field_of_expertise = get_object_or_404(
        FieldOfExpertise.objects.prefetch_related('projects'),
        id=field_id,
        portfolio=portfolio,
    )

    projects = list(Project.objects.filter(field_of_expertise=field_of_expertise))
    for project in projects:
        setattr(project, 'view_url', reverse('faculty-student-project-files', kwargs={'student_id': student.pk, 'project_id': project.pk}))

    aggregated_skills = "\n".join(
        skill_text.strip()
        for skill_text in (project.skills_demonstrated or "" for project in projects)
        if skill_text and skill_text.strip() and skill_text.strip().lower() != "skills demonstrated"
    )

    context = {
        'projects': projects,
        'field_of_expertise': field_of_expertise,
        'aggregated_skills': aggregated_skills,
        'portfolio_owner': student,
        'back_to_portfolio_url': reverse('faculty-view-student-portfolio', kwargs={'student_id': student.pk}),
    }
    return render(request, 'faculty_dashboard/student_field_projects_view.html', context)


@login_required
@faculty_required
def faculty_student_project_files(request, student_id, project_id):
    student = get_object_or_404(Student, id=student_id)
    portfolio = get_object_or_404(Portfolio, student=student)

    project = get_object_or_404(
        Project.objects.select_related('field_of_expertise__portfolio__student'),
        id=project_id,
        field_of_expertise__portfolio=portfolio,
    )

    sibling_projects = list(Project.objects.filter(field_of_expertise=project.field_of_expertise).exclude(pk=project.pk)[:2])
    for sibling in sibling_projects:
        setattr(sibling, 'view_url', reverse('faculty-student-project-files', kwargs={'student_id': student.pk, 'project_id': sibling.pk}))

    context = {
        'project': project,
        'pictures': Picture.objects.filter(project=project),
        'videos': Video.objects.filter(project=project),
        'files': Files.objects.filter(project=project),
        'project_skill_items': parse_text_entries(project.skills_demonstrated),
        'project_tech_items': parse_text_entries(project.tech_n_tools_used),
        'sibling_projects': sibling_projects,
        'portfolio_owner': student,
        'field_back_url': reverse('faculty-student-field-projects', kwargs={'student_id': student.pk, 'field_id': project.field_of_expertise.pk}),
    }
    return render(request, 'faculty_dashboard/student_project_view.html', context)


@login_required
@student_required
def job_detail(request, job_id):
    """Show a job listing detail page."""
    job = get_object_or_404(JobListing.objects.select_related('profile__faculty'), id=job_id)
    portfolio = get_user_portfolio(request.user)

    saved_job = SavedJob.objects.filter(student_portfolio=portfolio, job_listing=job).exists()
    application = JobApplication.objects.filter(student_portfolio=portfolio, job_listing=job).first()
    match_score = _calculate_student_job_match_score(get_user_student(request.user), job)

    context = {
        'job': job,
        'user_type': 'student',
        'is_saved': saved_job,
        'application': application,
        'match_score': match_score,
        'required_skills_items': parse_text_entries(job.required_skills_and_tools),
        'confidence_items': parse_text_entries(job.level_of_confidence),
    }
    return render(request, 'student_dashboard/job_detail.html', context)


@login_required
@student_required
def student_applications_page(request):
    portfolio = get_user_portfolio(request.user)
    status_filter = (request.GET.get('status') or 'all').strip().lower()

    applications = JobApplication.objects.filter(student_portfolio=portfolio).select_related('job_listing__profile__faculty').order_by('-updated_at')

    allowed_filters = {
        'all': None,
        JobApplication.STATUS_PENDING: JobApplication.STATUS_PENDING,
        JobApplication.STATUS_UNDER_REVIEW: JobApplication.STATUS_UNDER_REVIEW,
        JobApplication.STATUS_INTERVIEW: JobApplication.STATUS_INTERVIEW,
        JobApplication.STATUS_OFFER: JobApplication.STATUS_OFFER,
        JobApplication.STATUS_ACCEPTED: JobApplication.STATUS_ACCEPTED,
        JobApplication.STATUS_NOT_SELECTED: JobApplication.STATUS_NOT_SELECTED,
    }

    if status_filter in allowed_filters and allowed_filters[status_filter]:
        if status_filter == JobApplication.STATUS_OFFER:
            applications = applications.filter(status__in=[JobApplication.STATUS_OFFER, JobApplication.STATUS_ACCEPTED])
        else:
            applications = applications.filter(status=allowed_filters[status_filter])
    elif status_filter not in allowed_filters:
        status_filter = 'all'

    all_apps = JobApplication.objects.filter(student_portfolio=portfolio)
    stats = {
        'total': all_apps.count(),
        'pending': all_apps.filter(status=JobApplication.STATUS_PENDING).count(),
        'under_review': all_apps.filter(status=JobApplication.STATUS_UNDER_REVIEW).count(),
        'interview': all_apps.filter(status=JobApplication.STATUS_INTERVIEW).count(),
        'offer': all_apps.filter(status__in=[JobApplication.STATUS_OFFER, JobApplication.STATUS_ACCEPTED]).count(),
    }

    context = {
        'applications': applications,
        'stats': stats,
        'active_filter': status_filter,
    }
    return render(request, 'student_dashboard/applications.html', context)


@login_required
@student_required
def student_saved_jobs_page(request):
    portfolio = get_user_portfolio(request.user)

    saved_jobs = (
        SavedJob.objects
        .filter(student_portfolio=portfolio)
        .select_related('job_listing__profile__faculty')
        .order_by('-saved_at')
    )

    saved_cards = []
    for saved in saved_jobs:
        job = saved.job_listing
        saved_cards.append({
            'saved': saved,
            'job': job,
            'match_score': _calculate_student_job_match_score(get_user_student(request.user), job),
            'skill_tags': parse_text_entries(job.required_skills_and_tools)[:4],
        })

    context = {
        'saved_cards': saved_cards,
        'saved_count': len(saved_cards),
    }
    return render(request, 'student_dashboard/saved_jobs.html', context)


@login_required
@student_required
def student_job_search_page(request):
    portfolio = get_user_portfolio(request.user)
    student = get_user_student(request.user)
    student_course = (getattr(student, 'current_course', '') or '').strip()

    jobs = JobListing.objects.all().select_related('profile__faculty').order_by('-posted_date', '-id')

    search_query = (request.GET.get('q') or '').strip()
    active_skill_filter = (request.GET.get('skill') or 'all').strip().lower()
    active_field_filter = (request.GET.get('field') or 'all').strip().lower()

    jobs, _ = _filter_student_jobs(jobs, search_query, 'all')

    field_filters, field_token_map = _load_field_of_expertise_filters(student_course)

    if field_token_map:
        course_field_tokens = {token for token in field_token_map.keys() if token}

        student_course_keywords = set(_extract_course_keywords(student_course))

        scoped_jobs = []
        for job in list(jobs):
            required_tokens = set(_collect_job_required_skill_tokens(job))
            faculty_course_text = (
                getattr(getattr(getattr(job, 'profile', None), 'faculty', None), 'professor_of', '')
                or ''
            )
            faculty_course_token = _normalize_skill_token(faculty_course_text)
            faculty_course_keywords = set(_extract_course_keywords(faculty_course_text))

            matches_course_fields = bool(required_tokens.intersection(course_field_tokens))
            matches_faculty_course_field = bool(
                faculty_course_token
                and any(
                    len(token) > 4 and token in faculty_course_token
                    for token in course_field_tokens
                )
            )
            matches_same_course = bool(student_course_keywords.intersection(faculty_course_keywords))

            if matches_course_fields or matches_faculty_course_field or matches_same_course:
                scoped_jobs.append(job)

        jobs = scoped_jobs
    elif student_course:
        jobs, _ = _filter_jobs_by_course_scope(jobs, student_course, 'my_course')
    else:
        jobs = []

    if active_field_filter != 'all':
        field_token_set = field_token_map.get(active_field_filter)
        if field_token_set:
            jobs = [
                job for job in list(jobs)
                if _job_matches_field_filter(job, field_token_set, active_field_filter)
            ]
        else:
            jobs = []

    scoped_jobs = list(jobs)

    base_query_params = request.GET.copy()
    base_query_params.pop('page', None)

    skill_match_counts = {}
    skill_label_map = {}
    for job in scoped_jobs:
        tokens = _collect_job_required_skill_tokens(job)
        labels = [_skill_display_label(token) for token in tokens]
        for index, token in enumerate(tokens):
            if not token:
                continue
            skill_match_counts[token] = skill_match_counts.get(token, 0) + 1
            if token not in skill_label_map:
                skill_label_map[token] = labels[index] if index < len(labels) else _skill_display_label(token)

    required_skill_filters = []
    for token, count in skill_match_counts.items():
        query_params_for_skill = base_query_params.copy()
        query_params_for_skill['skill'] = token
        required_skill_filters.append({
            'raw': token,
            'label': skill_label_map.get(token) or _skill_display_label(token),
            'count': count,
            'querystring': query_params_for_skill.urlencode(),
        })

    required_skill_filters = sorted(
        required_skill_filters,
        key=lambda item: (-item.get('count', 0), (item.get('label') or '').lower()),
    )[:12]

    all_jobs_querystring = base_query_params.copy()
    all_jobs_querystring.pop('skill', None)

    if active_skill_filter != 'all':
        jobs = [job for job in scoped_jobs if _job_matches_skill_filter(job, active_skill_filter)]
    else:
        jobs = scoped_jobs

    paginator = Paginator(jobs, 12)
    jobs_page = paginator.get_page(request.GET.get('page'))

    for job in jobs_page.object_list:
        job.match_score = _calculate_student_job_match_score(student, job)

    application_qs = JobApplication.objects.filter(student_portfolio=portfolio).select_related('job_listing')
    saved_job_ids = set(SavedJob.objects.filter(student_portfolio=portfolio).values_list('job_listing_id', flat=True))
    applied_job_ids = set(application_qs.values_list('job_listing_id', flat=True))

    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'jobs': jobs_page.object_list,
        'jobs_page': jobs_page,
        'pagination_query': query_params.urlencode(),
        'saved_job_ids': saved_job_ids,
        'applied_job_ids': applied_job_ids,
        'active_search_query': search_query,
        'active_skill_filter': active_skill_filter,
        'active_field_filter': active_field_filter,
        'required_skill_filters': required_skill_filters,
        'all_jobs_querystring': all_jobs_querystring.urlencode(),
        'field_filters': field_filters,
        'student_course': student_course,
    }
    return render(request, 'student_dashboard/job_search.html', context)


@login_required
@student_required
def student_interviews_page(request):
    portfolio = get_user_portfolio(request.user)
    upcoming_interviews = Interview.objects.filter(
        student_portfolio=portfolio,
        scheduled_date__gte=timezone.now().date(),
    ).select_related('job_listing__profile__faculty').order_by('scheduled_date', 'scheduled_time')

    context = {
        'upcoming_interviews': upcoming_interviews,
    }
    return render(request, 'student_dashboard/interviews.html', context)


@login_required
@student_required
@require_POST
def apply_to_job(request, job_id):
    job = get_object_or_404(JobListing.objects.select_related('profile__faculty'), id=job_id)
    portfolio = get_user_portfolio(request.user)

    application, created = JobApplication.objects.get_or_create(
        student_portfolio=portfolio,
        job_listing=job,
        defaults={'status': JobApplication.STATUS_PENDING},
    )

    if created:
        Notification.objects.create(
            user=job.profile.faculty,
            kind=Notification.KIND_APPLICATION,
            title='New application received',
            body=f"{request.user.get_full_name() or request.user.username} applied for {job.job_title}.",
            related_url=reverse('faculty-job-detail', kwargs={'job_id': job.pk}),
        )

        Notification.objects.create(
            user=request.user,
            kind=Notification.KIND_APPLICATION,
            title='Application submitted',
            body=f"You successfully applied for {job.job_title}.",
            related_url=reverse('student-applications'),
        )

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if is_ajax:
        return JsonResponse({
            'success': True,
            'applied': True,
            'created': created,
            'status': application.status,
            'message': 'Application submitted successfully.' if created else 'You already applied to this job.',
        })

    if created:
        messages.success(request, 'Application submitted successfully.')
    else:
        messages.info(request, 'You already applied to this job.')

    return redirect('job-detail', job_id=job.pk)


@login_required
@student_required
@require_POST
def accept_application_offer(request, application_id):
    application = get_object_or_404(
        JobApplication.objects.select_related('job_listing__profile__faculty', 'student_portfolio__student'),
        id=application_id,
        student_portfolio=get_user_portfolio(request.user),
    )

    if application.status not in {JobApplication.STATUS_OFFER, JobApplication.STATUS_ACCEPTED}:
        messages.error(request, 'This offer is no longer available to accept.')
        return redirect('student-applications')

    if application.status != JobApplication.STATUS_ACCEPTED:
        application.status = JobApplication.STATUS_ACCEPTED
        application.save(update_fields=['status', 'updated_at'])

        Notification.objects.create(
            user=application.job_listing.profile.faculty,
            kind=Notification.KIND_APPLICATION_STATUS,
            title='Offer accepted',
            body=f"{request.user.get_full_name() or request.user.username} accepted the offer for {application.job_listing.job_title}.",
            related_url=reverse('applicant-tracking'),
        )

        messages.success(request, 'Offer accepted successfully.')
    else:
        messages.info(request, 'You have already accepted this offer.')

    return redirect('student-applications')


@login_required
@student_required
@require_POST
def toggle_save_job(request, job_id):
    job = get_object_or_404(JobListing, id=job_id)
    portfolio = get_user_portfolio(request.user)

    saved, created = SavedJob.objects.get_or_create(student_portfolio=portfolio, job_listing=job)

    if created:
        payload = {'success': True, 'saved': True, 'message': 'Job saved for later.'}
    else:
        saved.delete()
        payload = {'success': True, 'saved': False, 'message': 'Job removed from saved.'}

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if is_ajax:
        return JsonResponse(payload)

    if payload['saved']:
        messages.success(request, payload['message'])
    else:
        messages.info(request, payload['message'])

    return redirect('job-detail', job_id=job.pk)


@login_required
@faculty_required
def edit_job_listing(request, job_id):
    job = get_object_or_404(JobListing, id=job_id, profile=get_user_faculty_profile(request.user))

    if request.method == 'POST':
        form = forms.JobListingForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job listing updated successfully!')
            return redirect('faculty-profile')
    else:
        form = forms.JobListingForm(instance=job)

    return render(request, 'faculty_dashboard/edit_job_listing.html', {'form': form, 'job': job})


@login_required
@faculty_required
def delete_job_listing(request, job_id):
    job = get_object_or_404(JobListing, id=job_id, profile=get_user_faculty_profile(request.user))

    if request.method == 'POST':
        job_title = job.job_title
        job.delete()
        messages.success(request, f'Job listing "{job_title}" deleted successfully!')

    return redirect('faculty-profile')


@login_required
@faculty_required
def faculty_job_detail(request, job_id):
    """Faculty-facing detail page for a listing they own."""
    job = get_object_or_404(JobListing, id=job_id, profile=get_user_faculty_profile(request.user))

    if request.method == 'POST' and 'job_about_submit' in request.POST:
        about_text = (request.POST.get('job_about_text') or '').strip()
        if len(about_text.split()) > 500:
            messages.error(request, 'About this role cannot exceed 500 words.')
            return redirect('faculty-job-detail', job_id=job.pk)

        job.description = about_text
        job.save(update_fields=['description'])
        messages.success(request, 'About this role updated successfully.')
        scroll_pos = (request.POST.get('scroll_position') or '').strip()
        _scroll_suffix = ('?scroll=' + scroll_pos) if scroll_pos.isdigit() else ''
        return redirect(reverse('faculty-job-detail', kwargs={'job_id': job.pk}) + _scroll_suffix)

    if request.method == 'POST' and 'job_required_skills_submit' in request.POST:
        entries = parse_text_entries(request.POST.get('required_skills_entries') or '')
        job.required_skills_and_tools = '\n'.join(entries)
        job.save(update_fields=['required_skills_and_tools'])
        messages.success(request, 'Required skills updated successfully.')
        scroll_pos = (request.POST.get('scroll_position') or '').strip()
        _scroll_suffix = ('?scroll=' + scroll_pos) if scroll_pos.isdigit() else ''
        return redirect(reverse('faculty-job-detail', kwargs={'job_id': job.pk}) + _scroll_suffix)

    if request.method == 'POST' and 'job_requirements_submit' in request.POST:
        entries = parse_text_entries(request.POST.get('requirements_entries') or '')
        job.level_of_confidence = '\n'.join(entries)
        job.save(update_fields=['level_of_confidence'])
        messages.success(request, 'Requirements and qualifications updated successfully.')
        scroll_pos = (request.POST.get('scroll_position') or '').strip()
        _scroll_suffix = ('?scroll=' + scroll_pos) if scroll_pos.isdigit() else ''
        return redirect(reverse('faculty-job-detail', kwargs={'job_id': job.pk}) + _scroll_suffix)

    application_count = Notification.objects.filter(
        user=request.user,
        kind=Notification.KIND_APPLICATION,
        related_url__icontains=f'/dashboard/job/{job.pk}/'
    ).count()

    context = {
        'job': job,
        'application_count': application_count,
    }
    return render(request, 'faculty_dashboard/job_detail.html', context)


@login_required
@student_required
@require_POST
def delete_field_of_expertise(request, field_id):
    portfolio = get_user_portfolio(request.user)
    if portfolio is None:
        messages.warning(request, 'Please complete your portfolio setup.')
        return redirect('users-portfolio')

    field = get_object_or_404(FieldOfExpertise, id=field_id, portfolio=portfolio)
    field_name = (field.field_of_expertise or 'field').strip()
    field.delete()

    messages.success(request, f'Removed {field_name} from your portfolio.')
    return redirect('users-portfolio')


@login_required
@student_required
@require_POST
def delete_project(request, project_id):
    project = get_object_or_404(
        Project,
        id=project_id,
        field_of_expertise__portfolio=get_user_portfolio(request.user),
    )

    field_id = project.field_of_expertise_id
    project_title = (project.project_title or 'project').strip()
    project.delete()

    messages.success(request, f'Removed {project_title} from your portfolio.')
    return redirect('see-field-projects', field_id=field_id)


@login_required
def toggle_field_featured(request):
    """Toggle featured status for a field."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed"})
    
    try:
        data = json.loads(request.body)
        field_id = data.get("field_id")
        is_featured = data.get("is_featured")
        
        field = FieldOfExpertise.objects.get(id=field_id)
        
        # Ensure the field belongs to the current user.
        if field.portfolio.student.pk != request.user.pk:
            return JsonResponse({"success": False, "error": "Unauthorized"}, status=403)
        
        field.is_featured = is_featured
        field.save()
        
        return JsonResponse({"success": True, "is_featured": field.is_featured})
    except FieldOfExpertise.DoesNotExist:
        return JsonResponse({"success": False, "error": "Field not found"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})



@login_required
@faculty_required
@require_POST
def invite_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    job_listing_id = (request.POST.get('job_listing_id') or '').strip()
    selected_job = None
    if job_listing_id:
        try:
            selected_job = JobListing.objects.get(
                id=int(job_listing_id),
                profile=get_user_faculty_profile(request.user),
            )
        except (JobListing.DoesNotExist, ValueError):
            selected_job = None

    subject = (request.POST.get('subject') or '').strip()
    if not subject:
        if selected_job:
            subject = f"Invitation to apply: {selected_job.job_title}"
        else:
            subject = 'Interview invitation'

    body = (request.POST.get('message') or '').strip()
    if not body:
        body = (
            f"Hi {student.first_name or student.username}, we reviewed your profile and would like to invite "
            f"you to discuss a relevant opportunity."
        )

    related_url = reverse('conversation-detail', kwargs={'user_id': request.user.id})
    if selected_job:
        job_url = reverse('job-detail', kwargs={'job_id': selected_job.pk})
        absolute_job_url = request.build_absolute_uri(job_url)
        body += f"\n\nSee job: {absolute_job_url}"
        related_url = job_url

    # Prevent duplicate invite submissions.
    duplicate_cutoff = timezone.now() - timedelta(seconds=15)
    duplicate_exists = Message.objects.filter(
        sender=request.user,
        recipient=student,
        subject=subject,
        content=body,
        sent_at__gte=duplicate_cutoff,
    ).exists()

    if duplicate_exists:
        messages.info(request, 'Invitation already sent a moment ago. Skipping duplicate send.')
        return redirect('dashboard-home')

    Message.objects.create(
        sender=request.user,
        recipient=student,
        subject=subject,
        content=body,
    )

    Notification.objects.create(
        user=student,
        kind=Notification.KIND_INTERVIEW,
        title='Faculty invitation',
        body=f"{request.user.get_full_name() or request.user.username} sent you an invitation message.",
        related_url=related_url,
    )

    messages.success(request, f"Invitation sent to {student.get_full_name() or student.username}.")
    return redirect('dashboard-home')

# Faculty dashboard views.

@login_required
def create_job_listing_page(request):
    """Create a job listing."""
    if request.method == 'POST':
        form = forms.JobListingForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.profile = get_user_faculty_profile(request.user)
            job.required_skills_and_tools = request.POST.get('required_skills_and_tools', '')
            job.level_of_confidence = request.POST.get('level_of_confidence', '')
            job.save()
            messages.success(request, 'Job listing created successfully!')
            return redirect('faculty-job-detail', job_id=job.pk)
    else:
        form = forms.JobListingForm()
    
    context = {'form': form}
    return render(request, 'faculty_dashboard/create_job_listing.html', context)


@login_required
def saved_students_page(request):
    """Show saved students."""
    faculty_profile = get_user_faculty_profile(request.user)
    saved_students = SavedStudent.objects.filter(faculty_profile=faculty_profile).select_related('student_portfolio__student')
    
    context = {
        'saved_students': saved_students,
    }
    return render(request, 'faculty_dashboard/saved_students.html', context)


@login_required
@faculty_required
def faculty_student_search_page(request):
    faculty_profile = get_user_faculty_profile(request.user)
    jobs = list(JobListing.objects.filter(profile=faculty_profile).order_by('-posted_date', '-id'))

    active_job_filter = (request.GET.get('job_listing') or '').strip()
    selected_job = None
    if active_job_filter and active_job_filter.lower() != 'all':
        try:
            selected_job_id = int(active_job_filter)
            selected_job = next((job for job in jobs if job.pk == selected_job_id), None)
        except (TypeError, ValueError):
            selected_job = None
            active_job_filter = 'all'
    else:
        active_job_filter = 'all'

    jobs_for_matching = [selected_job] if selected_job is not None else jobs

    candidates, required_tokens = _get_cached_faculty_candidate_matches(faculty_profile, jobs_for_matching)
    candidates = _dedupe_candidate_cards_by_student(candidates)

    search_query = (request.GET.get('q') or '').strip()
    active_skill_filter = (request.GET.get('skill') or 'all').strip().lower()
    active_course_filter = (request.GET.get('course') or 'all').strip()
    active_campus_filter = (request.GET.get('campus') or 'all').strip()
    active_year_filter = (request.GET.get('year') or 'all').strip()
    base_query_params = request.GET.copy()
    base_query_params.pop('page', None)

    min_score_raw = (request.GET.get('min_score') or '').strip()
    try:
        active_min_score = max(0, min(100, int(min_score_raw))) if min_score_raw else 0
    except ValueError:
        active_min_score = 0

    course_filter_normalized = active_course_filter.lower()
    campus_filter_normalized = active_campus_filter.lower()
    year_filter_normalized = active_year_filter.lower()

    scoped_candidates = [c for c in candidates if _candidate_matches_query(c, search_query)]

    if active_course_filter and course_filter_normalized != 'all':
        scoped_candidates = [
            candidate for candidate in scoped_candidates
            if ((getattr(candidate.get('student'), 'current_course', '') or '').strip().lower() == course_filter_normalized)
        ]

    if active_campus_filter and campus_filter_normalized != 'all':
        scoped_candidates = [
            candidate for candidate in scoped_candidates
            if ((getattr(candidate.get('student'), 'campus', '') or '').strip().lower() == campus_filter_normalized)
        ]

    if active_year_filter and year_filter_normalized != 'all':
        scoped_candidates = [
            candidate for candidate in scoped_candidates
            if ((getattr(candidate.get('student'), 'current_year', '') or '').strip().lower() == year_filter_normalized)
        ]

    if active_min_score > 0:
        scoped_candidates = [
            candidate for candidate in scoped_candidates
            if int(candidate.get('match_score', 0) or 0) >= active_min_score
        ]

    visible_candidates = scoped_candidates

    # Build skill filters from the currently selected course scope so the chips stay relevant.
    token_match_counts = {}
    token_label_map = {}

    for candidate in visible_candidates:
        labels = candidate.get('student_skill_labels', [])
        for index, token in enumerate(candidate.get('student_skill_tokens', [])):
            token = (token or '').strip().lower()
            if not token:
                continue
            token_match_counts[token] = token_match_counts.get(token, 0) + 1
            if token not in token_label_map:
                token_label_map[token] = labels[index] if index < len(labels) else _format_skill_label(token)

    skill_filters = []
    for item in (required_tokens or []):
        token = (item.get('raw') or '').strip().lower()
        if not token:
            continue
        count = token_match_counts.get(token, 0)
        if count <= 0:
            continue
        query_params_for_skill = base_query_params.copy()
        query_params_for_skill['skill'] = token
        skill_filters.append({
            'raw': token,
            'label': item.get('label') or token_label_map.get(token) or _format_skill_label(token),
            'count': count,
            'querystring': query_params_for_skill.urlencode(),
        })

    if not skill_filters:
        for token, count in token_match_counts.items():
            query_params_for_skill = base_query_params.copy()
            query_params_for_skill['skill'] = token
            skill_filters.append({
                'raw': token,
                'label': token_label_map.get(token) or _format_skill_label(token),
                'count': count,
                'querystring': query_params_for_skill.urlencode(),
            })

    skill_filters = sorted(skill_filters, key=lambda item: (-item['count'], item['label'].lower()))[:12]

    all_students_querystring = base_query_params.copy()
    all_students_querystring.pop('skill', None)

    course_filters = sorted({
        ((candidate.get('student').current_course or '').strip())
        for candidate in candidates
        if candidate.get('student') and (candidate.get('student').current_course or '').strip()
    }, key=str.lower)

    campus_filters = sorted({
        ((candidate.get('student').campus or '').strip())
        for candidate in candidates
        if candidate.get('student') and (candidate.get('student').campus or '').strip()
    }, key=str.lower)

    year_filters = sorted({
        ((candidate.get('student').current_year or '').strip())
        for candidate in candidates
        if candidate.get('student') and (candidate.get('student').current_year or '').strip()
    }, key=str.lower)

    final_candidates = scoped_candidates
    if active_skill_filter != 'all':
        final_candidates = [
            candidate for candidate in final_candidates
            if _candidate_matches_skill_filter(candidate, active_skill_filter)
        ]

    paginator = Paginator(final_candidates, 12)
    students_page = paginator.get_page(request.GET.get('page'))

    saved_student_ids = set(
        SavedStudent.objects.filter(
            faculty_profile=faculty_profile
        ).values_list('student_portfolio__student_id', flat=True)
    )

    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'invite_jobs': jobs,
        'saved_student_ids': saved_student_ids,
        'candidates': students_page.object_list,
        'students_page': students_page,
        'pagination_query': query_params.urlencode(),
        'required_skill_filters': skill_filters,
        'all_students_querystring': all_students_querystring.urlencode(),
        'job_filters': jobs,
        'course_filters': course_filters,
        'campus_filters': campus_filters,
        'year_filters': year_filters,
        'active_search_query': search_query,
        'active_job_filter': active_job_filter,
        'active_skill_filter': active_skill_filter,
        'active_course_filter': active_course_filter,
        'active_campus_filter': active_campus_filter,
        'active_year_filter': active_year_filter,
        'active_min_score': active_min_score,
    }
    return render(request, 'faculty_dashboard/student_search.html', context)



@login_required
@faculty_required
def applicant_tracking_page(request):
    """Show applicant tracking dashboard."""
    faculty_profile = get_user_faculty_profile(request.user)
    faculty_jobs = JobListing.objects.filter(profile=faculty_profile).order_by('-posted_date', '-id')

    base_applications = JobApplication.objects.filter(
        job_listing__profile=faculty_profile
    ).select_related('student_portfolio__student', 'job_listing').order_by('-updated_at', '-applied_at')

    status_filter = (request.GET.get('status') or 'all').strip().lower()
    job_filter_raw = (request.GET.get('job') or '').strip()

    valid_statuses = {
        'all',
        JobApplication.STATUS_PENDING,
        JobApplication.STATUS_UNDER_REVIEW,
        JobApplication.STATUS_INTERVIEW,
        JobApplication.STATUS_OFFER,
        JobApplication.STATUS_ACCEPTED,
        JobApplication.STATUS_NOT_SELECTED,
    }
    if status_filter not in valid_statuses:
        status_filter = 'all'

    applications = base_applications
    if status_filter != 'all':
        applications = applications.filter(status=status_filter)

    selected_job_id = None
    if job_filter_raw.isdigit():
        candidate_job_id = int(job_filter_raw)
        if faculty_jobs.filter(id=candidate_job_id).exists():
            selected_job_id = candidate_job_id
            applications = applications.filter(job_listing_id=selected_job_id)

    total_applicants = base_applications.count()
    pending_count = base_applications.filter(status=JobApplication.STATUS_PENDING).count()
    reviewing_count = base_applications.filter(status=JobApplication.STATUS_UNDER_REVIEW).count()
    interview_count = base_applications.filter(status=JobApplication.STATUS_INTERVIEW).count()
    offer_count = base_applications.filter(status__in=[JobApplication.STATUS_OFFER, JobApplication.STATUS_ACCEPTED]).count()

    context = {
        'applicants': applications,
        'jobs': faculty_jobs,
        'total_applicants': total_applicants,
        'new_count': pending_count,
        'reviewing_count': reviewing_count,
        'interview_count': interview_count,
        'offer_count': offer_count,
        'active_status': status_filter,
        'active_job_id': selected_job_id,
    }
    return render(request, 'faculty_dashboard/applicant_tracking.html', context)


@login_required
@faculty_required
@require_POST
def update_application_status(request, application_id):
    application = get_object_or_404(
        JobApplication.objects.select_related('job_listing__profile__faculty', 'student_portfolio__student'),
        id=application_id,
        job_listing__profile=get_user_faculty_profile(request.user),
    )

    next_status = (request.POST.get('status') or '').strip().lower()
    allowed_statuses = {
        JobApplication.STATUS_UNDER_REVIEW,
        JobApplication.STATUS_INTERVIEW,
        JobApplication.STATUS_OFFER,
        JobApplication.STATUS_NOT_SELECTED,
    }

    if next_status not in allowed_statuses:
        messages.error(request, 'Invalid application status.')
        return redirect('applicant-tracking')

    application.status = next_status
    application.save(update_fields=['status', 'updated_at'])

    Notification.objects.create(
        user=application.student_portfolio.student,
        kind=Notification.KIND_APPLICATION_STATUS,
        title='Application status updated',
        body=f"Your application for {application.job_listing.job_title} is now {dict(JobApplication.STATUS_CHOICES).get(application.status, application.status)}.",
        related_url=reverse('student-applications'),
    )

    messages.success(request, f"Application updated to {dict(JobApplication.STATUS_CHOICES).get(application.status, application.status)}.")
    return redirect('applicant-tracking')


@login_required
@faculty_required
@require_POST
def delete_application(request, application_id):
    application = get_object_or_404(
        JobApplication.objects.select_related('job_listing__profile__faculty', 'student_portfolio__student'),
        id=application_id,
        job_listing__profile=get_user_faculty_profile(request.user),
    )

    interview_count, _ = Interview.objects.filter(
        job_listing=application.job_listing,
        student_portfolio=application.student_portfolio,
    ).delete()

    job_title = application.job_listing.job_title
    student_user = application.student_portfolio.student
    application.delete()

    Notification.objects.create(
        user=student_user,
        kind=Notification.KIND_APPLICATION_STATUS,
        title='Application removed',
        body=f'Your application for {job_title} was removed from active consideration.',
        related_url=reverse('student-applications'),
    )

    if interview_count:
        messages.success(request, f'Applicant deleted and {interview_count} related interview record(s) removed.')
    else:
        messages.success(request, 'Applicant deleted successfully.')
    return redirect('applicant-tracking')


@login_required
def interview_schedule_page(request):
    """Show interviews and scheduling tools."""
    from datetime import datetime

    faculty_profile = get_user_faculty_profile(request.user)
    faculty_jobs = JobListing.objects.filter(profile=faculty_profile)

    today = datetime.today().date()
    upcoming_interviews = Interview.objects.filter(
        job_listing__in=faculty_jobs,
        scheduled_date__gte=today
    ).order_by('scheduled_date', 'scheduled_time')

    initial = {}
    student_portfolio = (request.GET.get('student_portfolio') or '').strip()
    job_listing = (request.GET.get('job_listing') or '').strip()
    if student_portfolio.isdigit():
        initial['student_portfolio'] = int(student_portfolio)
    if job_listing.isdigit():
        initial['job_listing'] = int(job_listing)

    form = forms.InterviewScheduleForm(faculty_profile=faculty_profile, initial=initial)

    context = {
        'upcoming_interviews': upcoming_interviews,
        'form': form,
        'open_schedule': request.GET.get('open_schedule') == '1' or bool(initial),
    }
    return render(request, 'faculty_dashboard/interview_schedule.html', context)


@login_required
@faculty_required
@require_POST
def save_student(request, student_id):
    """Save or unsave a student."""
    try:
        student = Student.objects.get(id=student_id)
        faculty_profile = get_user_faculty_profile(request.user)
        
        saved, created = SavedStudent.objects.get_or_create(
            faculty_profile=faculty_profile,
            student_portfolio=getattr(student, 'portfolio'),
            defaults={'notes': ''}
        )
        
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if created:
            if is_ajax:
                return JsonResponse({'success': True, 'saved': True, 'message': 'Student saved!'})
            messages.success(request, 'Student saved!')
            return redirect('dashboard-home')
        else:
            saved.delete()
            if is_ajax:
                return JsonResponse({'success': True, 'saved': False, 'message': 'Student removed from saved'})
            messages.info(request, 'Student removed from saved')
            return redirect('dashboard-home')
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'}, status=404)


@login_required
@require_POST
def schedule_interview(request):
    """Schedule a student interview."""
    from datetime import datetime

    faculty_profile = get_user_faculty_profile(request.user)
    form = forms.InterviewScheduleForm(request.POST, faculty_profile=faculty_profile)

    if form.is_valid():
        interview = form.save()

        JobApplication.objects.filter(
            student_portfolio=interview.student_portfolio,
            job_listing=interview.job_listing,
        ).update(status=JobApplication.STATUS_INTERVIEW)

        Notification.objects.create(
            user=interview.student_portfolio.student,
            kind=Notification.KIND_INTERVIEW,
            title='Interview scheduled',
            body=f"An interview was scheduled for {interview.job_listing.job_title} on {interview.scheduled_date}.",
            related_url=reverse('student-interviews'),
        )

        messages.success(request, 'Interview scheduled successfully!')
        return redirect('interview-schedule')

    faculty_jobs = JobListing.objects.filter(profile=faculty_profile)
    today = datetime.today().date()
    upcoming_interviews = Interview.objects.filter(
        job_listing__in=faculty_jobs,
        scheduled_date__gte=today
    ).order_by('scheduled_date', 'scheduled_time')

    messages.error(request, 'Please fix the errors in the interview form.')
    context = {
        'upcoming_interviews': upcoming_interviews,
        'form': form,
        'open_schedule': True,
    }
    return render(request, 'faculty_dashboard/interview_schedule.html', context, status=400)

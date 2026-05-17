"""
Django management command to generate student stress test data.
Creates students per Westminster course, portfolio fields, projects, and media uploads.
"""

import base64
import json
import re
from datetime import datetime
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard.models import FieldOfExpertise, Files, Picture, Project, Video
from userManagement.models import Portfolio, Student


class Command(BaseCommand):
    help = (
        'Generate student stress test data: N students per course, M fields per student, '
        'K projects per field, and media uploads per project'
    )

    DEFAULT_PASSWORD = 'StrongPass123!'
    DEFAULT_STUDENT_ID_SEED = 1832389
    DEFAULT_PHONE_SEED = 71000000000

    FIRST_NAMES = [
        'Aiden', 'Maya', 'Noah', 'Zara', 'Liam', 'Leah', 'Ethan', 'Nadia',
        'Owen', 'Sofia', 'Caleb', 'Hana', 'Mason', 'Amira', 'Lucas', 'Ivy',
        'Arjun', 'Fatima', 'Daniel', 'Layla', 'Yusuf', 'Emily', 'Adam', 'Chloe',
    ]

    LAST_NAMES = [
        'Bennett', 'Walker', 'Patel', 'Ali', 'Nguyen', 'Khan', 'Thomas', 'Sharma',
        'Davies', 'Edwards', 'Ahmed', 'Singh', 'Turner', 'Roberts', 'Wilson', 'Brown',
        'Jones', 'Moore', 'Taylor', 'Hussain', 'Mills', 'Clark', 'Foster', 'Reid',
    ]

    CAMPUS_CYCLE = ['Cavendish Campus', 'Harrow Campus', 'Marylebone Campus', 'Regent Campus']
    YEAR_CYCLE = ['Level 4', 'Level 5', 'Level 6', 'Postgraduate', 'Doctoral']

    DOMAIN_TOPICS = {
        'computer': [
            ('Software Engineering', ['Python', 'API Design', 'Git Workflows']),
            ('Backend Development', ['Django', 'REST APIs', 'PostgreSQL']),
            ('Cloud and DevOps', ['Docker', 'CI/CD', 'Cloud Deployment']),
            ('Systems and Networks', ['Computer Networks', 'Linux', 'Security Controls']),
            ('Quality Engineering', ['Automated Testing', 'Debugging', 'Code Review']),
        ],
        'data': [
            ('Data Engineering', ['SQL Pipelines', 'ETL Design', 'Data Warehousing']),
            ('Analytics', ['Dashboarding', 'KPI Analysis', 'Data Storytelling']),
            ('Machine Learning', ['Model Training', 'Feature Engineering', 'Evaluation']),
            ('Statistical Methods', ['Hypothesis Testing', 'Regression', 'Sampling']),
            ('Data Governance', ['Data Quality', 'Lineage', 'Metadata Management']),
        ],
        'business': [
            ('Business Analysis', ['Requirements Analysis', 'Process Mapping', 'KPI Tracking']),
            ('Operations Management', ['Resource Planning', 'Workflow Optimisation', 'SLA Monitoring']),
            ('Strategy and Growth', ['Market Analysis', 'Business Planning', 'Scenario Modelling']),
            ('Digital Transformation', ['Process Automation', 'Systems Integration', 'Change Delivery']),
            ('Project Delivery', ['Risk Registers', 'Milestone Planning', 'Budget Control']),
        ],
        'finance': [
            ('Financial Modelling', ['DCF Modelling', 'Sensitivity Analysis', 'Forecasting']),
            ('Risk and Compliance', ['Risk Assessment', 'Control Testing', 'Regulatory Review']),
            ('Corporate Finance', ['Valuation', 'Capital Budgeting', 'Cash Flow Analysis']),
            ('Treasury Operations', ['Liquidity Management', 'Reconciliation', 'Treasury Reporting']),
            ('Accounting Analytics', ['Ledger Analysis', 'Variance Reporting', 'IFRS Application']),
        ],
        'design': [
            ('UX Research', ['User Interviews', 'Journey Mapping', 'Usability Testing']),
            ('Product Design', ['Wireframing', 'Prototyping', 'Design Systems']),
            ('Visual Communication', ['Typography', 'Layout Design', 'Brand Identity']),
            ('Design Production', ['Figma', 'Adobe Creative Suite', 'Asset Handoff']),
            ('Accessibility Design', ['WCAG Audits', 'Accessible Components', 'Contrast Testing']),
        ],
        'law': [
            ('Legal Research', ['Case Law Review', 'Statutory Analysis', 'Citation Practice']),
            ('Contract Drafting', ['Clause Drafting', 'Contract Review', 'Risk Clauses']),
            ('Compliance Practice', ['Regulatory Interpretation', 'Policy Drafting', 'Control Mapping']),
            ('Dispute Analysis', ['Issue Spotting', 'Evidence Assessment', 'Argument Structuring']),
            ('Legal Technology', ['Document Automation', 'Legal Databases', 'Matter Tracking']),
        ],
        'nursing': [
            ('Clinical Assessment', ['Patient Assessment', 'Vital Monitoring', 'Clinical Notes']),
            ('Care Planning', ['Care Pathways', 'Intervention Planning', 'Outcome Tracking']),
            ('Patient Safety', ['Risk Escalation', 'Medication Safety', 'Infection Control']),
            ('Healthcare Systems', ['EHR Documentation', 'Referral Workflows', 'Service Coordination']),
            ('Evidence-based Practice', ['Clinical Guidelines', 'Audit Review', 'Quality Improvement']),
        ],
        'architecture': [
            ('Design Development', ['Concept Sketching', 'Technical Detailing', 'Iteration Reviews']),
            ('BIM and CAD', ['BIM Modelling', 'CAD Drafting', 'Clash Detection']),
            ('Urban Analysis', ['Site Appraisal', 'Spatial Planning', 'Context Mapping']),
            ('Construction Documentation', ['Specification Writing', 'Drawing Packages', 'Compliance Checks']),
            ('Sustainability', ['Environmental Analysis', 'Material Selection', 'Performance Assessment']),
        ],
    }

    FALLBACK_TOPICS = [
        ('Applied Research', ['Research Design', 'Data Collection', 'Evidence Synthesis']),
        ('Professional Practice', ['Domain Workflows', 'Technical Documentation', 'Quality Assurance']),
        ('Subject Methods', ['Methodology Selection', 'Critical Evaluation', 'Results Reporting']),
        ('Project Delivery', ['Planning', 'Implementation', 'Outcome Review']),
        ('Domain Innovation', ['Problem Framing', 'Solution Design', 'Impact Assessment']),
    ]

    PROJECT_TYPE_HINTS = [
        ('Implementation Project', 'Built and evaluated a practical solution aligned with this field.'),
        ('Analysis Project', 'Investigated real-world data and produced evidence-backed findings.'),
        ('Optimisation Project', 'Improved an existing process with measurable outcomes and reflection.'),
    ]

    CONFIDENCE_SCALE_CHOICES = [
        'Low Confidence',
        'Developing Confidence',
        'Moderate Confidence',
        'High Confidence',
        'Advanced Confidence',
    ]

    COURSE_FIELDS_DIR = Path('static') / 'course_fields.json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--courses',
            type=str,
            default='static/westminster_courses.json',
            help='Path to Westminster courses JSON file',
        )
        parser.add_argument(
            '--students-per-course',
            type=int,
            default=5,
            help='Number of students to create for each course',
        )
        parser.add_argument(
            '--fields-per-student',
            type=int,
            default=5,
            help='Number of portfolio fields to create per student',
        )
        parser.add_argument(
            '--projects-per-field',
            type=int,
            default=3,
            help='Number of projects to create per field',
        )
        parser.add_argument(
            '--limit-courses',
            type=int,
            default=None,
            help='Limit number of courses processed (for testing)',
        )
        parser.add_argument(
            '--credentials-file',
            type=str,
            default='stress_test_student_logins.txt',
            help='Path to output text file for generated student login credentials',
        )

    def handle(self, *args, **options):
        courses_path = options['courses']
        students_per_course = max(0, options['students_per_course'])
        fields_per_student = max(0, options['fields_per_student'])
        projects_per_field = max(0, options['projects_per_field'])
        limit_courses = options['limit_courses']
        credentials_file = options['credentials_file']

        courses = self._load_courses(courses_path)
        if limit_courses:
            courses = courses[:limit_courses]

        if not courses:
            self.stdout.write(self.style.WARNING('No courses found. Nothing to generate.'))
            return

        assets = self._ensure_seed_assets()

        self.stdout.write(
            f'Processing {len(courses)} courses with {students_per_course} students per course...'
        )

        existing_student_count = Student.objects.count()
        self._used_full_names = {
            ((first_name or '').strip().lower(), (last_name or '').strip().lower())
            for first_name, last_name in Student.objects.values_list('first_name', 'last_name')
        }
        self._name_seed = max(existing_student_count, len(self._used_full_names))

        next_student_numeric_id = self._get_next_student_numeric_id()
        next_phone_number = self._get_next_phone_number()
        created_students = 0
        created_fields = 0
        created_projects = 0
        created_media_items = 0
        skipped_students = 0
        generated_credentials = []
        self._course_field_cache = {}
        progress_total = len(courses) * students_per_course
        progress_current = 0

        if progress_total > 0:
            self._write_progress_bar('Generating students', progress_current, progress_total)


        with transaction.atomic():
            for course_index, course in enumerate(courses, start=1):
                for student_slot in range(1, students_per_course + 1):
                    username = self._build_student_username(next_student_numeric_id)
                    while Student.objects.filter(username=username).exists():
                        next_student_numeric_id += 1
                        username = self._build_student_username(next_student_numeric_id)

                    phone_number = self._get_next_available_phone_number(next_phone_number)
                    student = self._create_student(
                        username=username,
                        course=course,
                        course_index=course_index,
                        student_slot=student_slot,
                        phone_number=phone_number,
                    )
                    next_student_numeric_id += 1
                    next_phone_number = int(phone_number) + 1

                    portfolio = getattr(student, 'portfolio', None)
                    if portfolio is None:
                        portfolio, _ = Portfolio.objects.get_or_create(student=student)

                    about_me, what_i_bring = self._build_portfolio_content(
                        student=student,
                        course=course,
                        course_index=course_index,
                        student_slot=student_slot,
                    )
                    portfolio.about_me = about_me
                    portfolio.what_I_bring = what_i_bring
                    portfolio.save(update_fields=['about_me', 'what_I_bring'])

                    generated_credentials.append(
                        {
                            'username': student.username,
                            'email': student.email,
                            'password': self.DEFAULT_PASSWORD,
                            'course': student.current_course,
                            'campus': student.campus,
                        }
                    )

                    field_topics = self._get_field_topics_for_course(course, fields_per_student)
                    for field_order, (field_name, field_skills) in enumerate(field_topics, start=1):
                        field = FieldOfExpertise.objects.create(
                            portfolio=portfolio,
                            field_of_expertise=field_name,
                            skills=', '.join(field_skills),
                            level_of_confidence=self.CONFIDENCE_SCALE_CHOICES[(field_order - 1) % len(self.CONFIDENCE_SCALE_CHOICES)],
                            is_featured=field_order == 1,
                        )
                        created_fields += 1

                        for project_index in range(1, projects_per_field + 1):
                            title_suffix, summary_hint = self.PROJECT_TYPE_HINTS[(project_index - 1) % len(self.PROJECT_TYPE_HINTS)]
                            project = Project.objects.create(
                                field_of_expertise=field,
                                project_title=f'{field_name} {title_suffix} {project_index}',
                                project_summary=(
                                    f'{summary_hint} Focused on {course} with hands-on deliverables '
                                    f'for portfolio evidence.'
                                ),
                                what_i_learnd=(
                                    f'Applied {field_name.lower()} techniques, documented outcomes, '
                                    'and reflected on iterative improvements.'
                                ),
                                skills_demonstrated=', '.join(field_skills),
                                tech_n_tools_used=', '.join(field_skills),
                                git_link='https://github.com/example/student-project',
                            )
                            created_projects += 1
                            created_media_items += self._attach_project_media(project, assets)

                    created_students += 1
                    progress_current += 1
                    if progress_total > 0:
                        self._write_progress_bar('Generating students', progress_current, progress_total)
        if progress_total > 0:
            self.stdout.write('')

        credentials_path = self._write_credentials_file(credentials_file, generated_credentials)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Created {created_students} students\n'
                f'  Fields created: {created_fields}\n'
                f'  Projects created: {created_projects}\n'
                f'  Media items created: {created_media_items}\n'
                f'  Skipped students: {skipped_students}\n'
                f'  Credentials file: {credentials_path}\n'
                f'  Credentials saved: {len(generated_credentials)}'
            )
        )

    def _load_courses(self, courses_path):
        try:
            with open(courses_path, 'r', encoding='utf-8') as stream:
                payload = json.load(stream)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {courses_path}'))
            return []

        return payload.get('courses', [])

    def _build_student_username(self, numeric_id):
        return f'w{numeric_id}'

    def _get_next_student_numeric_id(self):
        """Get next available Westminster-style numeric ID for student usernames."""
        max_id = self.DEFAULT_STUDENT_ID_SEED - 1
        pattern = re.compile(r'^w(\d+)$')

        for username in Student.objects.values_list('username', flat=True):
            match = pattern.match(username or '')
            if not match:
                continue
            value = int(match.group(1))
            if value > max_id:
                max_id = value

        return max_id + 1

    def _create_student(self, username, course, course_index, student_slot, phone_number):
        first_name, last_name = self._get_next_unique_name()
        student = Student.objects.create_user(
            username=username,
            email=f'{username}@my.westminster.ac.uk',
            password=self.DEFAULT_PASSWORD,
            first_name=first_name,
            last_name=last_name,
            class_type='student',
            phone_number=phone_number,
            current_course=course,
            campus=self.CAMPUS_CYCLE[(course_index + student_slot) % len(self.CAMPUS_CYCLE)],
            current_year=self.YEAR_CYCLE[(course_index + student_slot) % len(self.YEAR_CYCLE)],
        )
        return student

    def _get_next_unique_name(self):
        first_count = len(self.FIRST_NAMES)
        last_count = len(self.LAST_NAMES)

        while True:
            index = self._name_seed
            self._name_seed += 1

            first_name = self.FIRST_NAMES[index % first_count]
            last_name = self.LAST_NAMES[(index // first_count) % last_count]

            # Expand name space for large runs by adding a second given name after the first cycle.
            cycle = index // (first_count * last_count)
            if cycle > 0:
                second_first = self.FIRST_NAMES[cycle % first_count]
                if second_first == first_name:
                    second_first = self.FIRST_NAMES[(cycle + 1) % first_count]
                first_name = f'{first_name} {second_first}'

            key = (first_name.strip().lower(), last_name.strip().lower())
            if key in self._used_full_names:
                continue

            self._used_full_names.add(key)
            return first_name, last_name

    def _get_next_phone_number(self):
        # Get next phone number seed based on existing numeric student phone numbers.
        max_value = self.DEFAULT_PHONE_SEED - 1
        for value in Student.objects.values_list('phone_number', flat=True):
            raw = (value or '').strip()
            if not raw.isdigit():
                continue
            numeric = int(raw)
            if numeric > max_value:
                max_value = numeric
        return max_value + 1

    def _get_next_available_phone_number(self, starting_from):
        # Return next unused all-digit phone number string.
        candidate = int(starting_from)
        while Student.objects.filter(phone_number=str(candidate)).exists():
            candidate += 1
        return str(candidate)

    def _build_portfolio_content(self, student, course, course_index, student_slot):
        """Build unique about_me and what_I_bring text for each generated student."""
        domain = self._pick_domain(course)

        focus_lines = {
            'computer': 'I enjoy turning technical requirements into tested software components and maintainable systems.',
            'data': 'I focus on converting complex datasets into clear analysis that supports practical decisions.',
            'business': 'I am interested in improving organisational performance through structured analysis and delivery planning.',
            'finance': 'I enjoy applying quantitative methods to financial performance, risk, and forecasting decisions.',
            'design': 'I focus on user-centred design decisions backed by iterative prototyping and feedback.',
            'law': 'I work methodically through legal sources to produce clear, evidence-based argumentation.',
            'nursing': 'I prioritise safe, evidence-based care planning with accurate documentation and reflective practice.',
            'architecture': 'I combine design thinking with technical and regulatory awareness to shape workable built-environment solutions.',
            'default': 'I apply research-led, structured problem solving to produce practical outcomes within my discipline.',
        }

        impact_lines = [
            'Across projects, I document decisions carefully and track outcomes to improve each iteration.',
            'I prefer project work where clear milestones and measurable outputs are defined from the start.',
            'I enjoy collaborating with peers and incorporating critique to improve project quality.',
            'I balance technical depth with communication so project outputs are understandable and useful.',
            'I consistently reflect on feedback and convert it into actionable improvements for the next sprint.',
        ]

        bring_items = [
            [
                'Hands-on delivery mindset with clear milestone tracking',
                'Strong use of domain-specific tools and methods',
                'Structured documentation for reproducible outcomes',
                'Evidence-based reflection and continuous improvement',
            ],
            [
                'Consistent project ownership from planning through execution',
                'Practical application of course concepts in portfolio work',
                'Clear communication of technical choices and constraints',
                'Reliability in meeting deadlines and quality standards',
            ],
            [
                'Focused problem framing before implementation',
                'Methodical testing and validation of deliverables',
                'Comfort working across research, build, and review phases',
                'Ability to translate feedback into concrete improvements',
            ],
        ]

        selector = (course_index + student_slot + len(student.username))
        impact = impact_lines[selector % len(impact_lines)]
        selected_bring = bring_items[selector % len(bring_items)]

        about_me = (
            f"I am {student.first_name} {student.last_name}, a {student.current_year} student studying {course} at {student.campus}. "
            f"{focus_lines.get(domain, focus_lines['default'])} {impact} "
            f"Portfolio ID: {student.username}."
        )

        what_i_bring = "\n".join(f"- {item}" for item in selected_bring)
        return about_me, what_i_bring

    def _pick_domain(self, course_name):
        lowered = (course_name or '').lower()
        if any(word in lowered for word in ['computer', 'software', 'cyber', 'computing', 'ai']):
            return 'computer'
        if any(word in lowered for word in ['data', 'analytics', 'statistics', 'machine']):
            return 'data'
        if any(word in lowered for word in ['business', 'management', 'marketing', 'entrepreneurship']):
            return 'business'
        if any(word in lowered for word in ['finance', 'accounting', 'economics', 'fintech']):
            return 'finance'
        if any(word in lowered for word in ['design', 'fashion', 'media', 'photography', 'illustration']):
            return 'design'
        if any(word in lowered for word in ['law', 'legal', 'criminology', 'policing']):
            return 'law'
        if any(word in lowered for word in ['nursing', 'medical', 'biomedical', 'pharmacology', 'health']):
            return 'nursing'
        if any(word in lowered for word in ['architecture', 'urban', 'construction', 'planning', 'estate']):
            return 'architecture'
        return 'default'

    def _slugify_course_name(self, course_name):
        if not course_name:
            return ''
        slug = course_name.lower().strip()
        slug = re.sub(r'[^a-z0-9]+', '_', slug)
        return slug.strip('_')

    def _load_course_field_names(self, course_name):
        cache = getattr(self, '_course_field_cache', {})
        if course_name in cache:
            return cache[course_name]

        slug = self._slugify_course_name(course_name)
        if not slug:
            cache[course_name] = []
            self._course_field_cache = cache
            return []

        source_path = self.COURSE_FIELDS_DIR / f'{slug}_fields.json'
        if not source_path.exists():
            cache[course_name] = []
            self._course_field_cache = cache
            return []

        try:
            payload = json.loads(source_path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError):
            cache[course_name] = []
            self._course_field_cache = cache
            return []

        names = []
        if isinstance(payload, dict):
            groups = payload.get('groups')
            if isinstance(groups, dict):
                for values in groups.values():
                    if isinstance(values, list):
                        names.extend(str(item).strip() for item in values if str(item).strip())

            fields = payload.get('fields')
            if isinstance(fields, list):
                names.extend(str(item).strip() for item in fields if str(item).strip())

        deduped_names = []
        seen = set()
        for name in names:
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped_names.append(name)

        cache[course_name] = deduped_names
        self._course_field_cache = cache
        return deduped_names

    def _get_field_topics_for_course(self, course_name, fields_per_student):
        domain = self._pick_domain(course_name)
        templates = self.DOMAIN_TOPICS.get(domain, self.FALLBACK_TOPICS)
        course_field_names = self._load_course_field_names(course_name)

        topics = []
        for idx in range(fields_per_student):
            _, skills = templates[idx % len(templates)]
            if course_field_names:
                field_name = course_field_names[idx % len(course_field_names)]
            else:
                field_name = templates[idx % len(templates)][0]
            topics.append((field_name, skills))
        return topics

    def _ensure_seed_assets(self):
        media_root = Path('media') / 'stress_seed_assets'
        media_root.mkdir(parents=True, exist_ok=True)

        image_path = media_root / 'student_project_seed.png'
        if not image_path.exists():
            # 1x1 transparent PNG
            image_bytes = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAoMBgQqN2V8AAAAASUVORK5CYII='
            )
            image_path.write_bytes(image_bytes)

        video_path = media_root / 'student_project_seed.mp4'
        if not video_path.exists():
            video_path.write_bytes(b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom')

        doc_path = media_root / 'student_project_seed.docx'
        if not doc_path.exists():
            # Minimal placeholder content with docx extension for upload testing.
            doc_path.write_bytes(b'PK\x03\x04placeholder-docx-content')

        return {
            'image': image_path,
            'video': video_path,
            'doc': doc_path,
        }

    def _attach_project_media(self, project, assets):
        with assets['image'].open('rb') as stream:
            picture = Picture(project=project, caption='Portfolio project image')
            picture.image.save(assets['image'].name, File(stream), save=True)

        with assets['video'].open('rb') as stream:
            video = Video(project=project, title='Portfolio project walkthrough', description='Seeded stress test media')
            video.video.save(assets['video'].name, File(stream), save=True)

        with assets['doc'].open('rb') as stream:
            doc_file = Files(project=project, description='Seeded stress test document')
            doc_file.file.save(assets['doc'].name, File(stream), save=True)

        return 3

    def _write_credentials_file(self, file_path, credentials):
        output_path = Path(file_path).expanduser()
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path

        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            'Stress Test Student Login Credentials',
            f'Generated: {datetime.now().isoformat(timespec="seconds")}',
            f'Created users: {len(credentials)}',
            '',
            'username | email | password | course | campus',
        ]

        for item in credentials:
            lines.append(
                f"{item['username']} | {item['email']} | {item['password']} | {item['course']} | {item['campus']}"
            )

        output_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return output_path

    def _write_progress_bar(self, label, current, total, width=30):
        if total <= 0:
            return

        ratio = min(max(current / total, 0.0), 1.0)
        filled = int(width * ratio)
        bar = ('#' * filled) + ('-' * (width - filled))
        percent = int(ratio * 100)
        self.stdout.write(
            f'\r{label}: [{bar}] {current}/{total} ({percent}%)',
            ending='',
        )

"""
Django management command to generate stress test data.
Creates 1 faculty per Westminster course with realistic names and bios.
Each faculty has 3 unique job listings.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from userManagement.models import Faculty
from dashboard.models import JobListing


class Command(BaseCommand):
    help = 'Generate stress test data: 1 faculty per course, 3 jobs per faculty'
    DEFAULT_PASSWORD = 'StrongPass123!'
    CONFIDENCE_LEVEL_CHOICES = [
        'Low Confidence',
        'Developing Confidence',
        'Moderate Confidence',
        'High Confidence',
        'Advanced Confidence',
    ]

    # Diverse name pool
    FIRST_NAMES = [
        'James', 'Michael', 'David', 'Robert', 'Richard', 'Joseph', 'Thomas', 'Charles',
        'Christopher', 'Daniel', 'Matthew', 'Anthony', 'Mark', 'Donald', 'Steven',
        'Paul', 'Andrew', 'Joshua', 'Kenneth', 'Kevin', 'Brian', 'Edward', 'Ronald',
        'Timothy', 'Jason', 'Jeffrey', 'Ryan', 'Jacob', 'Gary', 'Nicholas',
        'Sarah', 'Maria', 'Jennifer', 'Mary', 'Linda', 'Patricia', 'Barbara', 'Elizabeth',
        'Susan', 'Jessica', 'Sarah', 'Karen', 'Nancy', 'Lisa', 'Betty', 'Margaret',
        'Sandra', 'Ashley', 'Kimberly', 'Emily', 'Donna', 'Michelle', 'Rebecca',
        'Carol', 'Amanda', 'Melissa', 'Deborah', 'Stephanie', 'Rebecca', 'Sharon',
        'Dr. Raj', 'Dr. Priya', 'Dr. Chen', 'Dr. Mohammed', 'Dr. Aisha', 'Prof. Ali',
        'Prof. Fatima', 'Prof. Kumar', 'Prof. Hassan'
    ]

    LAST_NAMES = [
        'Smith', 'Johnson', 'Williams', 'Jones', 'Brown', 'Davis', 'Miller', 'Wilson',
        'Moore', 'Taylor', 'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin',
        'Thompson', 'Garcia', 'Martinez', 'Robinson', 'Clark', 'Rodriguez', 'Lewis',
        'Lee', 'Walker', 'Hall', 'Allen', 'Young', 'King', 'Wright', 'Lopez',
        'Hill', 'Scott', 'Green', 'Adams', 'Nelson', 'Carter', 'Roberts', 'Phillips',
        'Evans', 'Turner', 'Diaz', 'Edwards', 'Collins', 'Reyes', 'Stewart', 'Morris',
        'Patel', 'Singh', 'Kumar', 'Khan', 'Ahmed', 'Hassan', 'Chen', 'Wang'
    ]

    BIO_TEMPLATES = {
        'Computer Science': [
            "Computer Science expert with 10+ years in software development. Passionate about mentoring the next generation of developers.",
            "PhD in Computer Science. Specializes in AI and machine learning applications. Published researcher in top-tier conferences.",
            "Lead architect with experience in distributed systems and cloud computing. Advocates for clean code and best practices."
        ],
        'Data': [
            "Data scientist with expertise in predictive modeling and analytics. Helped companies leverage data for strategic decisions.",
            "Big data specialist with strong background in statistical analysis. Skilled in Python, R, and SQL.",
            "Analytics leader focused on data-driven decision making. 8+ years building data pipelines and dashboards."
        ],
        'Business': [
            "Business strategist with MBA from top institution. Expert in digital transformation and organizational change.",
            "Business consultant specializing in entrepreneurship and startup ecosystems. Published author on business innovation.",
            "Operations expert with 15+ years managing cross-functional teams. Passionate about business excellence and lean methodology."
        ],
        'Finance': [
            "Finance professional with CFA certification. Specialized in investment management and financial risk analysis.",
            "Accounting expert with background in corporate finance and auditing. Strong knowledge of IFRS and accounting standards.",
            "Financial economist researching market dynamics and economic trends. Worked with major financial institutions."
        ],
        'Design': [
            "Award-winning designer with 12+ years in digital and product design. Focused on user-centered design principles.",
            "Creative director specializing in branding and visual identity. Worked with Fortune 500 companies on design innovation.",
            "UX/UI specialist passionate about creating intuitive and beautiful interfaces. Deep expertise in design systems and accessibility."
        ],
        'Marketing': [
            "Marketing strategist with proven track record in brand building and customer acquisition.",
            "Digital marketer specializing in SEO, content strategy, and social media growth. Data-driven approach to marketing.",
            "Marketing executive with experience in B2B and B2C sectors. Expert in customer journey optimization."
        ],
        'Law': [
            "Legal expert with 20+ years in corporate law and contract negotiations. Specialized in commercial and technology law.",
            "Barrister specializing in criminal law and litigation. Strong advocacy and courtroom experience.",
            "Legal scholar with focus on constitutional law and human rights. Published numerous articles in legal journals."
        ],
        'Nursing': [
            "Registered nurse with 15+ years clinical experience. Specialized in critical care and patient education.",
            "Nursing leader with expertise in healthcare management and quality improvement. Committed to compassionate patient care.",
            "Advanced practice nurse with background in emergency medicine. Advocate for evidence-based nursing practices."
        ],
        'Architecture': [
            "Architect with award-winning designs in sustainable and innovative building design.",
            "Senior architect specializing in commercial and residential projects. Experts in BIM and digital architecture tools.",
            "Design-focused architect passionate about creating spaces that improve people's lives. RIBA certified."
        ],
        'default': [
            "Experienced academic with strong track record in education and mentorship. Dedicated to student success.",
            "Industry professional with years of practical experience. Passionate about bridging theory and practice.",
            "Subject matter expert committed to advancing knowledge in their field. Active researcher and thought leader."
        ]
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--courses',
            type=str,
            default='static/westminster_courses.json',
            help='Path to Westminster courses JSON file'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of faculties to create (for testing)'
        )
        parser.add_argument(
            '--credentials-file',
            type=str,
            default='stress_test_faculty_logins.txt',
            help='Path to output text file for generated login credentials'
        )

    def handle(self, *args, **options):
        courses_file = options['courses']
        limit = options['limit']
        credentials_file = options['credentials_file']

        # Load courses
        try:
            with open(courses_file, 'r') as f:
                data = json.load(f)
                courses = data['courses']
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {courses_file}'))
            return

        if limit:
            courses = courses[:limit]

        self.stdout.write(f'Loading {len(courses)} courses...')

        phone_start = 7000000000
        existing_faculty_count = Faculty.objects.count()
        created_count = 0
        job_count = 0
        skipped = 0
        generated_credentials = []
        progress_total = len(courses)
        progress_current = 0

        if progress_total > 0:
            self._write_progress_bar('Generating faculties', progress_current, progress_total)


        with transaction.atomic():
            for idx, course in enumerate(courses, 1):
                try:
                    # Generate unique faculty data
                    first_name = self.FIRST_NAMES[idx % len(self.FIRST_NAMES)]
                    last_name = self.LAST_NAMES[(idx + 5) % len(self.LAST_NAMES)]
                    
                    username = f"{first_name.lower()}.{last_name.lower()}{idx}@westminster.ac.uk".replace(' ', '_')
                    phone = str(phone_start + existing_faculty_count + idx)
                    
                    # Skip if already exists
                    if Faculty.objects.filter(username=username).exists():
                        skipped += 1
                        continue

                    # Create faculty with bio
                    bio = self._generate_bio(course, idx)
                    
                    faculty = Faculty.objects.create_user(
                        username=username,
                        email=username,
                        password=self.DEFAULT_PASSWORD,
                        first_name=first_name.replace('Dr. ', '').replace('Prof. ', ''),
                        last_name=last_name,
                        phone_number=phone,
                        professor_of=course,
                        campus=self._get_campus(idx),
                    )
                    
                    # Update profile with bio
                    faculty_profile = getattr(faculty, 'profile')
                    faculty_profile.bio = bio
                    faculty_profile.save()
                    
                    created_count += 1
                    generated_credentials.append({
                        'username': username,
                        'email': username,
                        'password': self.DEFAULT_PASSWORD,
                        'course': course,
                        'campus': faculty.campus,
                    })

                    # Create 3 unique jobs for this faculty
                    job_titles = self._get_job_titles(course)
                    hourly_wages = ['14.00', '17.00', '20.00']
                    for job_idx, job_title in enumerate(job_titles):
                        description = self._generate_job_description(course, job_idx, first_name, last_name)
                        skills, confidence_level = self._get_job_requirements(course, job_title, job_idx)
                        hourly_wage = hourly_wages[job_idx % len(hourly_wages)]

                        JobListing.objects.create(
                            profile=faculty_profile,
                            job_title=job_title,
                            location=self._get_location(idx),
                            required_skills_and_tools=', '.join(skills),
                            description=description,
                            salary=hourly_wage,
                            level_of_confidence=confidence_level,
                        )
                        job_count += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error with course "{course}": {str(e)[:60]}'))
                    skipped += 1
                finally:
                    progress_current += 1
                    if progress_total > 0:
                        self._write_progress_bar('Generating faculties', progress_current, progress_total)

        if progress_total > 0:
            self.stdout.write('')

        credentials_path = self._write_credentials_file(credentials_file, generated_credentials)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Created {created_count} faculties and {job_count} job listings\n'
                f'  Skipped: {skipped}\n'
                f'  Credentials file: {credentials_path}\n'
                f'  Credentials saved: {len(generated_credentials)}'
            )
        )

    def _generate_bio(self, course, idx):
        """Generate course-specific bio."""
        # Find matching bio template
        for key in self.BIO_TEMPLATES.keys():
            if key != 'default' and key in course:
                bios = self.BIO_TEMPLATES[key]
                return bios[idx % len(bios)]
        
        # Default bio
        default_bios = self.BIO_TEMPLATES['default']
        return default_bios[idx % len(default_bios)]

    def _get_campus(self, idx):
        """Distribute faculties across campuses."""
        campuses = ['Cavendish Campus', 'Harrow Campus', 'Marylebone Campus', 'Regent Campus']
        return campuses[idx % len(campuses)]

    def _get_location(self, idx):
        """Generate realistic on-campus student job locations."""
        locations = [
            'Cavendish Campus',
            'Harrow Campus',
            'Marylebone Campus',
            'Regent Campus',
            'Hybrid (Campus + Remote)',
            'Multiple Westminster Campuses',
        ]
        return locations[idx % len(locations)]

    def _get_job_titles(self, course):
        """Generate 3 student-friendly university job titles based on course."""
        if 'Computer' in course or 'Computing' in course or 'Cyber' in course:
            return [
                'Student IT Support Assistant',
                'Digital Skills Mentor',
                'Junior Web Content Assistant',
            ]
        elif 'Data' in course or 'Analytics' in course or 'Mathematics' in course:
            return [
                'Student Data Assistant',
                'Learning Analytics Assistant',
                'Research Data Support Assistant',
            ]
        elif 'Business' in course or 'Management' in course or 'Finance' in course or 'Accounting' in course:
            return [
                'Student Services Assistant',
                'Careers and Employability Assistant',
                'Faculty Office Assistant',
            ]
        elif 'Design' in course or 'Architecture' in course or 'Media' in course or 'Fashion' in course:
            return [
                'Creative Studio Assistant',
                'Media Lab Assistant',
                'Exhibition and Events Assistant',
            ]
        elif 'Law' in course or 'Politics' in course or 'International' in course:
            return [
                'Legal Clinic Assistant',
                'Policy Research Assistant',
                'Student Advice Desk Assistant',
            ]
        elif 'Nursing' in course or 'Medical' in course or 'Biomedical' in course or 'Health' in course:
            return [
                'Clinical Simulation Lab Assistant',
                'Health Outreach Assistant',
                'Wellbeing Services Assistant',
            ]
        elif 'Marketing' in course or 'Communication' in course or 'English' in course or 'Language' in course:
            return [
                'Communications and Content Assistant',
                'Social Media Assistant',
                'Student Recruitment Ambassador',
            ]
        else:
            return [
                'Student Ambassador',
                'Library and Learning Resources Assistant',
                'Academic Support Assistant',
            ]

    def _generate_job_description(self, course, job_idx, first_name, last_name):
        """Generate student-focused university job descriptions."""
        descriptions = {
            0: (
                f"Part-time on-campus role in {course}. "
                f"{first_name} {last_name} is looking for a reliable student to support daily service delivery "
                f"for 10-15 hours per week around university timetables."
            ),
            1: (
                f"Flexible role for Westminster students with interest in {course}. "
                f"Work with {first_name} {last_name} to support peers, contribute to projects, "
                f"and build professional experience while studying."
            ),
            2: (
                f"Student-facing opportunity linked to {course}, supervised by {first_name} {last_name}. "
                f"Ideal for developing employability skills through practical campus-based work, "
                f"with training and mentoring provided."
            ),
        }
        return descriptions.get(job_idx, f"Campus student role in {course} with {first_name} {last_name}.")

    def _get_job_requirements(self, course, job_title, job_idx):
        """Return student-job-relevant skills/tools and confidence level text."""
        base_skills = ['Professional Communication', 'Time Management']
        title_key = (job_title or '').lower()

        role_map = [
            (
                ['it support'],
                ['IT Support', 'Troubleshooting', 'Windows', 'Service Desk', 'Customer Service'],
                'Developing Confidence',
            ),
            (
                ['digital skills mentor'],
                ['Digital Literacy', 'Peer Mentoring', 'Presentation Skills', 'Python', 'Office 365'],
                'Moderate Confidence',
            ),
            (
                ['web content'],
                ['HTML', 'CSS', 'CMS Editing', 'Accessibility Basics', 'Content Proofing'],
                'Developing Confidence',
            ),
            (
                ['data assistant', 'analytics assistant', 'research data'],
                ['Excel', 'SQL', 'Data Cleaning', 'Data Entry Accuracy', 'Reporting'],
                'Moderate Confidence',
            ),
            (
                ['student services'],
                ['Student Support', 'Case Logging', 'Communication', 'Confidentiality', 'Admin Workflow'],
                'Developing Confidence',
            ),
            (
                ['careers and employability'],
                ['Workshop Support', 'CV Review Basics', 'Event Coordination', 'Stakeholder Communication', 'CRM Updates'],
                'Moderate Confidence',
            ),
            (
                ['faculty office'],
                ['Administrative Support', 'Scheduling', 'Spreadsheet Tracking', 'Document Handling', 'Customer Service'],
                'Developing Confidence',
            ),
            (
                ['creative studio', 'media lab', 'exhibition and events'],
                ['Adobe Creative Suite', 'Content Production', 'Event Support', 'Visual Design', 'Asset Management'],
                'Moderate Confidence',
            ),
            (
                ['legal clinic', 'policy research', 'advice desk'],
                ['Legal Research', 'Policy Analysis', 'Client Communication', 'Note Taking', 'Confidentiality'],
                'Moderate Confidence',
            ),
            (
                ['clinical simulation', 'health outreach', 'wellbeing'],
                ['Patient Communication', 'Clinical Documentation', 'Data Recording', 'Safeguarding Awareness', 'Teamwork'],
                'Moderate Confidence',
            ),
            (
                ['communications and content', 'social media', 'recruitment ambassador'],
                ['Content Writing', 'Social Media Scheduling', 'Audience Engagement', 'Campaign Support', 'Brand Guidelines'],
                'Developing Confidence',
            ),
            (
                ['student ambassador', 'library', 'academic support'],
                ['Student Engagement', 'Front Desk Support', 'Information Handling', 'Campus Systems', 'Team Communication'],
                'Developing Confidence',
            ),
        ]

        for keywords, skills, confidence in role_map:
            if any(keyword in title_key for keyword in keywords):
                return base_skills + skills, confidence

        if 'Data' in course or 'Analytics' in course:
            return base_skills + ['Excel', 'SQL', 'Data Validation', 'Reporting', 'Research Methods'], 'Moderate Confidence'
        if 'Computer' in course or 'Computing' in course or 'Cyber' in course:
            return base_skills + ['IT Support', 'Python', 'Web Basics', 'Ticketing Systems', 'Troubleshooting'], 'Moderate Confidence'
        if 'Business' in course or 'Management' in course:
            return base_skills + ['Customer Service', 'Process Support', 'Scheduling', 'Records Management', 'Stakeholder Communication'], 'Developing Confidence'
        if 'Finance' in course or 'Accounting' in course:
            return base_skills + ['Spreadsheet Modelling', 'Numeracy', 'Data Accuracy', 'Reporting', 'Compliance Awareness'], 'Moderate Confidence'
        if 'Design' in course or 'Architecture' in course:
            return base_skills + ['Visual Communication', 'Adobe Creative Suite', 'Design Review', 'Asset Organisation', 'Presentation'], 'Moderate Confidence'
        if 'Marketing' in course:
            return base_skills + ['Content Creation', 'Campaign Support', 'Audience Insights', 'Social Media', 'Analytics Basics'], 'Developing Confidence'
        if 'Law' in course:
            return base_skills + ['Legal Research', 'Case Notes', 'Policy Review', 'Confidentiality', 'Written Communication'], 'Moderate Confidence'
        if 'Nursing' in course or 'Medical' in course:
            return base_skills + ['Clinical Communication', 'Documentation', 'Service Support', 'Patient Interaction', 'Care Standards'], 'Moderate Confidence'

        fallback_skills = self._derive_course_specific_skills(course, job_title)

        confidence_by_idx = [
            'Developing Confidence',
            'Moderate Confidence',
            'High Confidence',
        ]
        fallback_confidence = confidence_by_idx[job_idx % len(confidence_by_idx)]
        return base_skills + fallback_skills, fallback_confidence

    def _derive_course_specific_skills(self, course, job_title):
        """Derive technical/domain skills from course and job text when no mapping is matched."""
        token_text = f"{course or ''} {job_title or ''}".lower()
        tokens = [t for t in re.split(r'[^a-z0-9]+', token_text) if t]

        token_skill_map = {
            'accounting': ['Financial Accounting', 'Management Accounting', 'Financial Reporting'],
            'finance': ['Financial Modelling', 'Corporate Finance', 'Risk Analysis'],
            'economics': ['Econometric Analysis', 'Policy Evaluation', 'Forecast Modelling'],
            'business': ['Business Analysis', 'Process Modelling', 'Operational Planning'],
            'management': ['Resource Planning', 'Performance Metrics', 'Operational Governance'],
            'marketing': ['Campaign Analytics', 'SEO Strategy', 'Audience Segmentation'],
            'digital': ['Digital Content Strategy', 'Platform Analytics', 'CMS Workflows'],
            'computer': ['Software Development', 'Algorithm Design', 'Version Control'],
            'computing': ['Software Development', 'Database Systems', 'Systems Testing'],
            'software': ['Software Architecture', 'API Development', 'Test Automation'],
            'cyber': ['Threat Analysis', 'Security Monitoring', 'Incident Response'],
            'security': ['Vulnerability Assessment', 'Security Controls', 'Incident Response'],
            'forensics': ['Digital Forensics', 'Evidence Handling', 'Incident Investigation'],
            'data': ['Data Analysis', 'SQL Querying', 'Data Quality Assurance'],
            'analytics': ['Statistical Analysis', 'Dashboard Development', 'KPI Evaluation'],
            'ai': ['Model Evaluation', 'Feature Engineering', 'Prompt Design'],
            'artificial': ['Machine Learning Pipelines', 'Model Validation', 'AI Ethics'],
            'machine': ['Model Training', 'Feature Engineering', 'Model Monitoring'],
            'architecture': ['Technical Design', 'CAD/BIM Workflow', 'Design Compliance'],
            'architectural': ['Building Regulations', 'Technical Drawing', 'Material Specification'],
            'planning': ['Site Analysis', 'Planning Policy Review', 'Impact Assessment'],
            'law': ['Legal Research', 'Case Analysis', 'Regulatory Interpretation'],
            'legal': ['Contract Drafting', 'Legal Analysis', 'Compliance Review'],
            'criminology': ['Case Assessment', 'Evidence Review', 'Policy Analysis'],
            'psychology': ['Behavioural Assessment', 'Research Methods', 'Data Interpretation'],
            'nursing': ['Clinical Documentation', 'Care Planning', 'Patient Assessment'],
            'medical': ['Clinical Assessment', 'Care Pathway Design', 'Healthcare Documentation'],
            'biomedical': ['Laboratory Protocols', 'Data Recording', 'Clinical Interpretation'],
            'biochemistry': ['Laboratory Analysis', 'Experimental Design', 'Scientific Reporting'],
            'pharmacology': ['Drug Data Analysis', 'Clinical Safety Review', 'Regulatory Protocols'],
            'english': ['Textual Analysis', 'Editorial Review', 'Academic Writing'],
            'literature': ['Critical Analysis', 'Literature Review', 'Scholarly Referencing'],
            'translation': ['Translation Workflow', 'Terminology Management', 'Quality Assurance'],
            'interpreting': ['Consecutive Interpreting', 'Terminology Preparation', 'Briefing Analysis'],
            'communication': ['Content Structuring', 'Audience Analysis', 'Editorial Planning'],
            'media': ['Media Production', 'Content Planning', 'Editorial Workflow'],
            'journalism': ['News Research', 'Source Verification', 'Editorial Production'],
            'photography': ['Image Editing', 'Lighting Techniques', 'Post-Production'],
            'fashion': ['Collection Development', 'Trend Analysis', 'Garment Construction'],
            'design': ['Design Systems', 'Prototype Development', 'User Testing'],
            'urban': ['Urban Analysis', 'Spatial Planning', 'Policy Appraisal'],
            'construction': ['Construction Scheduling', 'Cost Estimation', 'Site Compliance'],
            'real': ['Property Valuation', 'Market Appraisal', 'Asset Analysis'],
            'estate': ['Property Valuation', 'Lease Analysis', 'Development Feasibility'],
            'project': ['Project Scheduling', 'Risk Register Management', 'Scope Control'],
            'transport': ['Transport Modelling', 'Network Analysis', 'Mobility Planning'],
            'sociology': ['Social Research', 'Qualitative Analysis', 'Policy Evaluation'],
            'politics': ['Policy Analysis', 'Legislative Review', 'Geopolitical Assessment'],
            'international': ['Policy Analysis', 'Cross-border Regulation', 'Comparative Research'],
            'language': ['Linguistic Analysis', 'Corpus Methods', 'Discourse Analysis'],
            'tesol': ['Lesson Planning', 'Language Assessment', 'Curriculum Design'],
            'phd': ['Research Design', 'Methodology Development', 'Scholarly Publication'],
        }

        collected = []
        for token in tokens:
            skills = token_skill_map.get(token)
            if not skills:
                continue
            for skill in skills:
                if skill not in collected:
                    collected.append(skill)
                if len(collected) >= 5:
                    break
            if len(collected) >= 5:
                break

        if not collected:
            collected = ['Domain Research', 'Applied Methodology', 'Technical Documentation']

        return collected[:5]


    def _write_credentials_file(self, file_path, credentials):
        """Write generated login credentials to a plain text file."""
        output_path = Path(file_path).expanduser()
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path

        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            'Stress Test Faculty Login Credentials',
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

from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from dashboard.models import (
    JobApplication,
    JobListing,
    SavedJob,
    upload_to_files,
    upload_to_pictures,
    upload_to_videos,
    validate_max_500_words,
)
from userManagement.models import Faculty, Notification, Student


class WordLimitValidatorTests(TestCase):
    def test_validate_max_500_words_accepts_500_words(self):
        text = "word " * 500
        validate_max_500_words(text)

    def test_validate_max_500_words_rejects_more_than_500_words(self):
        text = "word " * 501
        with self.assertRaises(ValidationError):
            validate_max_500_words(text)


class UploadPathHelperTests(TestCase):
    def _nested_instance(self, username):
        student = SimpleNamespace(username=username)
        portfolio = SimpleNamespace(student=student)
        field = SimpleNamespace(portfolio=portfolio)
        project = SimpleNamespace(field_of_expertise=field)
        return SimpleNamespace(project=project)

    def test_upload_helpers_include_username_when_available(self):
        instance = self._nested_instance("w1832388")

        self.assertEqual(upload_to_pictures(instance, "a.png"), "pictures/w1832388/a.png")
        self.assertEqual(upload_to_videos(instance, "a.mp4"), "videos/w1832388/a.mp4")
        self.assertEqual(upload_to_files(instance, "a.pdf"), "files/w1832388/a.pdf")

    def test_upload_helpers_fall_back_to_unknown_user(self):
        instance = SimpleNamespace()

        self.assertEqual(upload_to_pictures(instance, "a.png"), "pictures/unknown_user/a.png")
        self.assertEqual(upload_to_videos(instance, "a.mp4"), "videos/unknown_user/a.mp4")
        self.assertEqual(upload_to_files(instance, "a.pdf"), "files/unknown_user/a.pdf")


class DashboardAccessAndWorkflowTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create_user(
            username="w1832600",
            password="StrongPass123!",
            first_name="Sam",
            phone_number="07000000021",
            current_course="Computer Science BSc Honours",
            campus="Cavendish Campus",
            current_year="Level 5",
        )
        self.faculty = Faculty.objects.create_user(
            username="faculty2600@westminster.ac.uk",
            password="StrongPass123!",
            first_name="Fran",
            phone_number="07000000022",
            professor_of="Computer Science BSc Honours",
            campus="Marylebone Campus",
        )
        self.faculty_profile = getattr(self.faculty, 'profile')
        self.student_portfolio = getattr(self.student, 'portfolio')
        self.job = JobListing.objects.create(
            profile=self.faculty_profile,
            job_title="Junior Developer",
            location="London",
            required_skills_and_tools="Python, Django",
            description="Graduate role",
        )

    def test_faculty_cannot_apply_to_student_only_job_endpoint(self):
        self.client.force_login(self.faculty)

        response = self.client.post(reverse("apply-to-job", kwargs={"job_id": self.job.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("login")))
        self.assertFalse(JobApplication.objects.filter(job_listing=self.job).exists())

    def test_student_cannot_access_faculty_status_update_endpoint(self):
        application = JobApplication.objects.create(
            student_portfolio=self.student_portfolio,
            job_listing=self.job,
            status=JobApplication.STATUS_PENDING,
        )
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("update-application-status", kwargs={"application_id": application.pk}),
            data={"status": JobApplication.STATUS_UNDER_REVIEW},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("faculty-login")))
        application = JobApplication.objects.get(pk=application.pk)
        self.assertEqual(application.status, JobApplication.STATUS_PENDING)

    def test_apply_to_job_creates_pending_application_and_notifications(self):
        self.client.force_login(self.student)

        response = self.client.post(reverse("apply-to-job", kwargs={"job_id": self.job.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("job-detail", kwargs={"job_id": self.job.pk}))
        application = JobApplication.objects.get(student_portfolio=self.student_portfolio, job_listing=self.job)
        self.assertEqual(application.status, JobApplication.STATUS_PENDING)
        self.assertTrue(
            Notification.objects.filter(
                user=self.faculty,
                kind=Notification.KIND_APPLICATION,
                title="New application received",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.student,
                kind=Notification.KIND_APPLICATION,
                title="Application submitted",
            ).exists()
        )

    def test_apply_to_job_twice_does_not_duplicate_application(self):
        self.client.force_login(self.student)

        self.client.post(reverse("apply-to-job", kwargs={"job_id": self.job.pk}))
        self.client.post(reverse("apply-to-job", kwargs={"job_id": self.job.pk}))

        self.assertEqual(
            JobApplication.objects.filter(student_portfolio=self.student_portfolio, job_listing=self.job).count(),
            1,
        )

    def test_update_application_status_notifies_student(self):
        application = JobApplication.objects.create(
            student_portfolio=self.student_portfolio,
            job_listing=self.job,
            status=JobApplication.STATUS_PENDING,
        )
        self.client.force_login(self.faculty)

        response = self.client.post(
            reverse("update-application-status", kwargs={"application_id": application.pk}),
            data={"status": JobApplication.STATUS_UNDER_REVIEW},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("applicant-tracking"))
        application = JobApplication.objects.get(pk=application.pk)
        self.assertEqual(application.status, JobApplication.STATUS_UNDER_REVIEW)
        self.assertTrue(
            Notification.objects.filter(
                user=self.student,
                kind=Notification.KIND_APPLICATION_STATUS,
                title="Application status updated",
            ).exists()
        )

    def test_accept_offer_changes_status_and_notifies_faculty(self):
        application = JobApplication.objects.create(
            student_portfolio=self.student_portfolio,
            job_listing=self.job,
            status=JobApplication.STATUS_OFFER,
        )
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("accept-application-offer", kwargs={"application_id": application.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("student-applications"))
        application = JobApplication.objects.get(pk=application.pk)
        self.assertEqual(application.status, JobApplication.STATUS_ACCEPTED)
        self.assertTrue(
            Notification.objects.filter(
                user=self.faculty,
                kind=Notification.KIND_APPLICATION_STATUS,
                title="Offer accepted",
            ).exists()
        )

    def test_toggle_save_job_adds_then_removes_saved_job(self):
        self.client.force_login(self.student)

        add_response = self.client.post(reverse("toggle-save-job", kwargs={"job_id": self.job.pk}))
        self.assertEqual(add_response.status_code, 302)
        self.assertEqual(add_response["Location"], reverse("job-detail", kwargs={"job_id": self.job.pk}))
        self.assertTrue(SavedJob.objects.filter(student_portfolio=self.student_portfolio, job_listing=self.job).exists())

        remove_response = self.client.post(reverse("toggle-save-job", kwargs={"job_id": self.job.pk}))
        self.assertEqual(remove_response.status_code, 302)
        self.assertEqual(remove_response["Location"], reverse("job-detail", kwargs={"job_id": self.job.pk}))
        self.assertFalse(SavedJob.objects.filter(student_portfolio=self.student_portfolio, job_listing=self.job).exists())

    def test_student_job_search_exposes_match_score_badge_data(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("student-job-search"))

        self.assertEqual(response.status_code, 200)
        jobs = list(response.context["jobs"])
        self.assertTrue(jobs)
        self.assertIsInstance(getattr(jobs[0], "match_score", None), int)
        self.assertContains(response, f"{jobs[0].match_score}% Match")

    def test_student_job_search_can_filter_by_field_of_expertise(self):
        unrelated_faculty = Faculty.objects.create_user(
            username="faculty2601@westminster.ac.uk",
            password="StrongPass123!",
            first_name="Bina",
            phone_number="07000000023",
            professor_of="Business Management BA Honours",
            campus="Marylebone Campus",
        )
        unrelated_profile = getattr(unrelated_faculty, 'profile')
        JobListing.objects.create(
            profile=unrelated_profile,
            job_title="Business Analyst",
            location="London",
            required_skills_and_tools="Excel, Reporting",
            description="Business-focused graduate role",
        )

        self.client.force_login(self.student)

        initial_response = self.client.get(reverse("student-job-search"))
        self.assertEqual(initial_response.status_code, 200)
        field_filters = initial_response.context.get("field_filters", [])
        self.assertTrue(field_filters)

        field_labels = {(item.get("label") or "").lower() for item in field_filters}
        self.assertIn("software engineering", field_labels)
        self.assertNotIn("legal research", field_labels)

        all_titles = {job.job_title for job in initial_response.context["jobs"]}
        self.assertNotIn("Business Analyst", all_titles)
        selected_field = field_filters[0]

        response = self.client.get(reverse("student-job-search"), {"field": selected_field["raw"]})

        self.assertEqual(response.status_code, 200)
        titles = {job.job_title for job in response.context["jobs"]}
        self.assertTrue(titles.issubset(all_titles))
        self.assertLessEqual(len(titles), len(all_titles))
        self.assertEqual(response.context["active_field_filter"], selected_field["raw"])

    def test_student_job_search_field_filter_matches_domain_adjacent_jobs(self):
        related_faculty = Faculty.objects.create_user(
            username="faculty2602@westminster.ac.uk",
            password="StrongPass123!",
            first_name="Cyra",
            phone_number="07000000024",
            professor_of="Cyber Security BSc Honours",
            campus="Cavendish Campus",
        )
        related_profile = getattr(related_faculty, 'profile')
        JobListing.objects.create(
            profile=related_profile,
            job_title="Security Operations Analyst",
            location="Hybrid",
            required_skills_and_tools="SIEM, Incident Response",
            description="Protect enterprise infrastructure",
        )

        unrelated_faculty = Faculty.objects.create_user(
            username="faculty2603@westminster.ac.uk",
            password="StrongPass123!",
            first_name="Lara",
            phone_number="07000000025",
            professor_of="Law LLB Honours",
            campus="Regent Campus",
        )
        unrelated_profile = getattr(unrelated_faculty, 'profile')
        JobListing.objects.create(
            profile=unrelated_profile,
            job_title="Legal Research Assistant",
            location="London",
            required_skills_and_tools="Case law analysis",
            description="Support legal drafting and reviews",
        )

        self.client.force_login(self.student)

        initial_response = self.client.get(reverse("student-job-search"))
        self.assertEqual(initial_response.status_code, 200)
        field_filters = initial_response.context.get("field_filters", [])
        security_field = next(
            (
                item for item in field_filters
                if "security" in (item.get("label") or "").lower() or "cyber" in (item.get("label") or "").lower()
            ),
            None,
        )
        self.assertIsNotNone(security_field)

        response = self.client.get(reverse("student-job-search"), {"field": security_field["raw"]})

        self.assertEqual(response.status_code, 200)
        titles = {job.job_title for job in response.context["jobs"]}
        self.assertIn("Security Operations Analyst", titles)
        self.assertNotIn("Legal Research Assistant", titles)
        self.assertEqual(response.context["active_field_filter"], security_field["raw"])


class JobListingOwnershipTests(TestCase):
    """Test job listing ownership and edit/delete permissions."""
    
    def setUp(self):
        self.faculty1 = Faculty.objects.create_user(
            username="faculty_owner@westminster.ac.uk",
            password="StrongPass123!",
            first_name="Owner",
            phone_number="07000000030",
            professor_of="Computer Science BSc Honours",
            campus="Marylebone Campus",
        )
        self.faculty2 = Faculty.objects.create_user(
            username="faculty_other@westminster.ac.uk",
            password="StrongPass123!",
            first_name="Other",
            phone_number="07000000031",
            professor_of="Business BSc Honours",
            campus="Regent Campus",
        )
        self.faculty_profile = getattr(self.faculty1, 'profile')
        self.job = JobListing.objects.create(
            profile=self.faculty_profile,
            job_title="Senior Developer",
            location="London",
            required_skills_and_tools="Python, Django, AWS",
            description="Looking for an experienced developer",
        )
    
    def test_faculty_cannot_edit_another_faculty_job(self):
        self.client.force_login(self.faculty2)
        response = self.client.get(reverse("edit-job-listing", kwargs={"job_id": self.job.pk}))
        self.assertEqual(response.status_code, 404)
    
    def test_faculty_cannot_delete_another_faculty_job(self):
        self.client.force_login(self.faculty2)
        response = self.client.post(reverse("delete-job-listing", kwargs={"job_id": self.job.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(JobListing.objects.filter(id=self.job.pk).exists())
    
    def test_faculty_can_edit_own_job(self):
        self.client.force_login(self.faculty1)
        response = self.client.post(
            reverse("edit-job-listing", kwargs={"job_id": self.job.pk}),
            data={
                'job_title': 'Principal Developer',
                'location': 'Remote',
                'required_skills_and_tools': 'Python, Django, AWS, Kubernetes',
                'description': 'Principal level developer needed',
                'salary': '75000.00',
                'posted_date': '2026-04-18',
                'application_deadline': '2026-05-18',
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("faculty-profile"))
        self.job = JobListing.objects.get(pk=self.job.pk)
        self.assertEqual(self.job.job_title, 'Principal Developer')
    
    def test_faculty_can_delete_own_job(self):
        self.client.force_login(self.faculty1)
        job_id = self.job.pk
        response = self.client.post(reverse("delete-job-listing", kwargs={"job_id": job_id}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("faculty-profile"))
        self.assertFalse(JobListing.objects.filter(id=job_id).exists())


class SavedStudentsWorkflowTests(TestCase):
    """Test faculty save/unsave students workflow."""
    
    def setUp(self):
        from dashboard.models import SavedStudent
        self.faculty = Faculty.objects.create_user(
            username="faculty3000@westminster.ac.uk",
            password="StrongPass123!",
            first_name="Marcus",
            phone_number="07000000040",
            professor_of="Business BSc Honours",
            campus="Regent Campus",
        )
        self.student = Student.objects.create_user(
            username="w1832700",
            password="StrongPass123!",
            first_name="Alex",
            phone_number="07000000041",
            current_course="Business BSc Honours",
            campus="Regent Campus",
            current_year="Level 6",
        )
        self.faculty_profile = getattr(self.faculty, 'profile')
        self.student_portfolio = getattr(self.student, 'portfolio')
    
    def test_faculty_can_save_student(self):
        from dashboard.models import SavedStudent
        self.client.force_login(self.faculty)
        response = self.client.post(reverse("save-student", kwargs={"student_id": self.student.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            SavedStudent.objects.filter(
                faculty_profile=self.faculty_profile,
                student_portfolio=self.student_portfolio
            ).exists()
        )
    
    def test_faculty_can_unsave_student(self):
        from dashboard.models import SavedStudent
        SavedStudent.objects.create(
            faculty_profile=self.faculty_profile,
            student_portfolio=self.student_portfolio,
            notes="Good candidate"
        )
        self.client.force_login(self.faculty)
        response = self.client.post(reverse("save-student", kwargs={"student_id": self.student.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            SavedStudent.objects.filter(
                faculty_profile=self.faculty_profile,
                student_portfolio=self.student_portfolio
            ).exists()
        )
    
    def test_saved_student_unique_constraint(self):
        from dashboard.models import SavedStudent
        SavedStudent.objects.create(
            faculty_profile=self.faculty_profile,
            student_portfolio=self.student_portfolio,
        )
        with self.assertRaises(Exception):
            SavedStudent.objects.create(
                faculty_profile=self.faculty_profile,
                student_portfolio=self.student_portfolio,
            )


class InterviewSchedulingTests(TestCase):
    """Test interview scheduling workflow and constraints."""
    
    def setUp(self):
        from dashboard.models import Interview
        from datetime import date, time, timedelta
        self.faculty = Faculty.objects.create_user(
            username="faculty4000@westminster.ac.uk",
            password="StrongPass123!",
            first_name="Sarah",
            phone_number="07000000050",
            professor_of="Computer Science BSc Honours",
            campus="Cavendish Campus",
        )
        self.student = Student.objects.create_user(
            username="w1832800",
            password="StrongPass123!",
            first_name="Jamie",
            phone_number="07000000051",
            current_course="Computer Science BSc Honours",
            campus="Cavendish Campus",
            current_year="Level 6",
        )
        self.faculty_profile = getattr(self.faculty, 'profile')
        self.student_portfolio = getattr(self.student, 'portfolio')
        self.job = JobListing.objects.create(
            profile=self.faculty_profile,
            job_title="Data Engineer",
            location="London",
            required_skills_and_tools="Python, SQL, Apache Spark",
            description="Data engineering role",
        )
        self.application = JobApplication.objects.create(
            student_portfolio=self.student_portfolio,
            job_listing=self.job,
            status=JobApplication.STATUS_UNDER_REVIEW,
        )
    
    def test_interview_updates_application_status_to_interview(self):
        from dashboard.models import Interview
        from datetime import date, timedelta
        self.client.force_login(self.faculty)
        interview_date = (date.today() + timedelta(days=7)).isoformat()
        self.client.post(
            reverse("schedule-interview"),
            data={
                'job_listing': self.job.pk,
                'student_portfolio': self.student_portfolio.pk,
                'interview_type': Interview.INTERVIEW_TYPE_PHONE,
                'scheduled_date': interview_date,
                'scheduled_time': "14:00",
            }
        )
        self.application = JobApplication.objects.get(pk=self.application.pk)
        self.assertEqual(self.application.status, JobApplication.STATUS_INTERVIEW)
    
    def test_interview_sends_notification_to_student(self):
        from dashboard.models import Interview
        from datetime import date, timedelta
        self.client.force_login(self.faculty)
        interview_date = (date.today() + timedelta(days=7)).isoformat()
        self.client.post(
            reverse("schedule-interview"),
            data={
                'job_listing': self.job.pk,
                'student_portfolio': self.student_portfolio.pk,
                'interview_type': Interview.INTERVIEW_TYPE_IN_PERSON,
                'scheduled_date': interview_date,
                'scheduled_time': "11:00",
                'location': 'London Office, Regent Campus',
            }
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.student,
                kind=Notification.KIND_INTERVIEW,
                title="Interview scheduled"
            ).exists()
        )


class UniquePhoneNumberConstraintTests(TestCase):
    """Test unique phone number constraints on Student and Faculty models."""
    
    def test_cannot_create_two_students_with_same_phone_number(self):
        Student.objects.create_user(
            username="w1832900",
            password="StrongPass123!",
            first_name="Chris",
            phone_number="07000000060",
            current_course="Computer Science BSc Honours",
            campus="Cavendish Campus",
            current_year="Level 5",
        )
        with self.assertRaises(Exception):
            Student.objects.create_user(
                username="w1832901",
                password="StrongPass123!",
                first_name="Jordan",
                phone_number="07000000060",
                current_course="Computer Science BSc Honours",
                campus="Cavendish Campus",
                current_year="Level 5",
            )
    
    def test_cannot_create_two_faculty_with_same_phone_number(self):
        Faculty.objects.create_user(
            username="faculty5000@westminster.ac.uk",
            password="StrongPass123!",
            first_name="Dr. Smith",
            phone_number="07000000070",
            professor_of="Computer Science BSc Honours",
            campus="Cavendish Campus",
        )
        with self.assertRaises(Exception):
            Faculty.objects.create_user(
                username="faculty5001@westminster.ac.uk",
                password="StrongPass123!",
                first_name="Dr. Jones",
                phone_number="07000000070",
                professor_of="Business BSc Honours",
                campus="Regent Campus",
            )


class StatusTransitionValidationTests(TestCase):
    """Test application status transition rules and constraints."""
    
    def setUp(self):
        self.faculty = Faculty.objects.create_user(
            username="faculty7000@westminster.ac.uk",
            password="StrongPass123!",
            first_name="Dr. Brown",
            phone_number="07000000090",
            professor_of="Computer Science BSc Honours",
            campus="Cavendish Campus",
        )
        self.student = Student.objects.create_user(
            username="w1833100",
            password="StrongPass123!",
            first_name="Morgan",
            phone_number="07000000091",
            current_course="Computer Science BSc Honours",
            campus="Cavendish Campus",
            current_year="Level 6",
        )
        self.faculty_profile = getattr(self.faculty, 'profile')
        self.student_portfolio = getattr(self.student, 'portfolio')
        self.job = JobListing.objects.create(
            profile=self.faculty_profile,
            job_title="ML Engineer",
            location="Remote",
            required_skills_and_tools="Python, TensorFlow, PyTorch",
            description="Machine Learning role",
        )
    
    def test_application_status_transitions_are_recorded(self):
        application = JobApplication.objects.create(
            student_portfolio=self.student_portfolio,
            job_listing=self.job,
            status=JobApplication.STATUS_PENDING,
        )
        application.status = JobApplication.STATUS_UNDER_REVIEW
        application.save()
        application = JobApplication.objects.get(pk=application.pk)
        self.assertEqual(application.status, JobApplication.STATUS_UNDER_REVIEW)
        
        application.status = JobApplication.STATUS_INTERVIEW
        application.save()
        application = JobApplication.objects.get(pk=application.pk)
        self.assertEqual(application.status, JobApplication.STATUS_INTERVIEW)
        
        application.status = JobApplication.STATUS_OFFER
        application.save()
        application = JobApplication.objects.get(pk=application.pk)
        self.assertEqual(application.status, JobApplication.STATUS_OFFER)
    
    def test_application_rejection_at_any_stage(self):
        application = JobApplication.objects.create(
            student_portfolio=self.student_portfolio,
            job_listing=self.job,
            status=JobApplication.STATUS_UNDER_REVIEW,
        )
        application.status = JobApplication.STATUS_NOT_SELECTED
        application.save()
        self.assertEqual(application.status, JobApplication.STATUS_NOT_SELECTED)

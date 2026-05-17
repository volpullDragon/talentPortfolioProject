from datetime import datetime

from typing import cast

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from userManagement.forms import FacultyRegisterForm, StudentRegisterForm
from userManagement.models import Faculty, Message, Notification, Portfolio, Student


class StudentRegisterFormTests(TestCase):
    def test_clean_methods_lowercase_username_and_email(self):
        form = StudentRegisterForm(
            data={
                "username": "W1832388",
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "JANE.DOE@WESTMINSTER.AC.UK",
                "phone_number": "07111111111",
                "current_course": "Computer Science BSc Honours",
                "campus": "Cavendish Campus",
                "current_year": "Level 5",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["username"], "w1832388")
        self.assertEqual(form.cleaned_data["email"], "jane.doe@westminster.ac.uk")


class FacultyRegisterFormTests(TestCase):
    def test_professor_of_uses_westminster_course_datalist(self):
        form = FacultyRegisterForm()
        widget = form.fields["professor_of"].widget

        self.assertEqual(widget.attrs.get("list"), "westminster-course-list")
        self.assertEqual(widget.attrs.get("data-course-source"), "/static/westminster_courses.json")
        self.assertEqual(widget.attrs.get("autocomplete"), "off")

    def test_campus_is_choice_field_with_expected_options(self):
        form = FacultyRegisterForm()
        campus_choices = list(form.fields["campus"].choices)

        self.assertIn(("", "Select your campus"), campus_choices)
        self.assertIn(("Cavendish Campus", "Cavendish Campus"), campus_choices)
        self.assertIn(("Harrow Campus", "Harrow Campus"), campus_choices)


class RegistrationViewTests(TestCase):
    def test_student_register_redirects_when_authenticated(self):
        student = Student.objects.create_user(
            username="student-login",
            password="StrongPass123!",
            phone_number="07000000001",
            current_course="Computer Science BSc Honours",
            campus="Cavendish Campus",
            current_year="Level 5",
        )
        self.client.force_login(student)

        response = self.client.get(reverse("student-register"))

        self.assertRedirects(response, "/")

    def test_faculty_register_redirects_when_authenticated(self):
        faculty = Faculty.objects.create_user(
            username="faculty-login@westminster.ac.uk",
            password="StrongPass123!",
            phone_number="07000000002",
            professor_of="Computer Science BSc Honours",
            campus="Regent Campus",
        )
        self.client.force_login(faculty)

        response = self.client.get(reverse("faculty-register"))

        self.assertRedirects(response, "/")

    def test_faculty_register_post_creates_faculty_and_redirects(self):
        response = self.client.post(
            reverse("faculty-register"),
            data={
                "username": "PROF.TEST@WESTMINSTER.AC.UK",
                "first_name": "Prof",
                "last_name": "Tester",
                "phone_number": "07000000003",
                "professor_of": "Data Science MSc",
                "campus": "Marylebone Campus",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, "/")
        self.assertTrue(Faculty.objects.filter(username="prof.test@westminster.ac.uk").exists())


class PortfolioModelTests(TestCase):
    def test_what_i_bring_items_splits_and_trims_non_empty_lines(self):
        student = Student.objects.create_user(
            username="w1832399",
            password="StrongPass123!",
            phone_number="07000000004",
            current_course="Computer Science BSc Honours",
            campus="Cavendish Campus",
            current_year="Level 6",
        )
        portfolio = getattr(student, "portfolio")
        portfolio.what_I_bring = "  Teamwork  \n\nProblem solving\n  Communication\n"
        portfolio.save(update_fields=["what_I_bring"])

        self.assertEqual(
            portfolio.what_i_bring_items(),
            ["Teamwork", "Problem solving", "Communication"],
        )


class MessageAndNotificationModelTests(TestCase):
    def setUp(self):
        self.sender = Student.objects.create_user(
            username="w1832400",
            password="StrongPass123!",
            phone_number="07000000005",
            current_course="Computer Science BSc Honours",
            campus="Cavendish Campus",
            current_year="Level 5",
        )
        self.recipient = Student.objects.create_user(
            username="w1832401",
            password="StrongPass123!",
            phone_number="07000000006",
            current_course="Computer Science BSc Honours",
            campus="Harrow Campus",
            current_year="Level 5",
        )

    def test_message_mark_as_read_sets_flags_and_timestamp(self):
        msg = Message.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            subject="Hi",
            content="Hello there",
        )

        self.assertFalse(msg.is_read)
        self.assertIsNone(msg.read_at)

        msg.mark_as_read()
        msg = Message.objects.get(pk=msg.pk)

        self.assertTrue(msg.is_read)
        self.assertIsNotNone(msg.read_at)
        self.assertTrue(cast(datetime, msg.read_at) <= timezone.now())

    def test_notification_mark_as_read_sets_flags_and_timestamp(self):
        note = Notification.objects.create(
            user=self.recipient,
            kind=Notification.KIND_SYSTEM,
            title="System update",
            body="Testing notification read state",
        )

        self.assertFalse(note.is_read)
        self.assertIsNone(note.read_at)

        note.mark_as_read()
        note = Notification.objects.get(pk=note.pk)

        self.assertTrue(note.is_read)
        self.assertIsNotNone(note.read_at)
        self.assertTrue(cast(datetime, note.read_at) <= timezone.now())


class MessagingViewTests(TestCase):
    def setUp(self):
        self.user_a = Student.objects.create_user(
            username="w1832500",
            password="StrongPass123!",
            first_name="Alex",
            phone_number="07000000011",
            current_course="Computer Science BSc Honours",
            campus="Cavendish Campus",
            current_year="Level 5",
        )
        self.user_b = Student.objects.create_user(
            username="w1832501",
            password="StrongPass123!",
            first_name="Blake",
            phone_number="07000000012",
            current_course="Computer Science BSc Honours",
            campus="Harrow Campus",
            current_year="Level 6",
        )
        self.user_c = Student.objects.create_user(
            username="w1832502",
            password="StrongPass123!",
            first_name="Casey",
            phone_number="07000000013",
            current_course="Data Science MSc",
            campus="Regent Campus",
            current_year="Level 7",
        )

    def test_conversation_detail_marks_incoming_messages_as_read(self):
        incoming = Message.objects.create(
            sender=self.user_b,
            recipient=self.user_a,
            subject="Question",
            content="Can we connect?",
        )

        self.client.force_login(self.user_a)
        response = self.client.get(reverse("conversation-detail", kwargs={"user_id": self.user_b.pk}))

        self.assertEqual(response.status_code, 200)
        incoming = Message.objects.get(pk=incoming.pk)
        self.assertTrue(incoming.is_read)
        self.assertIsNotNone(incoming.read_at)

    def test_conversation_post_creates_message_and_notification(self):
        self.client.force_login(self.user_a)

        response = self.client.post(
            reverse("conversation-detail", kwargs={"user_id": self.user_b.pk}),
            data={"subject": "Hello", "content": "Nice to meet you"},
        )

        self.assertRedirects(response, reverse("conversation-detail", kwargs={"user_id": self.user_b.pk}))
        self.assertTrue(
            Message.objects.filter(
                sender=self.user_a,
                recipient=self.user_b,
                subject="Hello",
                content="Nice to meet you",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.user_b,
                kind=Notification.KIND_MESSAGE,
                title="New message",
            ).exists()
        )

    def test_delete_message_blocks_non_participant(self):
        msg = Message.objects.create(
            sender=self.user_a,
            recipient=self.user_b,
            subject="Private",
            content="Not for others",
        )

        self.client.force_login(self.user_c)
        response = self.client.post(reverse("message-delete", kwargs={"message_id": msg.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("messaging-home"))
        self.assertTrue(Message.objects.filter(id=msg.pk).exists())

    def test_mark_all_notifications_read_only_marks_current_user(self):
        own_unread = Notification.objects.create(
            user=self.user_a,
            kind=Notification.KIND_SYSTEM,
            title="Own",
            body="Own notification",
        )
        other_unread = Notification.objects.create(
            user=self.user_b,
            kind=Notification.KIND_SYSTEM,
            title="Other",
            body="Other notification",
        )

        self.client.force_login(self.user_a)
        response = self.client.get(reverse("notifications-read-all"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("notifications-list"))
        own_unread = Notification.objects.get(pk=own_unread.pk)
        other_unread = Notification.objects.get(pk=other_unread.pk)
        self.assertTrue(own_unread.is_read)
        self.assertFalse(other_unread.is_read)

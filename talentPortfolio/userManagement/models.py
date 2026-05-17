"""User and messaging models."""
from django.db import models
from django.contrib.auth.models import User, BaseUserManager, AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib import admin
from django.utils import timezone



class Student(User):
    """Student account model."""
    class_type      = models.CharField(max_length=20, choices=[('student', 'Student'), ('faculty', 'Faculty')], default='Student')
    phone_number    = models.CharField(max_length=11, unique=True)
    current_course  = models.CharField(max_length=100)
    campus          = models.CharField(max_length=100)
    current_year    = models.CharField(max_length=100, default="What Course Year Are You In?")
    
    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        """Return a readable student name."""
        return f" {self.first_name} {self.last_name} {self.username}"


class Portfolio(models.Model):
    """Student portfolio model."""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='portfolio')
    about_me = models.TextField(blank=True, null=True, default="Bio")
    what_I_bring = models.TextField(blank=True, default="")
    email_notifications = models.BooleanField(default=True)
    job_alerts = models.BooleanField(default=True)
    application_updates = models.BooleanField(default=True)
    # Additional preference fields.

    def what_i_bring_items(self):
        """Return non-empty bullet entries from what_I_bring (one per line)."""
        return [line.strip() for line in (self.what_I_bring or "").splitlines() if line.strip()]

    def __str__(self):
        """Return a readable portfolio name."""
        return f"{self.student.class_type} {self.student.first_name} {self.student.last_name} Portfolio"




# Faculty account model
class Faculty(User):
    class_type      = models.CharField(max_length=20, choices=[('student', 'Student'), ('faculty', 'Faculty')], default='Faculty')
    phone_number    = models.CharField(max_length=11, unique=True)
    professor_of    = models.CharField(max_length=100)
    campus          = models.CharField(max_length=100)    
    class Meta:
        verbose_name = "Faculty"
        verbose_name_plural = "Faculty Members"
    def __str__(self):
        return f" {self.first_name} {self.last_name} {self.username}"


class Profile(models.Model):
    faculty = models.OneToOneField(Faculty, on_delete=models.CASCADE, related_name='profile')
    bio     = models.TextField(blank=True, null=True, default="Bio")
    # Additional preference fields.
    def __str__(self):
        return f"{self.faculty.first_name} {self.faculty.last_name} Profile"



class Message(models.Model):
    """Direct message exchanged between two users."""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'sent_at']),
            models.Index(fields=['sender', 'recipient', 'sent_at']),
        ]

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username}"


class Notification(models.Model):
    """Persistent in-app notification for activity updates."""
    KIND_MESSAGE = 'message'
    KIND_JOB_POSTED = 'job_posted'
    KIND_APPLICATION = 'application'
    KIND_APPLICATION_STATUS = 'application_status'
    KIND_INTERVIEW = 'interview'
    KIND_SYSTEM = 'system'

    KIND_CHOICES = [
        (KIND_MESSAGE, 'Message'),
        (KIND_JOB_POSTED, 'Job Posted'),
        (KIND_APPLICATION, 'Application Submitted'),
        (KIND_APPLICATION_STATUS, 'Application Status'),
        (KIND_INTERVIEW, 'Interview'),
        (KIND_SYSTEM, 'System'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=30, choices=KIND_CHOICES, default=KIND_SYSTEM)
    title = models.CharField(max_length=120)
    body = models.TextField(blank=True)
    related_url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
        ]

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def __str__(self):
        return f"{self.user.username} - {self.title}"

"""Admin registrations for user management models."""
from django.contrib import admin
from .models import Student, Portfolio, Faculty, Profile, Message, Notification




@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    # Fields shown in admin.
    fields =('class_type', 'username', 'first_name', 'last_name', 'email', 'phone_number', 'current_course', 'campus', 'current_year')
    

 
@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    # Fields shown in admin.
    fields = ('student', 'about_me', 'what_I_bring')


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    # Fields shown in admin.
    fields =('class_type', 'username', 'first_name', 'last_name', 'phone_number', 'professor_of', 'campus')



@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # Fields shown in admin.
    fields = ('faculty', 'bio')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    fields = ('sender', 'recipient', 'subject', 'content', 'sent_at', 'is_read', 'read_at')
    readonly_fields = ('sent_at', 'read_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    fields = ('user', 'kind', 'title', 'body', 'related_url', 'created_at', 'is_read', 'read_at')
    readonly_fields = ('created_at', 'read_at')

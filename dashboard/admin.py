from django.contrib import admin
from .models import Project, FieldOfExpertise, Picture, Video, Files, JobListing, SavedStudent, Interview

@admin.register(FieldOfExpertise)
class FieldOfExpertiseAdmin(admin.ModelAdmin):
    # Fields shown in admin.
    list_display = ('__str__', 'is_featured')
    list_editable = ('is_featured',)
    fields = ('portfolio','field_of_expertise', 'skills', 'level_of_confidence')
 

@admin.register(Project) 
class ProjectAdmin(admin.ModelAdmin):
    # Fields shown in admin.
    fields = ('field_of_expertise' ,'project_title', 'project_summary', 'what_i_learnd', 'skills_demonstrated', 'tech_n_tools_used', 'git_link')

@admin.register(Picture)
class PictureAdmin(admin.ModelAdmin):
    # Fields shown in admin.
    fields = ('project', 'pictureUpload')

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    # Fields shown in admin.
    fields = ('project', 'videoUpload')

@admin.register(Files)
class FileAdmin(admin.ModelAdmin):
    # Fields shown in admin.
    fields = ('project', 'fileUpload')


@admin.register(JobListing)
class JobsAdmin(admin.ModelAdmin):
    # Fields shown in admin.
    fields = ('profile', 'job_title', 'location', 'required_skills_and_tools', 'description', 'salary', 'application_deadline')

@admin.register(SavedStudent)
class SavedStudentAdmin(admin.ModelAdmin):
    list_display = ('student_portfolio', 'faculty_profile', 'saved_at')
    search_fields = ('student_portfolio__student__first_name', 'student_portfolio__student__last_name', 'faculty_profile__faculty__first_name')
    list_filter = ('saved_at',)
    readonly_fields = ('saved_at',)


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('job_listing', 'student_portfolio', 'scheduled_date', 'scheduled_time', 'interview_type')
    search_fields = ('job_listing__job_title', 'student_portfolio__student__first_name')
    list_filter = ('interview_type', 'scheduled_date')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'scheduled_date'

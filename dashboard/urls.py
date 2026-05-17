from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard-home'),
    path('field-of-expertise/add/', views.add_field_of_expertise, name='add-field-of-expertise'),
    path('field-of-expertise/', views.see_field_of_expertise, name='see_field_of_expertise'),

    path('field/<int:field_id>/projects/', views.see_field_projects, name='see-field-projects'),
    path('field/<int:field_id>/delete/', views.delete_field_of_expertise, name='delete-field-of-expertise'),
    path('project/add/<int:field_id>/', views.add_project, name='add-project'),
    path('project/<int:project_id>/', views.see_project_files, name='see-project-files'),
    path('project/<int:project_id>/delete/', views.delete_project, name='delete-project'),
    path('faculty/student/<int:student_id>/field/<int:field_id>/projects/', views.faculty_student_field_projects, name='faculty-student-field-projects'),
    path('faculty/student/<int:student_id>/project/<int:project_id>/', views.faculty_student_project_files, name='faculty-student-project-files'),

    path('job-listing/add/', views.create_job_listing, name='create-job-listing'),
    path('job-listing/', views.see_job_listings, name='see-job-listings'),
    path('job/<int:job_id>/', views.job_detail, name='job-detail'),
    path('job/<int:job_id>/apply/', views.apply_to_job, name='apply-to-job'),
    path('job/<int:job_id>/save/', views.toggle_save_job, name='toggle-save-job'),
    path('student/applications/', views.student_applications_page, name='student-applications'),
    path('student/interviews/', views.student_interviews_page, name='student-interviews'),
    path('student/saved-jobs/', views.student_saved_jobs_page, name='student-saved-jobs'),
    path('student/job-search/', views.student_job_search_page, name='student-job-search'),
    path('student/application/<int:application_id>/accept-offer/', views.accept_application_offer, name='accept-application-offer'),
    path('job/<int:job_id>/edit/', views.edit_job_listing, name='edit-job-listing'),
    path('job/<int:job_id>/delete/', views.delete_job_listing, name='delete-job-listing'),
    path('job/<int:job_id>/manage/', views.faculty_job_detail, name='faculty-job-detail'),
    path('student/<int:student_id>/invite/', views.invite_student, name='invite-student'),

    # Media upload URLs
    path('project/<int:project_id>/upload-media/', views.upload_project_media, name='upload-project-media'),
    path('file-preview/<int:file_id>/', views.preview_media_file, name='preview-media-file'),
    path('delete-media/<str:file_type>/<int:file_id>/', views.delete_media_file, name='delete-media-file'),


    path('toggle-field-featured/', views.toggle_field_featured, name='toggle-field-featured'),
    # Faculty Dashboard Pages
    path('faculty/create-job/', views.create_job_listing_page, name='create-job'),
    path('faculty/saved-students/', views.saved_students_page, name='saved-students'),
    path('faculty/student-search/', views.faculty_student_search_page, name='faculty-student-search'),
    path('faculty/applicant-tracking/', views.applicant_tracking_page, name='applicant-tracking'),
    path('faculty/interview-schedule/', views.interview_schedule_page, name='interview-schedule'),
    path('faculty/application/<int:application_id>/status/', views.update_application_status, name='update-application-status'),
    path('faculty/application/<int:application_id>/delete/', views.delete_application, name='delete-application'),
    path('faculty/save-student/<int:student_id>/', views.save_student, name='save-student'),
    path('faculty/schedule-interview/', views.schedule_interview, name='schedule-interview'),
]
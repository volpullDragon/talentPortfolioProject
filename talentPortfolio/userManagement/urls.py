from django.urls import include, path
from . import views
from .views import home, StudentRegisterView, portfolio, portfolioSettings, profile, profileSettings, FacultyRegisterView  # Import the view here
from django.contrib.auth import views as auth_views
urlpatterns =  [
    path('', views.home, name="home"),
    
    path('student-register/', StudentRegisterView.as_view(), name="student-register"),
    
    
    path('faculty-register/', FacultyRegisterView.as_view(), name="faculty-register"),
  

    path('logout/', auth_views.LogoutView.as_view(template_name='student/logout.html'),
                                                    name='logout'),
    
    path('portfolio/', portfolio, name='users-portfolio'),
    path('portfolio/student/<int:student_id>/', views.faculty_view_student_portfolio, name='faculty-view-student-portfolio'),

    path('portfolio-settings/', portfolioSettings, name='users-portfolio-settings'),

    path('profile/', profile, name='faculty-profile'),

    path('profile-settings/', profileSettings, name='faculty-profile-settings'),

    path('messages/', views.messaging_home, name='messaging-home'),
    path('messages/conversation/<int:user_id>/', views.conversation_detail, name='conversation-detail'),
    path('messages/conversation/<int:user_id>/delete-old/', views.delete_old_messages, name='conversation-delete-old'),
    path('messages/delete/<int:message_id>/', views.delete_message, name='message-delete'),

    path('notifications/', views.notifications_list, name='notifications-list'),
    path('notifications/read/<int:notification_id>/', views.mark_notification_read, name='notification-read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='notifications-read-all'),
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name='notification-delete'),
    path('notifications/delete-old/', views.delete_old_notifications, name='notifications-delete-old'),
]
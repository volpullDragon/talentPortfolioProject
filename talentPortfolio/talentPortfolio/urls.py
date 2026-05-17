"""Urls module."""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from userManagement.views import CustomLoginView, ResetPasswordView, ChangePasswordView
from userManagement.forms import LoginForm
from django.contrib.staticfiles.storage import staticfiles_storage


urlpatterns = [
        path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.svg'), permanent=False)),
        path('admin/', admin.site.urls),
        path('', include('userManagement.urls')),
        path('dashboard/', include('dashboard.urls')),
        path('login/', CustomLoginView.as_view(redirect_authenticated_user=True, template_name='student/login.html', authentication_form=LoginForm), name='login'),
        path('faculty-login/', CustomLoginView.as_view(redirect_authenticated_user=True, template_name='faculty/login.html', authentication_form=LoginForm), name='faculty-login'),
        path('logout/', auth_views.LogoutView.as_view(template_name='student/logout.html'), name='logout'),
        path('password-reset/', ResetPasswordView.as_view(), name='password_reset'),
        path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='student/password_reset_confirm.html'), name='password_reset_confirm'),
        path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='student/password_reset_complete.html'), name='password_reset_complete'),
        path('password-change/', ChangePasswordView.as_view(), name='password_change'),



    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

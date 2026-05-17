from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
import re
from .forms import StudentRegisterForm, FacultyRegisterForm, LoginForm, UpdateStudentUserForm, UpdatePortfolioForm, UpdateProfileForm, UpdateFacultyUserForm, MessageComposeForm
from dashboard.models import FieldOfExpertise, JobListing
from .models import Message, Notification, Student, Portfolio


# User-facing views.

def home(request):
    return render(request, 'home/home.html', {})


class StudentRegisterView(View):
    """Register student users."""
    form_class = StudentRegisterForm
    initial = {'key': 'value'}
    template_name = 'student/register.html'

    def dispatch(self, request, *args, **kwargs):
        """Redirect logged-in users away from registration."""
        # Redirect logged-in users.
        if request.user.is_authenticated:
            return redirect(to='/')

        # Continue normal request handling.
        return super(StudentRegisterView, self).dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        """Show the student registration form."""
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}')

            return redirect(to='/')

        return render(request, self.template_name, {'form': form})




class CustomLoginView(LoginView):
    form_class = LoginForm

    def get_success_url(self):
        """Redirect users after login."""
        user = self.request.user
        
        # Student redirect.
        if hasattr(user, 'student'):
            return '/dashboard/'  # Student dashboard.
        
        # Faculty redirect.
        if hasattr(user, 'faculty'):
            return '/dashboard/'  # Faculty dashboard.
            
        # Default redirect.
        return '/'

    """def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')

        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        return super(CustomLoginView, self).form_valid(form)"""
    
    



class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = 'student/password_reset.html'
    email_template_name = 'student/password_reset_email.html'
    subject_template_name = 'student/password_reset_subject'
    success_message = "We've emailed you instructions for re-setting your password, " \
                      "if an account exists with the email you entered. You should receive them shortly." \
                      " If you don't receive an email, " \
                      "please make sure you've entered the address you registered with, and check your spam folder."
    success_url = reverse_lazy('home')


@login_required
def portfolioSettings(request):
    student = getattr(request.user, 'student', None)
    if student is None:
        messages.error(request, 'Student profile not found.')
        return redirect('dashboard-home')

    portfolio = getattr(student, 'portfolio', None)
    if portfolio is None:
        messages.error(request, 'Portfolio not found.')
        return redirect('dashboard-home')

    if request.method == 'POST' and 'profile_submit' in request.POST:
        course_name = request.POST.get('course', '').strip()
        campus_name = request.POST.get('campus', '').strip()

        update_fields = []
        if course_name != student.current_course:
            student.current_course = course_name
            update_fields.append('current_course')
        if campus_name != student.campus:
            student.campus = campus_name
            update_fields.append('campus')

        if update_fields:
            student.save(update_fields=update_fields)
            messages.success(request, 'Your profile changes were saved successfully')
        else:
            messages.info(request, 'No profile changes were detected')

        return redirect(to='users-portfolio-settings')

    if request.method == 'POST':
        user_form = UpdateStudentUserForm(request.POST, instance=student)
        portfolio_form = UpdatePortfolioForm(request.POST, instance=portfolio)

        if user_form.is_valid() and portfolio_form.is_valid():
            user_form.save()
            portfolio_form.save()
            messages.success(request, 'Your portfolio was updated successfully')
            return redirect(to='users-portfolio-settings')
    else:
        user_form = UpdateStudentUserForm(instance=student)
        portfolio_form = UpdatePortfolioForm(instance=portfolio)

    return render(request, 'student/portfolio_settings.html', {'user_form': user_form, 'portfolio_form': portfolio_form})





class FacultyRegisterView(View):
    
    form_class = FacultyRegisterForm
    initial = {'key': 'value'}
    template_name = 'faculty/register.html'

    def dispatch(self, request, *args, **kwargs):
        
        # Redirect logged-in users.
        if request.user.is_authenticated:
            return redirect(to='/')

        # Continue normal request handling.
        return super(FacultyRegisterView, self).dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}')

            return redirect(to='/')

        return render(request, self.template_name, {'form': form})



@login_required
def profile(request):
    faculty = getattr(request.user, 'faculty', None)
    faculty_profile = getattr(faculty, 'profile', None)
    if faculty is None or faculty_profile is None:
        messages.error(request, 'Faculty profile not found.')
        return redirect('dashboard-home')

    if request.method == 'POST' and 'faculty_about_submit' in request.POST:
        about_text = request.POST.get('about_me', '').strip()
        word_count = len(about_text.split())
        if word_count > 500:
            messages.error(request, 'About section cannot exceed 500 words.')
            return redirect(to='faculty-profile')

        faculty_profile.bio = about_text
        faculty_profile.save(update_fields=['bio'])
        messages.success(request, 'About section updated successfully.')
        return redirect(to='faculty-profile')

    if request.method == 'POST':
        user_form = UpdateFacultyUserForm(request.POST, instance=faculty)
        profile_form = UpdateProfileForm(request.POST, instance=faculty_profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile is updated successfully')
            return redirect(to='faculty-profile')
    else:
        user_form = UpdateFacultyUserForm(instance=faculty)
        profile_form = UpdateProfileForm(instance=faculty_profile)

    # Load this faculty user's job listings.
    try:
        jobs = JobListing.objects.filter(profile=faculty_profile).order_by('-posted_date', '-id')
        print(f"Found {jobs.count()} job listings for user {request.user}")
    except Exception as e:
        print(f"Error getting jobs: {e}")
        jobs = []

    # Add jobs to the template context.
    return render(request, 'faculty/profile.html', {
        'user_form': user_form, 
        'profile_form': profile_form,
        'jobs': jobs
    })



@login_required
def profileSettings(request):
    faculty_user = getattr(request.user, 'faculty', None)
    faculty_profile = getattr(faculty_user, 'profile', None)
    if faculty_user is None or faculty_profile is None:
        messages.error(request, 'Faculty profile not found.')
        return redirect('dashboard-home')

    if request.method == 'POST' and 'password_submit' in request.POST:
        password_form = PasswordChangeForm(request.user, request.POST)
        user_form = UpdateFacultyUserForm(instance=faculty_user)
        profile_form = UpdateProfileForm(instance=faculty_profile)

        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was updated successfully')
            return redirect(to='faculty-profile-settings')

        messages.error(request, 'Please fix the password errors below')
        return render(
            request,
            'faculty/profile_settings.html',
            {'user_form': user_form, 'profile_form': profile_form, 'password_form': password_form},
        )

    if request.method == 'POST':
        user_form = UpdateFacultyUserForm(request.POST, instance=faculty_user)
        profile_form = UpdateProfileForm(request.POST, instance=faculty_profile)
        password_form = PasswordChangeForm(request.user)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile is updated successfully')
            return redirect(to='faculty-profile-settings')
    else:
        user_form = UpdateFacultyUserForm(instance=faculty_user)
        profile_form = UpdateProfileForm(instance=faculty_profile)
        password_form = PasswordChangeForm(request.user)

    return render(
        request,
        'faculty/profile_settings.html',
        {'user_form': user_form, 'profile_form': profile_form, 'password_form': password_form},
    )


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'faculty/change_password.html'
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy('home')

# Portfolio helper functions.
def _slugify_field_name(field_name):
    value = (field_name or '').strip().lower()
    slug = re.sub(r'[^a-z0-9]+', '-', value).strip('-')
    return slug or 'default-cs'


def _field_image_path(field_name):
    slug = _slugify_field_name(field_name)
    relative = f'portfolio_images/field_images/{slug}.svg'
    absolute = Path(__file__).resolve().parents[1] / 'static' / 'portfolio_images' / 'field_images' / f'{slug}.svg'

    if absolute.exists():
        return relative

    return 'portfolio_images/field_images/default-cs.svg'


def _portfolio_redirect_with_scroll(request):
    scroll_value = (request.POST.get("scroll_position") or "").strip()
    if scroll_value.isdigit():
        return redirect(reverse("users-portfolio") + "?scroll=" + scroll_value)
    return redirect(to="users-portfolio")


def _split_skill_toolbase_entries(raw_text):
    entries = []
    seen = set()

    for segment in re.split(r"[,;\n|]+|\s+/\s+", raw_text or ""):
        value = (segment or '').strip()
        if not value:
            continue

        normalized = value.lower()
        if normalized in {
            'skills',
            'confidence level',
            'skills demonstrated',
            'technologies and tools used',
            'no tools listed',
        }:
            continue

        if normalized not in seen:
            entries.append(value)
            seen.add(normalized)

    return entries


def _build_skill_toolbase_groups(portfolio, fields):
    groups = []

    for field in fields:
        title = (getattr(field, 'field_of_expertise', '') or '').strip() or 'General Skills'
        items = []
        seen = set()

        for raw in [getattr(field, 'skills', '')]:
            for entry in _split_skill_toolbase_entries(raw):
                key = entry.lower()
                if key in seen:
                    continue
                seen.add(key)
                items.append(entry)

        for project in field.projects.all():
            for raw in [
                getattr(project, 'skills_demonstrated', ''),
                getattr(project, 'tech_n_tools_used', ''),
            ]:
                for entry in _split_skill_toolbase_entries(raw):
                    key = entry.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    items.append(entry)

        if items:
            groups.append({'title': title, 'items': items})

    if not groups:
        fallback_items = _split_skill_toolbase_entries('\n'.join(portfolio.what_i_bring_items()))
        if fallback_items:
            groups.append({'title': 'Core Strengths', 'items': fallback_items})

    return groups


@login_required
def portfolio(request):
    student = getattr(request.user, 'student', None)
    if student is None:
        messages.error(request, 'Student profile not found.')
        return redirect('dashboard-home')

    portfolio = getattr(student, 'portfolio', None)
    if portfolio is None:
        messages.error(request, 'Portfolio not found.')
        return redirect('dashboard-home')

    if request.method == 'POST' and 'about_me_submit' in request.POST:
        about_me_text = request.POST.get('about_me', '').strip()
        word_count = len(about_me_text.split())
        if word_count > 500:
            messages.error(request, 'About Me cannot exceed 500 words.')
            return _portfolio_redirect_with_scroll(request)
        portfolio.about_me = about_me_text
        portfolio.save(update_fields=['about_me'])
        messages.success(request, 'About Me updated successfully.')
        return _portfolio_redirect_with_scroll(request)

    if request.method == 'POST' and 'what_i_bring_remove' in request.POST:
        remove_entry = request.POST.get('what_i_bring_remove', '').strip()
        current_entries = portfolio.what_i_bring_items()
        updated_entries = [entry for entry in current_entries if entry != remove_entry]

        if len(updated_entries) != len(current_entries):
            portfolio.what_I_bring = '\n'.join(updated_entries)
            portfolio.save(update_fields=['what_I_bring'])
            messages.success(request, 'Strength removed successfully.')
        else:
            messages.info(request, 'Strength entry was not found.')
        return _portfolio_redirect_with_scroll(request)

    if request.method == 'POST' and 'what_i_bring_submit' in request.POST:
        strength_entry = request.POST.get('strength_entry', '').strip()
        if not strength_entry:
            messages.error(request, 'Please enter a strength before submitting.')
            return _portfolio_redirect_with_scroll(request)
        if len(strength_entry) > 80:
            messages.error(request, 'Strength entries must be 80 characters or fewer.')
            return _portfolio_redirect_with_scroll(request)

        current_entries = portfolio.what_i_bring_items()
        if strength_entry not in current_entries:
            current_entries.append(strength_entry)
            portfolio.what_I_bring = '\n'.join(current_entries)
            portfolio.save(update_fields=['what_I_bring'])
            messages.success(request, 'Strength added successfully.')
        else:
            messages.info(request, 'That strength is already in your list.')
        return _portfolio_redirect_with_scroll(request)

    fields = list(FieldOfExpertise.objects.filter(portfolio=portfolio).order_by('-is_featured', 'id').prefetch_related('projects'))
    for field in fields:
        setattr(field, 'image_path', _field_image_path(field.field_of_expertise))

    for field in fields:
        setattr(field, 'view_url', reverse('see-field-projects', kwargs={'field_id': field.pk}))

    skill_toolbase_groups = _build_skill_toolbase_groups(portfolio, fields)

    return render(request, 'student/portfolio.html', {
        'fields': fields,
        'portfolio': portfolio,
        'portfolio_user': getattr(request.user, 'student', None),
        'skill_toolbase_groups': skill_toolbase_groups,
        'can_edit': True,
    })


@login_required
def faculty_view_student_portfolio(request, student_id):
    if not hasattr(request.user, 'faculty'):
        messages.error(request, 'Access denied. Faculty only.')
        return redirect('dashboard-home')

    student = get_object_or_404(Student, id=student_id)
    portfolio = get_object_or_404(Portfolio, student=student)

    fields = list(
        FieldOfExpertise.objects
        .filter(portfolio=portfolio)
        .order_by('-is_featured', 'id')
        .prefetch_related('projects')
    )

    for field in fields:
        setattr(field, 'image_path', _field_image_path(field.field_of_expertise))
        setattr(field, 'view_url', reverse('faculty-student-field-projects', kwargs={'student_id': student.pk, 'field_id': field.pk}))

    return render(request, 'faculty_dashboard/student_portfolio_view.html', {
        'fields': fields,
        'portfolio': portfolio,
        'portfolio_user': student,
    })


@login_required
def messaging_home(request):
    all_messages = Message.objects.filter(Q(sender=request.user) | Q(recipient=request.user)).select_related('sender', 'recipient')
    conversations = {}
    for message in all_messages:
        other_user = message.recipient if message.sender.pk == request.user.pk else message.sender
        if other_user.is_staff or other_user.is_superuser:
            continue
        if other_user.pk not in conversations:
            unread_count = Message.objects.filter(sender=other_user, recipient=request.user, is_read=False).count()
            conversations[other_user.pk] = {'user': other_user, 'latest_message': message, 'unread_count': unread_count}
    available_users = User.objects.filter(is_staff=False, is_superuser=False).exclude(pk=request.user.pk).order_by('first_name', 'last_name', 'username')
    return render(request, 'messaging/inbox.html', {'conversations': list(conversations.values()), 'available_users': available_users})


@login_required
def conversation_detail(request, user_id):
    other_user = get_object_or_404(User, id=user_id, is_staff=False, is_superuser=False)
    thread_messages = Message.objects.filter(Q(sender=request.user, recipient=other_user) | Q(sender=other_user, recipient=request.user)).select_related('sender', 'recipient').order_by('sent_at')
    Message.objects.filter(sender=other_user, recipient=request.user, is_read=False).update(is_read=True, read_at=timezone.now())
    if request.method == 'POST':
        form = MessageComposeForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.recipient = other_user
            message.save()
            Notification.objects.create(user=other_user, kind=Notification.KIND_MESSAGE, title='New message', body=f'You have a new message from {request.user.get_full_name() or request.user.username}.', related_url=reverse_lazy('conversation-detail', kwargs={'user_id': request.user.pk}))
            return redirect('conversation-detail', user_id=other_user.pk)
    else:
        form = MessageComposeForm()
    return render(request, 'messaging/conversation.html', {'other_user': other_user, 'thread_messages': thread_messages, 'form': form})


@login_required
@require_POST
def delete_message(request, message_id):
    message_obj = get_object_or_404(
        Message.objects.select_related('sender', 'recipient'),
        id=message_id,
    )

    if request.user.pk not in {message_obj.sender.pk, message_obj.recipient.pk}:
        messages.error(request, 'You are not allowed to delete this message.')
        return redirect('messaging-home')

    other_user_id = message_obj.recipient.pk if message_obj.sender.pk == request.user.pk else message_obj.sender.pk
    message_obj.delete()
    messages.success(request, 'Message deleted successfully.')
    return redirect('conversation-detail', user_id=other_user_id)


@login_required
@require_POST
def delete_old_messages(request, user_id):
    other_user = get_object_or_404(User, id=user_id, is_staff=False, is_superuser=False)

    deleted_count, _ = Message.objects.filter(
        Q(sender=request.user, recipient=other_user) | Q(sender=other_user, recipient=request.user),
        is_read=True,
    ).delete()

    if deleted_count:
        messages.success(request, f'Deleted {deleted_count} old message(s).')
    else:
        messages.info(request, 'No old messages to delete in this conversation.')

    return redirect('conversation-detail', user_id=other_user.pk)


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()

    target = (notification.related_url or '').strip()
    if target and url_has_allowed_host_and_scheme(
        url=target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(target)

    if target.startswith('/'):
        return redirect(target)

    return redirect('notifications-list')


@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True, read_at=timezone.now())
    return redirect('notifications-list')


@login_required
@require_POST
def delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    messages.success(request, 'Notification deleted successfully.')
    return redirect('notifications-list')


@login_required
@require_POST
def delete_old_notifications(request):
    deleted_count, _ = Notification.objects.filter(user=request.user, is_read=True).delete()

    if deleted_count:
        messages.success(request, f'Deleted {deleted_count} old notification(s).')
    else:
        messages.info(request, 'No old notifications to delete.')

    return redirect('notifications-list')

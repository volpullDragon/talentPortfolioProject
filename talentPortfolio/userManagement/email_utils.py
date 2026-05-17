import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _from_email():
    """Prefer explicit DEFAULT_FROM_EMAIL but fall back to SMTP user."""
    return getattr(settings, 'DEFAULT_FROM_EMAIL', None) or settings.EMAIL_HOST_USER


def send_welcome_email(student_user):
    """Send a simple welcome email after student registration."""
    if not student_user.email:
        return False

    subject = 'Welcome to Talented Bank'
    message = render_to_string(
        'student/emails/welcome_email.txt',
        {
            'full_name': student_user.get_full_name() or student_user.username,
            'username': student_user.username,
        },
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=_from_email(),
            recipient_list=[student_user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception('Failed to send welcome email to %s', student_user.email)
        return False


def send_message_alert_email(message_obj):
    """Send an email alert for new direct messages when preferences allow."""
    recipient = message_obj.recipient
    if not recipient.email:
        return False

    # Respect student email preferences when available.
    try:
        student = getattr(recipient, 'student', None)
        portfolio = getattr(student, 'portfolio', None)
        if portfolio is not None and portfolio.email_notifications is False:
            return False
    except Exception:
        logger.exception('Failed preference check for recipient id=%s', recipient.id)
        return False

    subject = f'New message from {message_obj.sender.get_full_name() or message_obj.sender.username}'
    message = render_to_string(
        'student/emails/message_alert_email.txt',
        {
            'sender_name': message_obj.sender.get_full_name() or message_obj.sender.username,
            'recipient_name': recipient.get_full_name() or recipient.username,
            'subject': message_obj.subject,
            'body': message_obj.content,
        },
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=_from_email(),
            recipient_list=[recipient.email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception('Failed to send message alert email to %s', recipient.email)
        return False

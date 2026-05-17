"""Context Processors module."""
from .models import Message, Notification


def notification_counts(request):
    if not request.user.is_authenticated:
        return {
            'unread_messages_count': 0,
            'unread_notifications_count': 0,
            'recent_unread_messages': [],
            'recent_unread_notifications': [],
        }

    recent_unread_messages = (
        Message.objects
        .filter(recipient=request.user, is_read=False)
        .select_related('sender')
        .order_by('-sent_at')[:5]
    )
    recent_unread_notifications = (
        Notification.objects
        .filter(user=request.user, is_read=False)
        .order_by('-created_at')[:5]
    )

    return {
        'unread_messages_count': Message.objects.filter(recipient=request.user, is_read=False).count(),
        'unread_notifications_count': Notification.objects.filter(user=request.user, is_read=False).count(),
        'recent_unread_messages': recent_unread_messages,
        'recent_unread_notifications': recent_unread_notifications,
    }

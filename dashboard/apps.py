"""Apps module."""
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        # Register signal handlers for media cleanup.
        import dashboard.signals  # noqa: F401

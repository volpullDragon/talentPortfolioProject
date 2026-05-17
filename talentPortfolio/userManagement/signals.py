from django.db.models.signals import post_save
from userManagement.models import Student, Faculty
from django.dispatch import receiver

from .models import Portfolio, Profile


# Student signals
# Create a portfolio when a student account is created.
@receiver(post_save, sender=Student)
def create_portfolio_for_student(sender, instance, created, **kwargs):
    """Create a portfolio for new student accounts."""
    if created and not hasattr(instance, 'portfolio'):
        Portfolio.objects.create(student=instance)

@receiver(post_save, sender=Student)
def save_portfolio(sender, instance, **kwargs):
    instance.portfolio.save()




# Faculty signals
# Create a profile when a faculty account is created.
@receiver(post_save, sender=Faculty)
def create_profile_for_faculty(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(faculty=instance)

@receiver(post_save, sender=Faculty)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()
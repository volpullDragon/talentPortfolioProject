from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from userManagement.models import Portfolio, Profile
import os
import re
from decimal import Decimal
from pathlib import Path


def validate_max_500_words(value):
    words = re.findall(r"\b\w+\b", value or "")
    if len(words) > 500:
        raise ValidationError("Please keep this to 500 words or fewer.")


class FieldOfExpertise(models.Model):
    """Field of expertise model."""
    portfolio               = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='fields_of_expertise')
    field_of_expertise      = models.CharField(max_length=1000, blank=True, null=True, default="Field of Expertise")
    skills                  = models.CharField(max_length=1000, blank=True, null=True, default="Skills")
    level_of_confidence     = models.CharField(max_length=1000, blank=True, null=True, default="Confidence Level")
    is_featured             = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["portfolio", "id"]
    
    def __str__(self):
        """Return a readable field name."""
        student             = getattr(self.portfolio.student, 'student', None)
        first_name          = getattr(student, 'first_name', 'Unknown')
        last_name           = getattr(student, 'last_name', 'Unknown')
        return f"{first_name} {last_name}'s Field of Expertise: {self.field_of_expertise}"
    
    def get_field_image_url(self):
        """Return a relative static path for this field image with fallback."""
        value = (self.field_of_expertise or '').strip().lower()
        aliases = {
            'datascience': 'data-science',
            'data science': 'data-science',
        }
        base_value = aliases.get(value, value)
        slug = re.sub(r'[^a-z0-9]+', '-', base_value).strip('-') or 'software-engineering'
        relative = f'portfolio_images/field_images/{slug}.svg'
        absolute = Path(__file__).resolve().parents[1] / 'static' / 'portfolio_images' / 'field_images' / f'{slug}.svg'
        if absolute.exists():
            return relative
        return 'portfolio_images/field_images/software-engineering.svg'


class Project(models.Model):
    """Project model."""
    
    field_of_expertise      = models.ForeignKey(FieldOfExpertise, on_delete=models.CASCADE, related_name='projects')
    project_title           = models.CharField(max_length=1000, blank=True, null=True)
    project_summary         = models.TextField(blank=True, null=True, default="Project Description", validators=[validate_max_500_words])
    what_i_learnd           = models.TextField(blank=True, null=True, default="What I Learned", validators=[validate_max_500_words])
    skills_demonstrated     = models.TextField(blank=True, null=True, default="Skills Demonstrated")
    tech_n_tools_used       = models.TextField(blank=True, null=True, default="Technologies and Tools Used")
    git_link                = models.URLField(max_length=1000, blank=True, null=True)
    def __str__(self):
        """Return a readable project name."""
        student             = getattr(self.field_of_expertise.portfolio.student, 'student', None)
        first_name          = getattr(student, 'first_name', 'Unknown')
        last_name           = getattr(student, 'last_name', 'Unknown')
        return f"{first_name} {last_name}'s {self.project_title}"


# Media upload paths.

def upload_to_pictures(instance, filename): 
    try:
        user        = instance.project.field_of_expertise.portfolio.student
        username    = getattr(user, 'username', 'unknown_user')
        return f'pictures/{username}/{filename}'
    except (AttributeError, TypeError):
        return f'pictures/unknown_user/{filename}'

def upload_to_videos(instance, filename):
    try:
        user        = instance.project.field_of_expertise.portfolio.student
        username    = getattr(user, 'username', 'unknown_user')
        return f'videos/{username}/{filename}'
    except (AttributeError, TypeError):
        return f'videos/unknown_user/{filename}'

def upload_to_files(instance, filename):
    try:
        user        = instance.project.field_of_expertise.portfolio.student
        username    = getattr(user, 'username', 'unknown_user')
        return f'files/{username}/{filename}'
    except (AttributeError, TypeError):
        return f'files/unknown_user/{filename}'


class Picture(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='pics')
    image = models.ImageField(
        upload_to   = upload_to_pictures,
        validators  = [FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif'])],
        null        = True,  
        blank       = True, 
        help_text   = "Upload image files (JPG, PNG, GIF). Max size: 10MB"
    )
    caption         = models.CharField(max_length=200, blank=True)
    uploaded_at     = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering    = ['-uploaded_at']
    
    def __str__(self):
        return f"Picture for {self.project.project_title}"
    
    def delete(self, *args, **kwargs):
        """Delete the file from disk."""
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        super().delete(*args, **kwargs)



class Video(models.Model):
    project         = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='videos')
    video           = models.FileField(
        upload_to   = upload_to_videos,
        validators  = [FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'wmv'])],
        null        = True,  
        blank       = True, 
        help_text   = "Upload video files (MP4, AVI, MOV). Max size: 1000MB"
    )
    title           = models.CharField(max_length=200, blank=True)
    description     = models.TextField(blank=True)
    uploaded_at     = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering    = ['-uploaded_at']
    
    def __str__(self):
        return f"Video for {self.project.project_title}"
    
    def delete(self, *args, **kwargs):
        """Delete the file from disk."""
        if self.video:
            if os.path.isfile(self.video.path):
                os.remove(self.video.path)
        super().delete(*args, **kwargs)



class Files(models.Model):
    project         = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    file            = models.FileField(
        upload_to   = upload_to_files,
        validators  =[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'txt', 'zip', 'xlsx'])],
        null        =True,  # Allow empty uploads.
        blank       =True, 
        help_text   ="Upload documents (PDF, DOC, DOCX, TXT, ZIP, XLSX). Max size: 10MB"
    )
    file_name       = models.CharField(max_length=200, blank=True)
    description     = models.TextField(blank=True)
    uploaded_at     = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering    = ['-uploaded_at']
        verbose_name_plural = "Files"
    
    def __str__(self):
        return f"File for {self.project.project_title}"

    @property
    def extension(self):
        if not self.file:
            return ''
        return os.path.splitext(self.file.name)[1].lower()

    @property
    def is_pdf(self):
        return self.extension == '.pdf'

    @property
    def is_text(self):
        return self.extension == '.txt'

    @property
    def is_word(self):
        return self.extension in {'.doc', '.docx'}
    
    def save(self, *args, **kwargs):
        """Set file_name from uploaded file."""
        if not self.file_name and self.file:
            self.file_name = os.path.basename(self.file.name)
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Delete the file from disk."""
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)




class JobListing(models.Model):
    profile                 = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='JobListing')
    job_title               = models.CharField(max_length=1000, blank=True, null=True, default="Job Title")
    posted_date             = models.DateField(auto_now_add=True)
    location                = models.CharField(max_length=1000, blank=True, null=True, default="Job Location")    
    required_skills_and_tools = models.CharField(max_length=1000, blank=True, null=True, default="Skills")
    level_of_confidence = models.CharField(max_length=1500, blank=True, null=True, default="")
    description             = models.TextField(blank=True, null=True, default="Job Description")
    salary                  = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=Decimal('0.00'))
    application_deadline    = models.DateField(blank=True, null=True, default=None)
    def __str__(self):
        faculty             = getattr(self.profile.faculty, 'faculty', None)
        first_name          = getattr(faculty, 'first_name', 'Unknown')
        last_name           = getattr(faculty, 'last_name', 'Unknown')
        return f"{first_name} {last_name}'s Jobs: {self.job_title}"

class SavedStudent(models.Model):
    """Saved student model."""
    faculty_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='saved_students')
    student_portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='saved_by_faculties')
    saved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('faculty_profile', 'student_portfolio')
        ordering = ['-saved_at']
    
    def __str__(self):
        return f"{self.faculty_profile.faculty.get_full_name()} saved {self.student_portfolio.student.get_full_name()}"


class Interview(models.Model):
    """Interview model."""
    INTERVIEW_TYPE_VIDEO = 'video'
    INTERVIEW_TYPE_PHONE = 'phone'
    INTERVIEW_TYPE_IN_PERSON = 'in_person'
    
    INTERVIEW_TYPE_CHOICES = [
        (INTERVIEW_TYPE_VIDEO, 'Video'),
        (INTERVIEW_TYPE_PHONE, 'Phone'),
        (INTERVIEW_TYPE_IN_PERSON, 'In Person'),
    ]
    
    job_listing = models.ForeignKey(JobListing, on_delete=models.CASCADE, related_name='interviews')
    student_portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='interviews')
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPE_CHOICES, default=INTERVIEW_TYPE_VIDEO)
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    location = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    video_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['scheduled_date', 'scheduled_time']
    
    def __str__(self):
        return f"Interview for {self.student_portfolio.student.get_full_name()} - {self.job_listing.job_title}"


class SavedJob(models.Model):
    """Student bookmark for a job listing."""
    student_portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='saved_jobs')
    job_listing = models.ForeignKey(JobListing, on_delete=models.CASCADE, related_name='saved_by_students')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student_portfolio', 'job_listing')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.student_portfolio.student.username} saved {self.job_listing.job_title}"


class JobApplication(models.Model):
    """Student application to a job listing."""
    STATUS_PENDING = 'pending'
    STATUS_UNDER_REVIEW = 'under_review'
    STATUS_INTERVIEW = 'interview'
    STATUS_OFFER = 'offer'
    STATUS_ACCEPTED = 'accepted'
    STATUS_NOT_SELECTED = 'not_selected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_UNDER_REVIEW, 'Under Review'),
        (STATUS_INTERVIEW, 'Interview Scheduled'),
        (STATUS_OFFER, 'Offer Received'),
        (STATUS_ACCEPTED, 'Offer Accepted'),
        (STATUS_NOT_SELECTED, 'Not Selected'),
    ]

    student_portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='job_applications')
    job_listing = models.ForeignKey(JobListing, on_delete=models.CASCADE, related_name='job_applications')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True, default='')
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student_portfolio', 'job_listing')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.student_portfolio.student.username} -> {self.job_listing.job_title} ({self.status})"

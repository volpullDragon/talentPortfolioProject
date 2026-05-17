from pathlib import Path
import json
import os
import re
from typing import cast, Any
from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.datastructures import MultiValueDict
from .models import FieldOfExpertise, Project, Picture, Video, Files, JobListing, SavedStudent, Interview, Portfolio

CONFIDENCE_SCALE_CHOICES = [
        ("Low Confidence", "Low Confidence"),
        ("Developing Confidence", "Developing Confidence"),
        ("Moderate Confidence", "Moderate Confidence"),
        ("High Confidence", "High Confidence"),
        ("Advanced Confidence", "Advanced Confidence"),
]

DEFAULT_COMPUTER_SCIENCE_FIELD_GROUPS = {
        "Programming & Software": [
                "Mobile App Development",
                "Software Engineering",
                "Web Development",
        ],
        "Data & AI": [
                "Artificial Intelligence",
                "Data Science",
                "Machine Learning",
        ],
        "Systems & Infrastructure": [
                "Cloud Computing",
                "Database Systems",
                "Operating Systems",
        ],
        "Security & Networks": [
                "Computer Networks",
                "Cyber Security",
        ],
}


def _normalize_fields(values):
    return sorted({str(item).strip() for item in values if str(item).strip()}, key=str.lower)


def _slugify_course_name(course_name):
    """Convert a course name to a JSON filename slug.
    
    Example: 'Computer Science BSc Honours' -> 'computer_science_bsc_honours'
    """
    if not course_name:
        return ""
    slug = course_name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug


def _build_grouped_choices(group_map, course_name="Computer Science"):
    """Build grouped field choices for a given course."""
    choices: list[tuple[str, Any]] = [("", f"Select a {course_name} field")]

    for group_name in sorted(group_map.keys(), key=str.lower):
        normalized = _normalize_fields(group_map.get(group_name, []))
        if not normalized:
            continue
        choices.append((group_name, [(value, value) for value in normalized]))

    return choices


def _build_course_not_found_choices(course_name):
    """Build placeholder choices when course is not found."""
    return [("", f"Course not found: {course_name}")]


def _load_course_field_choices(course_name=None):
    """Load field choices for a specific course.
    
    Args:
        course_name: Name of the course (e.g., 'Computer Science BSc Honours')
                    If None or empty, defaults to Computer Science
    
    Returns:
        List of choice tuples for the ChoiceField widget
    """
    if not course_name or course_name.strip() == "":
        course_name = "Computer Science"
    
    # Try to load course-specific file
    slug = _slugify_course_name(course_name)
    if slug:
        filename = f"{slug}_fields.json"
        source_path = Path(__file__).resolve().parents[1] / "static" / "course_fields.json" / filename
        
        try:
            payload = json.loads(source_path.read_text(encoding="utf-8"))

            if isinstance(payload, dict):
                groups = payload.get("groups")
                if isinstance(groups, dict):
                    cleaned_groups = {
                        str(group_name).strip(): values
                        for group_name, values in groups.items()
                        if str(group_name).strip() and isinstance(values, list)
                    }
                    if cleaned_groups:
                        return _build_grouped_choices(cleaned_groups, course_name)

                fields = payload.get("fields")
                if isinstance(fields, list):
                    normalized = _normalize_fields(fields)
                    if normalized:
                        return _build_grouped_choices({course_name: normalized}, course_name)

        except (OSError, ValueError, TypeError):
            pass

    # If course was explicitly provided but not found, show "Course not found"
    if course_name != "Computer Science":
        return _build_course_not_found_choices(course_name)
    
    # Only for Computer Science, try to load the CS default file
    source_path = Path(__file__).resolve().parents[1] / "static" / "course_fields.json" / "computer_science_fields.json"

    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))

        if isinstance(payload, dict):
            groups = payload.get("groups")
            if isinstance(groups, dict):
                cleaned_groups = {
                    str(group_name).strip(): values
                    for group_name, values in groups.items()
                    if str(group_name).strip() and isinstance(values, list)
                }
                if cleaned_groups:
                    return _build_grouped_choices(cleaned_groups, "Computer Science")

            fields = payload.get("fields")
            if isinstance(fields, list):
                normalized = _normalize_fields(fields)
                if normalized:
                    return _build_grouped_choices({"Computer Science": normalized}, "Computer Science")

    except (OSError, ValueError, TypeError):
        pass

    return _build_grouped_choices(DEFAULT_COMPUTER_SCIENCE_FIELD_GROUPS, "Computer Science")


COMPUTER_SCIENCE_FIELD_CHOICES = _load_course_field_choices()

# Student forms.

class FieldOfExpertiseForm(forms.ModelForm):
    field_of_expertise = forms.ChoiceField(
                                 required=True,
                                 choices=COMPUTER_SCIENCE_FIELD_CHOICES,
                                 widget=forms.Select(attrs={
                                     "class": "form-select",
                                 }),
                             )

    level_of_confidence = forms.ChoiceField(
                                 required=True,
                                 choices=CONFIDENCE_SCALE_CHOICES,
                                 widget=forms.Select(attrs={
                                     "class": "form-select",
                                 }),
                             )

    class Meta:
        model = FieldOfExpertise
       
        fields = ['field_of_expertise', 'level_of_confidence', 'is_featured']

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If a student is provided, load course-specific fields
        if student and hasattr(student, 'current_course'):
            course_name = student.current_course
            if course_name and course_name.strip():
                self.fields['field_of_expertise'].choices = _load_course_field_choices(course_name)




class ProjectForm(forms.ModelForm):
    project_title = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your project title', 'class': 'form-control'}),
    )

    project_summary = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'Describe your project, its features, and what you learned...', 'class': 'form-control', 'rows': 5}),
    )

    what_i_learnd = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'Describe what you learned from this project...', 'class': 'form-control', 'rows': 5}),
    )

    skills_demonstrated = forms.CharField(required=True, widget=forms.HiddenInput())
    tech_n_tools_used = forms.CharField(required=False, widget=forms.HiddenInput())
    git_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'placeholder': 'https://github.com/...', 'class': 'form-control'}),
    )

    class Meta:
        model = Project
        fields = ['project_title', 'project_summary', 'what_i_learnd', 'skills_demonstrated', 'tech_n_tools_used', 'git_link']

    @staticmethod
    def _word_count(value):
        return len([word for word in (value or '').strip().split() if word])

    def clean_project_summary(self):
        value = (self.cleaned_data.get('project_summary') or '').strip()
        if self._word_count(value) > 500:
            raise forms.ValidationError('Project description must be 500 words or fewer.')
        return value

    def clean_what_i_learnd(self):
        value = (self.cleaned_data.get('what_i_learnd') or '').strip()
        if self._word_count(value) > 500:
            raise forms.ValidationError('What I learned must be 500 words or fewer.')
        return value

    def clean_skills_demonstrated(self):
        value = (self.cleaned_data.get('skills_demonstrated') or '').strip()
        if not value:
            raise forms.ValidationError('Add at least one skill.')
        return value

    def clean_tech_n_tools_used(self):
        return (self.cleaned_data.get('tech_n_tools_used') or '').strip()

    def clean_git_link(self):
        value = (self.cleaned_data.get('git_link') or '').strip()
        if not value:
            return ''
        if 'github.com/' not in value.lower():
            raise forms.ValidationError('Please enter a valid GitHub repository link.')
        return value


# Media upload forms.

class PictureUploadForm(forms.ModelForm):
    class Meta:
        model = Picture
        fields = ['image', 'caption']
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'caption': forms.TextInput(attrs={'class': 'form-control'}),
        }


class VideoUploadForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ['video', 'title', 'description']
        widgets = {
            'video': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*'
            }),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = Files
        fields = ['file', 'file_name', 'description']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'file_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }



# Multiple file upload helpers.

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result
    

class MediaUploadForm(forms.Form):
    def _uploaded_files(self) -> MultiValueDict[str, UploadedFile]:
        # Use __dict__ to avoid clashing with the form field named "files" in static typing.
        return cast(MultiValueDict[str, UploadedFile], self.__dict__.get('files') or MultiValueDict())

    def _validate_file_group(self, files, allowed_ext, max_mb, label):
        """Validate file type and size."""
        if not files:
            return files
        errors = []
        for f in files:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in allowed_ext:
                errors.append(f"{label} '{f.name}': unsupported extension {ext}")
            if f.size > max_mb * 1024 * 1024:
                errors.append(f"{label} '{f.name}': exceeds {max_mb}MB limit")
        if errors:
            raise forms.ValidationError(errors)
        return files

    images = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'accept': 'image/*',
            'class': 'form-control'
        }),
        help_text='Select multiple images (optional)'
    )
    
    videos = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'accept': 'video/*',
            'class': 'form-control'
        }),
        help_text='Select multiple videos (optional)'
    )
    
    documents = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control'
        }),
        help_text='Select multiple files (optional)'
    )

    def clean_images(self):
        images = self._uploaded_files().getlist('images')
        return self._validate_file_group(images, {'.jpg', '.jpeg', '.png', '.gif'}, 500, 'Image')

    def clean_videos(self):
        videos = self._uploaded_files().getlist('videos')
        return self._validate_file_group(videos, {'.mp4', '.avi', '.mov', '.wmv'}, 1000, 'Video')

    def clean_documents(self):
        docs = self._uploaded_files().getlist('documents')
        return self._validate_file_group(docs, {'.pdf', '.doc', '.docx', '.txt', '.zip', '.xlsx'}, 500, 'Document')


# Job listing form.

class JobListingForm(forms.ModelForm):
    # Form fields.
    job_title = forms.CharField(max_length=100,
                                 required=True,
                                 widget=forms.TextInput(attrs={'placeholder': 'Job Title',
                                                               'class': 'form-control',
                                                               }))
    
    salary = forms.CharField(max_length=100,
                                      required=True,
                                      widget=forms.TextInput(attrs={'placeholder': 'Salary',
                                                           'class': 'form-control',
                                                           }))
    
    location = forms.CharField(max_length=100,
                                 required=True,
                                 widget=forms.TextInput(attrs={'placeholder': 'Location',
                                                               'class': 'form-control',
                                                               }))
    
    required_skills_and_tools = forms.CharField(max_length=100,
                                      required=True,
                                      widget=forms.TextInput(attrs={'placeholder': 'Required Skills and Tools',
                                                           'class': 'form-control',
                                                           }))
    
    level_of_confidence = forms.CharField(max_length=150,
                                      required=False,
                                      widget=forms.TextInput(attrs={'placeholder': 'Level of Confidence',
                                                           'class': 'form-control',
                                                           }))
    
    description = forms.CharField(max_length=100,
                                      required=True,
                                      widget=forms.TextInput(attrs={'placeholder': 'Job Description',
                                                           'class': 'form-control',
                                                           }))
    
    
    
    application_deadline = forms.DateField(widget=forms.DateInput(attrs={'type': 'date',
                                                         'class': 'form-control',
                                                         }))    
    
    class Meta:
        model = JobListing

        fields = [ 'job_title', 'salary', 'location', 'required_skills_and_tools', 'level_of_confidence', 'description', 'application_deadline']

# Saved student and interview forms.
class SavedStudentForm(forms.ModelForm):
    class Meta:
        model = SavedStudent
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add notes about this student...', 'class': 'form-control'}),
        }

class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ['scheduled_date', 'scheduled_time', 'interview_type', 'location', 'description', 'video_link']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'scheduled_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'interview_type': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'placeholder': 'Interview location', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add interview notes...', 'class': 'form-control'}),
            'video_link': forms.URLInput(attrs={'placeholder': 'Video call link (if applicable)', 'class': 'form-control'}),
        }

class InterviewScheduleForm(forms.ModelForm):
    teams_meeting_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'placeholder': 'Teams or video call link', 'class': 'form-control'}),
    )

    class Meta:
        model = Interview
        fields = [
            'job_listing',
            'student_portfolio',
            'interview_type',
            'location',
            'teams_meeting_link',
            'scheduled_date',
            'scheduled_time',
            'description',
        ]
        widgets = {
            'job_listing': forms.Select(attrs={'class': 'form-select'}),
            'student_portfolio': forms.Select(attrs={'class': 'form-select'}),
            'interview_type': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'placeholder': 'Interview location', 'class': 'form-control'}),
            'scheduled_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'scheduled_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add interview notes...', 'class': 'form-control'}),
        }

    def __init__(self, *args, faculty_profile=None, **kwargs):
        super().__init__(*args, **kwargs)

        if faculty_profile is not None:
            cast(forms.ModelChoiceField, self.fields['job_listing']).queryset = JobListing.objects.filter(profile=faculty_profile).order_by('job_title')
            cast(forms.ModelChoiceField, self.fields['student_portfolio']).queryset = Portfolio.objects.select_related('student').order_by('student__first_name', 'student__last_name')

        if 'video_link' in self.initial and 'teams_meeting_link' not in self.initial:
            self.initial['teams_meeting_link'] = self.initial.get('video_link')

    def clean_teams_meeting_link(self):
        return (self.cleaned_data.get('teams_meeting_link') or '').strip()

    def save(self, commit=True):
        interview = super().save(commit=False)
        interview.video_link = self.cleaned_data.get('teams_meeting_link') or None
        if commit:
            interview.save()
        return interview


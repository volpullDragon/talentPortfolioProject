from django import forms
from .models import Student, Portfolio, Faculty, Profile, Message
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
WESTMINSTER_CAMPUS_CHOICES = [
    ('', 'Select your campus'),
    ('Cavendish Campus', 'Cavendish Campus'),
    ('Harrow Campus', 'Harrow Campus'),
    ('Marylebone Campus', 'Marylebone Campus'),
    ('Regent Campus', 'Regent Campus'),
]

STUDY_LEVEL_CHOICES = [
    ('', 'Select level'),
    ('Level 4', 'Level 4'),
    ('Level 5', 'Level 5'),
    ('Level 6', 'Level 6'),
    ('Level 7', 'Level 7'),
    ('Level 8', 'Level 8'),
]


class StudentRegisterForm(UserCreationForm):
    # Form fields.
    username = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'student ID',
                                                             'class': 'form-control',
                                                             }))
    first_name = forms.CharField(max_length=100,
                                 required=True,
                                 widget=forms.TextInput(attrs={'placeholder': 'First Name',
                                                               'class': 'form-control',
                                                               }))
    last_name = forms.CharField(max_length=100,
                                required=True,
                                widget=forms.TextInput(attrs={'placeholder': 'Last Name',
                                                              'class': 'form-control',
                                                              }))
    email = forms.EmailField(max_length=100,
                                    required=True,
                                    widget=forms.TextInput(attrs={'placeholder': 'Student Email',
                                                           'class': 'form-control',
                                                           }))
    phone_number = forms.CharField(max_length=11,
                                      required=True,
                                      widget=forms.TextInput(attrs={'placeholder': 'Phone Number',
                                                           'class': 'form-control',
                                                           }))
    current_course = forms.CharField(max_length=100,
                                    required=True,
                                    widget=forms.TextInput(attrs={'placeholder': 'Search your course...',
                                                              'class': 'form-control dropdown-field',
                                                              'list': 'westminster-course-list',
                                                              'data-course-source': '/static/westminster_courses.json',
                                                              'autocomplete': 'off',
                                                              }))
    campus = forms.ChoiceField(
        choices=WESTMINSTER_CAMPUS_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control select-with-arrow'})
    )
    current_year = forms.ChoiceField(
        choices=STUDY_LEVEL_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control select-with-arrow'})
    )
    password1 = forms.CharField(max_length=50,
                                required=True,
                                widget=forms.PasswordInput(attrs={'placeholder': 'Password',
                                                                  'class': 'form-control',
                                                                  'data-toggle': 'password',
                                                                  'id': 'password',
                                                                  }))
    password2 = forms.CharField(max_length=50,
                                required=True,
                                widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password',
                                                                  'class': 'form-control',
                                                                  'data-toggle': 'password',
                                                                  'id': 'password',
                                                                  }))
    def clean_username(self):
        username = self.cleaned_data['username']
        return username.lower()
    
    def clean_email(self):
        email = self.cleaned_data['email']
        return email.lower()
    
    class Meta:
        model = Student
        # Model and field order.
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'current_course', 'campus', 'current_year', 'password1', 'password2']
# Login form.


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'Username',
                                                             'class': 'form-control',
                                                             }))
    password = forms.CharField(max_length=50,
                               required=True,
                               widget=forms.PasswordInput(attrs={'placeholder': 'Password',
                                                                 'class': 'form-control',
                                                                 'data-toggle': 'password',
                                                                 'id': 'password',
                                                                 'name': 'password',
                                                                 }))
    remember_me = forms.BooleanField(required=False)

    def clean_username(self):
        username = self.cleaned_data['username']
        return username.lower()

    class Meta:
        model = Student
        fields = ['username', 'password', 'remember_me']
        


class UpdateStudentUserForm(forms.ModelForm):
    email = forms.EmailField(required=True,
                             widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Student
        fields = ['email']



class UpdatePortfolioForm(forms.ModelForm):
    about_me = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5})
    )
    what_I_bring = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Add one point per line',
            }
        ),
    )

    class Meta:
        model = Portfolio
        fields = ['about_me', 'what_I_bring']





class FacultyRegisterForm(UserCreationForm):
    # Form fields.
    username = forms.CharField(max_length=100,
                               required=True,
                               widget=forms.TextInput(attrs={'placeholder': 'Faculty Email',
                                                             'class': 'form-control',
                                                             }))
    first_name = forms.CharField(max_length=100,
                                 required=True,
                                 widget=forms.TextInput(attrs={'placeholder': 'First Name',
                                                               'class': 'form-control',
                                                               }))
    last_name = forms.CharField(max_length=100,
                                required=True,
                                widget=forms.TextInput(attrs={'placeholder': 'Last Name',
                                                              'class': 'form-control',
                                                              }))
    phone_number = forms.CharField(max_length=11,
                                      required=True,
                                      widget=forms.TextInput(attrs={'placeholder': 'Phone Number',
                                                           'class': 'form-control',
                                                           }))
    professor_of = forms.CharField(max_length=100,
                                    required=True,
                                    widget=forms.TextInput(attrs={'placeholder': 'Search your course...',
                                                              'class': 'form-control dropdown-field',
                                                              'list': 'westminster-course-list',
                                                              'data-course-source': '/static/westminster_courses.json',
                                                              'autocomplete': 'off',
                                                              }))
    campus = forms.ChoiceField(
        choices=WESTMINSTER_CAMPUS_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control select-with-arrow'})
    )
    password1 = forms.CharField(max_length=50,
                                required=True,
                                widget=forms.PasswordInput(attrs={'placeholder': 'Password',
                                                                  'class': 'form-control',
                                                                  'data-toggle': 'password',
                                                                  'id': 'password',
                                                                  }))
    password2 = forms.CharField(max_length=50,
                                required=True,
                                widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password',
                                                                  'class': 'form-control',
                                                                  'data-toggle': 'password',
                                                                  'id': 'password',
                                                                  }))
    def clean_username(self):
        username = self.cleaned_data['username']
        return username.lower()
    
    class Meta:
        model = Faculty
        # Model and field order.
        fields = ['username', 'first_name', 'last_name', 'phone_number', 'professor_of', 'campus', 'password1', 'password2']


class UpdateFacultyUserForm(forms.ModelForm):
    username = forms.EmailField(required=True,
                             widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Faculty
        fields = ['username']


class UpdateProfileForm(forms.ModelForm):
    bio = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}))

    class Meta:
        model = Profile
        fields = ['bio']



class MessageComposeForm(forms.ModelForm):
    subject = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Subject (optional)', 'class': 'form-control'})
    )
    content = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'Write your message...', 'class': 'form-control', 'rows': 4})
    )

    class Meta:
        model = Message
        fields = ['subject', 'content']

from pathlib import Path
from dotenv import load_dotenv
import os


# SECURITY WARNING: keep the secret key used in production secret!
load_dotenv()  # loads the configs from .env


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = str(os.getenv('SECRET_KEY'))
# This setting defines the secret key for the Django application.
# It is loaded from an environment variable using the python-dotenv package.
# It is crucial to keep this key secret, especially in production environments,
# as it is used for cryptographic signing and should not be shared publicly.

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'userManagement',
    'dashboard',


]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'talentPortfolio.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'userManagement.context_processors.notification_counts',
            ],
        },
    },
]

WSGI_APPLICATION = 'talentPortfolio.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]



# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days in seconds
# This setting defines the age of session cookies in seconds.
# It is set to 30 days (60 seconds * 60 minutes * 24 hours * 30 days).
# This means that the session will expire after 30 days of inactivity.

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# This setting configures the email backend to use SMTP for sending emails.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = str(os.getenv('EMAIL_USER'))
EMAIL_HOST_PASSWORD = str(os.getenv('EMAIL_PASSWORD'))




# Media files (User-uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# https://docs.djangoproject.com/en/5.0/topics/files/

# Maximum file upload size settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024 * 1024  # 10GB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024 * 1024   # 10GB

# Allowed file upload extensions
ALLOWED_UPLOAD_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif', '.svg',  # Images
    '.mp4', '.avi', '.mov', '.wmv', '.flv',   # Videos
    '.pdf', '.doc', '.docx', '.txt', '.zip'   # Documents
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

#login(redirect URL)
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = 'login'
# This setting defines the URL to redirect to after a successful login.

"""
Django settings for the municipal citizen-service assistant.

Configuration comes from environment variables; in development a local .env
file fills them in (see .env.example).
"""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Real environment variables win over .env (load_dotenv doesn't override them).
load_dotenv(BASE_DIR / '.env')


def env_list(name, default):
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY is not set; see .env.example')

DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',  # only for its translated error messages
    'accounts',
    'municipal',
    'chat',
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database: one URL, e.g. postgres://user:password@host:port/name
# pytest-django creates and destroys a separate "test_<name>" database by itself.

DATABASES = {
    'default': dj_database_url.parse(
        os.getenv('DATABASE_URL', 'postgres://muni:muni@localhost:5434/muni'),
        conn_max_age=60,
        conn_health_checks=True,
    )
}


# Users log in with their email and carry a DNI (see accounts/models.py).
# Set before the first migration: swapping the user model later is very hard.

AUTH_USER_MODEL = 'accounts.User'


# REST API

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # API clients send "Authorization: Bearer <token>".
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # Lets you explore the browsable API after logging in to the admin.
        'rest_framework.authentication.SessionAuthentication',
    ],
    # Secure by default: every endpoint needs a logged-in user unless it says otherwise.
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
}

SIMPLE_JWT = {
    # The access token goes with every request and expires soon; the refresh
    # token only gets new access tokens, so the password isn't typed again.
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}


# Claude. The API key isn't read here: the Anthropic SDK takes ANTHROPIC_API_KEY
# from the environment on its own (load_dotenv() above puts .env values there).

ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL') or 'claude-opus-5-5'
# Only for API keys that aren't scoped to a single workspace.
ANTHROPIC_WORKSPACE_ID = os.getenv('ANTHROPIC_WORKSPACE_ID') or None


# Show the chat loop's log lines (tool calls, token usage) in the console.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'simple': {'format': '{levelname} {name}: {message}', 'style': '{'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'}},
    'loggers': {'chat': {'handlers': ['console'], 'level': 'INFO'}},
}

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


# Internationalization: the admin speaks Spanish, and dates are shown in Lima
# time while the database stores them in UTC.

LANGUAGE_CODE = 'es-pe'

TIME_ZONE = 'America/Lima'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

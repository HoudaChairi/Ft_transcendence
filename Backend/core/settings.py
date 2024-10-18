"""
Django settings for core project.

Generated by 'django-admin startproject' using Django 4.2.16.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-e!-e$qj*#i@8s!=rd9=#2cwk99^-nx9#zk7_e^qethq*vwg!$('

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
##
# ALLOWED_HOSTS = ['localhost', '127.0.0.1']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'daphne',
    'django.contrib.staticfiles',
    # New apps
    'core.apps.authentication',
    'core.apps.chat',
    'core.apps.remote_auth',

    # 'core.apps.users',
    'rest_framework',
    # 'rest_framework.authtoken',
    # new for JWT
    'rest_framework_simplejwt',
    # 'rest_framework_simplejwt.token_blacklist', # new 
    # new for Access-Control-Allow-Origin for browser
    'corsheaders',


    ##
    'channels',
     'social_django',
    'django.contrib.sites', 
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # new for browser 
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',

    'social_django.middleware.SocialAuthExceptionMiddleware',
]
AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',  # Enable Google OAuth2
    'django.contrib.auth.backends.ModelBackend',
)

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'transcendence_db',
        'USER': 'postgres_user',
        'PASSWORD': '1337transcendence',
        'HOST': 'postgres',
        'PORT': '5432',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#-------------------------------------------------------------------------#
# new : step 2
AUTH_USER_MODEL = 'authentication.Player' #specify which model Django should use as the user model#

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # new for JWT
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

import datetime

SIMPLE_JWT = {
    'ALGORITHM': 'HS256',  # The default algorithm, should be HS256 or RS256
    'SIGNING_KEY': SECRET_KEY,  # Use your Django secret key or a different one if configured
    'VERIFYING_KEY': None,      # Use if RS256 is used
    'AUTH_HEADER_TYPES': ('Bearer',),
    
    'ACCESS_TOKEN_LIFETIME': datetime.timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': datetime.timedelta(days=1),
    
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
}

# MEDIA_URL = '/media/'
# MEDIA_ROOT = BASE_DIR / 'media'

# To allow all origins  to access your API  from browser
CORS_ALLOW_ALL_ORIGINS = True


## Meriem
ASGI_APPLICATION = 'core.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}   


#google:
import os

# GOOGLE_CLIENT_ID = os.getenv('851881649681-crjcohss2l0bh66tore6s4b6ik695g74.apps.googleusercontent.com')
# GOOGLE_CLIENT_SECRET = os.getenv('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')

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = '851881649681-crjcohss2l0bh66tore6s4b6ik695g74.apps.googleusercontent.com'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = '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'

GOOGLE_REDIRECT_URI = 'https://localhost/api/auth/google/callback/'

# Specify where Django can find your OAuth URLs
SOCIAL_AUTH_URL_NAMESPACE = 'social'

# Add 'django.contrib.sites' for multi-domain support
SITE_ID = 1

# settings.py

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
"""
Django settings for UploadServer project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

from __future__ import absolute_import
# ^^^ The above is required if you want to import from the celery
# library.  If you don't have this then `from celery.schedules import`
# becomes `proj.celery.schedules` in Python 2.x since it allows
# for relative imports by default.
import os
from os import getenv
# Celery settings

BROKER_SERVER = getenv('BROKER_SERVER', '127.0.0.1')
BROKER_PORT = getenv('BROKER_PORT', 5672)
BROKER_VHOST = getenv('BROKER_VHOST', 'Uploader')
BROKER_USER = getenv('BROKER_USER', 'guest')
BROKER_PASS = getenv('BROKER_PASS', 'guest')
BROKER_TRANSPORT = getenv('BROKER_TRANSPORT', 'amqp')
BROKER_URL = '{transport}://{user}:{password}@{server}:{port}/{vhost}'.format(
    transport=BROKER_TRANSPORT,
    user=BROKER_USER,
    password=BROKER_PASS,
    server=BROKER_SERVER,
    port=BROKER_PORT,
    vhost=BROKER_VHOST
)

CELERY_RESULT_BACKEND = getenv('CELERY_BACKEND', 'amqp')

CELERYD_STATE_DB = "celery_worker_state"

#: Only add pickle to this list if your broker is secured
#: from unwanted access (see userguide/security.html)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '_u)@b5#$b7l$z87+0_k_+ux*77kyevk_bf$q7!%w5ff_3%%du#'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ALLOWED_HOSTS = ['*']

# URL of the login page.
LOGIN_URL = '/login/'
# when we log out we want to immediately redirect to the login page
LOGOUT_URL = '/login/'

# login view
LOGIN_VIEW = 'login.html'

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'home',
    'UploadServer',
    'home.templatetags.app_filters',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'UploadServer.urls'

WSGI_APPLICATION = 'UploadServer.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Session stuff
# SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# SESSION_COOKIE_AGE = 3 * 30

# see if this gets rid of sqlite lockup
SESSION_SAVE_EVERY_REQUEST = False
# SESSION_SAVE_EVERY_REQUEST = True

# added to make admin work?
SESSION_COOKIE_SECURE = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

MEDIA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media')
MEDIA_URL = '/media/'

DJANGO_LOG_LEVEL = DEBUG

STATIC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
STATIC_URL = "/static/"

RESOURCES_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources')
RESOURCES_URL = '/resources/'

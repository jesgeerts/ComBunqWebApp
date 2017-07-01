"""
Django settings for BunqWebApp project.

Generated by 'django-admin startproject' using Django 1.10.6.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
import dj_database_url
from ruamel.yaml import YAML
from box import Box
import pathlib
# import raven
# from django.core.urlresolvers import reverse_lazy
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

config_file = pathlib.Path(os.path.join(BASE_DIR, 'BunqWebApp/config.yaml'))
if config_file.is_file():
    config = Box(YAML(typ='safe').load(pathlib.Path(
                                                    os.path.join(BASE_DIR,
                                                                'BunqWebApp/config.yaml'))))  # noqa
else:
    config = None

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!

try:
    SECRET_KEY
except NameError:
    SECRET_FILE = os.path.join(PROJECT_ROOT, 'secret.txt')
    try:
        SECRET_KEY = open(SECRET_FILE).read().strip()
    except IOError:  # pragma: no cover
        try:
            import random
            SECRET_KEY = ''.join([random.SystemRandom().choice(
                'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
                for i in range(50)])
            secret = open(SECRET_FILE, 'w')
            secret.write(SECRET_KEY)
            secret.close()
        except IOError:
            Exception('Please create a %s file with random characters \
            to generate your secret key!' % SECRET_FILE)

if config is not None:
    DEBUG = True if str(config.DEBUG) == 'True' else False
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    DESABLE_LOGGERS = False
    SANDBOX = True if str(config.SANDBOX) == 'True' else False
    ALLOWED_HOSTS = ['*']
    USE_PROXY = True if str(config.USE_PROXY) == 'True' else False
    PROXY_URI = config.PROXY_URI
    TELEGRAM_TOKEN = None if str(config.TELEGRAM_TOKEN) == "None" else config\
                                                                            .TELEGRAM_TOKEN  # noqa

else:
    DEBUG = True
    SANDBOX = True
    DESABLE_LOGGERS = False
    ALLOWED_HOSTS = ['*']
    USE_PROXY = False
    TELEGRAM_TOKEN = None

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


if config is not None and config.DSN is not 'None':
    RAVEN_CONFIG = {
        'dsn': config.DSN if str(config.DSN) != "None" else None,
    }

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'Manager',
    'captcha',
    'simple_history',
    'BunqAPI',
    'raven.contrib.django.raven_compat',
    'filecreator',
    'bunq_bot'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',
    'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',  # noqa
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'BunqWebApp.urls'


LOGGING = {  # NOTE: need to write logg msges. This can be done later :)
    'version': 1,
    'disable_existing_loggers': DESABLE_LOGGERS,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s '
                      '%(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',  # To capture more than ERROR, change to WARNING, INFO, etc.  # noqa
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',  # noqa
            'tags': {'custom-tag': 'x'},
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'BunqWebApp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
# http://www.marinamele.com/taskbuster-django-tutorial/install-and-configure-posgresql-for-django
# pg_ctl -D ./db start

if 'TRAVIS' in os.environ:  # pragma: no cover
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     'travisci',
            'USER':     'postgres',
            'PASSWORD': '',
            'HOST':     'localhost',
            'PORT':     '',
        }
    }
else:  # pragma: no cover
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME':  'khellemun' if config is None else config.DATABASE.NAME,
            'USER': None if config is None else config.DATABASE.USER
        }
    }
    db_from_env = dj_database_url.config()
    DATABASES['default'].update(db_from_env)


# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilari'
        'tyValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidato'
        'r',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidat'
        'or',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValida'
        'tor',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Amsterdam'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static-files')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static'), os.path.join(
    BASE_DIR, 'node_modules')]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
WHITENOISE_ROOT = STATIC_ROOT

# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# MEDIA_URL = '/media/'

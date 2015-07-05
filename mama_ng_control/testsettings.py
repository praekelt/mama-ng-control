from mama_ng_control.settings import *  # flake8: noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'mama_ng_control',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '5432'
    }
}

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'TESTSEKRET'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

VUMI_ACCOUNT_KEY = 'acc-key'
VUMI_CONVERSATION_KEY = 'conv-key'
VUMI_ACCOUNT_TOKEN = 'conv-token'

CONTENTSTORE_AUTH_TOKEN = 'auth_token'
CONTENTSTORE_API_URL = 'http://127.0.0.1:8000/contentstore'

SCHEDULER_URL = 'http://127.0.0.1:8000/mama-ng-scheduler/rest/'
SCHEDULER_USERNAME = 'sc-username'
SCHEDULER_PASSWORD = 'sc-password'

CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_ALWAYS_EAGER = True
BROKER_BACKEND = 'memory'

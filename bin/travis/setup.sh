#!/bin/bash
# pwd is the git repo.
set -e

echo "Making settings/local.py"
cat > airmozilla/settings/local.py <<SETTINGS
from . import base
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'airmozilla',
        'USER': 'travis',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    },
}
HMAC_KEYS = {'some': 'thing'}
SECRET_KEY = 'something'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}

RUN_SELENIUM_TESTS = True
SETTINGS

echo "Installing the node packages"
npm install

echo "Running collectstatic"
python manage.py collectstatic --noinput

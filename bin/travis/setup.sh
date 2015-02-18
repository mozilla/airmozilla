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

# RUN_SELENIUM_TESTS = True
SETTINGS

# The reason the `RUN_SELENIUM_TESTS=True` piece is commented out is because
# the selenium tests have become unpredictably broken in Travis and causing
# many test builds to stall or error out due to the addition of running
# the selenium tests.
# But we don't want to entirely abandon this effort. We just need to figure
# out how to make it more stable. 

#!/bin/sh
# This script makes sure that Jenkins can properly run your tests against your
# codebase.
set -e

DB_HOST="localhost"
DB_USER="hudson"

cd $WORKSPACE
VENV=$WORKSPACE/venv

echo "Starting build on executor $EXECUTOR_NUMBER..."

# Make sure there's no old pyc files around.
find . -name '*.pyc' -exec rm {} \;

if [ ! -d "$VENV/bin" ]; then
  echo "No virtualenv found.  Making one..."
  virtualenv $VENV --no-site-packages
  source $VENV/bin/activate
  pip install --upgrade pip
  pip install coverage
fi

git submodule sync -q
git submodule update --init --recursive

if [ ! -d "$WORKSPACE/vendor" ]; then
    echo "No /vendor... crap."
    exit 1
fi

source $VENV/bin/activate
pip install -q -r requirements/compiled.txt
pip install -q -r requirements/dev.txt

cat > airmozilla/settings/local.py <<SETTINGS
from .base import *

ROOT_URLCONF = 'airmozilla.urls'
LOG_LEVEL = logging.ERROR
# Database name has to be set because of sphinx
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': 'jenkins-services1.dmz.phx1.mozilla.com',
        'NAME': 'airmozillatests',
        'USER': 'airmozilla',
        'PASSWORD': 'airmozillaTests',
    }
}
EMAIL_FROM_ADDRESS = 'any@doesntmatter.com'
SECRET_KEY = 'blablabla'
HMAC_KEYS = {
'2012-06-06': 'anything',
}
from django_sha2 import get_password_hashers
hashers = (#'django_sha2.hashers.BcryptHMACCombinedPasswordVerifier',
#'django_sha2.hashers.SHA512PasswordHasher',
#'django_sha2.hashers.SHA256PasswordHasher',
'django.contrib.auth.hashers.SHA1PasswordHasher',
'django.contrib.auth.hashers.MD5PasswordHasher',
'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher'
)
PASSWORD_HASHERS = get_password_hashers(hashers, HMAC_KEYS)
INSTALLED_APPS += ('django_nose',)
CELERY_ALWAYS_EAGER = True

VIDLY_USER_ID = 'any...'
VIDLY_USER_KEY = '...thing not empty'
EDGECAST_SECURE_KEY = 'anythingheretoo'

MOZILLIANS_API_APPNAME = 'some_app_name'
MOZILLIANS_API_KEY = 'any018273012873019283key'

SETTINGS

echo "Creating database if we need it..."
echo "CREATE DATABASE IF NOT EXISTS ${JOB_NAME}"|mysql -u $DB_USER -h $DB_HOST

echo "Starting tests..."
export FORCE_DB=1
coverage run manage.py test --noinput --with-xunit
coverage xml $(find airmozilla lib -name '*.py')

echo "FIN"

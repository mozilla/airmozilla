"""
These settings will always be overriding for all test runs.
"""

import tempfile

EMAIL_FROM_ADDRESS = 'doesnt@matter.com'

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

MOZILLIANS_API_APPNAME = 'something'
MOZILLIANS_API_BASE = 'https://shouldneveractuallybeused.net'
MOZILLIANS_API_KEY = 'supersecret'

VIDLY_API_URL = 'http://vid.ly.shouldneveractuallybeused.com/api/'

# So that we never accidentally send tweets during tests
TWITTER_ACCESS_TOKEN_SECRET = "test"
TWITTER_CONSUMER_KEY = TWITTER_ACCESS_TOKEN_SECRET
TWITTER_CONSUMER_SECRET = TWITTER_CONSUMER_KEY
TWITTER_ACCESS_TOKEN = TWITTER_CONSUMER_KEY

TWEETER_BACKEND = None

URL_TRANSFORM_PASSWORDS = {
    'bla': 'bla',
}

BITLY_ACCESS_TOKEN = '123456789'
BITLY_URL = 'https://bitly-mock/v3/shorten'

# don't accidentally send anything to sentry whilst running tests
RAVEN_CONFIG = {}
SENTRY_DSN = None

SITE_URL = 'http://localhost:8000'

AWS_ACCESS_KEY_ID = AWS_SECRET_ACCESS_KEY = 'something'

EDGECAST_SECURE_KEY = 'soemthing'

AKAMAI_SECURE_KEY = 'something'

BROWSERID_AUDIENCES = ['http://testserver']

MEDIA_ROOT = tempfile.mkdtemp(prefix='testmedia')

SCRAPE_CREDENTIALS = {}

LOG_SEARCHES = True

TWITTER_USERNAME = 'airmozilla'

MEDIA_URL = '/media/'
STATIC_URL = '/static/'

VIDLY_BASE_URL = 'https://vid.ly.example'
VIDLY_USER_ID = 'any...'
VIDLY_USER_KEY = '...thing not empty'
EDGECAST_SECURE_KEY = 'anythingheretoo'

ALLOWED_BID = (
    'mozilla.com',
)

# Use memcached only for session storage
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# deliberately set so tests never actually accidentally use it
AUTOCOMPETER_URL = 'https://autocompeter.example/v1'
AUTOCOMPETER_DOMAIN = ''

# make sure these are definitely off
GOD_MODE = False
BROWSERID_DISABLED = False


# Don't actually use celery in tests
CELERY_ALWAYS_EAGER = True

SCREENCAPTURES_NO_PICTURES = 5  # faster

# Deliberately disabled since reducing the size of PNGs
# slows down the tests significantly and we have deliberate
# tests that re-enables it.
PNGQUANT_LOCATION = None

# Elastic search test indexing
ELASTICSEARCH_INDEX = 'test-events'

# For using the google API
YOUTUBE_API_KEY = 'doesnthavetobesomethingreal'

# Make sure pipeline is enabled so it does not collectstatic on every test
PIPELINE_ENABLED = True

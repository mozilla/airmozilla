# These settings will always be overriding for all test runs

EMAIL_FROM_ADDRESS = 'doesnt@matter.com'

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

MOZILLIANS_API_BASE = 'https://shouldneveractuallybeused.net'
MOZILLIANS_API_KEY = 'supersecret'

VIDLY_API_URL = 'http://vid.ly.shouldneveractuallybeused.com/api/'

# So that we never accidentally send tweets during tests
TWITTER_CONSUMER_KEY = \
TWITTER_CONSUMER_SECRET = \
TWITTER_ACCESS_TOKEN = \
TWITTER_ACCESS_TOKEN_SECRET = "test"
TWEETER_BACKEND = None


URL_TRANSFORM_PASSWORDS = {
    'bla': 'bla',
}

BITLY_ACCESS_TOKEN = '123456789'

# don't accidentally send anything to sentry whilst running tests
RAVEN_CONFIG = {}
SENTRY_DSN = None

SITE_URL = 'http://localhost:8000'

AWS_ACCESS_KEY_ID = AWS_SECRET_ACCESS_KEY = 'something'
#S3_UPLOAD_BUCKET = 'air-mozilla-uploads'

EDGECAST_SECURE_KEY = 'soemthing'

BROWSERID_AUDIENCES = ['http://testserver']

import tempfile
MEDIA_ROOT = tempfile.mkdtemp(prefix='testmedia')

SCRAPE_CREDENTIALS = {}

LOG_SEARCHES = True

TWITTER_USERNAME = 'airmozilla'

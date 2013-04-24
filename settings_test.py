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

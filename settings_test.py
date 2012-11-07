# These settings will always be overriding for all test runs

EMAIL_FROM_ADDRESS = 'doesnt@matter.com'

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

MOZILLIANS_API_BASE = 'https://shouldneveractuallybeused.net'
MOZILLIANS_API_KEY = 'supersecret'

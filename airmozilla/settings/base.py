# This is your project's main settings file that can be committed to your
# repo. If you need to override a setting locally, use settings_local.py

from funfactory.settings_base import *

# Name of the top-level module where you put all your apps.
# If you did not install Playdoh with the funfactory installer script
# you may need to edit this value. See the docs about installing from a
# clone.
PROJECT_MODULE = 'airmozilla'


# Defines the views served for root URLs.
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

INSTALLED_APPS = (
    'funfactory',
    'compressor',
    'django_browserid',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'commonware.response.cookies',
    'session_csrf',

    # Application base, containing global templates.
    '%s.base' % PROJECT_MODULE,
    '%s.main' % PROJECT_MODULE,
    '%s.auth' % PROJECT_MODULE,
    '%s.manage' % PROJECT_MODULE,
    '%s.suggest' % PROJECT_MODULE,
    '%s.search' % PROJECT_MODULE,
    '%s.comments' % PROJECT_MODULE,
    '%s.uploads' % PROJECT_MODULE,
    '%s.starred' % PROJECT_MODULE,
    '%s.subtitles' % PROJECT_MODULE,
    '%s.surveys' % PROJECT_MODULE,
    '%s.roku' % PROJECT_MODULE,
    '%s.cronlogger' % PROJECT_MODULE,
    '%s.webrtc' % PROJECT_MODULE,
    '%s.staticpages' % PROJECT_MODULE,
    '%s.new' % PROJECT_MODULE,
    '%s.popcorn' % PROJECT_MODULE,

    'djcelery',
    'kombu.transport.django',
    'bootstrapform',
    'sorl.thumbnail',
    'south',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.flatpages',  # this can be deleted later
    'cronjobs',
    'raven.contrib.django.raven_compat',
    'django_nose',  # deliberately making this the last one
)

# Necessary so that test-utils doesn't try to execute some deprecated
# functionality on the database connection.
SQL_RESET_SEQUENCES = False

# We can use the simplest hasher because we never store usable passwords
# thanks to Persona.
PASSWORD_HASHERS = ('django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',)

# And this must be set according to funfactory but its value isn't important
HMAC_KEYS = {'any': 'thing'}

# our session storage is all memcache so using it instead of FallbackStorage
# which uses CookieStorage by default so sessions are better
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# Because Jinja2 is the default template loader, add any non-Jinja templated
# apps here:
JINGO_EXCLUDE_APPS = [
    'admin',
    'registration',
    'bootstrapform',
    'browserid',
]

# Note that this is different when running tests.
# You know in case you're debugging tests.
AUTHENTICATION_BACKENDS = (
    '%s.auth.backend.AirmozillaBrowserIDBackend' % PROJECT_MODULE,
    # but we're keeping this in case people still have sessions
    # whose backend cookie points to this class path
    'django_browserid.auth.BrowserIDBackend',
    # Needed because the tests use self.client.login(username=..., password=...)
    'django.contrib.auth.backends.ModelBackend',
)

# Domains allowed for log in
ALLOWED_BID = (
    'mozilla.com',
    'mozillafoundation.org',
    'mozilla-japan.org',
)

# This is only needed when not in DEBUG mode
# SITE_URL = 'http://127.0.0.1:8000'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL_FAILURE = '/login-failure/'

TEMPLATE_CONTEXT_PROCESSORS += (
    'airmozilla.manage.context_processors.badges',
    'airmozilla.main.context_processors.base',
    'airmozilla.main.context_processors.nav_bar',
    'airmozilla.main.context_processors.search_form',
    'airmozilla.main.context_processors.sidebar',
    'airmozilla.main.context_processors.analytics',
    'airmozilla.main.context_processors.dev',
    'airmozilla.main.context_processors.browserid',
    'airmozilla.main.context_processors.faux_i18n',
    'airmozilla.main.context_processors.autocompeter',
    'airmozilla.starred.context_processors.stars',
)

# Always generate a CSRF token for anonymous users.
ANON_ALWAYS = True

# Tells the extract script what files to look for L10n in and what function
# handles the extraction. The Tower library expects this.
# DOMAIN_METHODS['messages'] = [
#     ('%s/**.py' % PROJECT_MODULE,
#         'tower.management.commands.extract.extract_tower_python'),
#     ('%s/**/templates/**.html' % PROJECT_MODULE,
#         'tower.management.commands.extract.extract_tower_template'),
#     ('templates/**.html',
#         'tower.management.commands.extract.extract_tower_template'),
# ],

# # Use this if you have localizable HTML files:
# DOMAIN_METHODS['lhtml'] = [
#    ('**/templates/**.lhtml',
#        'tower.management.commands.extract.extract_tower_template'),
# ]

# # Use this if you have localizable JS files:
# DOMAIN_METHODS['javascript'] = [
#    # Make sure that this won't pull in strings from external libraries you
#    # may use.
#    ('media/js/**.js', 'javascript'),
# ]

# This disables all mail_admins on all django.request errors.
# We can do this because we use Sentry now instead
LOGGING = {
    'loggers': {
        'django.request': {
            'handlers': []
        }
    }
}


def JINJA_CONFIG():
    # different from that in funfactory in that we don't want to
    # load the `tower` extension
    config = {
        'extensions': [
            'jinja2.ext.do',
            'jinja2.ext.with_',
            'jinja2.ext.loopcontrols'
        ],
        'finalize': lambda x: x if x is not None else '',
    }
    # config = funfactory_JINJA_CONFIG()
    # config['extensions'].remove('tower.template.i18n')
    return config


def COMPRESS_JINJA2_GET_ENVIRONMENT():
    from jingo import env
    from compressor.contrib.jinja2ext import CompressorExtension
    env.add_extension(CompressorExtension)

    return env

# Remove localization middleware
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'session_csrf.CsrfMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'commonware.middleware.FrameOptionsHeader',
    'airmozilla.manage.middleware.CacheBustingMiddleware',
    'airmozilla.staticpages.middleware.StaticPageFallbackMiddleware',
)

# Enable timezone support for Django TZ-aware datetime objects
# Times stored in the db as UTC; forms/templates as Pacific time
USE_TZ = True
TIME_ZONE = 'US/Pacific'

# Configuration for live/archiving events treatment
# How much time, in minutes, an event shows as "live" before its start time.
LIVE_MARGIN = 10

# Default amount of time, in minutes, an event spends in the "archiving" state.
ARCHIVING_MARGIN = 60

# How many events in the past (and future) should the calendar system
# return.  E.g. if CALENDAR_SIZE=30, up to 60 events (half from the past
# and half from the future) will be output.
CALENDAR_SIZE = 30

# How many events should appear in the syndication feeds
FEED_SIZE = 20

# Number of upcoming events to display in the sidebar
UPCOMING_SIDEBAR_COUNT = 5

# Number of featured/trending events to display in the sidebar
FEATURED_SIDEBAR_COUNT = 5

# Number of trending events to display in the Roku feed
TRENDING_ROKU_COUNT = 20

# Use memcached for session storage with fallback on the database
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# Always use secure cookies
COOKIES_SECURE = True

# Default for related content
RELATED_CONTENT_URL = 'http://localhost:9200/'

# Number of related events to display (max)
RELATED_CONTENT_SIZE = 6

# Defaults for Mozillians
MOZILLIANS_API_BASE = 'https://mozillians.org'

# API base URL
VIDLY_BASE_URL = 'https://vid.ly'
VIDLY_API_URL = 'http://m.vid.ly/api/'

# Name of the default Channel
DEFAULT_CHANNEL_SLUG = 'main'
DEFAULT_CHANNEL_NAME = 'Main'

# Name of the default channel for Mozillians
MOZILLIANS_CHANNEL_SLUG = 'mozillians'
MOZILLIANS_CHANNEL_NAME = 'Mozillians'

# How often, maximum are approval pester emails sent
PESTER_INTERVAL_DAYS = 3  # days

# Where you put secure username+password combinations for example
URL_TRANSFORM_PASSWORDS = {}

# Bit.ly URL shortener access token
# See README about how to generate one
BITLY_ACCESS_TOKEN = None
BITLY_URL = 'https://api-ssl.bitly.com/v3/shorten'

# Overridden so we can depend on more complex checking
BROWSERID_VERIFY_CLASS = '%s.auth.views.CustomBrowserIDVerify' % PROJECT_MODULE
BROWSERID_REQUEST_ARGS = {'siteName': 'Air Mozilla'}

# Name of the bucket where you upload all large videos
S3_UPLOAD_BUCKET = 'air-mozilla-uploads'

# See http://amara.org/en/profiles/account/
AMARA_BASE_URL = 'https://www.amara.org/api2/partners'
AMARA_API_USERNAME = ''
AMARA_API_KEY = ''

SCRAPE_CREDENTIALS = {
    # ('username', 'password'): ['intranet.mozilla.org'],
}

# If true, every search is logged and recorded
LOG_SEARCHES = True

try:
    # ujson is a much faster json serializer
    # We tell the django-jsonview decorator to use it only if the ujson
    # package is installed and can be imported
    import ujson
    JSON_MODULE = 'ujson'
    JSON_USE_DJANGO_SERIALIZER = False
except ImportError:
    pass


# When extracting screen captures, how many do we want to extract
# for each video. This number is static independent of the length
# of the video.
SCREENCAPTURES_NO_PICTURES = 12

# Name of the directory that gets created in the temp directory
# that we fill with screencaps, and that gets later picked up
# by another job that imports the JPEGs created there.
SCREENCAPTURES_TEMP_DIRECTORY_NAME = 'airmozilla-screencaps'


# Usernames of people who have contributed to Air Mozilla (as a contributor).
# This list is ordered! Ordered by the first contributor first, and the most
# recent contributor last.
# These usernames must exist in the
# https://mozillians.org/en-US/group/air-mozilla-contributors/ group.
CONTRIBUTORS = (
    'onceuponatimeforever',
    'bugZPDX',
    'lcamacho',
    'quentinp',
    'leo',
    'koddsson',
    'KrystalYu',
    'anuragchaudhury',
    'blossomica',
    'a-buck',
)

# Override this if you want to run the selenium based tests
RUN_SELENIUM_TESTS = False


# Whether we should use the new upload nav bar item.
# Once the new upload is fully tested and ready to go live we might as
# well delete this setting and remove the if-statement in
# main.context_processors.nav_bar.
USE_NEW_UPLOADER = True


# When enabled, together with DEBUG==True, by visiting /god-mode/ you
# can become anybody.
# This is a good tool for doing testing without doing any Persona auth.
GOD_MODE = False


# If you want to disable all of the browser ID stuff, set this to True.
# That means you won't be able to sign in at all. Or sign out.
BROWSERID_DISABLED = False



# How many times to try sending out an event tweet.
MAX_TWEET_ATTEMPTS = 3


# Where do we store jobs for the celery message queue
BROKER_URL = 'django://'

CELERY_ALWAYS_EAGER = False

BROKER_CONNECTION_TIMEOUT = 0.1
CELERYD_CONCURRENCY = 2
CELERY_IGNORE_RESULT = True


THUMBNAIL_BACKEND = 'optisorl.backend.OptimizingThumbnailBackend'


# This turns of the thumbnail optimizer using pngquant so it's
# not used unless you explicitely turn it on.
PNGQUANT_LOCATION = None

# The user group where being a member means you get an email about
# all new event requests
NOTIFICATIONS_GROUP_NAME = 'Event Notifications'

# This is here in order to override the code related to elastic search
# once things are said and done, ie. it works, this will be deleted
USE_RELATED_CONTENT = False


# Adding prefix to airmozilla events index
ELASTICSEARCH_PREFIX = 'airmozilla'
ELASTICSEARCH_INDEX = 'events'

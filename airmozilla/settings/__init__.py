import sys
import os

from .base import *  # NOQA
try:
    from .local import *  # NOQA
except ImportError, exc:  # pragma: no cover
    exc.args = tuple([
        '%s (did you rename airmozilla/settings/local.py-dist?)' % (
            exc.args[0],
        )
    ])
    raise exc

# Certain things are not possible to do until AFTER the base and local
# settings have been loaded.
if FANOUT_REALM_ID:
    CSP_SCRIPT_SRC = CSP_SCRIPT_SRC + (
        '{}.fanoutcdn.com'.format(FANOUT_REALM_ID),
    )
    CSP_CONNECT_SRC = CSP_CONNECT_SRC + (
        '{}.fanoutcdn.com'.format(FANOUT_REALM_ID),
        'wss://{}.fanoutcdn.com'.format(FANOUT_REALM_ID),
    )
if (
    not OIDC_RP_CLIENT_ID and
    not OIDC_RP_CLIENT_SECRET and
    AUTH0_CLIENT_ID and
    AUTH0_SECRET
):
    OIDC_RP_CLIENT_ID = AUTH0_CLIENT_ID
    OIDC_RP_CLIENT_SECRET = AUTH0_SECRET

if not OIDC_OP_AUTHORIZATION_ENDPOINT and AUTH0_DOMAIN:
    OIDC_OP_AUTHORIZATION_ENDPOINT = 'https://{}/authorize'.format(
        AUTH0_DOMAIN
    )
if not OIDC_OP_TOKEN_ENDPOINT and AUTH0_DOMAIN:
    OIDC_OP_TOKEN_ENDPOINT = 'https://{}/oauth/token'.format(AUTH0_DOMAIN)
if not OIDC_OP_USER_ENDPOINT and AUTH0_DOMAIN:
    OIDC_OP_USER_ENDPOINT = 'https://{}/userinfo'.format(AUTH0_DOMAIN)

if not LOGIN_REDIRECT_URL and AUTH0_SUCCESS_URL:
    LOGIN_REDIRECT_URL = AUTH0_SUCCESS_URL

if not LOGOUT_REDIRECT_URL and AUTH_SIGNOUT_URL:
    LOGOUT_REDIRECT_URL = AUTH_SIGNOUT_URL

# This takes care of removing that pesky warning, about raven not
# being configured in local development, that looks like an error.
try:
    assert RAVEN_CONFIG['dsn']  # NOQA
except (NameError, KeyError, AssertionError):  # pragma: no cover
    # Then it's not been configured!
    INSTALLED_APPS = list(INSTALLED_APPS)  # NOQA
    INSTALLED_APPS.remove('raven.contrib.django.raven_compat')
    INSTALLED_APPS = tuple(INSTALLED_APPS)


if len(sys.argv) > 1 and sys.argv[1] == 'test':
    # Shuts up excessive logging when running tests
    import logging
    logging.disable(logging.WARNING)

    from .test import *  # NOQA

    # Are you getting full benefit from django-nose?
    if not os.getenv('REUSE_DB', 'false').lower() in ('true', '1', ''):
        print (
            "Note!\n\tIf you want much faster tests in local development "
            "consider setting the REUSE_DB=1 environment variable.\n"
        )

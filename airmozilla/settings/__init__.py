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

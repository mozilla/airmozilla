from .base import *
try:
    from .local import *
except ImportError, exc:  # pragma: no cover
    exc.args = tuple([
        '%s (did you rename airmozilla/settings/local.py-dist?)' % (
            exc.args[0],
        )
    ])
    raise exc


# This takes care of removing
try:
    assert RAVEN_CONFIG['dsn']
except (NameError, KeyError, AssertionError):  # pragma: no cover
    # Then it's not been configured!
    INSTALLED_APPS = list(INSTALLED_APPS)
    INSTALLED_APPS.remove('raven.contrib.django.raven_compat')
    INSTALLED_APPS = tuple(INSTALLED_APPS)

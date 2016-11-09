"""
In production we use root/wsgi/playdoh.wsgi which only works with mod_wsgi.
If you want to run with uwsgi you need to have a .py file here.

NOTE: This file a complete copy of the .wsgi one except this comment.
"""

import os
import site

os.environ.setdefault('CELERY_LOADER', 'django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'airmozilla.settings')

# Add the app dir to the python path so we can import manage.
wsgidir = os.path.dirname(__file__)
site.addsitedir(os.path.abspath(os.path.join(wsgidir, '../')))


from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()


## the following comes from
## https://mana.mozilla.org/wiki/display/websites/How+to+Set+up+New+Relic+for+a+site

try:
    import newrelic.agent
except ImportError:
    newrelic = False

if newrelic:
    newrelic_ini = os.getenv('NEWRELIC_PYTHON_INI_FILE', False)
    if newrelic_ini:
        newrelic.agent.initialize(newrelic_ini)
    else:
        newrelic = False

if newrelic:
    application = newrelic.agent.wsgi_application()(application)

# vim: ft=python

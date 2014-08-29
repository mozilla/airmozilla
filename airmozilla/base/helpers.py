import jinja2
from jingo import register

from django.contrib.sites.models import RequestSite

from funfactory.helpers import static


@register.function
@jinja2.contextfunction
def abs_static(context, path):
    """Make sure we always return a FULL absolute URL that starts
    with 'http'.
    """
    path = static(path)
    # print "AFTER", path
    prefix = context['request'].is_secure() and 'https' or 'http'

    if path.startswith('/') and not path.startswith('//'):
        # e.g. '/media/foo.png'
        root_url = '%s://%s' % (prefix, RequestSite(context['request']).domain)
        path = root_url + path
        # print "path now", path

    if path.startswith('//'):
        path = '%s:%s' % (prefix, path)

    assert path.startswith('http://') or path.startswith('https://')
    return path

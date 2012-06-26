import functools
import json

from django import http
from django.template.defaultfilters import slugify


def unique_slugify(data, model, duplicate_key=''):
    """Returns a unique slug string.  If duplicate_key is provided, this is
       appended for non-unique slugs before adding a count."""
    slug_base = slugify(data)
    counter = 0
    slug = slug_base
    while model.objects.filter(slug__iexact=slug):
        counter += 1
        if counter == 1 and duplicate_key:
            slug_base += '-' + duplicate_key
            slug = slug_base
            continue
        slug = "%s-%i" % (slug_base, counter)
    return slug


# From socorro-crashstats
def json_view(f):
    @functools.wraps(f)
    def wrapper(*args, **kw):
        response = f(*args, **kw)
        if isinstance(response, http.HttpResponse):
            return response
        else:
            return http.HttpResponse(_json_clean(json.dumps(response)),
                                content_type='application/json; charset=UTF-8')
    return wrapper


def _json_clean(value):
    """JSON-encodes the given Python object."""
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript. Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    return value.replace("</", "<\\/")

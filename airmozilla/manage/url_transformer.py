import re

from django.conf import settings

from django.template import engines

from airmozilla.main.models import URLMatch, URLTransform


def run(url, dry=False):
    """return a tuple of (result, error)"""
    original = url
    _context = None

    for match in URLMatch.objects.all():
        regex = re.compile(match.string)
        if regex.findall(url):
            transforms = (
                URLTransform.objects.filter(match=match).order_by('order')
            )
            for transform in transforms:
                find_regex = re.compile(transform.find)
                if _context is None:
                    _context = create_context()
                # the `replace_with` string might have variables in it
                replace_with_template = engines['backend'].from_string(
                    transform.replace_with
                )
                replace_with = replace_with_template.render(_context)
                # if this is a `dry` run we don't want to accidentally
                # reveal a real password
                if dry:
                    from airmozilla.manage.templatetags.jinja_helpers import (
                        scrub_transform_passwords
                    )
                    replace_with = scrub_transform_passwords(replace_with)
                url = find_regex.sub(replace_with, url)
            match.use_count += 1

    if original != url and not dry:
        match.save()

    return url, None


def _password_lookup(username):
    return settings.URL_TRANSFORM_PASSWORDS[username]


def create_context():
    return {
        'password': _password_lookup,
    }

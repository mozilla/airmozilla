from django.core.cache import cache
from django.conf import settings

from airmozilla.main.models import get_profile_safely


def is_contributor(user):
    if not hasattr(user, 'pk'):
        return False
    cache_key = 'is-contributor-%s' % user.pk
    is_ = cache.get(cache_key)
    if is_ is None:
        profile = get_profile_safely(user)
        is_ = False
        if profile and profile.contributor:
            is_ = True
        cache.set(cache_key, is_, 60 * 60)
    return is_


def is_employee(user):
    if not hasattr(user, 'pk'):
        return False
    cache_key = 'is-employee-%s' % user.pk
    is_ = cache.get(cache_key)
    if is_ is None:
        is_ = False
        for bid in settings.ALLOWED_BID:
            if user.email.endswith('@%s' % bid):
                is_ = True
                break
        cache.set(cache_key, is_, 60 * 60)
    return is_

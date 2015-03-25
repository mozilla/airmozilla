from django.core.cache import cache

from airmozilla.starred.models import StarredEvent


def stars(request):
    context = {}
    if request.user.is_active:
        context['star_ids'] = _get_star_ids(request.user)
    return context


def _get_star_ids(user):
    cache_key = 'star_ids%s' % user.id
    as_string = cache.get(cache_key)
    if as_string is None:
        ids = list(
            StarredEvent.objects
            .filter(user=user)
            .values_list('event_id', flat=True)
            .order_by('created')
        )
        as_string = ','.join(str(x) for x in ids)
        cache.set(cache_key, as_string, 60 * 60)
    return as_string

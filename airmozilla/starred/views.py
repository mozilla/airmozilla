import collections

from django import http
from django.shortcuts import render
from django.views.decorators import cache
from django.core.urlresolvers import reverse

from session_csrf import anonymous_csrf
from jsonview.decorators import json_view

from airmozilla.base.utils import paginate
from airmozilla.starred.models import StarredEvent
from airmozilla.main.models import (
    Event,
    CuratedGroup,
)


@cache.cache_control(private=True)
@anonymous_csrf
@json_view
def sync_starred_events(request):
    context = {'csrf_token': request.csrf_token}
    if request.user.is_anonymous():
        context['ids'] = []
        return context
    elif request.method == 'POST':
        ids = request.POST.getlist('ids')
        StarredEvent.objects.filter(user=request.user).exclude(
            id__in=ids).delete()
        for id in ids:
            try:
                event = Event.objects.get(id=id)
                StarredEvent.objects.get_or_create(
                    user=request.user,
                    event=event
                )
            except Event.DoesNotExist:
                # ignore events that don't exist but fail on other errors
                pass

    starred = StarredEvent.objects.filter(user=request.user)
    context['ids'] = list(starred.values_list('event_id', flat=True))
    return context


def home(request, page=1):
    template_name = 'starred/home.html'
    ids = request.GET.get('ids')
    if request.is_ajax():
        template_name = 'starred/events.html'

    if request.user.is_authenticated():
        events = (
            Event.objects.filter(starredevent__user=request.user.id)
            .order_by('starredevent__created')
        )

    elif ids:
        # If you're not authenticated, you should only be able to see
        # public events.
        try:
            ids = [int(x) for x in ids.split(',')]
        except ValueError:
            return http.HttpResponseBadRequest('invalid id')
        events = Event.objects.filter(id__in=ids, privacy=Event.PRIVACY_PUBLIC)
        events = sorted(events, key=lambda e: ids.index(e.id))
    else:
        events = None

    starred_paged = next_page_url = prev_page_url = None
    if events:
        starred_paged = paginate(events, page, 10)

        # to simplify the complexity of the template when it tries to make the
        # pagination URLs, we just figure it all out here
        if starred_paged.has_next():
            next_page_url = reverse(
                'starred:home',
                args=(starred_paged.next_page_number(),)
            )
        if starred_paged.has_previous():
            prev_page_url = reverse(
                'starred:home',
                args=(starred_paged.previous_page_number(),)
            )

        curated_groups_map = collections.defaultdict(list)
        curated_groups = (
            CuratedGroup.objects.filter(event__in=[
                x.id for x in starred_paged
            ])
            .values_list('event_id', 'name')
            .order_by('name')
        )
        for event_id, name in curated_groups:
            curated_groups_map[event_id].append(name)

    def get_curated_groups(event):
        if events:
            return curated_groups_map.get(event.id)

    context = {
        'events': starred_paged,
        'get_curated_groups': get_curated_groups,
        'next_page_url': next_page_url,
        'prev_page_url': prev_page_url,
        'star_on': True,
    }

    return render(request, template_name, context)

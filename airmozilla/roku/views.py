from django.contrib.sites.requests import RequestSite
from django.shortcuts import render
from django.conf import settings
from django.db.models import Q
from django.core.urlresolvers import reverse

from airmozilla.main.models import Channel, Event
from airmozilla.main.views import is_contributor
from airmozilla.base.utils import (
    paginate
)
from airmozilla.main.context_processors import get_featured_events


def categories_feed(request):
    context = {}

    privacy_filter = {}
    privacy_exclude = {}
    if request.user.is_active:
        if is_contributor(request.user):
            # feed_privacy = 'contributors'
            privacy_exclude = {'privacy': Event.PRIVACY_COMPANY}
        # else:
            # feed_privacy = 'company'
    else:
        privacy_filter = {'privacy': Event.PRIVACY_PUBLIC}
        # feed_privacy = 'public'
    events = Event.objects.scheduled().approved()
    live_events = Event.objects.live().approved()
    if privacy_filter:
        events = events.filter(**privacy_filter)
        live_events = live_events.filter(**privacy_filter)
    elif privacy_exclude:
        events = events.exclude(**privacy_exclude)
        live_events = live_events.exclude(**privacy_exclude)

    channels = get_channels(events)
    context['channels'] = channels

    context['live_events'] = live_events

    prefix = request.is_secure() and 'https' or 'http'
    root_url = '%s://%s' % (prefix, RequestSite(request).domain)

    def abs_url_maker(viewname, *args, **kwargs):
        return root_url + reverse(viewname, args=args, kwargs=kwargs)

    context['abs_url'] = abs_url_maker
    context['get_media_info'] = get_media_info

    response = render(request, 'roku/categories.xml', context)
    response['Content-Type'] = 'text/xml'
    return response


def get_channels(events, parent=None):
    channels = []
    channels_qs = Channel.objects.all()
    if parent is None:
        channels_qs = channels_qs.filter(parent__isnull=True)
    else:
        channels_qs = channels_qs.filter(parent=parent)
    for channel in channels_qs:
        event_count = events.filter(channels=channel).count()
        subchannel_count = Channel.objects.filter(parent=channel).count()
        if event_count or subchannel_count:
            # channel.subchannels = get_channels(events, parent=channel)
            channels.append(channel)

    def sorter(x, y):
        if x.slug == settings.DEFAULT_CHANNEL_SLUG:
            return -2
        return cmp(x.name.lower(), y.name.lower())
    channels.sort(sorter)
    return channels


def get_media_info(event):
    if event.template and 'vid.ly' in event.template.name.lower():
        tag = event.template_environment['tag']
        return {
            # 'url': 'http://vid.ly/%s?content=video&format=webm' % tag,
            # 'format': 'webm'
            # NOTE that it's deliberately set to the HTTP URL. Not HTTPS :(
            'url': 'http://vid.ly/%s?content=video&format=mp4' % tag,
            'format': 'mp4'
        }
    elif event.template and 'hls' in event.template.name.lower():
        try:
            file = event.template_environment['file']
            wowzaapp = event.template_environment.get('wowzaapp') or 'Edgecast'
            return {
                # it's important to use HTTP here :(
                'url': (
                    'http://wowza1.cdn.mozilla.net/%s/ngrp:%s_all'
                    '/playlist.m3u8' % (wowzaapp, file)
                ),
                'format': 'hls',
            }
        except KeyError:
            pass

    return None


def event_feed(request, id):
    # return a feed containing exactly only one event
    context = {}
    events = Event.objects.filter(id=id)
    context['events'] = events

    context['get_media_info'] = get_media_info

    response = render(request, 'roku/channel.xml', context)
    response['Content-Type'] = 'text/xml'
    return response


def channel_feed(request, slug):
    # this slug might be the slug of a parent
    channels = Channel.objects.filter(
        Q(slug=slug) |
        Q(parent__slug=slug)
    )
    events = Event.objects.archived().approved()
    events = events.filter(channels__in=channels)
    privacy_filter = {}
    privacy_exclude = {}
    if request.user.is_active:
        if is_contributor(request.user):
            privacy_exclude = {'privacy': Event.PRIVACY_COMPANY}
    else:
        privacy_filter = {'privacy': Event.PRIVACY_PUBLIC}

    if privacy_filter:
        events = events.filter(**privacy_filter)
    elif privacy_exclude:
        events = events.exclude(**privacy_exclude)
    events = events.order_by('-start_time')

    paged = paginate(events, 1, 100)
    return render_channel_events(paged, request)


def trending_feed(request):
    events = get_featured_events(
        None,  # across all channels
        request.user,
        length=settings.TRENDING_ROKU_COUNT,
    )
    return render_channel_events(events, request)


def render_channel_events(events, request):
    context = {}
    context['events'] = events
    context['get_media_info'] = get_media_info

    response = render(request, 'roku/channel.xml', context)
    response['Content-Type'] = 'text/xml'
    return response

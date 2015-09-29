from collections import defaultdict

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Rss201rev2Feed
from django.shortcuts import get_object_or_404
from django.utils import timezone

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Event, Channel, Tag
from airmozilla.base.utils import get_base_url, get_abs_static
from airmozilla.main.helpers import short_desc


def format_duration(duration):
    hours = duration / 3600
    seconds = duration % 3600
    minutes = seconds / 60
    seconds = seconds % 60
    return '%02d:%02d:%02d' % (
        hours,
        minutes,
        seconds
    )


class EventsFeed(Feed):
    title = "Air Mozilla"
    description = (
        "Air Mozilla is the Internet multimedia presence of Mozilla, "
        "with live and pre-recorded shows, interviews, news snippets, "
        "tutorial videos, and features about the Mozilla community."
    )
    subtitle = 'Mozilla in video'

    description_template = 'main/feeds/event_description.html'

    def get_object(self, request, private_or_public='',
                   channel_slug=settings.DEFAULT_CHANNEL_SLUG,
                   format_type=None):
        if private_or_public == 'private':
            # old URL
            private_or_public = 'company'
        self.private_or_public = private_or_public
        self.format_type = format_type
        self._root_url = get_base_url(request)
        self._channel = get_object_or_404(Channel, slug=channel_slug)

    def link(self):
        return self._root_url + '/'

    def feed_url(self):
        return self.link()

    def feed_copyright(self):
        return (
            "Except where otherwise noted, content on this site is "
            "licensed under the Creative Commons Attribution Share-Alike "
            "License v3.0 or any later version."
        )

    def items(self):
        now = timezone.now()
        qs = (
            Event.objects.scheduled_or_processing()
            .filter(start_time__lt=now,
                    channels=self._channel)
            .order_by('-start_time')
        )
        if not self.private_or_public or self.private_or_public == 'public':
            qs = qs.approved()
            qs = qs.filter(privacy=Event.PRIVACY_PUBLIC)
        elif self.private_or_public == 'contributors':
            qs = qs.exclude(privacy=Event.PRIVACY_COMPANY)
        return qs[:settings.FEED_SIZE]

    def item_title(self, event):
        return event.title

    def item_link(self, event):
        if self.format_type in ('webm', 'mp4'):
            if event.template and 'vid.ly' in event.template.name.lower():
                if self.format_type == 'webm':
                    return self._get_webm_link(event)
                else:
                    return self._get_mp4_link(event)
        return self._root_url + reverse('main:event', args=(event.slug,))

    def item_author_name(self, event):
        return self.title

    def _get_webm_link(self, event):
        tag = event.template_environment['tag']
        return 'https://vid.ly/%s?content=video&format=webm' % tag

    def _get_mp4_link(self, event):
        tag = event.template_environment['tag']
        return 'https://vid.ly/%s?content=video&format=mp4_hd' % tag

    def item_pubdate(self, event):
        return event.start_time


class ITunesElements(object):

    def add_root_elements(self, handler):
        """extra elements to the <channel> tag"""
        super(ITunesElements, self).add_root_elements(handler)

        handler.addQuickElement('itunes:image', attrs={
            'href': self.feed['itunes_lg_url']
        })

        handler.startElement('image', {})
        handler.addQuickElement('url', self.feed['itunes_sm_url'])
        handler.endElement('image')

        handler.addQuickElement('itunes:subtitle', self.feed['subtitle'])
        handler.addQuickElement('itunes:author', 'Mozilla')
        handler.startElement('itunes:owner', {})
        handler.addQuickElement('itunes:name', 'Air Mozilla')
        handler.addQuickElement('itunes:email', settings.EMAIL_FROM_ADDRESS)
        handler.endElement('itunes:owner')

        # Should we have some more categories here?
        # There's a list at the bottom of
        # http://www.apple.com/itunes/podcasts/specs.html
        handler.addQuickElement('itunes:category', attrs={
            'text': 'Technology'
        })

        handler.addQuickElement('description', self.feed['description'])
        handler.addQuickElement('itunes:summary', self.feed['description'])
        handler.addQuickElement('itunes:explicit', 'clean')

    def add_item_elements(self, handler, item):
        """extra elements to the <item> tag"""
        super(ITunesElements, self).add_item_elements(handler, item)

        # A slug can change, an ID can't
        handler.addQuickElement('guid', str(item['id']), attrs={
            'isPermaLink': 'false'}
        )

        handler.addQuickElement('itunes:author', 'Air Mozilla')
        handler.addQuickElement('itunes:subtitle', item['subtitle'])

        handler.addQuickElement('itunes:summary', item['summary'])

        handler.addQuickElement(
            'itunes:duration',
            format_duration(item['duration'])
        )
        if item['tags']:
            handler.addQuickElement(
                'itunes:keywords',
                ', '.join(item['tags'])
            )
        handler.addQuickElement('itunes:explicit', 'clean')

    def namespace_attributes(self):
        return {'xmlns:itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}


class RssITunesFeedGenerator(ITunesElements, Rss201rev2Feed):
    def rss_attributes(self):
        rss_attrs = super(RssITunesFeedGenerator, self).rss_attributes()
        rss_attrs.update(self.namespace_attributes())
        return rss_attrs


class ITunesFeed(EventsFeed):

    feed_type = RssITunesFeedGenerator

    # reset the super, so that item_description() gets called
    description_template = None

    private_or_public = 'public'
    format_type = 'mp4'

    def title(self):
        title = 'Air Mozilla'
        if self._root_url != 'https://air.mozilla.org':
            # This extra title makes it easier for us to test the
            # feed on stage and dev etc.
            title += ' (testing on: {})'.format(self._root_url)
        return title

    def get_object(self, request):
        self.itunes_sm_url = get_abs_static(
            'main/img/podcast-cover-144x144.png',
            request
        )
        self.itunes_lg_url = get_abs_static(
            'main/img/podcast-cover.png',
            request
        )
        self._root_url = get_base_url(request)
        super(ITunesFeed, self).get_object(request)

    def items(self):
        channel = Channel.objects.get(slug=settings.DEFAULT_CHANNEL_SLUG)
        qs = (
            Event.objects.archived()
            .approved()
            .filter(channels=channel)
            .filter(privacy=Event.PRIVACY_PUBLIC)
            .filter(template__name__icontains='vid.ly')
            .filter(template_environment__contains='tag')
            .exclude(duration__isnull=True)
            .order_by('-start_time')
        )[:settings.FEED_SIZE]

        all_tag_ids = set()
        self.all_tags = defaultdict(list)
        for x in Event.tags.through.objects.filter(event__in=qs):
            self.all_tags[x.event_id].append(x.tag_id)
            all_tag_ids.add(x.tag_id)
        # now `all_tags` is a dict like this:
        #  123: [45, 67]
        # where '123' is an event ID, and 45 and 67 are tag IDs
        # Convert it to something like this:
        #  123: ['tag1', 'tagX']
        tags_qs = (
            Tag.objects
            .filter(id__in=all_tag_ids)
            .values_list('id', 'name')
        )
        all_tag_names = dict(x for x in tags_qs)
        for event_id, tag_ids in self.all_tags.items():
            self.all_tags[event_id] = [
                all_tag_names[x] for x in tag_ids
            ]
        return qs

    def feed_extra_kwargs(self, obj):
        return {
            'itunes_sm_url': self.itunes_sm_url,
            'itunes_lg_url': self.itunes_lg_url,
        }

    def item_guid(self, _):  # override the super
        return None

    def item_link(self, event):
        return self._root_url + reverse('main:event', args=(event.slug,))

    def item_description(self, event):
        return event.description.upper()

    def item_enclosure_url(self, event):
        tag = event.template_environment['tag']
        return 'https://vid.ly/%s?content=video&format=mp4_hd' % tag

    def item_enclosure_mime_type(self, event):
        return 'video/mp4'

    def item_enclosure_length(self, event):
        return event.duration

    def item_author_name(self, event):  # override the super
        return None

    def item_extra_kwargs(self, event):
        return {
            'id': event.id,
            'subtitle': short_desc(event),
            'summary': event.description,
            'duration': event.duration,
            'tags': self.all_tags.get(event.id, []),
        }

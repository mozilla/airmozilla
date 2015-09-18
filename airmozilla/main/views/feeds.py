from django.conf import settings
from django.contrib.sites.models import RequestSite
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.utils import timezone

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Event, Channel


class EventsFeed(Feed):
    title = "Air Mozilla"
    description = (
        "Air Mozilla is the Internet multimedia presence of Mozilla, "
        "with live and pre-recorded shows, interviews, news snippets, "
        "tutorial videos, and features about the Mozilla community. "
    )

    description_template = 'main/feeds/event_description.html'

    def get_object(self, request, private_or_public='',
                   channel_slug=settings.DEFAULT_CHANNEL_SLUG,
                   format_type=None):
        if private_or_public == 'private':
            # old URL
            private_or_public = 'company'
        self.private_or_public = private_or_public
        self.format_type = format_type
        prefix = request.is_secure() and 'https' or 'http'
        self._root_url = '%s://%s' % (prefix, RequestSite(request).domain)
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
        if self.format_type == 'webm':
            if event.template and 'vid.ly' in event.template.name.lower():
                return self._get_webm_link(event)
        return self._root_url + reverse('main:event', args=(event.slug,))

    def item_author_name(self, event):
        return self.title

    def _get_webm_link(self, event):
        tag = event.template_environment['tag']
        return 'https://vid.ly/%s?content=video&format=webm' % tag

    def item_pubdate(self, event):
        return event.start_time

import datetime
import hashlib
import urllib
import time
import collections

from django import http
from django.conf import settings
from django.contrib.sites.requests import RequestSite
from django.shortcuts import get_object_or_404, redirect, render
from django.core.cache import cache
from django.views.decorators.cache import never_cache
from django.views.generic.base import View
from django.db.models import Count, Q, F
from django.db import transaction
from django.core.urlresolvers import reverse
from django.template import engines

from jsonview.decorators import json_view

from airmozilla.main.models import (
    Event,
    EventOldSlug,
    Tag,
    Channel,
    EventHitStats,
    CuratedGroup,
    Picture,
    VidlySubmission,
    EventLiveHits,
    Chapter,
)
from airmozilla.base.utils import (
    paginate,
    edgecast_tokenize,
    akamai_tokenize,
)
from airmozilla.main.templatetags.jinja_helpers import thumbnail
from airmozilla.search.models import LoggedSearch
from airmozilla.comments.models import Discussion
from airmozilla.surveys.models import Survey
from airmozilla.manage import vidly
from airmozilla.manage import related
from airmozilla.base import mozillians
from airmozilla.staticpages.views import staticpage
from airmozilla.main import cloud
from airmozilla.main.views import is_contributor, is_employee
from airmozilla.main import forms


def page(request, template):
    """Base page:  renders templates bare, used for static pages."""
    return render(request, template)


def home(request, page=1, channel_slug=settings.DEFAULT_CHANNEL_SLUG):
    """Paginated recent videos and live videos."""
    channels = Channel.objects.filter(slug=channel_slug)
    if not channels.count():
        if channel_slug == settings.DEFAULT_CHANNEL_SLUG:
            # then, the Main channel hasn't been created yet
            Channel.objects.create(
                name=settings.DEFAULT_CHANNEL_NAME,
                slug=settings.DEFAULT_CHANNEL_SLUG
            )
            channels = Channel.objects.filter(slug=channel_slug)
        else:
            raise http.Http404('Channel not found')

    request.channels = channels

    privacy_filter = {}
    privacy_exclude = {}
    archived_events = Event.objects.archived()
    if request.user.is_active:
        if is_contributor(request.user):
            privacy_exclude = {'privacy': Event.PRIVACY_COMPANY}
    else:
        privacy_filter = {'privacy': Event.PRIVACY_PUBLIC}
        archived_events = archived_events.approved()

    if privacy_filter:
        archived_events = archived_events.filter(**privacy_filter)
    elif privacy_exclude:
        archived_events = archived_events.exclude(**privacy_exclude)
    archived_events = archived_events.order_by('-start_time')

    archived_events = archived_events.select_related('picture')

    found_tags = []
    if request.GET.getlist('tag'):
        requested_tags = request.GET.getlist('tag')
        for each in requested_tags:
            found_tags.extend(Tag.objects.filter(name__iexact=each))
        if len(found_tags) < len(requested_tags):
            # invalid tags were used in the query string
            url = reverse('main:home')
            if found_tags:
                # some were good
                url += '?%s' % urllib.urlencode({
                    'tag': [x.name for x in found_tags]
                }, True)
            return redirect(url, permanent=True)
        archived_events = archived_events.filter(tags__in=found_tags)
    if found_tags:
        # no live events when filtering by tag
        live_events = Event.objects.none()
    else:
        live_events = (Event.objects.live()
                       .order_by('start_time'))
        if not request.user.is_active:
            live_events = live_events.approved()

        if privacy_filter:
            live_events = live_events.filter(**privacy_filter)
        elif privacy_exclude:
            live_events = live_events.exclude(**privacy_exclude)

        # apply the mandatory channels filter
        # but only do this if it's not filtered by tags
        live_events = live_events.filter(channels=channels)
        archived_events = archived_events.filter(channels=channels)

        live_events = live_events.select_related('picture')

    if channels and channels[0].reverse_order:
        archived_events = archived_events.reverse()

    archived_paged = paginate(archived_events, page, 10)

    # to simplify the complexity of the template when it tries to make the
    # pagination URLs, we just figure it all out here
    next_page_url = prev_page_url = None
    channel = channels[0]
    if archived_paged.has_next():
        if channel.slug == settings.DEFAULT_CHANNEL_SLUG:
            next_page_url = reverse(
                'main:home',
                args=(archived_paged.next_page_number(),)
            )
        else:
            next_page_url = reverse(
                'main:home_channels',
                args=(channel.slug,
                      archived_paged.next_page_number())
            )
    if archived_paged.has_previous():
        if channel.slug == settings.DEFAULT_CHANNEL_SLUG:
            prev_page_url = reverse(
                'main:home',
                args=(archived_paged.previous_page_number(),)
            )
        else:
            prev_page_url = reverse(
                'main:home_channels',
                args=(channel.slug,
                      archived_paged.previous_page_number())
            )

    events_qs = Event.objects.archived().all()
    if request.user.is_active:
        if is_contributor(request.user):
            feed_privacy = 'contributors'
            events_qs = events_qs.exclude(privacy=Event.PRIVACY_COMPANY)
        else:
            feed_privacy = 'company'
    else:
        events_qs = events_qs.filter(privacy=Event.PRIVACY_PUBLIC)
        feed_privacy = 'public'

    channel_children = []
    for child in channel.get_children().order_by('name'):
        channel_children.append((
            child,
            events_qs.filter(channels=child).count()
        ))

    curated_groups_map = collections.defaultdict(list)
    curated_groups = (
        CuratedGroup.objects.all()
        .values_list('event_id', 'name')
        .order_by('name')
    )
    for event_id, name in curated_groups:
        curated_groups_map[event_id].append(name)

    def get_curated_groups(event):
        return curated_groups_map.get(event.id)

    context = {
        'events': archived_paged,
        'live_events': live_events,
        'tags': found_tags,
        'Event': Event,
        'channel': channel,
        'channel_children': channel_children,
        'feed_privacy': feed_privacy,
        'next_page_url': next_page_url,
        'prev_page_url': prev_page_url,
        'get_curated_groups': get_curated_groups,
    }

    return render(request, 'main/home.html', context)


def can_view_event(event, user):
    """return True if the current user has right to view this event"""
    if event.privacy == Event.PRIVACY_PUBLIC:
        return True
    elif not user.is_active:
        return False

    # you're logged in
    if event.privacy == Event.PRIVACY_COMPANY:
        # but then it's not good enough to be contributor
        if is_contributor(user):
            return False
    else:
        if not is_contributor(user):
            # staff can always see it
            return True

        curated_groups = [
            x[0] for x in
            CuratedGroup.objects.filter(event=event).values_list('name')
        ]
        if curated_groups:
            return any(
                [mozillians.in_group(user.email, x) for x in curated_groups]
            )

    return True


class EventView(View):
    """Video, description, and other metadata."""

    template_name = 'main/event.html'

    def cant_view_event(self, event, request):
        """return a response appropriate when you can't view the event"""
        if request.user.is_authenticated():
            return redirect('main:permission_denied', event.slug)
        else:
            desired_url = reverse('main:event', args=(event.slug,))
            url = reverse('main:login')
            return redirect('%s?next=%s' % (url, urllib.quote(desired_url)))

    def cant_find_event(self, request, slug):
        """return an appropriate response if no event can be found"""
        return staticpage(request, slug)

    def can_view_event(self, event, request):
        """wrapper on the utility function can_view_event()"""
        return can_view_event(event, request.user)

    def get_default_context(self, event, request):
        context = {}
        prefix = request.is_secure() and 'https' or 'http'
        root_url = '%s://%s' % (prefix, RequestSite(request).domain)
        url = reverse('main:event_video', kwargs={'slug': event.slug})
        absolute_url = root_url + url
        context['embed_code'] = (
            '<iframe src="%s" '
            'width="640" height="380" frameborder="0" allowfullscreen>'
            '</iframe>'
            % absolute_url
        )
        context['embed_code_big'] = (
            '<iframe src="%s" '
            'width="896" height="524" frameborder="0" allowfullscreen>'
            '</iframe>'
            % absolute_url
        )
        return context

    def get_event(self, slug, request):
        try:
            return Event.objects.get(slug=slug)
        except Event.DoesNotExist:
            try:
                return Event.objects.get(slug__iexact=slug)
            except Event.DoesNotExist:
                try:
                    old_slug = EventOldSlug.objects.get(slug=slug)
                    return redirect('main:event', slug=old_slug.event.slug)
                except EventOldSlug.DoesNotExist:
                    # does it exist as a static page
                    if slug.isdigit():
                        # it might be the ID of the event
                        try:
                            return Event.objects.get(id=slug)
                        except Event.DoesNotExist:
                            # not that either
                            pass
                    return self.cant_find_event(request, slug)

    @staticmethod
    def get_vidly_information(event, tag):
        cache_key = 'event_vidly_information-{}'.format(event.id)
        from_cache = cache.get(cache_key)
        if from_cache is not None:
            return from_cache

        # It was not cached, we have to figure it out
        vidly_tag = hd = None
        if (
            not (event.is_pending() or event.is_processing()) and
            event.is_public() and
            event.has_vidly_template() and event.template_environment
        ):
            if event.template_environment.get('tag'):
                vidly_tag = tag or event.template_environment['tag']
                hd = False  # default
                vidly_submissions = (
                    VidlySubmission.objects
                    .filter(event=event, tag=vidly_tag)
                    .order_by('-submission_time')
                )
                for vidly_submission in vidly_submissions.values('hd'):
                    hd = vidly_submission['hd']
                    break
        cache.set(cache_key, (vidly_tag, hd), 60 * 60)
        return vidly_tag, hd

    def get(self, request, slug):
        event = self.get_event(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        if not self.can_view_event(event, request):
            return self.cant_view_event(event, request)

        tag = request.GET.get('tag')

        warning = None
        ok_statuses = (
            Event.STATUS_SCHEDULED,
            Event.STATUS_PENDING,
            Event.STATUS_PROCESSING,
            )
        if event.status not in ok_statuses:
            if not request.user.is_superuser:
                self.template_name = 'main/event_not_scheduled.html'
            else:
                warning = "Event is not publicly visible - not scheduled."

        if event.approval_set.filter(approved=False).exists():
            if not request.user.is_active:
                return http.HttpResponse('Event not approved')
            else:
                warning = "Event is not publicly visible - not yet approved."

        hits = None

        # assume this to false to start with
        can_edit_chapters = False

        template_tagged = ''
        if event.template and not event.is_upcoming():
            # The only acceptable way to make autoplay be on
            # is to send ?autoplay=true
            # All other attempts will switch it off.
            autoplay = request.GET.get('autoplay', 'false') == 'true'
            try:
                template_tagged = get_video_tagged(
                    event,
                    request,
                    autoplay=autoplay,
                    tag=tag,
                )
            except VidlySubmission.DoesNotExist:
                return http.HttpResponseBadRequest(
                    'Tag %s does not exist for this event' % (tag,)
                )
            stats_query = (
                EventHitStats.objects.filter(event=event)
                .values_list('total_hits', flat=True)
            )
            for total_hits in stats_query:
                hits = total_hits

            # if the event has a template is not upcoming
            if not event.is_live():
                # ...and is not live, then
                if request.user.is_active:
                    can_edit_chapters = True

        can_manage_edit_event = (
            request.user.is_active and
            request.user.is_staff and
            request.user.has_perm('main.change_event')
        )
        can_edit_event = request.user.is_active
        can_edit_discussion = (
            can_edit_event and
            # This is a little trick to avoid waking up the
            # SimpleLazyObject on the user. If the .is_active is true
            # the ID will have already been set by the session.
            # So doing this comparison instead avoids causing a
            # select query on the auth_user table.
            request.user.pk == event.creator_id and
            Discussion.objects.filter(event=event).exists()
        )

        request.channels = event.channels.all()

        # needed for the open graph stuff
        event.url = reverse('main:event', args=(event.slug,))

        context = self.get_default_context(event, request)
        context.update({
            'event': event,
            'video': template_tagged,
            'warning': warning,
            'can_manage_edit_event': can_manage_edit_event,
            'can_edit_event': can_edit_event,
            'can_edit_discussion': can_edit_discussion,
            'can_edit_chapters': can_edit_chapters,
            'Event': Event,
            'hits': hits,
            'tags': [t.name for t in event.tags.all()],
            'channels': request.channels,
            # needed for the _event_privacy.html template
            'curated_groups': CuratedGroup.get_names(event),
        })

        context['chapters'] = []
        for chapter in Chapter.objects.filter(event=event, is_active=True):
            context['chapters'].append({
                'timestamp': chapter.timestamp,
                'text': chapter.text,
            })

        vidly_tag, vidly_hd = self.get_vidly_information(event, tag)
        if vidly_tag:
            context['vidly_tag'] = vidly_tag
            context['vidly_hd'] = vidly_hd

        # If the event is in the processing state (or pending), we welcome
        # people to view it but it'll say that the video isn't ready yet.
        # But we'll also try to include an estimate of how long we think
        # it will take until it's ready to be viewed.
        if (
            (event.is_processing() or event.is_pending()) and
            event.duration and
            event.template_environment.get('tag')
        ):
            vidly_submissions = (
                VidlySubmission.objects
                .filter(event=event, tag=event.template_environment.get('tag'))
                .order_by('-submission_time')
            )
            for vidly_submission in vidly_submissions:
                context['estimated_time_left'] = (
                    vidly_submission.get_estimated_time_left()
                )

        if event.pin:
            if (
                not request.user.is_authenticated() or
                not is_employee(request.user)
            ):
                entered_pins = request.session.get('entered_pins', [])
                if event.pin not in entered_pins:
                    self.template_name = 'main/event_requires_pin.html'
                    context['pin_form'] = forms.PinForm()
        try:
            context['discussion'] = Discussion.objects.get(event=event)
        except Discussion.DoesNotExist:
            context['discussion'] = {'enabled': False}

        if event.recruitmentmessage and event.recruitmentmessage.active:
            context['recruitmentmessage'] = event.recruitmentmessage

        cache_key = 'event_survey_id_%s' % event.id
        context['survey_id'] = cache.get(cache_key, -1)
        if context['survey_id'] == -1:  # not known in cache
            try:
                survey = Survey.objects.get(
                    events=event,
                    active=True
                )
                cache.set(cache_key, survey.id, 60 * 60 * 24)
                context['survey_id'] = survey.id
            except Survey.DoesNotExist:
                cache.set(cache_key, None, 60 * 60 * 24)
                context['survey_id'] = None

        if settings.LOG_SEARCHES:
            if request.session.get('logged_search'):
                pk, time_ago = request.session.get('logged_search')
                age = time.time() - time_ago
                if age <= 5:
                    # the search was made less than 5 seconds ago
                    try:
                        logged_search = LoggedSearch.objects.get(pk=pk)
                        logged_search.event_clicked = event
                        logged_search.save()
                    except LoggedSearch.DoesNotExist:
                        pass

        return render(request, self.template_name, context)

    def post(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        pin_form = forms.PinForm(request.POST, instance=event)
        if pin_form.is_valid():
            entered_pins = self.request.session.get('entered_pins', [])
            pin = pin_form.cleaned_data['pin']
            if pin not in entered_pins:
                entered_pins.append(pin)
                request.session['entered_pins'] = entered_pins
                return redirect('main:event', slug=slug)

        context = {
            'event': event,
            'pin_form': pin_form,
        }
        return render(request, 'main/event_requires_pin.html', context)


def get_video_tagged(event, request, autoplay=False, tag=None):

    def poster_url(geometry='896x504', crop='center'):
        image = event.picture and event.picture.file or event.placeholder_img
        return thumbnail(image, geometry, crop=crop).url

    context = {
        'md5': lambda s: hashlib.md5(s).hexdigest(),
        'event': event,
        'request': request,
        'datetime': datetime.datetime.utcnow(),
        'vidly_tokenize': vidly.tokenize,
        'edgecast_tokenize': edgecast_tokenize,
        'akamai_tokenize': akamai_tokenize,
        'popcorn_url': event.popcorn_url,
        'autoplay': autoplay and 'true' or 'false',  # javascript
        'poster_url': poster_url,
    }
    if isinstance(event.template_environment, dict):
        context.update(event.template_environment)
    if tag:
        submissions = VidlySubmission.objects.filter(
            tag=tag,
            event=event
        )
        if not submissions.exists():
            raise VidlySubmission.DoesNotExist(tag)
        context['tag'] = tag
    template = engines['backend'].from_string(event.template.content)
    try:
        template_tagged = template.render(context)
    except vidly.VidlyTokenizeError, msg:
        template_tagged = '<code style="color:red">%s</code>' % msg

    return template_tagged


class EventVideoView(EventView):
    template_name = 'main/event_video.html'

    def can_view_event(self, event, request):
        if self.embedded:
            if event.privacy != Event.PRIVACY_PUBLIC:
                # If you are the owner of it, it's fine, if we don't
                # want any warnings
                if (
                    self.no_warning and
                    request.user.is_active and request.user == event.creator
                ):
                    return True
                return False
            return True
        else:
            return super(EventVideoView, self).can_view_event(event, request)

    def cant_view_event(self, event, request):
        """return a response appropriate when you can't view the event"""
        return render(request, self.template_name, {
            'error': "Not a public event",
            'event': None,
        })

    def cant_find_event(self, request, slug):
        """return an appropriate response if no event can be found"""
        return render(request, self.template_name, {
            'error': "Event not found",
            'event': None
        })

    def get_default_context(self, event, request):
        context = {}
        prefix = request.is_secure() and 'https' or 'http'
        root_url = '%s://%s' % (prefix, RequestSite(request).domain)
        url = reverse('main:event', kwargs={'slug': event.slug})
        context['absolute_url'] = root_url + url
        context['embedded'] = self.embedded
        context['no_warning'] = self.no_warning
        context['no_footer'] = request.GET.get('no-footer')
        return context

    def get(self, request, slug):
        self.embedded = request.GET.get('embedded', 'true') == 'true'
        self.no_warning = request.GET.get('no-warning')

        response = super(EventVideoView, self).get(request, slug)
        # ALLOWALL is what YouTube uses for sharing
        if self.embedded:
            response['X-Frame-Options'] = 'ALLOWALL'
        return response


class EventDiscussionView(EventView):
    template_name = 'main/event_discussion.html'

    def can_edit_discussion(self, event, request):
        # this might change in the future to only be
        # employees and vouched mozillians
        return (
            request.user.is_active and
            request.user == event.creator and
            Discussion.objects.filter(event=event)
        )

    def cant_edit_discussion(self, event, user):
        return redirect('main:event', event.slug)

    def get_event_safely(self, slug, request):
        event = self.get_event(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        if not self.can_view_event(event, request):
            return self.cant_view_event(event, request)
        if not self.can_edit_discussion(event, request):
            return self.cant_edit_discussion(event, request)

        return event

    def get(self, request, slug, form=None):
        event = self.get_event_safely(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        discussion = Discussion.objects.get(event=event)

        if form is None:
            initial = {
                'moderators': ', '.join(
                    x.email for x in discussion.moderators.all()
                ),
            }
            form = forms.EventDiscussionForm(
                instance=discussion,
                event=event,
                initial=initial,
            )

        context = {
            'event': event,
            'form': form,
        }
        return render(request, self.template_name, context)

    @transaction.atomic
    @json_view
    def post(self, request, slug):
        event = self.get_event_safely(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        if 'cancel' in request.POST:
            return redirect('main:event', event.slug)

        discussion = Discussion.objects.get(event=event)

        form = forms.EventDiscussionForm(
            request.POST,
            instance=discussion,
            event=event,
        )

        if form.is_valid():
            form.save()
            return redirect('main:event', event.slug)

        return self.get(request, slug, form=form)


@json_view
def all_tags(request):
    tags = list(Tag.objects.all().values_list('name', flat=True))
    return {'tags': tags}


def related_content(request, slug):
    event = get_object_or_404(Event, slug=slug)

    events, __, __ = find_related_events(event, request.user)

    curated_groups_map = collections.defaultdict(list)

    def get_curated_groups(event):
        return curated_groups_map.get('event_id')

    context = {
        'events': events,
        'get_curated_groups': get_curated_groups,
    }

    return render(request, 'main/es.html', context)


def find_related_events(
    event, user, boost_title=None, boost_tags=None, size=None,
    use_title=True, use_tags=True, explain=False
):
    assert use_title or use_tags
    if boost_title is None:
        boost_title = settings.RELATED_CONTENT_BOOST_TITLE
    if boost_tags is None:
        boost_tags = settings.RELATED_CONTENT_BOOST_TAGS
    if size is None:
        size = settings.RELATED_CONTENT_SIZE
    index = related.get_index()
    doc_type = 'event'

    es = related.get_connection()

    fields = ['title']
    if list(event.channels.all()) != [
            Channel.objects.get(slug=settings.DEFAULT_CHANNEL_SLUG)]:
        fields.append('channel')

    mlt_queries = []
    if use_title:
        mlt_queries.append({
            'more_like_this': {
                'fields': ['title'],
                # 'analyzer': 'snowball',
                'docs': [
                    {
                        '_index': index,
                        '_type': doc_type,
                        '_id': event.id
                    }],
                'min_term_freq': 1,
                'max_query_terms': 20,
                'min_doc_freq': 1,
                # 'max_doc_freq': 2,
                # 'stop_words': ['your', 'about'],
                'boost': boost_title,
            }
        })
    if use_tags and event.tags.all().exists():
        fields.append('tags')
        mlt_queries.append({
            'more_like_this': {
                'fields': ['tags'],
                'docs': [
                    {
                        '_index': index,
                        '_type': doc_type,
                        '_id': event.id
                    }],
                'min_term_freq': 1,
                'max_query_terms': 20,
                'min_doc_freq': 1,
                'boost': boost_tags,
            }
        })

    query_ = {
        'bool': {
            'should': mlt_queries,
        }
    }

    if user.is_active:
        if is_contributor(user):
            query = {
                'fields': fields,
                'query': query_,
                'filter': {
                    'bool': {
                        'must_not': {
                            'term': {
                                'privacy': Event.PRIVACY_COMPANY
                            }
                        }
                    }
                }
            }
        else:
            query = {
                'fields': fields,
                'query': query_
            }
    else:
        query = {
            'fields': fields,
            'query': query_,
            "filter": {
                "bool": {
                    "must": {
                        "term": {"privacy": Event.PRIVACY_PUBLIC}
                    }
                }
            }
        }

    ids = []
    query['from'] = 0
    query['size'] = size
    query['explain'] = explain
    hits = es.search(query, index=index)['hits']

    scores = {}
    explanations = []
    for doc in hits['hits']:
        _id = int(doc['_id'])
        scores[_id] = doc['_score']
        ids.append(_id)
        if explain:
            explanations.append(doc['_explanation'])

    events = Event.objects.scheduled_or_processing().filter(id__in=ids)

    if user.is_active:
        if is_contributor(user):
            events = events.exclude(privacy=Event.PRIVACY_COMPANY)
    else:
        events = events.filter(privacy=Event.PRIVACY_PUBLIC)

    events = sorted(events, key=lambda e: ids.index(e.id))

    return (events, scores, explanations)


def channels(request):
    channels = []

    privacy_filter = {}
    privacy_exclude = {}
    if request.user.is_active:
        if is_contributor(request.user):
            feed_privacy = 'contributors'
            privacy_exclude = {'privacy': Event.PRIVACY_COMPANY}
        else:
            feed_privacy = 'company'
    else:
        privacy_filter = {'privacy': Event.PRIVACY_PUBLIC}
        feed_privacy = 'public'
    events = Event.objects.filter(status=Event.STATUS_SCHEDULED)
    if privacy_filter:
        events = events.filter(**privacy_filter)
    elif privacy_exclude:
        events = events.exclude(**privacy_exclude)

    channels_qs = (
        Channel.objects
        .filter(parent__isnull=True)
        .exclude(slug=settings.DEFAULT_CHANNEL_SLUG)
    )

    # make a dict of parental counts
    subchannel_counts = {}
    qs = (
        Channel.objects
        .filter(parent__isnull=False)
        .values('parent_id')
        .order_by()  # necessary because the model has a default ordering
        .annotate(Count('parent'))
    )
    for each in qs:
        subchannel_counts[each['parent_id']] = each['parent__count']

    # make a dict of events counts by channel
    event_counts = {}
    qs = (
        Event.channels.through.objects.filter(event__in=events)
        .values('channel_id')
        .annotate(Count('channel'))
    )
    for each in qs:
        event_counts[each['channel_id']] = each['channel__count']

    for channel in channels_qs:
        event_count = event_counts.get(channel.id, 0)
        subchannel_count = subchannel_counts.get(channel.id, 0)
        if event_count or subchannel_count:
            channels.append((channel, event_count, subchannel_count))
    data = {
        'channels': channels,
        'feed_privacy': feed_privacy,
    }
    return render(request, 'main/channels.html', data)


class _Tag(object):
    def __init__(self, name, count):
        self.name = name
        self.count = count


def tag_cloud(request, THRESHOLD=1):
    context = {}
    qs = (
        Event.tags.through.objects
        .values('tag_id')
        .annotate(Count('tag__id'))
    )
    if request.user.is_active:
        if is_contributor(request.user):
            # because of a bug in Django we can't use qs.exclude()
            qs = qs.filter(
                Q(event__privacy=Event.PRIVACY_CONTRIBUTORS) |
                Q(event__privacy=Event.PRIVACY_PUBLIC)
            )
    else:
        qs = qs.filter(event__privacy=Event.PRIVACY_PUBLIC)
    tags_map = dict(
        (x['id'], x['name'])
        for x in
        Tag.objects.all()
        .values('id', 'name')
    )
    tags = []
    for each in qs.values('tag__id__count', 'tag_id'):
        count = each['tag__id__count']
        if count > THRESHOLD:
            tags.append(_Tag(tags_map[each['tag_id']], count))

    context['tags'] = cloud.calculate_cloud(
        tags,
        steps=10
    )
    return render(request, 'main/tag_cloud.html', context)


def permission_denied(request, slug):
    context = {}
    event = get_object_or_404(Event, slug=slug)
    context['event'] = event
    context['is_contributor'] = is_contributor(request.user)
    context['is_company_only'] = event.privacy == Event.PRIVACY_COMPANY

    curated_groups = CuratedGroup.objects.filter(event=event).order_by('name')
    context['curated_groups'] = []
    for group in curated_groups:
        context['curated_groups'].append({
            'name': group.name,
            'url': group.url
        })

    return render(request, 'main/permission_denied.html', context)


def contributors(request):
    context = {}
    cache_key = 'mozillians_contributors'
    cache_key += hashlib.md5(str(settings.CONTRIBUTORS)).hexdigest()[:10]
    users = cache.get(cache_key)
    if users is None:
        users = mozillians.get_contributors()
        cache.set(cache_key, users, 60 * 60 * 24)

    context['users'] = reversed(users)
    return render(request, 'main/contributors.html', context)


@never_cache
@json_view
def event_livehits(request, id):
    event = get_object_or_404(Event, id=id)
    if request.method == 'POST' and event.is_live():
        live_hits, _ = EventLiveHits.objects.get_or_create(event=event)

        if request.user.is_authenticated():
            cache_key = 'event_livehits-%d' % request.user.id
        else:
            cache_key = ''
            for thing in (
                'HTTP_USER_AGENT',
                'HTTP_ACCEPT_LANGUAGE',
                'REMOVE_ADDR',
            ):
                value = request.META.get(thing)
                if value:
                    cache_key += value
            cache_key = 'event_livehits' + hashlib.md5(cache_key).hexdigest()
            cache_key = cache_key[:30]
        counted = cache.get(cache_key)
        total_hits = live_hits.total_hits
        if not counted:
            # let's assume the longest possible time it's live is 12 hours
            cache.set(cache_key, True, 60 * 60 * 12)
            # we need to increment!
            (
                EventLiveHits.objects.filter(event=event)
                .update(total_hits=F('total_hits') + 1)
            )
            total_hits += 1
    else:
        try:
            total_hits = EventLiveHits.objects.get(event=event).total_hits
        except EventLiveHits.DoesNotExist:
            total_hits = 0

    return {'hits': total_hits}


@never_cache
@json_view
def event_status(request, slug):
    cache_key = 'event_status_{0}'.format(hashlib.md5(slug).hexdigest())
    status = cache.get(cache_key)
    if status is None:
        status = get_object_or_404(Event, slug=slug).status
        cache.set(cache_key, status, 60 * 60)
    return {'status': status}


@json_view
def thumbnails(request):
    form = forms.ThumbnailsForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(form.errors)
    id = form.cleaned_data['id']
    width = form.cleaned_data['width']
    height = form.cleaned_data['height']
    geometry = '%sx%s' % (width, height)
    event = get_object_or_404(Event, id=id)
    thumbnails = []
    for picture in Picture.objects.filter(event=event).order_by('created'):
        thumb = thumbnail(picture.file, geometry, crop='center')
        thumbnails.append(thumb.url)

    return {'thumbnails': thumbnails}

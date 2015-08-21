import datetime
import hashlib
import json
import urllib
import time
import collections

from django import http
from django.conf import settings
from django.contrib.sites.models import RequestSite
from django.shortcuts import get_object_or_404, redirect, render
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.syndication.views import Feed
from django.views.generic.base import View
from django.db.models import Count, Q, F
from django.db import transaction

from slugify import slugify
from funfactory.urlresolvers import reverse
from jingo import Template
import vobject
from sorl.thumbnail import get_thumbnail
from jsonview.decorators import json_view

from airmozilla.main.models import (
    Event,
    EventOldSlug,
    Tag,
    get_profile_safely,
    Channel,
    Location,
    EventHitStats,
    CuratedGroup,
    EventRevision,
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
from airmozilla.main.helpers import thumbnail
from airmozilla.search.models import LoggedSearch
from airmozilla.comments.models import Discussion
from airmozilla.surveys.models import Survey
from airmozilla.manage import vidly
from airmozilla.manage import related
from airmozilla.main.helpers import short_desc
from airmozilla.base import mozillians
from airmozilla.base.utils import get_base_url
from airmozilla.staticpages.views import staticpage
from . import cloud
from . import forms


def debugger__(request):  # pragma: no cover
    r = http.HttpResponse()
    r.write('BROWSERID_AUDIENCES=%r\n' % settings.BROWSERID_AUDIENCES)
    r.write('Todays date: 2014-05-21 14:02 PST\n')
    r.write('Request secure? %s\n' % request.is_secure())
    r['Content-Type'] = 'text/plain'
    return r


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
            return mozillians.in_groups(
                user.email,
                curated_groups
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
                    return self.cant_find_event(request, slug)

    def get(self, request, slug):
        event = self.get_event(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        if not self.can_view_event(event, request):
            return self.cant_view_event(event, request)

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

        template_tagged = ''
        if event.template and not event.is_upcoming():
            # The only acceptable way to make autoplay be on
            # is to send ?autoplay=true
            # All other attempts will switch it off.
            autoplay = request.GET.get('autoplay', 'false') == 'true'
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
            }
            if isinstance(event.template_environment, dict):
                context.update(event.template_environment)
            template = Template(event.template.content)
            try:
                template_tagged = template.render(context)
            except vidly.VidlyTokenizeError, msg:
                template_tagged = '<code style="color:red">%s</code>' % msg

            stats_query = (
                EventHitStats.objects.filter(event=event)
                .values_list('total_hits', flat=True)
            )
            for total_hits in stats_query:
                hits = total_hits

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
            'Event': Event,
            'hits': hits,
            'tags': [t.name for t in event.tags.all()],
            'channels': request.channels,
            # needed for the _event_privacy.html template
            'curated_groups': CuratedGroup.get_names(event),
        })

        context['chapters'] = []
        for chapter in Chapter.objects.filter(event=event):
            context['chapters'].append({
                'timestamp': chapter.timestamp,
                'text': chapter.text,
            })

        if (
            not (event.is_pending() or event.is_processing()) and
            event.is_public() and
            event.has_vidly_template() and event.template_environment
        ):
            if event.template_environment.get('tag'):
                context['vidly_tag'] = event.template_environment['tag']
                hd = False  # default
                vidly_submissions = (
                    VidlySubmission.objects
                    .filter(event=event, tag=context['vidly_tag'])
                    .order_by('-submission_time')
                )

                for vidly_submission in vidly_submissions.values('hd'):
                    hd = vidly_submission['hd']
                    break

                context['vidly_hd'] = hd

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


class EventRevisionView(EventView):

    template_name = 'main/revision_change.html'
    difference = False

    def can_view_event(self, event, request):
        return (
            request.user.is_active and
            super(EventRevisionView, self).can_view_event(event, request)
        )

    def get(self, request, slug, id):
        event = self.get_event(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        if not self.can_view_event(event, request):
            return self.cant_view_event(event, request)

        revision = get_object_or_404(
            EventRevision,
            event=event,
            pk=id
        )

        if self.difference:
            # compare this revision against the current event
            previous = event
        else:
            previous = revision.get_previous_by_created(event=event)

        fields = (
            ('title', 'Title'),
            ('placeholder_img', 'Placeholder image'),
            ('picture', 'Picture'),
            ('description', 'Description'),
            ('short_description', 'Short description'),
            ('channels', 'Channels'),
            ('tags', 'Tags'),
            ('call_info', 'Call info'),
            ('additional_links', 'Additional links'),
            ('recruitmentmessage', 'Recruitment message'),
        )
        differences = []

        def getter(key, obj):
            if key == 'tags' or key == 'channels':
                return ', '.join(sorted(
                    x.name for x in getattr(obj, key).all()
                ))
            return getattr(obj, key)

        class _Difference(object):
            """use a simple class so we can use dot notation in templates"""
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        for key, label in fields:
            before = getter(key, previous)
            after = getter(key, revision)
            if before != after:
                differences.append(_Difference(
                    key=key,
                    label=label,
                    before=before,
                    after=after
                ))

        context = {}
        context['difference'] = self.difference
        context['event'] = event
        context['revision'] = revision
        context['differences'] = differences
        return render(request, self.template_name, context)


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


class EventEditView(EventView):
    template_name = 'main/event_edit.html'

    def can_edit_event(self, event, request):
        # this might change in the future to only be
        # employees and vouched mozillians
        return request.user.is_active

    def cant_edit_event(self, event, user):
        return redirect('main:event', event.slug)

    @staticmethod
    def event_to_dict(event):
        picture_id = event.picture.id if event.picture else None
        data = {
            'event_id': event.id,
            'title': event.title,
            'description': event.description,
            'short_description': event.short_description,
            'channels': [x.pk for x in event.channels.all()],
            'tags': ', '.join([x.name for x in event.tags.all()]),
            'call_info': event.call_info,
            'additional_links': event.additional_links,
            'recruitmentmessage': None,
            'picture': picture_id
        }
        if event.recruitmentmessage_id:
            data['recruitmentmessage'] = event.recruitmentmessage_id
        if event.placeholder_img:
            data['placeholder_img'] = event.placeholder_img.url
            if event.picture:
                file = event.picture.file
            else:
                file = event.placeholder_img
            data['thumbnail_url'] = (
                get_thumbnail(
                    file,
                    '121x68',
                    crop='center'
                ).url
            )
        return data

    def get(self, request, slug, form=None, conflict_errors=None):
        event = self.get_event(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        if not self.can_view_event(event, request):
            return self.cant_view_event(event, request)
        if not self.can_edit_event(event, request):
            return self.cant_edit_event(event, request)

        initial = self.event_to_dict(event)
        if form is None:
            form = forms.EventEditForm(initial=initial, event=event)
            if not request.user.has_perm('main.change_recruitmentmessage'):
                del form.fields['recruitmentmessage']

        context = {
            'event': event,
            'form': form,
            'previous': json.dumps(initial),
            'conflict_errors': conflict_errors,
        }
        if 'thumbnail_url' in initial:
            context['thumbnail_url'] = initial['thumbnail_url']

        context['revisions'] = (
            EventRevision.objects
            .filter(event=event)
            .order_by('-created')
            .select_related('user')
        )

        return render(request, self.template_name, context)

    @transaction.commit_on_success
    @json_view
    def post(self, request, slug):
        event = self.get_event(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        if not self.can_view_event(event, request):
            return self.cant_view_event(event, request)
        if not self.can_edit_event(event, request):
            return self.cant_edit_event(event, request)

        previous = request.POST['previous']
        previous = json.loads(previous)
        form = forms.EventEditForm(request.POST, request.FILES, event=event)
        base_revision = None

        if form.is_valid():
            if not EventRevision.objects.filter(event=event).count():
                base_revision = EventRevision.objects.create_from_event(event)

            cleaned_data = form.cleaned_data
            if 'placeholder_img' in request.FILES:
                cleaned_data['picture'] = None

            changes = {}
            conflict_errors = []
            for key, value in cleaned_data.items():

                # figure out what the active current value is in the database
                if key == 'placeholder_img':
                    if (
                        event.picture and
                        'placeholder_img' not in request.FILES
                    ):
                        current_value = event.picture.file.url
                    else:
                        if event.placeholder_img:
                            current_value = event.placeholder_img.url
                        else:
                            current_value = None

                elif key == 'tags':
                    current_value = ', '.join(x.name for x in event.tags.all())
                elif key == 'channels':
                    current_value = [x.pk for x in event.channels.all()]
                elif key == 'picture':
                    current_value = event.picture.id if event.picture else None
                elif key == 'event_id':
                    pass
                else:
                    current_value = getattr(event, key)
                    if key == 'recruitmentmessage':
                        if current_value:
                            current_value = current_value.pk

                if key == 'channels':
                    prev = set([
                        Channel.objects.get(pk=x)
                        for x in previous[key]
                    ])
                    value = set(value)
                    for channel in prev - value:
                        event.channels.remove(channel)
                    for channel in value - prev:
                        event.channels.add(channel)
                    if prev != value:
                        changes['channels'] = {
                            'from': ', '.join(
                                sorted(x.name for x in prev)
                            ),
                            'to': ', '.join(
                                sorted(x.name for x in value)
                            )
                        }
                elif key == 'tags':
                    value = set([
                        x.strip()
                        for x in value.split(',')
                        if x.strip()
                    ])
                    prev = set([
                        x.strip()
                        for x in previous['tags'].split(',')
                        if x.strip()
                    ])
                    for tag in prev - value:
                        tag_obj = Tag.objects.get(name=tag)
                        event.tags.remove(tag_obj)
                    for tag in value - prev:
                        try:
                            tag_obj = Tag.objects.get(name__iexact=tag)
                        except Tag.DoesNotExist:
                            tag_obj = Tag.objects.create(name=tag)
                        except Tag.MultipleObjectsReturned:
                            tag_obj, = Tag.objects.filter(name__iexact=tag)[:1]
                        event.tags.add(tag_obj)
                    if prev != value:
                        changes['tags'] = {
                            'from': ', '.join(sorted(prev)),
                            'to': ', '.join(sorted(value))
                        }
                elif key == 'placeholder_img':
                    if value:
                        changes[key] = {
                            'from': (
                                event.placeholder_img and
                                event.placeholder_img.url or
                                ''
                            ),
                            'to': '__saved__event_placeholder_img'
                        }
                        event.placeholder_img = value
                elif key == 'recruitmentmessage':
                    prev = event.recruitmentmessage
                    event.recruitmentmessage = value
                    if value != prev:
                        changes[key] = {
                            'from': prev,
                            'to': event.recruitmentmessage
                        }
                elif key == 'event_id':
                    pass
                else:
                    if value != previous[key]:
                        changes[key] = {
                            'from': previous[key],
                            'to': value
                        }
                        setattr(event, key, value)
                if key in changes:
                    # you wanted to change it, but has your reference changed
                    # since you loaded it?
                    previous_value = previous.get(key)
                    if previous_value != current_value:
                        conflict_errors.append(key)
                        continue

            if conflict_errors:
                return self.get(
                    request,
                    slug,
                    form=form,
                    conflict_errors=conflict_errors
                )
            elif changes:
                event.save()
                EventRevision.objects.create_from_event(
                    event,
                    user=request.user,
                )
            else:
                if base_revision:
                    base_revision.delete()

            return redirect('main:event', event.slug)

        return self.get(request, slug, form=form)


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

    @transaction.commit_on_success
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


def events_calendar_ical(request, privacy=None):
    cache_key = 'calendar'
    if privacy:
        cache_key += '_%s' % privacy
    if request.GET.get('location'):
        if request.GET.get('location').isdigit():
            location = get_object_or_404(
                Location,
                pk=request.GET.get('location')
            )
        else:
            location = get_object_or_404(
                Location,
                name=request.GET.get('location')
            )
        cache_key += str(location.pk)
        cached = None
    else:
        location = None
        cached = cache.get(cache_key)

    if cached:
        # additional response headers aren't remembered so add them again
        cached['Access-Control-Allow-Origin'] = '*'
        return cached
    cal = vobject.iCalendar()

    now = timezone.now()
    base_qs = Event.objects.scheduled_or_processing()
    if privacy == 'public':
        base_qs = base_qs.approved().filter(
            privacy=Event.PRIVACY_PUBLIC
        )
        title = 'Air Mozilla Public Events'
    elif privacy == 'private':
        base_qs = base_qs.exclude(
            privacy=Event.PRIVACY_PUBLIC
        )
        title = 'Air Mozilla Private Events'
    else:
        title = 'Air Mozilla Events'
    if location:
        base_qs = base_qs.filter(location=location)

    cal.add('X-WR-CALNAME').value = title
    events = list(base_qs
                  .filter(start_time__lt=now)
                  .order_by('-start_time')[:settings.CALENDAR_SIZE])
    events += list(base_qs
                   .filter(start_time__gte=now)
                   .order_by('start_time'))
    base_url = get_base_url(request)
    for event in events:
        vevent = cal.add('vevent')
        vevent.add('summary').value = event.title
        vevent.add('dtstart').value = event.start_time
        vevent.add('dtend').value = (
            event.start_time +
            datetime.timedelta(
                seconds=event.duration or event.estimated_duration
            )
        )
        vevent.add('description').value = short_desc(event, strip_html=True)
        if event.location:
            vevent.add('location').value = event.location.name
        vevent.add('url').value = (
            base_url + reverse('main:event', args=(event.slug,))
        )
    icalstream = cal.serialize()
    # response = http.HttpResponse(
    #     icalstream,
    #     content_type='text/plain; charset=utf-8'
    # )
    response = http.HttpResponse(
        icalstream,
        content_type='text/calendar; charset=utf-8'
    )
    filename = 'AirMozillaEvents%s' % (privacy and privacy or '')
    if location:
        filename += '_%s' % slugify(location.name)
    filename += '.ics'
    response['Content-Disposition'] = (
        'inline; filename=%s' % filename)
    if not location:
        cache.set(cache_key, response, 60 * 10)  # 10 minutes

    # https://bugzilla.mozilla.org/show_bug.cgi?id=909516
    response['Access-Control-Allow-Origin'] = '*'

    return response


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


def related_content(request, slug):
    event = get_object_or_404(Event, slug=slug)

    index = settings.ELASTICSEARCH_PREFIX + settings.ELASTICSEARCH_INDEX
    doc_type = 'event'

    es = related.get_connection()

    fields = ['title', 'tags']
    if list(event.channels.all()) != [
            Channel.objects.get(slug=settings.DEFAULT_CHANNEL_SLUG)]:
        fields.append('channel')

    mlt_query1 = {
        'more_like_this': {
            'fields': ['title'],
            'docs': [
                {
                    '_index': index,
                    '_type': doc_type,
                    '_id': event.id
                }],
            'min_term_freq': 1,
            'max_query_terms': 20,
            'min_doc_freq': 1,
            'boost': 1.0,
        }
    }
    mlt_query2 = {
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
            'boost': -0.5,
        }
    }

    query_ = {
        'bool': {
            'should': [mlt_query1, mlt_query2],
        }
    }

    if request.user.is_active:
        if is_contributor(request.user):
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
    hits = es.search(query, index=index)['hits']
    for doc in hits['hits']:
        ids.append(int(doc['_id']))

    events = Event.objects.scheduled_or_processing() \
        .filter(id__in=ids)

    if request.user.is_active:
        if is_contributor(request.user):
            events = events.exclude(privacy=Event.PRIVACY_COMPANY)
    else:
        events = events.filter(privacy=Event.PRIVACY_PUBLIC)

    curated_groups_map = collections.defaultdict(list)
    events = sorted(events, key=lambda e: ids.index(e.id))

    def get_curated_groups(event):
        return curated_groups_map.get('event_id')

    context = {
        'events': events,
        'get_curated_groups': get_curated_groups,
    }

    return render(request, 'main/es.html', context)


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


def calendars(request):
    data = {}
    locations = []
    now = timezone.now()
    time_ago = now - datetime.timedelta(days=30)
    base_qs = Event.objects.filter(start_time__gte=time_ago)
    for location in Location.objects.all().order_by('name'):
        count = base_qs.filter(location=location).count()
        if count:
            locations.append(location)
    data['locations'] = locations
    if request.user.is_active:
        profile = get_profile_safely(request.user)
        if profile and profile.contributor:
            data['calendar_privacy'] = 'contributors'
        else:
            data['calendar_privacy'] = 'company'
    else:
        data['calendar_privacy'] = 'public'
    return render(request, 'main/calendars.html', data)


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
                Q(event__privacy=Event.PRIVACY_CONTRIBUTORS)
                |
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


def calendar(request):
    context = {}
    return render(request, 'main/calendar.html', context)


@json_view
def calendar_data(request):
    form = forms.CalendarDataForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    start = form.cleaned_data['start']
    end = form.cleaned_data['end']

    start = start.replace(tzinfo=utc)
    end = end.replace(tzinfo=utc)

    privacy_filter = {}
    privacy_exclude = {}
    events = Event.objects.scheduled_or_processing()
    if request.user.is_active:
        if is_contributor(request.user):
            privacy_exclude = {'privacy': Event.PRIVACY_COMPANY}
    else:
        privacy_filter = {'privacy': Event.PRIVACY_PUBLIC}
        events = events.approved()

    if privacy_filter:
        events = events.filter(**privacy_filter)
    elif privacy_exclude:
        events = events.exclude(**privacy_exclude)

    events = events.filter(
        start_time__gte=start,
        start_time__lt=end
    )
    event_objects = []
    for event in events.select_related('location'):
        start_time = event.start_time
        end_time = start_time + datetime.timedelta(
            seconds=max(event.duration or event.estimated_duration, 60 * 20)
        )
        # We don't need 'end' because we don't yet know how long the event
        # was or will be.
        event_objects.append({
            'title': event.title,
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'url': reverse('main:event', args=(event.slug,)),
            'description': short_desc(event),
            'allDay': False,
        })

    return event_objects


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


def edgecast_smil(request):
    context = {}
    for key, value in request.GET.items():
        context[key] = value
    response = render(request, 'main/edgecast_smil.xml', context)
    response['Content-Type'] = 'application/smil'
    response['Access-Control-Allow-Origin'] = '*'
    return response


def crossdomain_xml(request):
    response = http.HttpResponse(content_type='text/xml')
    response.write(
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE cross-domain-policy SYSTEM '
        '"http://www.adobe.com/xml/dtds/cross-domain-policy.dtd">\n'
        '<cross-domain-policy>'
        '<allow-access-from domain="*" />'
        '</cross-domain-policy>'
    )
    response['Access-Control-Allow-Origin'] = '*'
    return response


@json_view
def videoredirector(request):  # pragma: no cover
    """this is part of an experiment to try out JW Player on something
    beyong peterbe's laptop."""

    tag = request.GET['tag']
    user_agent = request.META.get('HTTP_USER_AGENT')

    import requests
    response = requests.head(
        'https://vid.ly/%s?content=video' % tag,
        headers={'User-Agent': user_agent}
    )
    assert response.status_code == 302
    url = response.headers['location']

    response = requests.head(
        'https://vid.ly/%s?content=video&format=mp4' % tag
    )
    assert response.status_code == 302
    fallback = response.headers['location']
    urls = [url, fallback]
    return {'urls': urls, 'user_agent': user_agent}


@login_required
def unpicked_pictures(request):
    """returns a report of all events that have pictures in the picture
    gallery but none has been picked yet. """
    pictures = Picture.objects.filter(event__isnull=False)
    events = Event.objects.archived()
    assert request.user.is_active
    if is_contributor(request.user):
        events = events.exclude(privacy=Event.PRIVACY_COMPANY)

    events = events.filter(id__in=pictures.values('event'))
    events = events.exclude(picture__in=pictures)
    count = events.count()
    events = events.order_by('?')[:20]
    pictures_counts = {}
    grouped_pictures = (
        Picture.objects
        .filter(event__in=events)
        .values('event')
        .annotate(Count('event'))
    )
    for each in grouped_pictures:
        pictures_counts[each['event']] = each['event__count']

    context = {
        'count': count,
        'events': events,
        'pictures_counts': pictures_counts,
    }
    return render(request, 'main/unpicked_pictures.html', context)


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


def executive_summary(request):
    form = forms.ExecutiveSummaryForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))
    if form.cleaned_data.get('start'):
        start_date = form.cleaned_data['start']
    else:
        start_date = timezone.now()
        start_date -= datetime.timedelta(days=start_date.weekday())
    # start date is now a Monday
    assert start_date.strftime('%A') == 'Monday'

    def make_date_range_title(start):
        title = "Week of "
        last = start + datetime.timedelta(days=6)
        if start.month == last.month:
            title += start.strftime('%d ')
        else:
            title += start.strftime('%d %B ')
        title += '- ' + last.strftime('%d %B %Y')
        return title

    def get_ranges(start):
        this_week = start.replace(hour=0, minute=0, second=0)
        next_week = this_week + datetime.timedelta(days=7)
        yield ("This Week", this_week, next_week)
        last_week = this_week - datetime.timedelta(days=7)
        yield ("Last Week", last_week, this_week)
        # Subtracting 365 days doesn't mean land on a Monday of last
        # year so we need to trace back to the nearest Monday
        this_week_ly = this_week - datetime.timedelta(days=365)
        this_week_ly = (
            this_week_ly - datetime.timedelta(days=this_week_ly.weekday())
        )
        next_week_ly = this_week_ly + datetime.timedelta(days=7)
        yield ("This Week Last Year", this_week_ly, next_week_ly)
        first_day = this_week.replace(month=1, day=1)
        if first_day.year == next_week.year:
            yield ("Year to Date", first_day, next_week)
        else:
            yield ("Year to Date", first_day, this_week)
        first_day_ny = first_day.replace(year=first_day.year + 1)
        yield ("%s Total" % first_day.year, first_day, first_day_ny)
        last_year = first_day.replace(year=first_day.year - 1)
        yield ("%s Total" % last_year.year, last_year, first_day)
        last_year2 = last_year.replace(year=last_year.year - 1)
        yield ("%s Total" % last_year2.year, last_year2, last_year)
        last_year3 = last_year2.replace(year=last_year2.year - 1)
        yield ("%s Total" % last_year3.year, last_year3, last_year2)

    ranges = get_ranges(start_date)

    rows = []
    for label, start, end in ranges:
        events = Event.objects.all().approved().filter(
            start_time__gte=start, start_time__lt=end
        )
        rows.append((
            label,
            (start, end, end - datetime.timedelta(days=1)),
            events.count(),
            events.filter(location__name__istartswith='Cyberspace').count(),
            events.filter(location__isnull=True).count(),
        ))

    # Now for stats on views, which is done by their archive date
    week_from_today = timezone.now() - datetime.timedelta(days=7)
    stats = (
        EventHitStats.objects
        .exclude(event__archive_time__isnull=True)
        .filter(
            event__archive_time__lt=week_from_today,
        )
        .exclude(event__channels__exclude_from_trending=True)
        .order_by('-score')
        .extra(select={
            'score': '(featured::int + 1) * total_hits'
                     '/ extract(days from (now() - archive_time)) ^ 1.8',
        })
        .select_related('event')
    )

    prev_start = start_date - datetime.timedelta(days=7)
    now = timezone.now()
    if (start_date + datetime.timedelta(days=7)) <= now:
        next_start = start_date + datetime.timedelta(days=7)
    else:
        next_start = None

    context = {
        'date_range_title': make_date_range_title(start_date),
        'rows': rows,
        'stats': stats[:10],
        'prev_start': prev_start,
        'next_start': next_start,
    }
    return render(request, 'main/executive_summary.html', context)


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


def god_mode(request):
    if not (settings.DEBUG and settings.GOD_MODE):
        raise http.Http404()

    if request.method == 'POST':
        from django.contrib.auth.models import User
        user = User.objects.get(email__iexact=request.POST['email'])
        from django.contrib import auth
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth.login(request, user)
        return redirect('/')

    context = {}
    return render(request, 'main/god_mode.html', context)


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

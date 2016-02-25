import re
import urllib
import time

from django.shortcuts import render, redirect, get_object_or_404
from django import http
from django.db.utils import DatabaseError
from django.db import transaction
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST

from jsonview.decorators import json_view

from airmozilla.main.models import Event, Tag, Channel, get_profile_safely
from airmozilla.main.views import is_contributor
from airmozilla.base.utils import paginator
from airmozilla.main.utils import get_event_channels

from . import forms
from . import utils
from .models import LoggedSearch, SavedSearch
from .split_search import split_search


@transaction.atomic
def home(request):
    context = {
        'q': None,
        'events_found': None,
        'search_error': None,
        'tags': None,
        'possible_tags': None,
        'channels': None,
        'possible_channels': None
    }

    if request.GET.get('q'):
        form = forms.SearchForm(request.GET)
    else:
        form = forms.SearchForm()

    if request.GET.get('q') and form.is_valid():
        context['q'] = form.cleaned_data['q']
        privacy_filter = {}
        privacy_exclude = {}
        qs = Event.objects.scheduled_or_processing()
        if request.user.is_active:
            if is_contributor(request.user):
                privacy_exclude = {'privacy': Event.PRIVACY_COMPANY}
        else:
            privacy_filter = {'privacy': Event.PRIVACY_PUBLIC}
            qs = qs.approved()

        extra = {}
        rest, params = split_search(context['q'], ('tag', 'channel'))
        if params.get('tag'):
            tags = Tag.objects.filter(name__iexact=params['tag'])
            if tags:
                context['q'] = rest
                context['tags'] = extra['tags'] = tags
        else:
            # is the search term possibly a tag?
            all_tag_names = Tag.objects.all().values_list('name', flat=True)
            tags_regex = re.compile(
                r'\b(%s)\b' %
                ('|'.join(re.escape(x) for x in all_tag_names),),
                re.I
            )
            # next we need to turn all of these into a Tag QuerySet
            # because we can't do `filter(name__in=tags_regex.findall(...))`
            # because that case sensitive.
            tag_ids = []
            for match in tags_regex.findall(rest):
                tag_ids.extend(
                    Tag.objects.filter(name__iexact=match)
                    .values_list('id', flat=True)
                )
            possible_tags = Tag.objects.filter(
                id__in=tag_ids
            )
            for tag in possible_tags:
                regex = re.compile(re.escape(tag.name), re.I)
                tag._query_string = regex.sub(
                    '',
                    context['q'],
                )
                tag._query_string += ' tag: %s' % tag.name
                # reduce all excess whitespace into 1
                tag._query_string = re.sub(
                    '\s\s+',
                    ' ',
                    tag._query_string
                )
                tag._query_string = tag._query_string.strip()
            context['possible_tags'] = possible_tags

        if params.get('channel'):
            channels = Channel.objects.filter(name__iexact=params['channel'])
            if channels:
                context['q'] = rest
                context['channels'] = extra['channels'] = channels
        else:
            # is the search term possibly a channel?
            all_channel_names = (
                Channel.objects.all().values_list('name', flat=True)
            )
            channels_regex = re.compile(
                r'\b(%s)\b' %
                ('|'.join(re.escape(x) for x in all_channel_names),),
                re.I
            )
            channel_ids = []
            for match in channels_regex.findall(rest):
                channel_ids.extend(
                    Channel.objects
                    .filter(name__iexact=match).values_list('id', flat=True)
                )
            possible_channels = Channel.objects.filter(
                id__in=channel_ids
            )
            for channel in possible_channels:
                regex = re.compile(re.escape(channel.name), re.I)
                channel._query_string = regex.sub(
                    '',
                    context['q'],
                )
                channel._query_string += ' channel: %s' % channel.name
                # reduce all excess whitespace into 1
                channel._query_string = re.sub(
                    '\s\s+',
                    ' ',
                    channel._query_string
                )
                channel._query_string = channel._query_string.strip()
            context['possible_channels'] = possible_channels

        events = _search(
            qs,
            context['q'],
            privacy_filter=privacy_filter,
            privacy_exclude=privacy_exclude,
            sort=request.GET.get('sort'),
            **extra
        )
        if not events.count() and utils.possible_to_or_query(context['q']):
            events = _search(
                qs,
                context['q'],
                privacy_filter=privacy_filter,
                privacy_exclude=privacy_exclude,
                sort=request.GET.get('sort'),
                fuzzy=True
            )
    elif request.GET.get('ss'):
        savedsearch = get_object_or_404(
            SavedSearch,
            id=request.GET.get('ss')
        )
        context['savedsearch'] = savedsearch
        events = savedsearch.get_events()
        # But if you're just browsing we want to make sure you don't
        # see anything you're not supposed to see.
        if request.user.is_active:
            if is_contributor(request.user):
                events = events.exclude(privacy=Event.PRIVACY_COMPANY)
        else:
            events = events.filter(privacy=Event.PRIVACY_PUBLIC)

        # It's not obvious how to sort these. They all match the saved
        # search.
        # Let's keep it simple and sort by start time for now
        events = events.order_by('-start_time')
    else:
        events = None

    if events is not None:

        try:
            page = int(request.GET.get('page', 1))
            if page < 1:
                raise ValueError
        except ValueError:
            return http.HttpResponseBadRequest('Invalid page')

        # we use the paginator() function to get the Paginator
        # instance so we can avoid calling `events.count()` for the
        # header of the page where it says "XX events found"
        try:
            with transaction.atomic():
                pager, events_paged = paginator(events, page, 10)
            _database_error_happened = False
        except DatabaseError:
            _database_error_happened = True
            # don't feed the trolls, just return nothing found
            pager, events_paged = paginator(Event.objects.none(), 1, 10)

        next_page_url = prev_page_url = None

        def url_maker(page):
            querystring = {'page': page}
            if context.get('savedsearch'):
                querystring['ss'] = context['savedsearch'].id
            else:
                querystring['q'] = context['q'].encode('utf-8')
            querystring = urllib.urlencode(querystring)
            return '%s?%s' % (reverse('search:home'), querystring)

        if events_paged.has_next():
            next_page_url = url_maker(events_paged.next_page_number())
        if events_paged.has_previous():
            prev_page_url = url_maker(events_paged.previous_page_number())

        context['events_paged'] = events_paged
        context['next_page_url'] = next_page_url
        context['prev_page_url'] = prev_page_url
        context['events_found'] = pager.count
        context['channels'] = get_event_channels(events_paged)

        log_searches = settings.LOG_SEARCHES and '_nolog' not in request.GET
        if (
            log_searches and
            not _database_error_happened and
            request.GET.get('q', '').strip()
        ):
            logged_search = LoggedSearch.objects.create(
                term=request.GET['q'][:200],
                results=events.count(),
                page=page,
                user=request.user.is_authenticated() and request.user or None
            )
            request.session['logged_search'] = (
                logged_search.pk,
                time.time()
            )
    elif request.GET.get('q'):
        context['search_error'] = form.errors['q']
    else:
        context['events'] = []

    context['form'] = form
    return render(request, 'search/home.html', context)


def _search(qs, q, **options):
    # we only want to find upcoming or archived events

    # some optional filtering
    if 'tags' in options:
        qs = qs.filter(tags__in=options['tags'])
    if 'channels' in options:
        qs = qs.filter(channels__in=options['channels'])

    if options.get('privacy_filter'):
        qs = qs.filter(**options['privacy_filter'])
    elif options.get('privacy_exclude'):
        qs = qs.exclude(**options['privacy_exclude'])

    if q and options.get('fuzzy'):
        sql = """
        (
          to_tsvector('english', title) @@ to_tsquery('english', %s)
          OR
          to_tsvector('english', description || ' ' || short_description)
           @@ to_tsquery('english', %s)
          OR
          to_tsvector('english', transcript) @@ to_tsquery('english', %s)
        )
        """
        search_escaped = utils.make_or_query(q)
    elif q:
        sql = """
        (
          to_tsvector('english', title) @@ plainto_tsquery('english', %s)
          OR
          to_tsvector('english', description || ' ' || short_description)
           @@ plainto_tsquery('english', %s)
          OR
          to_tsvector('english', transcript) @@ plainto_tsquery('english', %s)
        )
        """
        search_escaped = q

    if q:
        qs = qs.extra(
            where=[sql],
            params=[search_escaped, search_escaped, search_escaped],
            select={
                'title_highlit': (
                    "ts_headline('english', title, "
                    "plainto_tsquery('english', %s))"
                ),
                'desc_highlit': (
                    "ts_headline('english', short_description, "
                    "plainto_tsquery('english', %s))"
                ),
                'transcript_highlit': (
                    "ts_headline('english', transcript, "
                    "plainto_tsquery('english', %s))"
                ),
                'rank_title': (
                    "ts_rank_cd(to_tsvector('english', title), "
                    "plainto_tsquery('english', %s))"
                ),
                'rank_desc': (
                    "ts_rank_cd(to_tsvector('english', description "
                    "|| ' ' || short_description), "
                    "plainto_tsquery('english', %s))"
                ),
                'rank_transcript': (
                    "ts_rank_cd(to_tsvector('english', transcript), "
                    "plainto_tsquery('english', %s))"
                ),

            },
            select_params=[
                search_escaped,
                search_escaped,
                search_escaped,
                search_escaped,
                search_escaped,
                search_escaped
            ],
        )
        qs = qs.order_by('-rank_title', '-start_time', '-rank_desc')
    else:
        qs = qs.order_by('-start_time')
    return qs


@require_POST
@login_required
@transaction.atomic()
def savesearch(request):
    q = request.POST.get('q', '').strip()
    if not q:
        return http.HttpResponseBadRequest('no q')
    form = forms.SearchForm(request.POST)
    if not form.is_valid():
        return http.HttpResponseBadRequest(form.errors)

    title = form.cleaned_data['q']
    rest, params = split_search(title, ('tag', 'channel'))
    tags = None
    channels = None
    if params.get('tag'):
        tags = Tag.objects.filter(name__iexact=params['tag'])
        if tags:
            title = rest
    if params.get('channel'):
        channels = Channel.objects.filter(
            name__iexact=params['channel']
        )
        if channels:
            title = rest

    filters = {}
    if q:
        filters['title'] = {
            'include': title
        }
    if tags:
        filters['tags'] = {
            'include': [tag.id for tag in tags],
        }
    if channels:
        filters['channels'] = {
            'include': [channel.id for channel in channels],
        }

    for other in SavedSearch.objects.filter(user=request.user):
        if other.filters == filters:
            return redirect('search:savedsearch', id=other.id)

    savedsearch = SavedSearch.objects.create(
        user=request.user,
        filters=filters,
    )
    messages.success(
        request,
        'Search saved'
    )
    return redirect('search:savedsearch', id=savedsearch.id)


@login_required
@transaction.atomic()
def savedsearch(request, id=None):
    savedsearch = get_object_or_404(SavedSearch, id=id)

    if request.method == 'POST':
        forked = False
        if savedsearch.user != request.user:
            # fork the saved search
            forked = True
            savedsearch = SavedSearch.objects.create(
                user=request.user,
                name=savedsearch.name,
                filters=savedsearch.filters,
            )
        form = forms.SavedSearchForm(request.POST)
        if form.is_valid():
            data = form.export_filters()
            savedsearch.name = form.cleaned_data['name']
            savedsearch.filters = data
            savedsearch.save()

            if forked:
                messages.success(
                    request,
                    'Saved Search forked and saved'
                )
            else:
                messages.success(
                    request,
                    'Saved Search saved'
                )
            return redirect('search:savedsearch', id=savedsearch.id)
    elif request.GET.get('sample'):
        events = savedsearch.get_events()
        return http.JsonResponse({'events': events.count()})
    else:
        data = forms.SavedSearchForm.convert_filters(
            savedsearch.filters,
            pks=True
        )
        data['name'] = savedsearch.name
        form = forms.SavedSearchForm(data)

    context = {
        'savedsearch': savedsearch,
        'form': form,
        'use_findable': True,
    }
    return render(request, 'search/savesearch.html', context)


@login_required
@transaction.atomic()
def new_savedsearch(request):
    if request.method == 'POST':
        form = forms.SavedSearchForm(request.POST)
        if form.is_valid():
            data = form.export_filters()
            SavedSearch.objects.create(
                user=request.user,
                filters=data,
                name=form.cleaned_data['name'],
            )
            messages.success(
                request,
                'Saved Search saved'
            )
            return redirect('search:savedsearches')
    else:
        form = forms.SavedSearchForm()

    context = {
        'form': form,
        'use_findable': False,
    }
    return render(request, 'search/savesearch.html', context)


@login_required
def savedsearches(request):
    context = {}
    return render(request, 'search/savedsearches.html', context)


@login_required
@json_view
def savedsearches_data(request):
    context = {}
    qs = SavedSearch.objects.filter(
        user=request.user
    ).order_by('-created')
    searches = []
    for savedsearch in qs:
        item = {
            'id': savedsearch.id,
            'name': savedsearch.name,
            'summary': savedsearch.summary,
            'modified': savedsearch.modified.isoformat(),
        }
        searches.append(item)

    # We need a general Feed URL that is tailored to this user
    from airmozilla.main.context_processors import base
    feed = base(request)['get_feed_data']()

    if request.user.is_active:
        profile = get_profile_safely(request.user)
        if profile and profile.contributor:
            calendar_privacy = 'contributors'
        else:
            calendar_privacy = 'company'
    else:
        calendar_privacy = 'public'

    context['savedsearches'] = searches
    context['urls'] = {
        'search:savedsearch': reverse('search:savedsearch', args=(0,)),
        'search:home': reverse('search:home'),
        'feed': feed['url'],
        'ical': reverse('main:calendar_ical', args=(calendar_privacy,)),

    }
    return context


@login_required
@json_view
def delete_savedsearch(request, id):
    savedsearch = get_object_or_404(SavedSearch, id=id)
    if savedsearch.user != request.user:
        return http.HttpResponseForbidden('Not yours to delete')
    savedsearch.delete()
    return {'ok': True}

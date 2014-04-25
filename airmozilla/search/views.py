import urllib

from django.shortcuts import render
from django import http
from django.db.utils import DatabaseError
from django.db import connection

from airmozilla.main.models import Event
from airmozilla.main.views import is_contributor

from funfactory.urlresolvers import reverse

from . import forms
from . import utils
from airmozilla.base.utils import paginator


def home(request):
    context = {
        'q': None,
        'events_found': None,
        'search_error': None,
    }

    if request.GET.get('q'):
        form = forms.SearchForm(request.GET)
    else:
        form = forms.SearchForm()

    if request.GET.get('q') and form.is_valid():
        context['q'] = form.cleaned_data['q']
        privacy_filter = {}
        privacy_exclude = {}
        if request.user.is_active:
            if is_contributor(request.user):
                privacy_exclude = {'privacy': Event.PRIVACY_COMPANY}
        else:
            privacy_filter = {'privacy': Event.PRIVACY_PUBLIC}

        events = _search(
            context['q'],
            privacy_filter=privacy_filter,
            privacy_exclude=privacy_exclude,
            sort=request.GET.get('sort'),
        )
        if not events.count() and utils.possible_to_or_query(context['q']):
            events = _search(
                context['q'],
                privacy_filter=privacy_filter,
                privacy_exclude=privacy_exclude,
                sort=request.GET.get('sort'),
                fuzzy=True
            )

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
            pager, events_paged = paginator(events, page, 10)
        except DatabaseError:
            # If the fulltext SQL causes a low-level Postgres error,
            # Django re-wraps the exception as a django.db.utils.DatabaseError
            # exception and then unfortunately you can't simply do
            # django.db.transaction.rollback() because the connection is dirty
            # deeper down.
            # Thanks http://stackoverflow.com/a/7753748/205832
            # This is supposedly fixed in Django 1.6
            connection._rollback()

            # don't feed the trolls, just return nothing found
            pager, events_paged = paginator(Event.objects.none(), 1, 10)

        next_page_url = prev_page_url = None

        def url_maker(page):
            querystring = {'q': context['q'], 'page': page}
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
    elif request.GET.get('q'):
        context['search_error'] = form.errors['q']
    else:
        context['events'] = []

    context['form'] = form
    return render(request, 'search/home.html', context)


def _search(q, **options):
    qs = Event.objects.approved()
    # we only want to find upcoming or archived events

    if options.get('privacy_filter'):
        qs = qs.filter(**options['privacy_filter'])
    elif options.get('privacy_exclude'):
        qs = qs.exclude(**options['privacy_exclude'])

    if options.get('sort') == 'date':
        raise NotImplementedError

    if options.get('fuzzy'):
        sql = """
        (
          to_tsvector('english', title) @@ to_tsquery('english', %s)
          OR
          to_tsvector('english', description || ' ' || short_description)
           @@ to_tsquery('english', %s)
        )
        """
        search_escaped = utils.make_or_query(q)
    else:
        sql = """
        (
          to_tsvector('english', title) @@ plainto_tsquery('english', %s)
          OR
          to_tsvector('english', description || ' ' || short_description)
           @@ plainto_tsquery('english', %s)
        )
        """
        search_escaped = q
    qs = qs.extra(
        where=[sql],
        params=[search_escaped, search_escaped],
        select={
            'title_highlit': "ts_headline('english', title, "
                             "plainto_tsquery('english', %s))",
            'desc_highlit': "ts_headline('english', short_description, "
                            "plainto_tsquery('english', %s))",
            'rank_title': "ts_rank_cd(to_tsvector('english', title), "
                          "plainto_tsquery('english', %s))",
            'rank_desc': "ts_rank_cd(to_tsvector('english', description "
                         "|| ' ' || short_description), "
                         "plainto_tsquery('english', %s))",
        },
        select_params=[
            search_escaped,
            search_escaped,
            search_escaped,
            search_escaped
        ],
    )
    qs = qs.order_by('-rank_title', '-start_time', '-rank_desc')
    return qs

import urllib

from django.shortcuts import render
from django import http

from airmozilla.main.models import Event
from airmozilla.main.views import is_contributor

from funfactory.urlresolvers import reverse

from . import forms
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

    def possible_to_or_query(q):
        """return true if it's possible to turn this query into something with
        | characters in between"""
        if len(q.split()) > 1:
            if '&' in q or '|' in q:
                return False
            return True
        return False

    if request.GET.get('q') and form.is_valid():
        context['q'] = request.GET.get('q')
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
        if not events.count() and possible_to_or_query(context['q']):
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
        pager, events_paged = paginator(events, page, 10)
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
        search_escaped = q.replace(' ', '|')
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
    qs = qs.order_by('-rank_title', '-rank_desc', '-start_time')
    return qs

import datetime
from collections import defaultdict

from django.contrib.auth.models import User
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum
from django.template.defaultfilters import filesizeformat

from jsonview.decorators import json_view

from airmozilla.main.models import (
    Event,
    SuggestedEvent,
    Picture,
    EventRevision,
    Chapter,
)
from airmozilla.starred.models import StarredEvent
from airmozilla.comments.models import Comment
from airmozilla.uploads.models import Upload

from .decorators import staff_required


@staff_required
def dashboard(request):
    """Management home / explanation page."""
    return render(request, 'manage/dashboard.html')


@staff_required
@json_view
def dashboard_data(request):
    context = {}
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + datetime.timedelta(days=1)
    yesterday = today - datetime.timedelta(days=1)
    this_week = today - datetime.timedelta(days=today.weekday())
    next_week = this_week + datetime.timedelta(days=7)
    last_week = this_week - datetime.timedelta(days=7)
    this_month = today.replace(day=1)
    next_month = this_month
    while next_month.month == this_month.month:
        next_month += datetime.timedelta(days=1)
    last_month = (this_month - datetime.timedelta(days=1)).replace(day=1)
    this_year = this_month.replace(month=1)
    next_year = this_year.replace(year=this_year.year + 1)
    last_year = this_year.replace(year=this_year.year - 1)
    context['groups'] = []

    def make_filter(key, gte=None, lt=None):
        filter = {}
        if gte is not None:
            filter['%s__gte' % key] = gte
        if lt is not None:
            filter['%s__lt' % key] = lt
        return filter

    def get_counts(qs, key):
        counts = {}

        counts['today'] = qs.filter(
            **make_filter(key, gte=today, lt=tomorrow)
        ).count()
        counts['yesterday'] = qs.filter(
            **make_filter(key, gte=yesterday, lt=today)).count()

        counts['this_week'] = qs.filter(
            **make_filter(key, gte=this_week, lt=next_week)).count()
        counts['last_week'] = qs.filter(
            **make_filter(key, gte=last_week, lt=this_week)).count()

        counts['this_month'] = qs.filter(
            **make_filter(key, gte=this_month, lt=next_month)).count()
        counts['last_month'] = qs.filter(
            **make_filter(key, gte=last_month, lt=this_month)).count()

        counts['this_year'] = qs.filter(
            **make_filter(key, gte=this_year, lt=next_year)).count()
        counts['last_year'] = qs.filter(
            **make_filter(key, gte=last_year, lt=this_year)).count()

        counts['ever'] = qs.count()
        return counts

    # Events
    events = Event.objects.exclude(status=Event.STATUS_REMOVED)
    counts = get_counts(events, 'start_time')
    context['groups'].append({
        'name': 'New Events',
        'counts': counts
    })

    # Suggested Events
    counts = get_counts(SuggestedEvent.objects.all(), 'created')
    context['groups'].append({
        'name': 'Requested Events',
        'counts': counts
    })

    # Users
    counts = get_counts(User.objects.all(), 'date_joined')
    context['groups'].append({
        'name': 'New Users',
        'counts': counts
    })

    # Comments
    counts = get_counts(Comment.objects.all(), 'created')
    context['groups'].append({
        'name': 'Comments',
        'counts': counts
    })

    # Event revisions
    counts = get_counts(EventRevision.objects.all(), 'created')
    context['groups'].append({
        'name': 'Event Revisions',
        'counts': counts
    })

    # Pictures
    counts = get_counts(Picture.objects.all(), 'created')
    context['groups'].append({
        'name': 'Pictures',
        'counts': counts
    })

    # Chapters
    counts = get_counts(Chapter.objects.all(), 'created')
    context['groups'].append({
        'name': 'Chapters',
        'counts': counts
    })

    # Starred events
    counts = get_counts(StarredEvent.objects.all(), 'created')
    context['groups'].append({
        'name': 'Starred events',
        'counts': counts
    })

    def get_duration_totals(qs, key='start_time'):

        # def make_filter(gte=None, lt=None):
        #     filter = {}
        #     if gte is not None:
        #         filter['%s__gte' % key] = gte
        #     if lt is not None:
        #         filter['%s__lt' % key] = lt
        #     return filter

        counts = {}

        def sum(elements):
            seconds = elements.aggregate(Sum('duration'))['duration__sum']
            seconds = seconds or 0  # in case it's None
            minutes = seconds / 60
            hours = minutes / 60
            if hours > 1:
                return "%dh" % hours
            elif minutes > 1:
                return "%dm" % minutes
            return "%ds" % seconds

        counts['today'] = sum(qs.filter(
            **make_filter(key, gte=today)))
        counts['yesterday'] = sum(qs.filter(
            **make_filter(key, gte=yesterday, lt=today)))

        counts['this_week'] = sum(qs.filter(
            **make_filter(key, gte=this_week)))
        counts['last_week'] = sum(qs.filter(
            **make_filter(key, gte=last_week, lt=this_week)))

        counts['this_month'] = sum(qs.filter(
            **make_filter(key, gte=this_month)))
        counts['last_month'] = sum(qs.filter(
            **make_filter(key, gte=last_month, lt=this_month)))

        counts['this_year'] = sum(qs.filter(
            **make_filter(key, gte=this_year)))
        counts['last_year'] = sum(qs.filter(
            **make_filter(key, gte=last_year, lt=this_year)))

        counts['ever'] = sum(qs)
        return counts

    def get_size_totals(qs, key='created'):

        counts = {}

        def sum(elements):
            bytes = elements.aggregate(Sum('size'))['size__sum']
            return filesizeformat(bytes)

        counts['today'] = sum(qs.filter(
            **make_filter(key, gte=today)))
        counts['yesterday'] = sum(qs.filter(
            **make_filter(key, gte=yesterday, lt=today)))

        counts['this_week'] = sum(qs.filter(
            **make_filter(key, gte=this_week)))
        counts['last_week'] = sum(qs.filter(
            **make_filter(key, gte=last_week, lt=this_week)))

        counts['this_month'] = sum(qs.filter(
            **make_filter(key, gte=this_month)))
        counts['last_month'] = sum(qs.filter(
            **make_filter(key, gte=last_month, lt=this_month)))

        counts['this_year'] = sum(qs.filter(
            **make_filter(key, gte=this_year)))
        counts['last_year'] = sum(qs.filter(
            **make_filter(key, gte=last_year, lt=this_year)))

        counts['ever'] = sum(qs)
        return counts

    # Exceptional
    counts = get_duration_totals(Event.objects.exclude(duration__isnull=True))
    context['groups'].append({
        'name': 'Total Event Durations',
        'counts': counts
    })

    counts = get_size_totals(Upload.objects.all())
    context['groups'].append({
        'name': 'Uploads',
        'counts': counts,
        'small': True
    })

    return context


@staff_required
def dashboard_graphs(request):  # pragma: no cover
    """experimental"""
    return render(request, 'manage/dashboard_graphs.html')


@staff_required
@json_view
def dashboard_data_graphs(request):  # pragma: no cover
    """experimental"""
    YEARS = 3
    now = timezone.now()

    def get_events(years_back):
        first_date = datetime.datetime(now.year - years_back + 1, 1, 1)

        objects = (
            Event.objects
            .filter(archive_time__lt=now)
            .filter(created__gt=first_date.replace(tzinfo=timezone.utc))
            .order_by('created')
        )
        buckets = {}
        for each in objects.values_list('created'):
            created, = each
            year = created.year
            if year not in buckets:
                buckets[year] = defaultdict(int)
            next_monday = created + datetime.timedelta(
                days=7 - created.weekday()
            )
            key = next_monday.strftime('%Y-%m-%d')
            buckets[year][key] += 1
        legends = sorted(buckets.keys())

        last_year = legends[-1]

        def fake_year(date_str, year):
            return date_str.replace(str(year), str(last_year))

        data = []
        for year in legends:
            group = sorted(
                {'date': fake_year(k, year), 'value': v}
                for k, v in buckets[year].items()
            )
            data.append(group)
        return {
            'type': 'events',
            'title': 'New Events',
            'data': data,
            'description': 'Number of added events per year',
            'legends': legends,
        }

    def get_revisions(years_back):
        first_date = datetime.datetime(now.year - years_back + 1, 1, 1)

        objects = (
            EventRevision.objects
            .filter(created__gt=first_date.replace(tzinfo=timezone.utc))
            .order_by('created')
        )
        buckets = {}
        for each in objects.values_list('created'):
            created, = each
            year = created.year
            if year not in buckets:
                buckets[year] = defaultdict(int)
            next_monday = created + datetime.timedelta(
                days=7 - created.weekday()
            )
            key = next_monday.strftime('%Y-%m-%d')
            buckets[year][key] += 1
        legends = sorted(buckets.keys())

        last_year = legends[-1]

        def fake_year(date_str, year):
            return date_str.replace(str(year), str(last_year))

        data = []
        for year in legends:
            group = sorted(
                {'date': fake_year(k, year), 'value': v}
                for k, v in buckets[year].items()
            )
            data.append(group)
        return {
            'type': 'revisions',
            'title': 'Event Revisions',
            'data': data,
            'description': 'Number of event edits per year',
            'legends': legends,
        }

    def get_users(years_back):
        first_date = datetime.datetime(now.year - years_back + 1, 1, 1)

        objects = (
            User.objects
            .filter(date_joined__gt=first_date.replace(tzinfo=timezone.utc))
            .order_by('date_joined')
        )
        buckets = {}
        for each in objects.values_list('date_joined'):
            created, = each
            year = created.year
            if year not in buckets:
                buckets[year] = defaultdict(int)
            next_monday = created + datetime.timedelta(
                days=7 - created.weekday()
            )
            key = next_monday.strftime('%Y-%m-%d')
            buckets[year][key] += 1
        legends = sorted(buckets.keys())

        last_year = legends[-1]

        def fake_year(date_str, year):
            return date_str.replace(str(year), str(last_year))

        data = []
        for year in legends:
            group = sorted(
                {'date': fake_year(k, year), 'value': v}
                for k, v in buckets[year].items()
            )
            data.append(group)
        return {
            'type': 'users',
            'title': 'New Users',
            'data': data,
            'description': 'Number of first joining users per year',
            'legends': legends,
        }

    groups = []
    groups.append(get_events(YEARS))
    groups.append(get_users(YEARS))
    groups.append(get_revisions(2))
    return {'groups': groups}

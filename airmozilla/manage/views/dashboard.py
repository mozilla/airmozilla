import datetime

from django.contrib.auth.models import User
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum

from jsonview.decorators import json_view

from airmozilla.main.models import (
    Event,
    SuggestedEvent,
    Picture,
    EventRevision,
)
from airmozilla.starred.models import StarredEvent
from airmozilla.comments.models import Comment

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

    def get_counts(qs, key):
        counts = {}

        def make_filter(gte=None, lt=None):
            filter = {}
            if gte is not None:
                filter['%s__gte' % key] = gte
            if lt is not None:
                filter['%s__lt' % key] = lt
            return filter

        counts['today'] = qs.filter(
            **make_filter(gte=today, lt=tomorrow)
        ).count()
        counts['yesterday'] = qs.filter(
            **make_filter(gte=yesterday, lt=today)).count()

        counts['this_week'] = qs.filter(
            **make_filter(gte=this_week, lt=next_week)).count()
        counts['last_week'] = qs.filter(
            **make_filter(gte=last_week, lt=this_week)).count()

        counts['this_month'] = qs.filter(
            **make_filter(gte=this_month, lt=next_month)).count()
        counts['last_month'] = qs.filter(
            **make_filter(gte=last_month, lt=this_month)).count()

        counts['this_year'] = qs.filter(
            **make_filter(gte=this_year, lt=next_year)).count()
        counts['last_year'] = qs.filter(
            **make_filter(gte=last_year, lt=this_year)).count()

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

    # Starred events
    counts = get_counts(StarredEvent.objects.all(), 'created')
    context['groups'].append({
        'name': 'Starred events',
        'counts': counts
    })

    def get_duration_totals(qs):

        key = 'start_time'

        def make_filter(gte=None, lt=None):
            filter = {}
            if gte is not None:
                filter['%s__gte' % key] = gte
            if lt is not None:
                filter['%s__lt' % key] = lt
            return filter

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

        counts['today'] = sum(qs.filter(**make_filter(gte=today)))
        counts['yesterday'] = sum(qs.filter(
            **make_filter(gte=yesterday, lt=today)))

        counts['this_week'] = sum(qs.filter(**make_filter(gte=this_week)))
        counts['last_week'] = sum(qs.filter(
            **make_filter(gte=last_week, lt=this_week)))

        counts['this_month'] = sum(qs.filter(**make_filter(gte=this_month)))
        counts['last_month'] = sum(qs.filter(
            **make_filter(gte=last_month, lt=this_month)))

        counts['this_year'] = sum(qs.filter(**make_filter(gte=this_year)))
        counts['last_year'] = sum(qs.filter(
            **make_filter(gte=last_year, lt=this_year)))

        counts['ever'] = sum(qs)
        return counts

    # Exceptional
    counts = get_duration_totals(Event.objects.exclude(duration__isnull=True))
    context['groups'].append({
        'name': 'Total Event Durations',
        'counts': counts
    })

    return context

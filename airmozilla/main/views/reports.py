import datetime

from django import http
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required

from airmozilla.main.models import (
    Event,
    EventHitStats,
    Tag,
    EventRevision,
    Picture
)
from airmozilla.main.views import is_contributor
from airmozilla.main import forms


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


@login_required
@transaction.atomic
def too_few_tags(request):
    """returns a report of all events that very few tags"""
    if request.method == 'POST':
        form = forms.EventEditTagsForm(request.POST)
        if form.is_valid():
            event = get_object_or_404(Event, id=form.cleaned_data['event_id'])
            assert request.user.is_active
            if is_contributor(request.user):
                assert event.privacy != Event.PRIVACY_COMPANY

            if not EventRevision.objects.filter(event=event).count():
                EventRevision.objects.create_from_event(event)

            value = set([
                x.strip()
                for x in form.cleaned_data['tags'].split(',')
                if x.strip()
            ])
            prev = set([x.name for x in event.tags.all()])
            for tag in prev - value:
                tag_obj = Tag.objects.get(name=tag)
                event.tags.remove(tag_obj)
            added = []
            for tag in value - prev:
                try:
                    tag_obj = Tag.objects.get(name__iexact=tag)
                except Tag.DoesNotExist:
                    tag_obj = Tag.objects.create(name=tag)
                except Tag.MultipleObjectsReturned:
                    tag_obj, = Tag.objects.filter(name__iexact=tag)[:1]
                event.tags.add(tag_obj)
                added.append(tag_obj)
            EventRevision.objects.create_from_event(
                event,
                user=request.user
            )
            messages.success(
                request,
                'Thank you for adding: %s' % ', '.join(x.name for x in added)
            )
            return redirect('main:too_few_tags')

    zero_tags = (
        Event.objects.scheduled_or_processing()
        .exclude(id__in=Event.tags.through.objects.values('event_id'))
    )
    few_tags = (
        Event.tags.through.objects
        .filter(event__status=Event.STATUS_SCHEDULED)
        .values('event_id')
        .annotate(count=Count('event'))
        .filter(count__lt=2)
    )

    assert request.user.is_active
    if is_contributor(request.user):
        few_tags = few_tags.exclude(event__privacy=Event.PRIVACY_COMPANY)
        zero_tags = zero_tags.exclude(privacy=Event.PRIVACY_COMPANY)

    count = zero_tags.count()
    count += few_tags.count()
    try:
        event, = zero_tags.order_by('?')[:1]
    except ValueError:
        event = None
        if few_tags.count():
            try:
                first, = few_tags.order_by('?')[:1]
                event = Event.objects.get(id=first['event_id'])
            except ValueError:
                # there's nothing!
                event = None
                assert count == 0

    context = {
        'count': count,
        'event': event,
    }
    if event:
        initial = {
            'tags': ', '.join(x.name for x in event.tags.all()),
            'event_id': event.id,
        }
        context['form'] = forms.EventEditTagsForm(
            initial=initial,
            instance=event
        )

    return render(request, 'main/too_few_tags.html', context)

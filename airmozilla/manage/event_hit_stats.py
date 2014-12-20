import logging
import datetime

from django.utils import timezone

from airmozilla.main.models import Event, EventHitStats
from . import vidly


# this is what the cron job fires every X minutes
def update(cap=10, swallow_errors=False):
    count = 0

    # first do those that have never been updated
    _stats_ids_qs = (
        EventHitStats.objects.all()
        .values_list('event_id', flat=True)
    )
    qs = (
        Event.objects
        .archived()
        .filter(template__name__contains='Vid.ly',
                template_environment__contains='"tag"')
        .exclude(id__in=_stats_ids_qs)
    )

    for event in qs.order_by('created')[:cap]:  # oldest first
        environment = event.template_environment or {}
        tag = environment.get('tag')
        if not tag or tag == 'None':
            logging.warn("Event %r does not have a Vid.ly tag", event.title)
            continue

        try:
            hits = vidly.statistics(tag)['total_hits']
            count += 1
        except:
            if not swallow_errors:
                raise
            logging.error(
                "Unable to download statistics for %r (tag: %s)",
                event.title, tag
            )
            hits = 0

        EventHitStats.objects.create(
            event=event,
            total_hits=hits,
            shortcode=tag
        )

    def update_qs(qs):
        count = 0
        # oldest first
        for stat in qs.order_by('modified')[:cap]:
            total_hits_before = stat.total_hits
            # if the event more recently modified than the EventHitStats
            # the re-read the tag in case it has changed
            if stat.event.modified > stat.modified:
                environment = stat.event.template_environment or {}
                tag = environment.get('tag')
                if not tag:
                    logging.warn(
                        "Event %r does not have a Vid.ly tag",
                        stat.event.title
                    )
                    stat.delete()
                    continue
                stat.shortcode = tag
            shortcode = stat.shortcode
            try:
                hits = vidly.statistics(shortcode)['total_hits']
                count += 1
            except:
                if not swallow_errors:
                    raise
                logging.error(
                    "Unable to download statistics for %r (tag: %s)",
                    stat.event.title, shortcode
                )
                # we'll come back some other time
                hits = total_hits_before

            if hits >= total_hits_before:
                stat.total_hits = hits

            stat.save()
        return count

    # Old one only get updated once a week
    now = timezone.now()
    week_ago = now - datetime.timedelta(days=7)
    qs = (
        EventHitStats.objects
        .filter(event__modified__lt=week_ago)
        .filter(modified__lt=week_ago)
    )
    count += update_qs(qs)

    # Less old ones only get update once a day
    day_ago = now - datetime.timedelta(days=1)
    qs = (
        EventHitStats.objects
        .filter(event__modified__lt=day_ago,
                event__modified__gt=week_ago)
        .filter(modified__lt=day_ago)
    )

    count += update_qs(qs)

    # Recent ones get updated every hour
    hour_ago = now - datetime.timedelta(hours=1)
    qs = (
        EventHitStats.objects
        .filter(event__modified__lt=hour_ago,
                event__modified__gt=day_ago)
        .filter(modified__lt=hour_ago)
    )
    count += update_qs(qs)

    return count

import sys
import datetime
import traceback

from django.conf import settings
from django.utils import timezone

from airmozilla.main.models import Event, EventEmail, get_profile_safely
from airmozilla.new import sending


def send_new_event_emails(verbose=False):
    now = timezone.now()
    yesterday = now - datetime.timedelta(hours=24)
    events = Event.objects.scheduled().filter(
        created__gt=yesterday,
        created__lt=now,
    ).approved().exclude(
        id__in=EventEmail.objects.values('event_id')
    )

    optout_users = {}
    attempted = successful = skipped = 0
    for event in events:
        if event.creator.email not in optout_users:
            user_profile = get_profile_safely(event.creator)
            # if they don't have a profile, assume not
            optout_users[event.creator.email] = (
                user_profile and
                user_profile.optout_event_emails or
                False
            )
        if optout_users[event.creator.email]:
            if verbose:  # pragma: no cover
                print "Skipping sending to", event.creator.email
            skipped += 1
            continue

        attempted += 1
        send_failure = None
        try:
            sending.send_about_new_event(event)
            if verbose:  # pragma: no cover
                print "Successfully sent about", repr(event)
            successful += 1
        except Exception:
            if settings.DEBUG:  # pragma: no cover
                raise
            exc_type, exc_value, exc_tb = sys.exc_info()
            send_failure = "{0}{1}: {2}".format(
                ''.join(traceback.format_tb(exc_tb)),
                exc_type.__name__,
                exc_value
            )
            if verbose:  # pragma: no cover
                print "Failed to send about", repr(event)
                print send_failure

        EventEmail.objects.create(
            event=event,
            user=event.creator,
            to=event.creator.email,
            send_failure=send_failure,
        )

    return attempted, successful, skipped

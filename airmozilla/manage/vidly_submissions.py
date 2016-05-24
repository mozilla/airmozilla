import dateutil.parser

from django.utils.timezone import UTC
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.db import transaction

from airmozilla.main.models import Event, VidlySubmission
from airmozilla.manage import vidly


@transaction.atomic
def resubmit(clone):
    event = clone.event
    token_protection = event.privacy != Event.PRIVACY_PUBLIC
    url = clone.url
    hd = clone.hd

    site = Site.objects.get_current()
    base_url = 'https://%s' % site.domain  # yuck!
    webhook_url = base_url + reverse('manage:vidly_media_webhook')

    shortcode, error = vidly.add_media(
        url=url,
        hd=hd,
        token_protection=token_protection,
        notify_url=webhook_url,
    )
    VidlySubmission.objects.create(
        event=event,
        url=url,
        token_protection=token_protection,
        hd=hd,
        tag=shortcode,
        submission_error=error
    )
    event.status = Event.STATUS_PROCESSING
    event.save()
    return error


def parse_non_iso_date(timestr):
    dt = dateutil.parser.parse(timestr)
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=UTC())
    return dt


def resubmit_failures(max_attempts=1, verbose=False):
    failed = vidly.medialist('Error')
    resubmitted = []
    for shortcode in failed:
        try:
            submission = VidlySubmission.objects.get(tag=shortcode)
        except VidlySubmission.DoesNotExist:
            # If we have no record of submissions with that shortcode,
            # it's probably a piece of video on Vid.ly that came from
            # some other instance.
            continue

        if verbose:  # pragma: no cover
            print repr(shortcode), "has failed"
            # print submissions.count(), "known vidly submissions in our DB"

        if not submission.errored:
            # That's weird and nearly impossible.
            # It can happen that the transcoding *did* fail but we
            # were never informed (or failed to acknowledge being
            # informed).
            results = vidly.query(shortcode)[shortcode]
            if results['Status'] == 'Error':
                submission.errored = parse_non_iso_date(results['Updated'])
                submission.save()
        assert submission.errored

        # If we can find any submissions that are submitted after
        # this failed one that has not errored, then bail out.
        non_failures = VidlySubmission.objects.filter(
            event=submission.event,
            errored__isnull=True,
            submission_time__gt=submission.errored,
        )
        if non_failures.exists():
            if verbose:  # pragma: no cover
                print (
                    "Found at least one submission more recent that succeeded."
                )
            continue

        # How many failed attempts have there been?
        # If there's too many resubmissions, the bail out of fear of
        # re-submitting something that'll never work.
        failures = VidlySubmission.objects.filter(
            event=submission.event,
            errored__isnull=False,
        ).exclude(
            id=submission.id
        )
        if failures.count() >= max_attempts:
            if verbose:  # pragma: no cover
                print (
                    "Already been {} failed attempts.".format(failures.count())
                )
            continue

        if verbose:  # pragma: no cover
            print "Resubmitting! {!r}".format(submission.event)
        error = resubmit(submission)
        if verbose:  # pragma: no cover
            print "Resubmission error", error
            print "\n"

        resubmitted.append(submission)
    return resubmitted

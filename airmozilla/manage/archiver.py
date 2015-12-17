import logging
import urlparse

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.cache import cache
from django.utils import timezone
from django.contrib.sites.models import Site
from django.db.models import Q
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event, VidlySubmission
from .vidly import query


# what the cron jobs can execute
def auto_archive(verbose=False):
    events = (
        Event.objects
        .filter(Q(status=Event.STATUS_PENDING) |
                Q(status=Event.STATUS_PROCESSING),
                archive_time__isnull=True,
                template__name__contains='Vid.ly')
    )
    any = False
    for event in events:
        archive(event, swallow_email_exceptions=True, verbose=verbose)
        any = True

    if verbose:  # pragma: no cover
        if any:
            print "No processing or pending events."
        else:
            print "No events to archive."


def archive(event, swallow_email_exceptions=False, verbose=False):
    if 'Vid.ly' not in event.template.name:
        logging.warn("Event %r not a Vid.ly event", event.title)
        return
    environment = event.template_environment or {}
    tag = environment.get('tag')
    if not tag:
        logging.warn("Event %r does not have a Vid.ly tag", event.title)
        return
    results = query([tag])

    if verbose:  # pragma: no cover
        print "Results for", tag
        print results

    if tag not in results:
        cache_key = 'archiver-%s-notfound' % tag
        if not cache.get(cache_key):
            try:
                email_about_tag_not_found(
                    event,
                    tag,
                )
                if verbose:  # pragma: no cover
                    print (
                        'Unable to find Vid.ly video with tag %s for event '
                        '"%s"\n' % (
                            tag,
                            event
                        )
                    )
            except:  # pragma: no cover
                if not swallow_email_exceptions:
                    raise
                logging.error(
                    "Failing to send an email about %r (%s)",
                    event.title, tag,
                    exc_info=True
                )
            cache.set(cache_key, 'Done', 60 * 60 * 24)

    elif results[tag].get('Status') == 'Error':
        # Terrible!
        submissions = VidlySubmission.objects.filter(
            event=event,
            tag=tag,
            finished__isnull=True
        )
        for submission in submissions:
            submission.errored = timezone.now()
            submission.save()

        # Email the admins!
        cache_key = 'archiver-%s-error' % tag
        if not cache.get(cache_key):
            try:
                email_about_archiver_error(
                    event,
                    tag,
                )
                if verbose:  # pragma: no cover
                    print (
                        'Unable to archive event "%s" with tag %s\n'
                        % (
                            event,
                            tag
                        )
                    )
            except:  # pragma: no cover
                if not swallow_email_exceptions:
                    raise
                logging.error(
                    "Failing to send an email about %r (%s)",
                    event.title, tag,
                    exc_info=True
                )
            cache.set(cache_key, 'Done', 60 * 60 * 24)

    elif results[tag].get('Status') == 'Finished':
        # hurray!
        now = timezone.now()
        event.archive_time = now
        event.status = Event.STATUS_SCHEDULED
        event.save()

        if verbose:  # pragma: no cover
            print 'Event "%s" archived!' % event

        submissions = VidlySubmission.objects.filter(
            event=event,
            tag=tag,
            finished__isnull=True
        )
        for submission in submissions:
            submission.finished = timezone.now()
            submission.save()


def build_absolute_url(uri):
    site = Site.objects.get_current()
    base = 'https://%s' % site.domain  # yuck!
    return urlparse.urljoin(base, uri)


def email_about_archiver_error(event, tag):
    subject = "Unable to archive event with tag %s" % tag
    message = (
        'When trying to archive the "%s" event we had an error from Vid.ly.\n'
        '\n'
        'To address the error go to:\n'
        '\t%s\n'
        % (event.title,
           build_absolute_url(reverse('manage:event_edit', args=(event.pk,))))
    )

    email = EmailMessage(
        subject,
        message,
        settings.EMAIL_FROM_ADDRESS,
        [x[1] for x in settings.ADMINS]
    )
    email.send()


def email_about_tag_not_found(event, tag):
    subject = "Unable to find Vid.ly video with tag %s" % tag
    message = (
        'When trying to archive the "%s" event the tag could not be '
        'found with on Vid.ly.\n'
        '\n'
        'To address the error go to:\n'
        '\t%s\n'
        % (event.title,
           build_absolute_url(reverse('manage:event_edit', args=(event.pk,))))
    )

    email = EmailMessage(
        subject,
        message,
        settings.EMAIL_FROM_ADDRESS,
        [x[1] for x in settings.ADMINS]
    )
    email.send()

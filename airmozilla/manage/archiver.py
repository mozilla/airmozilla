import datetime
import logging
import urlparse

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.cache import cache
from django.utils.timezone import utc
from django.contrib.sites.models import Site

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Event
from .vidly import query


def archive(event):
    if 'Vid.ly' not in event.template.name:
        logging.warn("Event %r not a Vid.ly event", event.title)
        return
    environment = event.template_environment or {}
    tag = environment.get('tag')
    if not tag:
        logging.warn("Event %r does not have a Vid.ly tag", event.title)
        return
    results = query([tag])
    if tag not in results:
        cache_key = 'archiver-%s-notfound' % tag
        if not cache.get(cache_key):
            try:
                email_about_tag_not_found(
                    event,
                    tag,
                )
            except:  # pragma: no cover
                logging.error(
                    "Failing to send an email about %r (%s)",
                    event.title, tag,
                    exc_info=True
                )
            cache.set(cache_key, 'Done', 60 * 60 * 24)

    elif results[tag].get('Status') == 'Error':
        # terrible! Email the admins!
        cache_key = 'archiver-%s-error' % tag
        if not cache.get(cache_key):
            try:
                email_about_archiver_error(
                    event,
                    tag,
                )
            except:  # pragma: no cover
                logging.error(
                    "Failing to send an email about %r (%s)",
                    event.title, tag,
                    exc_info=True
                )
            cache.set(cache_key, 'Done', 60 * 60 * 24)

    elif results[tag].get('Status') == 'Finished':
        # hurray!
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        event.archive_time = now
        event.status = Event.STATUS_SCHEDULED
        event.save()


def build_absolute_url(uri):
    site = Site.objects.get_current()
    base = 'https://%s' % site.domain  # yuck!
    return urlparse.urljoin(base, uri)


def email_about_archiver_error(event, tag):
    subject = "Unable to archive pending event with tag %s" % tag
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

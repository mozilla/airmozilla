"""
Similar to the Approval Inbox but it makes it possible to put these
together in an email.
"""
import datetime
import collections
import urlparse

from django.utils.timezone import utc
from django.core.cache import cache
from django.conf import settings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.utils.timesince import timesince
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event, Approval


INTERVAL = settings.PESTER_INTERVAL_DAYS * 60 * 60 * 24


def build_absolute_url(uri):
    site = Site.objects.get_current()
    base = 'https://%s' % site.domain  # yuck!
    return urlparse.urljoin(base, uri)


def pester(dry_run=False, force_run=False):
    # because some users potentially belong to multiple groups
    # we need to make a map of each users' events to be
    # pestered about
    users = collections.defaultdict(list)

    # we only want to bother with approvals of events that are
    # of a minimum age
    now = datetime.datetime.utcnow().replace(tzinfo=utc, microsecond=0)
    minimum_created_date = now - datetime.timedelta(seconds=INTERVAL)

    approvals = (
        Approval.objects
        .filter(processed=False,
                event__created__lt=minimum_created_date)
        .exclude(event__status=Event.STATUS_REMOVED)
        .select_related('event', 'group')
        .order_by('event__created')  # oldest first ???
    )

    for approval in approvals:
        # exclude those with no email
        for user in approval.group.user_set.exclude(email=''):
            cache_key = 'pestered-%s-%s' % (user.pk, approval.pk)
            if not cache.get(cache_key) or force_run:
                users[user].append(approval)

    approval_texts = {}

    emails_sent = []
    for user, approvals in users.items():
        texts = []
        cache_keys = []
        for approval in approvals:
            if approval not in approval_texts:
                if approval.event.start_time > now:
                    time_left = timesince(
                        approval.event.start_time,
                        reversed=True
                    )
                else:
                    time_left = 'overdue!'
                participants = []
                for participant in approval.event.participants.all():
                    participants.append(participant.name)
                participants = ' and '.join(participants)
                text = render_to_string(
                    'manage/_pester_approval_event.html',
                    {
                        'approval': approval,
                        'event': approval.event,
                        'time_left': time_left,
                        'manage_url': build_absolute_url(
                            reverse('manage:approval_review',
                                    args=(approval.pk,)),
                        ),
                    }
                )
                approval_texts[approval] = text
            texts.append(approval_texts[approval])
            cache_keys.append(
                'pestered-%s-%s' % (user.pk, approval.pk)
            )
        group_names = [x.name for x in user.groups.all()]
        message = render_to_string(
            'manage/_pester_approvals.html',
            {
                'texts': texts,
                'group_names': ' and '.join(group_names),
                'approvals_url': build_absolute_url(
                    reverse('manage:approvals')
                )
            }
        )

        subject = '[Air Mozilla] Approval reminder. You have '
        if len(texts) == 1:
            subject += '1 event '
        else:
            subject += '%s events ' % len(texts)
        subject += 'to approve.'

        email = EmailMessage(
            subject,
            message,
            settings.EMAIL_FROM_ADDRESS,
            [user.email]
        )
        emails_sent.append((user.email, subject, message))
        if not dry_run:
            email.send()
            for cache_key in cache_keys:
                cache.set(cache_key, True, INTERVAL)

    return emails_sent

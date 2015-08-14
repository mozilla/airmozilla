from html2text import html2text

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import Group

from airmozilla.main.models import (
    SuggestedEventComment
)
from airmozilla.base.utils import fix_base_url


def _get_notifications_group_emails():
    """return a list of email addresses of users who belong to a certain
    group."""
    group, _ = Group.objects.get_or_create(
        name=settings.NOTIFICATIONS_GROUP_NAME
    )
    emails = set()
    for user in group.user_set.filter(is_active=True):
        emails.add(user.email)
    return list(emails)


def email_about_suggested_event_comment(comment, base_url):
    base_url = fix_base_url(base_url)
    emails = _get_notifications_group_emails()
    if not emails:
        return
    event_title = comment.suggested_event.title
    if len(event_title) > 30:
        event_title = '%s...' % event_title[:27]
    subject = (
        '[Air Mozilla] New comment on suggested event: %s' % event_title
    )
    context = {
        'event': comment.suggested_event,
        'comment': comment,
        'base_url': base_url,
        'subject': subject,
    }
    html_body = render_to_string(
        'suggest/_email_comment.html',
        context
    )
    assert emails
    body = html2text(html_body)
    email = EmailMultiAlternatives(
        subject,
        body,
        settings.EMAIL_FROM_ADDRESS,
        emails
    )
    email.attach_alternative(html_body, "text/html")
    email.send()


def email_about_suggested_event(event, base_url):
    base_url = fix_base_url(base_url)
    emails = _get_notifications_group_emails()
    if not emails:
        return
    event_title = event.title
    if len(event_title) > 30:
        event_title = '%s...' % event_title[:27]
    comments = (
        SuggestedEventComment.objects
        .filter(suggested_event=event)
        .order_by('created')
    )
    subject = (
        '[Air Mozilla] New suggested event: %s' % event_title
    )
    assert emails
    context = {
        'event': event,
        'base_url': base_url,
        'comments': comments,
        'subject': subject,
    }
    html_body = render_to_string(
        'suggest/_email_submitted.html',
        context
    )
    body = html2text(html_body)
    email = EmailMultiAlternatives(
        subject,
        body,
        settings.EMAIL_FROM_ADDRESS,
        emails
    )
    email.attach_alternative(html_body, "text/html")
    email.send()

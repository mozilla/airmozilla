from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from html2text import html2text

from airmozilla.main.models import (
    SuggestedEvent
)
from airmozilla.base.utils import fix_base_url


def email_about_suggestion_comment(comment, user, base_url):
    base_url = fix_base_url(base_url)
    event = comment.suggested_event
    emails = (event.user.email,)
    event_title = comment.suggested_event.title
    if len(event_title) > 30:
        event_title = '%s...' % event_title[:27]
    subject = (
        '[Air Mozilla] New comment on your suggested event ("%s")' % (
            event_title,
        )
    )
    context = {
        'event': event,
        'comment': comment,
        'user': user,
        'base_url': base_url,
        'subject': subject,
    }
    html_body = render_to_string(
        'manage/_email_suggested_comment.html',
        context
    )
    body = html2text(html_body)
    email = EmailMultiAlternatives(
        subject,
        body,
        'Air Mozilla <%s>' % settings.EMAIL_FROM_ADDRESS,
        emails
    )
    email.attach_alternative(html_body, "text/html")
    email.send()


def email_about_accepted_suggestion(event, real, base_url):
    base_url = fix_base_url(base_url)
    emails = (event.user.email,)
    event_title = real.title
    if len(event_title) > 30:
        event_title = '%s...' % event_title[:27]
    subject = (
        '[Air Mozilla] Requested event accepted! %s'
        % event_title
    )

    context = {
        'event': event,
        'base_url': base_url,
        'subject': subject,
    }
    html_body = render_to_string(
        'manage/_email_suggested_accepted.html',
        context
    )
    body = html2text(html_body)
    email = EmailMultiAlternatives(
        subject,
        body,
        'Air Mozilla <%s>' % settings.EMAIL_FROM_ADDRESS,
        emails
    )
    email.attach_alternative(html_body, "text/html")
    email.send()


def email_about_rejected_suggestion(event, user, base_url):
    base_url = fix_base_url(base_url)
    emails = (event.user.email,)
    subject = (
        '[Air Mozilla] Requested event not accepted: %s' % event.title
    )
    context = {
        'event': event,
        'user': user,
        'base_url': base_url,
        'subject': subject,
    }
    html_body = render_to_string(
        'manage/_email_suggested_rejected.html',
        context
    )
    body = html2text(html_body)
    email = EmailMultiAlternatives(
        subject,
        body,
        'Air Mozilla <%s>' % settings.EMAIL_FROM_ADDRESS,
        emails
    )
    email.attach_alternative(html_body, "text/html")
    email.send()


def email_about_approval_requested(event, group, base_url):
    base_url = fix_base_url(base_url)
    emails = [u.email for u in group.user_set.filter(is_active=True)]
    if not emails:
        return
    subject = (
        '[Air Mozilla] Approval requested: "%s"' % event.title
    )
    try:
        suggested_event = SuggestedEvent.objects.get(accepted=event)
    except SuggestedEvent.DoesNotExist:
        suggested_event = None
    context = {
        'group': group.name,
        'title': event.title,
        'event': event,
        'suggested_event': suggested_event,
        'subject': subject,
        'base_url': base_url,
    }

    html_body = render_to_string(
        'manage/_email_approval.html',
        context
    )
    body = html2text(html_body)
    email = EmailMultiAlternatives(
        subject,
        body,
        'Air Mozilla <%s>' % settings.EMAIL_FROM_ADDRESS,
        emails
    )
    email.attach_alternative(html_body, "text/html")
    email.send()


def email_sending_test(subject, html_body, emails, base_url):
    base_url = fix_base_url(base_url)
    context = {
        'base_url': base_url,
        'subject': subject,
        'html_body': html_body,
    }
    html_body = render_to_string(
        'manage/_email_sending_test.html',
        context,
    )
    body = html2text(html_body)
    email = EmailMultiAlternatives(
        subject,
        body,
        'Air Mozilla <%s>' % settings.EMAIL_FROM_ADDRESS,
        emails
    )
    email.attach_alternative(html_body, "text/html")
    email.send()

    return email

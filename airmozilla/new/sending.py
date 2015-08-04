import uuid

from html2text import html2text

from django.template.loader import render_to_string
from django.core.urlresolvers import reverse
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives

from airmozilla.base.utils import build_absolute_url


def _get_unsubscribe_url(user):
    identifier = uuid.uuid4().hex[:10]
    url = reverse('new:unsubscribe', args=(identifier,))
    cache.set('unsubscribe-%s' % identifier, user.pk, 60 * 60 * 24 * 7)
    return url


def send_about_new_event(event):

    assert event.creator.email, "No user email"

    unsubscribe_url = _get_unsubscribe_url(event.creator)

    subject = (
        "[Air Mozilla] Yay! Your video is ready: %s"
        % (event.title,)
    )
    context = {
        'event': event,
        'build_absolute_url': build_absolute_url,
        'unsubscribe_url': unsubscribe_url,
    }

    context['subject'] = subject
    html_body = render_to_string(
        'new/_email_new_event.html',
        context
    )
    # base_url = build_absolute_url('/')
    # html_body = premailer.transform(
    #     html_body,
    #     base_url=base_url
    # )
    body = html2text(html_body)
    email = EmailMultiAlternatives(
        subject,
        body,
        'Air Mozilla <%s>' % settings.EMAIL_FROM_ADDRESS,
        [event.creator.email],
        # headers=headers,
    )
    email.attach_alternative(html_body, "text/html")
    email.send()

import urlparse

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.contrib.sites.models import Site
from django.template.loader import render_to_string

from html2text import html2text


def build_absolute_url(uri):
    site = Site.objects.get_current()
    base = 'https://%s' % site.domain  # yuck!
    return urlparse.urljoin(base, uri)


def email_about_mozillian_video(event, swallow_errors=False):
    """called when a video has been successfully transcoded and thus making
    the video scheduled and available."""
    try:
        _email_about_mozillian_video(event)
    except:  # pragma: no cover
        if not swallow_errors:
            raise
        print "Unable notify about event %r" % event


def _email_about_mozillian_video(event):
    assert event.mozillian, "not a mozillian event"
    subject = '[Air Mozilla] Your Mozshorts video is ready!'

    context = {
        'event': event,
        'build_absolute_url': build_absolute_url,
        'subject': subject,
    }
    html_body = render_to_string(
        'webrtc/_email_mozillian_video.html',
        context
    )
    body = html2text(html_body)
    emails = (event.creator.email,)
    email = EmailMultiAlternatives(
        subject,
        body,
        'Air Mozilla <%s>' % settings.EMAIL_FROM_ADDRESS,
        emails
    )
    email.attach_alternative(html_body, "text/html")
    email.send()

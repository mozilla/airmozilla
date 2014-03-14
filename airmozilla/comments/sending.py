import uuid

from html2text import html2text

from django.template.loader import render_to_string
from django.core.urlresolvers import reverse
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives

from airmozilla.base.utils import fix_base_url
from .models import Discussion, Unsubscription


def _get_unsubscribe_all_url(user):
    identifier = uuid.uuid4().hex[:10]
    url = reverse('comments:unsubscribe_all', args=(identifier,))
    cache.set('unsubscribe-%s' % identifier, user.pk, 60 * 60 * 24 * 7)
    return url


def _get_unsubscribe_discussion_url(user, discussion):
    identifier = uuid.uuid4().hex[:10]
    url = reverse('comments:unsubscribe_discussion',
                  args=(identifier, discussion.pk))
    cache.set('unsubscribe-%s' % identifier, user.pk, 60 * 60 * 24 * 7)
    return url


def send_reply_notification(comment, base_url):
    base_url = fix_base_url(base_url)
    parent = comment.reply_to
    assert parent
    event = comment.event
    discussion = Discussion.objects.get(event=event)

    try:
        Unsubscription.objects.get(
            user=parent.user,
            discussion=discussion
        )
        return
    except Unsubscription.DoesNotExist:
        try:
            Unsubscription.objects.get(
                user=parent.user,
            )
            return
        except Unsubscription.DoesNotExist:
            pass

    discussion = Discussion.objects.get(event=event)
    unsubscribe_discussion_url = _get_unsubscribe_discussion_url(
        parent.user,
        discussion
    )
    unsubscribe_all_url = _get_unsubscribe_all_url(
        parent.user
    )
    context = {
        'reply': comment,
        'comment': parent,
        'event': event,
        'base_url': base_url,
        'unsubscribe_discussion_url': unsubscribe_discussion_url,
        'unsubscribe_all_url': unsubscribe_all_url,
    }
    subject = (
        "Reply to your Air Mozilla comment on: %s"
        % (event.title,)
    )
    context['subject'] = subject
    html_body = render_to_string(
        'comments/_email_reply_notification.html',
        context
    )
    #headers = {'Reply-To': payment.email}
    #html_body = premailer.transform(
    #    html_body,
    #    base_url=base_url
    #)
    body = html2text(html_body)
    email = EmailMultiAlternatives(
        subject,
        body,
        'Air Mozilla <%s>' % settings.EMAIL_FROM_ADDRESS,
        [parent.user.email],
        #headers=headers,
    )
    email.attach_alternative(html_body, "text/html")
    email.send()


def _get_approve_comment_url(comment):
    identifier = uuid.uuid4().hex[:10]
    url = reverse('comments:approve_immediately',
                  args=(identifier, comment.pk))
    cache.set('approve-%s' % identifier, comment.pk, 60 * 60 * 24 * 7)
    return url


def _get_remove_comment_url(comment):
    identifier = uuid.uuid4().hex[:10]
    url = reverse('comments:remove_immediately',
                  args=(identifier, comment.pk))
    cache.set('remove-%s' % identifier, comment.pk, 60 * 60 * 24 * 7)
    return url


def send_moderator_notifications(comment, base_url):
    base_url = fix_base_url(base_url)
    event = comment.event
    discussion = Discussion.objects.get(event=event)

    moderators = discussion.moderators.exclude(id=comment.user.id)
    if not moderators:
        return

    approve_comment_url = _get_approve_comment_url(comment)
    remove_comment_url = _get_remove_comment_url(comment)

    context = {
        'comment': comment,
        'event': event,
        'base_url': base_url,
        'approve_comment_url': approve_comment_url,
        'remove_comment_url': remove_comment_url,
    }
    subject = (
        "New comment requires moderation on: %s"
        % (event.title,)
    )
    context['subject'] = subject
    html_body = render_to_string(
        'comments/_email_moderator_notification.html',
        context
    )
    #headers = {'Reply-To': payment.email}
    #html_body = premailer.transform(
    #    html_body,
    #    base_url=base_url
    #)
    body = html2text(html_body)
    email = EmailMultiAlternatives(
        subject,
        body,
        'Air Mozilla <%s>' % settings.EMAIL_FROM_ADDRESS,
        [x.email for x in moderators],
        #headers=headers,
    )
    email.attach_alternative(html_body, "text/html")
    email.send()

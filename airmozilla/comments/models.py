from django.core.cache import cache
from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver

from airmozilla.main.models import Event, SuggestedEvent


class Comment(models.Model):
    event = models.ForeignKey(Event)
    user = models.ForeignKey(User, null=True)
    comment = models.TextField()
    reply_to = models.ForeignKey('self', related_name='parent', null=True)

    STATUS_POSTED = 'posted'
    STATUS_APPROVED = 'approved'
    STATUS_REMOVED = 'removed'
    STATUS_CHOICES = (
        (STATUS_POSTED, 'Posted'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REMOVED, 'Removed'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_POSTED)
    flagged = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    @property
    def anonymous(self):
        return not self.user_id


@receiver(models.signals.post_save, sender=Comment)
def invalidate_latest_comment_cache(sender, instance, **kwargs):
    event = instance.event
    cache_keys = []
    # there's one cache key for moderators and one for non-moderators
    for truth in (True, False):
        cache_keys.append('latest_comment:%s:%s' % (event.id, truth))
    [cache.delete(x) for x in cache_keys]


# class CommentVotes(models.Model):
#     comment = models.ForeignKey(Comment)
#     vote = models.IntegerField(default=1)
#     created = models.DateTimeField(auto_now_add=True)


class Discussion(models.Model):
    event = models.OneToOneField(Event)
    enabled = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether comments will be available at all."
    )
    closed = models.BooleanField(
        default=False,
        help_text="Existing comments remain visible but the discussion is "
                  "not open for new comments."
    )
    moderate_all = models.BooleanField(
        default=False,
        help_text="Moderators must approve all comments before "
                  "they become visible."
    )
    notify_all = models.BooleanField(
        default=False,
        help_text="Moderators will receive an email about "
                  "all new comments."
    )
    moderators = models.ManyToManyField(User, related_name='moderators')


class SuggestedDiscussion(models.Model):
    event = models.OneToOneField(SuggestedEvent)
    enabled = models.BooleanField(default=False)
    moderate_all = models.BooleanField(default=False)
    notify_all = models.BooleanField(default=False)
    moderators = models.ManyToManyField(
        User,
        related_name='suggested_moderators'
    )


class Unsubscription(models.Model):
    user = models.ForeignKey(User)
    discussion = models.ForeignKey(Discussion, null=True)
    created = models.DateTimeField(auto_now_add=True)

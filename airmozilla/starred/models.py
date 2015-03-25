from django.core.cache import cache
from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver

from airmozilla.main.models import Event


class StarredEvent(models.Model):
    event = models.ForeignKey(Event)
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "user")


@receiver(models.signals.post_delete, sender=StarredEvent)
@receiver(models.signals.post_save, sender=StarredEvent)
def invalidate_user_ids_cache(sender, instance, **kwargs):
    cache_key = 'star_ids%s' % instance.user_id
    cache.delete(cache_key)

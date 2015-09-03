from django.core.cache import cache
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import models


@receiver(models.signals.post_save, sender=User)
def invalidate_user_cache(sender, instance, **kwargs):
    if instance.id:
        cache_key = 'user:%s' % (instance.id,)
        cache.delete(cache_key)

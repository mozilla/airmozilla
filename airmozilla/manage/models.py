from django.core.cache import cache
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db import models


@receiver(models.signals.post_save, sender=User)
@receiver(models.signals.m2m_changed, sender=User.groups.through)
def invalidate_user_cache(sender, instance, **kwargs):
    cache_key = '_get_all_users'
    cache.delete(cache_key)

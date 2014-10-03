from django.core.cache import cache
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db import models

from airmozilla.main.models import Picture


@receiver(models.signals.post_save, sender=User)
@receiver(models.signals.m2m_changed, sender=User.groups.through)
def invalidate_user_cache(sender, instance, **kwargs):
    cache_key = '_get_all_users'
    cache.delete(cache_key)


@receiver(models.signals.post_save, sender=Picture)
def invalidate_picture_cache(sender, instance, **kwargs):
    cache_key = '_get_all_pictures'
    cache.delete(cache_key)

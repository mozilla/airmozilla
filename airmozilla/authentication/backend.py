from django_browserid.auth import BrowserIDBackend
from django.core.cache import cache


class AirmozillaBrowserIDBackend(BrowserIDBackend):
    """The only difference between this backend and the default
    BrowserIDBackend backend is that this one uses the cache framework
    to remember the user.

    The cache is invalidated by a post_save signal in this app's models.py.
    """

    def get_user(self, user_id):
        if not user_id:
            return None
        cache_key = 'user:%s' % (user_id,)
        user = cache.get(cache_key)
        if user:
            return user
        try:
            user = self.User.objects.get(pk=user_id)
            cache.set(cache_key, user, 60 * 60 * 3)  # 3 hours
            return user
        except self.User.DoesNotExist:
            return None

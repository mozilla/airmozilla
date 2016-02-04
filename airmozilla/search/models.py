from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.dispatch import receiver
from django.core.cache import cache

from jsonfield.fields import JSONField

from airmozilla.main.models import Event, Channel, Tag


def _get_now():
    return timezone.now()


class LoggedSearch(models.Model):
    term = models.CharField(max_length=200)
    results = models.IntegerField(default=0)
    page = models.IntegerField(default=1)
    user = models.ForeignKey(User, null=True)
    event_clicked = models.ForeignKey(Event, null=True)
    date = models.DateTimeField(default=_get_now)


class SavedSearch(models.Model):
    name = models.CharField(max_length=200, null=True)
    slug = models.SlugField(max_length=200, null=True)
    filters = JSONField()

    parent = models.ForeignKey('self', related_name='savedsearch', null=True)
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def get_events(self):
        qs = Event.objects.scheduled_or_processing().approved()

        # this is just the text search
        if self.filters['title'].get('include'):
            sql = (
                "to_tsvector('english', title) @@ "
                "plainto_tsquery('english', %s)"
            )
            qs = qs.extra(
                where=[sql],
                params=[self.filters['title']['include']]
            )

        if self.filters['title'].get('exclude'):
            sql = (
                "NOT "
                "to_tsvector('english', title) @@ to_tsquery('english', %s)"
            )
            qs = qs.extra(
                where=[sql],
                params=[self.filters['title']['exclude']]
            )

        for key in ('channels', 'tags'):
            if self.filters.get(key, {}).get('include'):
                qs = qs.filter(
                    **{
                        '{}__in'.format(key): self.filters[key].get('include')
                    }
                )

            if self.filters.get(key, {}).get('exclude'):
                qs = qs.exclude(
                    **{
                        '{}__in'.format(key): self.filters[key].get('exclude')
                    }
                )

        if self.filters.get('privacy'):
            qs = qs.filter(privacy__in=self.filters['privacy'])

        return qs

    @property
    def summary(self):
        """return a string that tries to be human-readable and a summary
        of the saved search."""
        parts = []

        for key in ('title', 'tags', 'channels'):
            if key not in self.filters:
                continue
            for op in ('include', 'exclude'):
                if self.filters[key].get(op):
                    value = self.filters[key][op]
                    if key == 'tags':
                        value = ', '.join(
                            x.name for x in
                            Tag.objects.filter(id__in=value)
                        )
                    elif key == 'channels':
                        value = ', '.join(
                            x.name for x in
                            Channel.objects.filter(id__in=value)
                        )
                    else:
                        assert isinstance(value, basestring)
                    parts.append('{} must {}: {}'.format(
                        key.title(),
                        op,
                        value
                    ))
        if self.filters.get('privacy'):
            choices = dict(Event.PRIVACY_CHOICES)
            parts.append('Privacy: {}'.format(
                ', '.join([
                    choices[x] for x in self.filters['privacy']
                ])
            ))

        return '; '.join(parts)


@receiver(models.signals.post_save, sender=SavedSearch)
def invalidate_savedsearch_caches(sender, instance, **kwargs):
    # invalidate the calendars
    for privacy in ('public', 'contributors', 'company'):
        assert instance.id
        cache_key = 'calendar_{}_{}'.format(privacy, instance.id)
        # Remember, you get no error if you try to delete a key that
        # doesn't exist.
        cache.delete(cache_key)

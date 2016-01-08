from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from jsonfield.fields import JSONField

from airmozilla.main.models import Event


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
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def get_events(self):
        qs = Event.objects.scheduled_or_processing().approved()

        # this is just the text search
        if self.filters['title'].get('include'):
            sql = "to_tsvector('english', title) @@ to_tsquery('english', %s)"
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

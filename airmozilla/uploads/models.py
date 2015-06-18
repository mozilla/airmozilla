from django.db import models
from django.contrib.auth.models import User

from airmozilla.main.models import Event, SuggestedEvent


class Upload(models.Model):
    user = models.ForeignKey(User)
    url = models.URLField(max_length=400)
    file_name = models.CharField(max_length=200, null=True, blank=True)
    mime_type = models.CharField(max_length=200, null=True, blank=True)
    size = models.BigIntegerField()
    suggested_event = models.ForeignKey(
        SuggestedEvent,
        null=True,
        related_name='suggested_event'
    )
    event = models.ForeignKey(
        Event,
        null=True,
        related_name='event'
    )
    upload_time = models.PositiveIntegerField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.file_name or self.url

    @property
    def upload_speed(self):
        return float(self.size) / self.upload_time

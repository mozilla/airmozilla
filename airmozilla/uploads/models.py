from django.db import models
from django.contrib.auth.models import User

from airmozilla.main.models import SuggestedEvent


class Upload(models.Model):
    user = models.ForeignKey(User)
    url = models.URLField(max_length=400)
    file_name = models.CharField(max_length=200, null=True, blank=True)
    size = models.IntegerField()
    suggested_event = models.ForeignKey(SuggestedEvent, null=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import utc

from airmozilla.main.models import Event


def _get_now():
    return datetime.datetime.utcnow().replace(tzinfo=utc)


class LoggedSearch(models.Model):
    term = models.CharField(max_length=200)
    results = models.IntegerField(default=0)
    page = models.IntegerField(default=1)
    user = models.ForeignKey(User, null=True)
    event_clicked = models.ForeignKey(Event, null=True)
    date = models.DateTimeField(default=_get_now)

from django.contrib.auth.models import User
from django.db import models

from airmozilla.main.models import Event


class Chapter(models.Model):
    event = models.ForeignKey(Event)
    timestamp = models.PositiveIntegerField()
    text = models.TextField()

    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('timestamp',)

    def __repr__(self):
        return '<%s: %d %r>' % (
            self.__class__,
            self.timestamp,
            self.text
        )

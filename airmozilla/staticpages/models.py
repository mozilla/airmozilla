from django.db import models

from jsonfield.fields import JSONField

from airmozilla.main.models import Event


class StaticPage(models.Model):
    url = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    template_name = models.CharField(max_length=100, blank=True)
    privacy = models.CharField(
        max_length=40,
        choices=Event.PRIVACY_CHOICES,
        default=Event.PRIVACY_PUBLIC,
        db_index=True
    )
    page_name = models.CharField(max_length=100, blank=True)
    headers = JSONField()
    allow_querystring_variables = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('url',)

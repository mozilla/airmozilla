from django.db import models

from airmozilla.main.models import Event


class StaticPage(models.Model):
    url = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    template_name = models.CharField(max_length=100, blank=True)
    # privacy =
    # privacy = Event.privacy
    privacy = models.CharField(
        max_length=40,
        choices=Event.PRIVACY_CHOICES,
        default=Event.PRIVACY_PUBLIC,
        db_index=True
    )
    cors_header = models.CharField(max_length=100, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    page_name = models.CharField(max_length=100, blank=True)
    allow_querystring_variables = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('url',)

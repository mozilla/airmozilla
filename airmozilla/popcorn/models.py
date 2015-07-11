from django.db import models
from django.contrib.auth.models import User

from airmozilla.main.models import Event
from airmozilla.uploads.models import Upload

from jsonfield.fields import JSONField


class PopcornEdit(models.Model):
    event = models.ForeignKey(Event)
    user = models.ForeignKey(User, null=True)
    upload = models.ForeignKey(Upload, null=True)

    last_error = models.TextField(null=True)

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    data = JSONField()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    finished = models.DateTimeField(null=True)

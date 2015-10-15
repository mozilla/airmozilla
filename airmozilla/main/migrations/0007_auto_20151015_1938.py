# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.conf import settings


def bump_channel_feed_size(apps, schema_editor):
    # We can't import the Channel model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    Channel = apps.get_model('main', 'Channel')
    for channel in Channel.objects.filter(feed_size=2):
        channel.feed_size = settings.FEED_SIZE
        channel.save()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_channel_feed_size'),
    ]

    operations = [
        migrations.RunPython(bump_channel_feed_size),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def remove_suggested_popcorn_events(apps, schema_editor):
    SuggestedEvent = apps.get_model('main', 'SuggestedEvent')
    SuggestedEvent.objects.filter(popcorn_url__isnull=False).update(
        status='removed'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0011_vidlymedia'),
    ]

    operations = [
        migrations.RunPython(remove_suggested_popcorn_events),
    ]

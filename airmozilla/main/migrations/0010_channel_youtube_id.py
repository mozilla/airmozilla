# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_remove_event_mozillian'),
    ]

    operations = [
        migrations.AddField(
            model_name='channel',
            name='youtube_id',
            field=models.CharField(max_length=100, null=True),
            preserve_default=True,
        ),
    ]

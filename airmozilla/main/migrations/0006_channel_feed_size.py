# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_channel_cover_art'),
    ]

    operations = [
        migrations.AddField(
            model_name='channel',
            name='feed_size',
            field=models.PositiveIntegerField(default=2),
            preserve_default=True,
        ),
    ]

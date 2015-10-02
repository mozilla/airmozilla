# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import airmozilla.main.models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_chapter_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='channel',
            name='cover_art',
            field=models.ImageField(null=True, upload_to=airmozilla.main.models._upload_path_channels, blank=True),
            preserve_default=True,
        ),
    ]

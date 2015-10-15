# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_auto_20151015_1938'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channel',
            name='feed_size',
            field=models.PositiveIntegerField(default=20),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0024_channel_modified'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channel',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
    ]

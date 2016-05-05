# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0020_chapter_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='prep_time',
            field=models.PositiveIntegerField(default=1800, help_text=b'A number of seconds, that when generating the iCal for event assignments we pad the start time based on this. Default is 30 minutes (1800 seconds).'),
        ),
    ]

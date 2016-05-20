# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0021_location_prep_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='picture',
            name='timestamp',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
    ]

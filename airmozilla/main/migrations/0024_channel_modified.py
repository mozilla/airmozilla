# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import airmozilla.main.models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0023_auto_20160630_2004'),
    ]

    operations = [
        migrations.AddField(
            model_name='channel',
            name='modified',
            field=models.DateTimeField(default=airmozilla.main.models._get_now),
        ),
    ]

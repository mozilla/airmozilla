# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0022_picture_timestamp'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE INDEX main_channel_name_fts_idx
            ON main_channel
            USING gin(to_tsvector('english', name))
            """
        )
    ]

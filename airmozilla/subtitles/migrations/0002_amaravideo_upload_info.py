# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('subtitles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='amaravideo',
            name='upload_info',
            field=jsonfield.fields.JSONField(null=True),
        ),
    ]

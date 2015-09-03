# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sorl.thumbnail.fields
import airmozilla.main.models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_auto_20150903_1343'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channel',
            name='image',
            field=sorl.thumbnail.fields.ImageField(upload_to=airmozilla.main.models._upload_path_channels, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='placeholder_img',
            field=sorl.thumbnail.fields.ImageField(null=True, upload_to=airmozilla.main.models._upload_path_event_placeholder, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='eventrevision',
            name='placeholder_img',
            field=sorl.thumbnail.fields.ImageField(null=True, upload_to=airmozilla.main.models._upload_path_event_placeholder, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='picture',
            name='file',
            field=models.ImageField(height_field=b'height', width_field=b'width', upload_to=airmozilla.main.models._upload_path_pictures),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='suggestedevent',
            name='placeholder_img',
            field=sorl.thumbnail.fields.ImageField(null=True, upload_to=airmozilla.main.models._upload_path_event_placeholder, blank=True),
            preserve_default=True,
        ),
    ]

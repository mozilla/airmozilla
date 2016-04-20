# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import airmozilla.main.models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0019_auto_20160420_1035'),
    ]

    operations = [
        migrations.AddField(
            model_name='chapter',
            name='image',
            field=models.ImageField(null=True, upload_to=airmozilla.main.models._upload_path_chapters, blank=True),
        ),
    ]

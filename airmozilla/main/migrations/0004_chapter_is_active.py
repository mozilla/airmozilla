# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_auto_20150903_1633'),
    ]

    operations = [
        migrations.AddField(
            model_name='chapter',
            name='is_active',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]

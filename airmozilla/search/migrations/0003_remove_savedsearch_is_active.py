# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0002_savedsearch'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='savedsearch',
            name='is_active',
        ),
    ]

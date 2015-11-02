# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_auto_20151015_1954'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='mozillian',
        ),
    ]

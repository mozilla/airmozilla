# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0029_userprofile_id_token'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='refresh_token',
        ),
    ]

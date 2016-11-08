# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0028_userprofile_refresh_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='id_token',
            field=models.TextField(max_length=100, null=True),
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0027_auto_20160929_1211'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='refresh_token',
            field=models.CharField(max_length=100, null=True),
        ),
    ]

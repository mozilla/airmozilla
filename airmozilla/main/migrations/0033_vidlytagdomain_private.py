# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0032_auto_20161111_1614'),
    ]

    operations = [
        migrations.AddField(
            model_name='vidlytagdomain',
            name='private',
            field=models.BooleanField(default=False),
        ),
    ]

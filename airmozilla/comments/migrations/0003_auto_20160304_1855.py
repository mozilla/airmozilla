# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comments', '0002_auto_20150903_1343'),
    ]

    operations = [
        migrations.AlterField(
            model_name='discussion',
            name='event',
            field=models.OneToOneField(to='main.Event'),
        ),
        migrations.AlterField(
            model_name='suggesteddiscussion',
            name='event',
            field=models.OneToOneField(to='main.SuggestedEvent'),
        ),
    ]

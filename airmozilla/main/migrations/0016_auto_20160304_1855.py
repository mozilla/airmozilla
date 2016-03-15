# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0015_auto_20160304_1851'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventassignment',
            name='event',
            field=models.OneToOneField(to='main.Event'),
        ),
        migrations.AlterField(
            model_name='eventhitstats',
            name='event',
            field=models.OneToOneField(to='main.Event'),
        ),
        migrations.AlterField(
            model_name='eventlivehits',
            name='event',
            field=models.OneToOneField(to='main.Event'),
        ),
    ]

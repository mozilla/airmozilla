# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import airmozilla.main.models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0016_auto_20160304_1855'),
    ]

    operations = [
        migrations.CreateModel(
            name='SuggestedCuratedGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('url', models.URLField(null=True)),
                ('created', models.DateTimeField(default=airmozilla.main.models._get_now)),
                ('event', models.ForeignKey(to='main.SuggestedEvent')),
            ],
        ),
        migrations.AlterField(
            model_name='eventtweet',
            name='send_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]

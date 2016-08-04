# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0025_auto_20160630_2040'),
        ('closedcaptions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClosedCaptionsTranscript',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('closedcaptions', models.ForeignKey(to='closedcaptions.ClosedCaptions')),
                ('event', models.OneToOneField(to='main.Event')),
            ],
        ),
    ]

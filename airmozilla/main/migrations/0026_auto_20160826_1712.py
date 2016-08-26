# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0025_auto_20160630_2040'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventMetadata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=300)),
                ('value', models.TextField()),
                ('modified', models.DateTimeField(auto_now=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('event', models.ForeignKey(to='main.Event')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='eventmetadata',
            unique_together=set([('event', 'key')]),
        ),
    ]

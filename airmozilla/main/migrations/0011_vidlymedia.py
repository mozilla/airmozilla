# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_channel_youtube_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='VidlyMedia',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tag', models.CharField(max_length=100)),
                ('hd', models.BooleanField(default=False)),
                ('video_format', models.CharField(max_length=100)),
                ('url', models.URLField()),
                ('size', models.BigIntegerField()),
                ('content_type', models.CharField(max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

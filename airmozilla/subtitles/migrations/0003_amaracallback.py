# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('subtitles', '0002_amaravideo_upload_info'),
    ]

    operations = [
        migrations.CreateModel(
            name='AmaraCallback',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('payload', jsonfield.fields.JSONField(default=dict)),
                ('api_url', models.URLField()),
                ('video_id', models.CharField(max_length=100)),
                ('team', models.CharField(max_length=300, null=True)),
                ('project', models.CharField(max_length=300, null=True, blank=True)),
                ('language_code', models.CharField(max_length=100, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('amara_video', models.ForeignKey(to='subtitles.AmaraVideo', null=True)),
            ],
        ),
    ]

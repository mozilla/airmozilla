# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Upload',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField(max_length=400)),
                ('file_name', models.CharField(max_length=200, null=True, blank=True)),
                ('mime_type', models.CharField(max_length=200, null=True, blank=True)),
                ('size', models.BigIntegerField()),
                ('upload_time', models.PositiveIntegerField(null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('event', models.ForeignKey(related_name='event', to='main.Event', null=True)),
                ('suggested_event', models.ForeignKey(related_name='suggested_event', to='main.SuggestedEvent', null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

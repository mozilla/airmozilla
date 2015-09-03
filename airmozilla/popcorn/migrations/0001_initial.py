# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
        ('uploads', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PopcornEdit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('failed_attempts', models.PositiveIntegerField(default=0)),
                ('last_error', models.TextField(null=True)),
                ('status', models.CharField(default=b'pending', max_length=20, choices=[(b'pending', b'Pending'), (b'processing', b'Processing'), (b'success', b'Success'), (b'failed', b'Failed'), (b'cancelled', b'Cancelled')])),
                ('data', jsonfield.fields.JSONField(default=dict)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('finished', models.DateTimeField(null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('event', models.ForeignKey(to='main.Event')),
                ('upload', models.ForeignKey(to='uploads.Upload', null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

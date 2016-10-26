# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields
from django.conf import settings
import django.db.models.deletion
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0027_auto_20160929_1211'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('closedcaptions', '0002_closedcaptionstranscript'),
    ]

    operations = [
        migrations.CreateModel(
            name='RevInput',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField(max_length=500)),
                ('content_type', models.CharField(max_length=100, null=True)),
                ('filename', models.CharField(max_length=100, null=True)),
                ('uri', models.CharField(max_length=200, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='RevOrder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order_number', models.CharField(max_length=100, null=True)),
                ('uri', models.CharField(max_length=200, null=True)),
                ('output_file_formats', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=100), size=None)),
                ('status', models.CharField(max_length=100, null=True)),
                ('cancelled', models.BooleanField(default=False)),
                ('metadata', jsonfield.fields.JSONField(null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('created_user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('event', models.ForeignKey(to='main.Event')),
                ('input', models.ForeignKey(to='closedcaptions.RevInput')),
            ],
        ),
    ]

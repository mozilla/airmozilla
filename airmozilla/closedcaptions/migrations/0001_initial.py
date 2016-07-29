# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import airmozilla.closedcaptions.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0025_auto_20160630_2040'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ClosedCaptions',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file', models.FileField(upload_to=airmozilla.closedcaptions.models._upload_path_closed_captions)),
                ('transcript', jsonfield.fields.JSONField(null=True)),
                ('submission_info', jsonfield.fields.JSONField(null=True)),
                ('file_info', jsonfield.fields.JSONField(null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('created_user', models.ForeignKey(related_name='created_user', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('event', models.ForeignKey(to='main.Event')),
            ],
        ),
    ]

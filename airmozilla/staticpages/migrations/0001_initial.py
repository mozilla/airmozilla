# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='StaticPage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.CharField(max_length=100, db_index=True)),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField(blank=True)),
                ('template_name', models.CharField(max_length=100, blank=True)),
                ('privacy', models.CharField(default=b'public', max_length=40, db_index=True, choices=[(b'public', b'Public'), (b'contributors', b'Contributors'), (b'company', b'Staff')])),
                ('page_name', models.CharField(max_length=100, blank=True)),
                ('headers', jsonfield.fields.JSONField(default=dict)),
                ('allow_querystring_variables', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ('url',),
            },
            bases=(models.Model,),
        ),
    ]

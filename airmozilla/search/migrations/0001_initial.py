# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import airmozilla.search.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LoggedSearch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('term', models.CharField(max_length=200)),
                ('results', models.IntegerField(default=0)),
                ('page', models.IntegerField(default=1)),
                ('date', models.DateTimeField(default=airmozilla.search.models._get_now)),
                ('event_clicked', models.ForeignKey(to='main.Event', null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

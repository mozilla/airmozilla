# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('comments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='suggesteddiscussion',
            name='event',
            field=models.ForeignKey(to='main.SuggestedEvent', unique=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='suggesteddiscussion',
            name='moderators',
            field=models.ManyToManyField(related_name='suggested_moderators', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='discussion',
            name='event',
            field=models.ForeignKey(to='main.Event', unique=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='discussion',
            name='moderators',
            field=models.ManyToManyField(related_name='moderators', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='comment',
            name='event',
            field=models.ForeignKey(to='main.Event'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='comment',
            name='reply_to',
            field=models.ForeignKey(related_name='parent', to='comments.Comment', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='comment',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('uploads', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='suggestedevent',
            name='upload',
            field=models.ForeignKey(related_name='upload', to='uploads.Upload', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='suggestedevent',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='recruitmentmessage',
            name='modified_user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='picture',
            name='event',
            field=models.ForeignKey(related_name='picture_event', to='main.Event', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='picture',
            name='modified_user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='locationdefaultenvironment',
            name='location',
            field=models.ForeignKey(to='main.Location'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='locationdefaultenvironment',
            name='template',
            field=models.ForeignKey(to='main.Template'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='locationdefaultenvironment',
            unique_together=set([('location', 'privacy', 'template')]),
        ),
        migrations.AddField(
            model_name='location',
            name='regions',
            field=models.ManyToManyField(to='main.Region', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventtweet',
            name='creator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventtweet',
            name='event',
            field=models.ForeignKey(to='main.Event'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventrevision',
            name='channels',
            field=models.ManyToManyField(to='main.Channel'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventrevision',
            name='event',
            field=models.ForeignKey(to='main.Event'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventrevision',
            name='picture',
            field=models.ForeignKey(blank=True, to='main.Picture', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventrevision',
            name='recruitmentmessage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='main.RecruitmentMessage', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventrevision',
            name='tags',
            field=models.ManyToManyField(to='main.Tag', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventrevision',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventoldslug',
            name='event',
            field=models.ForeignKey(to='main.Event'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventlivehits',
            name='event',
            field=models.ForeignKey(to='main.Event', unique=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventhitstats',
            name='event',
            field=models.ForeignKey(to='main.Event', unique=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventemail',
            name='event',
            field=models.ForeignKey(to='main.Event'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventemail',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventassignment',
            name='event',
            field=models.ForeignKey(to='main.Event', unique=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventassignment',
            name='locations',
            field=models.ManyToManyField(to='main.Location'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='eventassignment',
            name='users',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='channels',
            field=models.ManyToManyField(to='main.Channel'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='creator',
            field=models.ForeignKey(related_name='creator', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='location',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='main.Location', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='modified_user',
            field=models.ForeignKey(related_name='modified_user', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='picture',
            field=models.ForeignKey(related_name='event_picture', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='main.Picture', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='recruitmentmessage',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='main.RecruitmentMessage', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='tags',
            field=models.ManyToManyField(to='main.Tag', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='main.Template', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='topics',
            field=models.ManyToManyField(to='main.Topic'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='upload',
            field=models.ForeignKey(related_name='event_upload', on_delete=django.db.models.deletion.SET_NULL, to='uploads.Upload', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='curatedgroup',
            name='event',
            field=models.ForeignKey(to='main.Event'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='chapter',
            name='event',
            field=models.ForeignKey(to='main.Event'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='chapter',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='channel',
            name='parent',
            field=models.ForeignKey(to='main.Channel', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='approval',
            name='event',
            field=models.ForeignKey(to='main.Event'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='approval',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='auth.Group', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='approval',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]

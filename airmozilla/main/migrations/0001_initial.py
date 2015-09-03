# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sorl.thumbnail.fields
import airmozilla.main.fields
import airmozilla.main.models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Approval',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('approved', models.BooleanField(default=False, db_index=True)),
                ('processed', models.BooleanField(default=False, db_index=True)),
                ('processed_time', models.DateTimeField(auto_now=True)),
                ('comment', models.TextField(blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(unique=True, max_length=100)),
                ('image', sorl.thumbnail.fields.ImageField(upload_to=airmozilla.main.models._upload_path_tagged, blank=True)),
                ('image_is_banner', models.BooleanField(default=False)),
                ('description', models.TextField()),
                ('created', models.DateTimeField(default=airmozilla.main.models._get_now)),
                ('reverse_order', models.BooleanField(default=False)),
                ('exclude_from_trending', models.BooleanField(default=False)),
                ('always_show', models.BooleanField(default=False, help_text=b'If always shown, it will appear as a default option visible by\n        default when uploading and entering details.')),
                ('never_show', models.BooleanField(default=False, help_text=b"If never show, it's not an option for new events. Not even\n        available but hidden first.")),
                ('default', models.BooleanField(default=False, help_text=b'\n        If no channel is chosen by the user, this one definitely gets\n        associated with the event. You can have multiple of these.\n        It doesn\'t matter if the channel is "never_show".\n    ')),
                ('no_automated_tweets', models.BooleanField(default=False, help_text=b'\n        If an event belongs to a channel with this on, that event\n        will not cause automatic EventTweets to be generated.\n    ')),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Chapter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.PositiveIntegerField()),
                ('text', models.TextField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ('timestamp',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CuratedGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('url', models.URLField(null=True)),
                ('created', models.DateTimeField(default=airmozilla.main.models._get_now)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200)),
                ('slug', models.SlugField(unique=True, max_length=215, blank=True)),
                ('template_environment', airmozilla.main.fields.EnvironmentField(help_text=b'Specify the template variables in the format<code>variable1=value</code>, one per line.', blank=True)),
                ('status', models.CharField(default=b'initiated', max_length=20, db_index=True, choices=[(b'submitted', b'Submitted'), (b'scheduled', b'Scheduled'), (b'pending', b'Pending'), (b'processing', b'Processing'), (b'removed', b'Removed')])),
                ('placeholder_img', sorl.thumbnail.fields.ImageField(null=True, upload_to=airmozilla.main.models._upload_path_tagged, blank=True)),
                ('description', models.TextField()),
                ('short_description', models.TextField(help_text=b'If not provided, this will be filled in by the first words of the full description.', blank=True)),
                ('start_time', models.DateTimeField(db_index=True)),
                ('archive_time', models.DateTimeField(db_index=True, null=True, blank=True)),
                ('call_info', models.TextField(blank=True)),
                ('additional_links', models.TextField(blank=True)),
                ('remote_presenters', models.TextField(null=True, blank=True)),
                ('popcorn_url', models.URLField(null=True, blank=True)),
                ('privacy', models.CharField(default=b'public', max_length=40, db_index=True, choices=[(b'public', b'Public'), (b'contributors', b'Contributors'), (b'company', b'Staff')])),
                ('featured', models.BooleanField(default=False, db_index=True)),
                ('pin', models.CharField(max_length=20, null=True, blank=True)),
                ('transcript', models.TextField(null=True)),
                ('duration', models.PositiveIntegerField(null=True)),
                ('estimated_duration', models.PositiveIntegerField(default=3600, null=True)),
                ('mozillian', models.CharField(max_length=200, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'permissions': (('change_event_others', 'Can edit events created by other users'), ('add_event_scheduled', 'Can create events with scheduled status')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventAssignment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=airmozilla.main.models._get_now)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventEmail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('to', models.EmailField(max_length=75)),
                ('send_failure', models.TextField(null=True, blank=True)),
                ('created', models.DateTimeField(default=airmozilla.main.models._get_now)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventHitStats',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('total_hits', models.IntegerField()),
                ('shortcode', models.CharField(max_length=100)),
                ('modified', models.DateTimeField(default=airmozilla.main.models._get_now)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventLiveHits',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('total_hits', models.IntegerField(default=0)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventOldSlug',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField(unique=True, max_length=215)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventRevision',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200)),
                ('placeholder_img', sorl.thumbnail.fields.ImageField(null=True, upload_to=airmozilla.main.models._upload_path_tagged, blank=True)),
                ('description', models.TextField()),
                ('short_description', models.TextField(help_text=b'If not provided, this will be filled in by the first words of the full description.', blank=True)),
                ('call_info', models.TextField(blank=True)),
                ('additional_links', models.TextField(blank=True)),
                ('created', models.DateTimeField(default=airmozilla.main.models._get_now)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventTweet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.CharField(max_length=140)),
                ('include_placeholder', models.BooleanField(default=False)),
                ('send_date', models.DateTimeField(default=airmozilla.main.models._get_now)),
                ('sent_date', models.DateTimeField(null=True, blank=True)),
                ('error', models.TextField(null=True, blank=True)),
                ('tweet_id', models.CharField(max_length=20, null=True, blank=True)),
                ('failed_attempts', models.IntegerField(default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=300)),
                ('timezone', models.CharField(max_length=250)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LocationDefaultEnvironment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('privacy', models.CharField(default=b'public', max_length=40, choices=[(b'public', b'Public'), (b'contributors', b'Contributors'), (b'company', b'Staff')])),
                ('template_environment', airmozilla.main.fields.EnvironmentField(help_text=b'Specify the template variables in the format<code>variable1=value</code>, one per line.')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Picture',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('size', models.PositiveIntegerField()),
                ('width', models.PositiveIntegerField()),
                ('height', models.PositiveIntegerField()),
                ('file', models.ImageField(height_field=b'height', width_field=b'width', upload_to=airmozilla.main.models._upload_path_tagged)),
                ('default_placeholder', models.BooleanField(default=False)),
                ('notes', models.CharField(max_length=100, blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created', models.DateTimeField(default=airmozilla.main.models._get_now)),
                ('modified', models.DateTimeField(default=airmozilla.main.models._get_now, auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RecruitmentMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.CharField(max_length=250)),
                ('url', models.URLField()),
                ('active', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True)),
                ('created', models.DateTimeField(default=airmozilla.main.models._get_now)),
                ('modified', models.DateTimeField(default=airmozilla.main.models._get_now, auto_now=True)),
            ],
            options={
                'ordering': ['text'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=300)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SuggestedEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200)),
                ('upcoming', models.BooleanField(default=True)),
                ('slug', models.SlugField(unique=True, max_length=215, blank=True)),
                ('placeholder_img', sorl.thumbnail.fields.ImageField(null=True, upload_to=airmozilla.main.models._upload_path_tagged, blank=True)),
                ('description', models.TextField()),
                ('short_description', models.TextField(help_text=b'If not provided, this will be filled in by the first words of the full description.', blank=True)),
                ('start_time', models.DateTimeField(db_index=True, null=True, blank=True)),
                ('call_info', models.TextField(blank=True)),
                ('additional_links', models.TextField(blank=True)),
                ('remote_presenters', models.TextField(null=True, blank=True)),
                ('popcorn_url', models.URLField(null=True, blank=True)),
                ('privacy', models.CharField(default=b'public', max_length=40, choices=[(b'public', b'Public'), (b'contributors', b'Contributors'), (b'company', b'Staff')])),
                ('featured', models.BooleanField(default=False)),
                ('created', models.DateTimeField(default=airmozilla.main.models._get_now)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('first_submitted', models.DateTimeField(null=True, blank=True)),
                ('submitted', models.DateTimeField(null=True, blank=True)),
                ('review_comments', models.TextField(null=True, blank=True)),
                ('status', models.CharField(default=b'created', max_length=40, choices=[(b'created', b'Created'), (b'submitted', b'Submitted'), (b'resubmitted', b'Resubmitted'), (b'rejected', b'Bounced back'), (b'retracted', b'Retracted'), (b'accepted', b'Accepted')])),
                ('estimated_duration', models.PositiveIntegerField(default=3600, null=True)),
                ('accepted', models.ForeignKey(blank=True, to='main.Event', null=True)),
                ('channels', models.ManyToManyField(to='main.Channel')),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='main.Location', null=True)),
                ('picture', models.ForeignKey(blank=True, to='main.Picture', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SuggestedEventComment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('comment', models.TextField()),
                ('created', models.DateTimeField(default=airmozilla.main.models._get_now)),
                ('suggested_event', models.ForeignKey(to='main.SuggestedEvent')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Template',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('content', models.TextField(help_text=b"The HTML framework for this template.  Use <code>{{ any_variable_name }}</code> for per-event tags. Other Jinja2 constructs are available, along with the related <code>request</code>, <code>datetime</code>, <code>event</code>  objects, <code>popcorn_url</code> and the <code>md5</code> function. You can also reference <code>autoplay</code> and it's always safe. Additionally we have <code>vidly_tokenize(tag, seconds)</code>, <code>edgecast_tokenize([seconds], **kwargs)</code> and  <code>akamai_tokenize([seconds], **kwargs)</code><br> Warning! Changes affect all events associated with this template.")),
                ('default_popcorn_template', models.BooleanField(default=False, help_text=b'If you have more than one templates for Popcorn videos this dictates which one is the default one.')),
                ('default_archive_template', models.BooleanField(default=False, help_text=b'When you archive an event, it needs to preselect which template it should use. This selects the best default.')),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('topic', models.TextField()),
                ('sort_order', models.PositiveIntegerField(default=0, help_text=b'The lower the higher in the list')),
                ('is_active', models.BooleanField(default=True)),
                ('groups', models.ManyToManyField(to='auth.Group')),
            ],
            options={
                'ordering': ('sort_order',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='URLMatch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('string', models.CharField(help_text=b'This matcher can contain basic regular expression characters like <code>*</code>, <code>^</code> (only as first character) and <code>$</code> (only as last character).', max_length=200)),
                ('use_count', models.IntegerField(default=0)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='URLTransform',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('find', models.CharField(max_length=200)),
                ('replace_with', models.CharField(max_length=200)),
                ('order', models.IntegerField(default=1)),
                ('match', models.ForeignKey(to='main.URLMatch')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('contributor', models.BooleanField(default=False)),
                ('optout_event_emails', models.BooleanField(default=False)),
                ('user', models.OneToOneField(related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VidlySubmission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField()),
                ('submission_time', models.DateTimeField(default=airmozilla.main.models._get_now)),
                ('tag', models.CharField(max_length=100, null=True, blank=True)),
                ('email', models.EmailField(max_length=75, null=True, blank=True)),
                ('token_protection', models.BooleanField(default=False)),
                ('hd', models.BooleanField(default=False)),
                ('submission_error', models.TextField(null=True, blank=True)),
                ('finished', models.DateTimeField(null=True, db_index=True)),
                ('errored', models.DateTimeField(null=True)),
                ('event', models.ForeignKey(to='main.Event')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='suggestedevent',
            name='tags',
            field=models.ManyToManyField(to='main.Tag', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='suggestedevent',
            name='topics',
            field=models.ManyToManyField(to='main.Topic'),
            preserve_default=True,
        ),
    ]

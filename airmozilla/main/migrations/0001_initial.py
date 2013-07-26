# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserProfile'
        db.create_table('main_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('contributor', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('main', ['UserProfile'])

        # Adding model 'Participant'
        db.create_table('main_participant', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=65, blank=True)),
            ('photo', self.gf('sorl.thumbnail.fields.ImageField')(max_length=100, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('department', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('team', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('irc', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('topic_url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('blog_url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('twitter', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('cleared', self.gf('django.db.models.fields.CharField')(default='no', max_length=15, db_index=True)),
            ('clear_token', self.gf('django.db.models.fields.CharField')(max_length=36, blank=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='participant_creator', null=True, on_delete=models.SET_NULL, to=orm['auth.User'])),
        ))
        db.send_create_signal('main', ['Participant'])

        # Adding model 'Category'
        db.create_table('main_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('main', ['Category'])

        # Adding model 'Channel'
        db.create_table('main_channel', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=100)),
            ('image', self.gf('sorl.thumbnail.fields.ImageField')(max_length=100, blank=True)),
            ('image_is_banner', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 25, 0, 0))),
        ))
        db.send_create_signal('main', ['Channel'])

        # Adding model 'Tag'
        db.create_table('main_tag', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('main', ['Tag'])

        # Adding model 'Template'
        db.create_table('main_template', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('content', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('main', ['Template'])

        # Adding model 'Location'
        db.create_table('main_location', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=300)),
            ('timezone', self.gf('django.db.models.fields.CharField')(max_length=250)),
        ))
        db.send_create_signal('main', ['Location'])

        # Adding model 'Event'
        db.create_table('main_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=215, blank=True)),
            ('template', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Template'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('template_environment', self.gf('airmozilla.main.fields.EnvironmentField')(blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='initiated', max_length=20, db_index=True)),
            ('placeholder_img', self.gf('sorl.thumbnail.fields.ImageField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('short_description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('start_time', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('archive_time', self.gf('django.db.models.fields.DateTimeField')(db_index=True, null=True, blank=True)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Location'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Category'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('call_info', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('additional_links', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('remote_presenters', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('privacy', self.gf('django.db.models.fields.CharField')(default='public', max_length=40, db_index=True)),
            ('featured', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='creator', null=True, on_delete=models.SET_NULL, to=orm['auth.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified_user', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='modified_user', null=True, on_delete=models.SET_NULL, to=orm['auth.User'])),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('main', ['Event'])

        # Adding M2M table for field participants on 'Event'
        db.create_table('main_event_participants', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('event', models.ForeignKey(orm['main.event'], null=False)),
            ('participant', models.ForeignKey(orm['main.participant'], null=False))
        ))
        db.create_unique('main_event_participants', ['event_id', 'participant_id'])

        # Adding M2M table for field tags on 'Event'
        db.create_table('main_event_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('event', models.ForeignKey(orm['main.event'], null=False)),
            ('tag', models.ForeignKey(orm['main.tag'], null=False))
        ))
        db.create_unique('main_event_tags', ['event_id', 'tag_id'])

        # Adding M2M table for field channels on 'Event'
        db.create_table('main_event_channels', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('event', models.ForeignKey(orm['main.event'], null=False)),
            ('channel', models.ForeignKey(orm['main.channel'], null=False))
        ))
        db.create_unique('main_event_channels', ['event_id', 'channel_id'])

        # Adding model 'SuggestedEvent'
        db.create_table('main_suggestedevent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=215, blank=True)),
            ('placeholder_img', self.gf('sorl.thumbnail.fields.ImageField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('short_description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('start_time', self.gf('django.db.models.fields.DateTimeField')(db_index=True, null=True, blank=True)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Location'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Category'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('call_info', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('additional_links', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('remote_presenters', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('privacy', self.gf('django.db.models.fields.CharField')(default='public', max_length=40)),
            ('featured', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 25, 0, 0))),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('submitted', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('accepted', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Event'], null=True, blank=True)),
            ('review_comments', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('main', ['SuggestedEvent'])

        # Adding M2M table for field tags on 'SuggestedEvent'
        db.create_table('main_suggestedevent_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('suggestedevent', models.ForeignKey(orm['main.suggestedevent'], null=False)),
            ('tag', models.ForeignKey(orm['main.tag'], null=False))
        ))
        db.create_unique('main_suggestedevent_tags', ['suggestedevent_id', 'tag_id'])

        # Adding M2M table for field channels on 'SuggestedEvent'
        db.create_table('main_suggestedevent_channels', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('suggestedevent', models.ForeignKey(orm['main.suggestedevent'], null=False)),
            ('channel', models.ForeignKey(orm['main.channel'], null=False))
        ))
        db.create_unique('main_suggestedevent_channels', ['suggestedevent_id', 'channel_id'])

        # Adding M2M table for field participants on 'SuggestedEvent'
        db.create_table('main_suggestedevent_participants', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('suggestedevent', models.ForeignKey(orm['main.suggestedevent'], null=False)),
            ('participant', models.ForeignKey(orm['main.participant'], null=False))
        ))
        db.create_unique('main_suggestedevent_participants', ['suggestedevent_id', 'participant_id'])

        # Adding model 'SuggestedEventComment'
        db.create_table('main_suggestedeventcomment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('suggested_event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.SuggestedEvent'])),
            ('comment', self.gf('django.db.models.fields.TextField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 25, 0, 0))),
        ))
        db.send_create_signal('main', ['SuggestedEventComment'])

        # Adding model 'EventOldSlug'
        db.create_table('main_eventoldslug', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Event'])),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=215)),
        ))
        db.send_create_signal('main', ['EventOldSlug'])

        # Adding model 'EventTweet'
        db.create_table('main_eventtweet', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Event'])),
            ('text', self.gf('django.db.models.fields.CharField')(max_length=140)),
            ('include_placeholder', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('send_date', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 25, 0, 0))),
            ('sent_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('error', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('tweet_id', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
        ))
        db.send_create_signal('main', ['EventTweet'])

        # Adding model 'Approval'
        db.create_table('main_approval', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Event'])),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.Group'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, on_delete=models.SET_NULL, blank=True)),
            ('approved', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('processed', self.gf('django.db.models.fields.BooleanField')(default=False, db_index=True)),
            ('processed_time', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('main', ['Approval'])

        # Adding model 'VidlySubmission'
        db.create_table('main_vidlysubmission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Event'])),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('submission_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 25, 0, 0))),
            ('tag', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True)),
            ('token_protection', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('hd', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('submission_error', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('main', ['VidlySubmission'])

        # Adding model 'URLMatch'
        db.create_table('main_urlmatch', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('string', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('use_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('main', ['URLMatch'])

        # Adding model 'URLTransform'
        db.create_table('main_urltransform', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('match', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.URLMatch'])),
            ('find', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('replace_with', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('order', self.gf('django.db.models.fields.IntegerField')(default=1)),
        ))
        db.send_create_signal('main', ['URLTransform'])

        # Adding model 'EventHitStats'
        db.create_table('main_eventhitstats', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Event'], unique=True)),
            ('total_hits', self.gf('django.db.models.fields.IntegerField')()),
            ('shortcode', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 7, 25, 0, 0))),
        ))
        db.send_create_signal('main', ['EventHitStats'])


    def backwards(self, orm):
        # Deleting model 'UserProfile'
        db.delete_table('main_userprofile')

        # Deleting model 'Participant'
        db.delete_table('main_participant')

        # Deleting model 'Category'
        db.delete_table('main_category')

        # Deleting model 'Channel'
        db.delete_table('main_channel')

        # Deleting model 'Tag'
        db.delete_table('main_tag')

        # Deleting model 'Template'
        db.delete_table('main_template')

        # Deleting model 'Location'
        db.delete_table('main_location')

        # Deleting model 'Event'
        db.delete_table('main_event')

        # Removing M2M table for field participants on 'Event'
        db.delete_table('main_event_participants')

        # Removing M2M table for field tags on 'Event'
        db.delete_table('main_event_tags')

        # Removing M2M table for field channels on 'Event'
        db.delete_table('main_event_channels')

        # Deleting model 'SuggestedEvent'
        db.delete_table('main_suggestedevent')

        # Removing M2M table for field tags on 'SuggestedEvent'
        db.delete_table('main_suggestedevent_tags')

        # Removing M2M table for field channels on 'SuggestedEvent'
        db.delete_table('main_suggestedevent_channels')

        # Removing M2M table for field participants on 'SuggestedEvent'
        db.delete_table('main_suggestedevent_participants')

        # Deleting model 'SuggestedEventComment'
        db.delete_table('main_suggestedeventcomment')

        # Deleting model 'EventOldSlug'
        db.delete_table('main_eventoldslug')

        # Deleting model 'EventTweet'
        db.delete_table('main_eventtweet')

        # Deleting model 'Approval'
        db.delete_table('main_approval')

        # Deleting model 'VidlySubmission'
        db.delete_table('main_vidlysubmission')

        # Deleting model 'URLMatch'
        db.delete_table('main_urlmatch')

        # Deleting model 'URLTransform'
        db.delete_table('main_urltransform')

        # Deleting model 'EventHitStats'
        db.delete_table('main_eventhitstats')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'main.approval': {
            'Meta': {'object_name': 'Approval'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Event']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'processed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'processed_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'})
        },
        'main.category': {
            'Meta': {'ordering': "['name']", 'object_name': 'Category'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'main.channel': {
            'Meta': {'ordering': "['name']", 'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 25, 0, 0)'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'image_is_banner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'main.event': {
            'Meta': {'object_name': 'Event'},
            'additional_links': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'archive_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'call_info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Category']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'channels': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['main.Channel']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Location']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'modified_user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modified_user'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'participants': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['main.Participant']", 'symmetrical': 'False'}),
            'placeholder_img': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '100'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'public'", 'max_length': '40', 'db_index': 'True'}),
            'remote_presenters': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '215', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'initiated'", 'max_length': '20', 'db_index': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['main.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Template']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'template_environment': ('airmozilla.main.fields.EnvironmentField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'main.eventhitstats': {
            'Meta': {'object_name': 'EventHitStats'},
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Event']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 25, 0, 0)'}),
            'shortcode': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'total_hits': ('django.db.models.fields.IntegerField', [], {})
        },
        'main.eventoldslug': {
            'Meta': {'object_name': 'EventOldSlug'},
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '215'})
        },
        'main.eventtweet': {
            'Meta': {'object_name': 'EventTweet'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_placeholder': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'send_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 25, 0, 0)'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'tweet_id': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'})
        },
        'main.location': {
            'Meta': {'object_name': 'Location'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'timezone': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        },
        'main.participant': {
            'Meta': {'object_name': 'Participant'},
            'blog_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'clear_token': ('django.db.models.fields.CharField', [], {'max_length': '36', 'blank': 'True'}),
            'cleared': ('django.db.models.fields.CharField', [], {'default': "'no'", 'max_length': '15', 'db_index': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'participant_creator'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['auth.User']"}),
            'department': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'irc': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'photo': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '65', 'blank': 'True'}),
            'team': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'topic_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'twitter': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        'main.suggestedevent': {
            'Meta': {'object_name': 'SuggestedEvent'},
            'accepted': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Event']", 'null': 'True', 'blank': 'True'}),
            'additional_links': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'call_info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Category']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'channels': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['main.Channel']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 25, 0, 0)'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Location']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'participants': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['main.Participant']", 'symmetrical': 'False'}),
            'placeholder_img': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '100'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'public'", 'max_length': '40'}),
            'remote_presenters': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'review_comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '215', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'submitted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['main.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'main.suggestedeventcomment': {
            'Meta': {'object_name': 'SuggestedEventComment'},
            'comment': ('django.db.models.fields.TextField', [], {}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 25, 0, 0)'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'suggested_event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.SuggestedEvent']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'})
        },
        'main.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'main.template': {
            'Meta': {'object_name': 'Template'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'main.urlmatch': {
            'Meta': {'object_name': 'URLMatch'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'string': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'use_count': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'main.urltransform': {
            'Meta': {'object_name': 'URLTransform'},
            'find': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'match': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.URLMatch']"}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'replace_with': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'main.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'contributor': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'main.vidlysubmission': {
            'Meta': {'object_name': 'VidlySubmission'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['main.Event']"}),
            'hd': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'submission_error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'submission_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 7, 25, 0, 0)'}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'token_protection': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['main']
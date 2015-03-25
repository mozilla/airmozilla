# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'StarredEvent'
        db.create_table(u'starred_starredevent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['main.Event'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'starred', ['StarredEvent'])


    def backwards(self, orm):
        # Deleting model 'StarredEvent'
        db.delete_table(u'starred_starredevent')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'main.channel': {
            'Meta': {'ordering': "['name']", 'object_name': 'Channel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2015, 2, 13, 0, 0)'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'exclude_from_trending': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'image_is_banner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.Channel']", 'null': 'True'}),
            'reverse_order': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'main.event': {
            'Meta': {'object_name': 'Event'},
            'additional_links': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'archive_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'call_info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'channels': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['main.Channel']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'creator'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['auth.User']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.Location']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'modified_user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'modified_user'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['auth.User']"}),
            'mozillian': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True'}),
            'picture': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'event_picture'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['main.Picture']"}),
            'pin': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'placeholder_img': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'popcorn_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'public'", 'max_length': '40', 'db_index': 'True'}),
            'recruitmentmessage': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.RecruitmentMessage']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'remote_presenters': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '215', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'initiated'", 'max_length': '20', 'db_index': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['main.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'template': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.Template']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'template_environment': ('airmozilla.main.fields.EnvironmentField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'transcript': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'upload': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'event_upload'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['uploads.Upload']"})
        },
        u'main.location': {
            'Meta': {'ordering': "['name']", 'object_name': 'Location'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'}),
            'regions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['main.Region']", 'symmetrical': 'False', 'blank': 'True'}),
            'timezone': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        },
        u'main.picture': {
            'Meta': {'object_name': 'Picture'},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2015, 2, 13, 0, 0)'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'picture_event'", 'null': 'True', 'to': u"orm['main.Event']"}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.PositiveIntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2015, 2, 13, 0, 0)', 'auto_now': 'True', 'blank': 'True'}),
            'modified_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'notes': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'size': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'width': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'main.recruitmentmessage': {
            'Meta': {'ordering': "['text']", 'object_name': 'RecruitmentMessage'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2015, 2, 13, 0, 0)'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2015, 2, 13, 0, 0)', 'auto_now': 'True', 'blank': 'True'}),
            'modified_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'main.region': {
            'Meta': {'ordering': "['name']", 'object_name': 'Region'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '300'})
        },
        u'main.suggestedevent': {
            'Meta': {'object_name': 'SuggestedEvent'},
            'accepted': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.Event']", 'null': 'True', 'blank': 'True'}),
            'additional_links': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'call_info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'channels': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['main.Channel']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2015, 2, 13, 0, 0)'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'first_submitted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.Location']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'picture': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.Picture']", 'null': 'True', 'blank': 'True'}),
            'placeholder_img': ('sorl.thumbnail.fields.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'popcorn_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'public'", 'max_length': '40'}),
            'remote_presenters': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'review_comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '215', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'created'", 'max_length': '40'}),
            'submitted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['main.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'upcoming': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'upload': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'upload'", 'null': 'True', 'to': u"orm['uploads.Upload']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'main.tag': {
            'Meta': {'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'main.template': {
            'Meta': {'ordering': "['name']", 'object_name': 'Template'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'default_archive_template': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'default_popcorn_template': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'starred.starredevent': {
            'Meta': {'object_name': 'StarredEvent'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['main.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'uploads.upload': {
            'Meta': {'object_name': 'Upload'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'event'", 'null': 'True', 'to': u"orm['main.Event']"}),
            'file_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.BigIntegerField', [], {}),
            'suggested_event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'suggested_event'", 'null': 'True', 'to': u"orm['main.SuggestedEvent']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '400'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['starred']
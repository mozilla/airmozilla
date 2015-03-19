# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'StaticPage'
        db.create_table(u'staticpages_staticpage', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=100, db_index=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('template_name', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('privacy', self.gf('django.db.models.fields.CharField')(default='public', max_length=40, db_index=True)),
            ('cors_header', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('content_type', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('page_name', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('allow_querystring_variables', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'staticpages', ['StaticPage'])


    def backwards(self, orm):
        # Deleting model 'StaticPage'
        db.delete_table(u'staticpages_staticpage')


    models = {
        u'staticpages.staticpage': {
            'Meta': {'object_name': 'StaticPage'},
            'allow_querystring_variables': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content_type': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'cors_header': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'page_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'privacy': ('django.db.models.fields.CharField', [], {'default': "'public'", 'max_length': '40', 'db_index': 'True'}),
            'template_name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'})
        }
    }

    complete_apps = ['staticpages']
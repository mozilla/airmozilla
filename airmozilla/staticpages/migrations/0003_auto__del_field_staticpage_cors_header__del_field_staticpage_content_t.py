# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'StaticPage.cors_header'
        db.delete_column(u'staticpages_staticpage', 'cors_header')

        # Deleting field 'StaticPage.content_type'
        db.delete_column(u'staticpages_staticpage', 'content_type')

        # Adding field 'StaticPage.headers'
        db.add_column(u'staticpages_staticpage', 'headers',
                      self.gf('jsonfield.fields.JSONField')(default={}),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'StaticPage.cors_header'
        db.add_column(u'staticpages_staticpage', 'cors_header',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True),
                      keep_default=False)

        # Adding field 'StaticPage.content_type'
        db.add_column(u'staticpages_staticpage', 'content_type',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=100, blank=True),
                      keep_default=False)

        # Deleting field 'StaticPage.headers'
        db.delete_column(u'staticpages_staticpage', 'headers')


    models = {
        u'staticpages.staticpage': {
            'Meta': {'ordering': "('url',)", 'object_name': 'StaticPage'},
            'allow_querystring_variables': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'headers': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
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
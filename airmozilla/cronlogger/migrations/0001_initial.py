# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CronLog'
        db.create_table(u'cronlogger_cronlog', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('job', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('stdout', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('stderr', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('exc_type', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('exc_value', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('exc_traceback', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'cronlogger', ['CronLog'])


    def backwards(self, orm):
        # Deleting model 'CronLog'
        db.delete_table(u'cronlogger_cronlog')


    models = {
        u'cronlogger.cronlog': {
            'Meta': {'object_name': 'CronLog'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'exc_traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'exc_type': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'exc_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'job': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'stderr': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stdout': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['cronlogger']
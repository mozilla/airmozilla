# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'CronLog.duration'
        db.add_column(u'cronlogger_cronlog', 'duration',
                      self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=10, decimal_places=3),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'CronLog.duration'
        db.delete_column(u'cronlogger_cronlog', 'duration')


    models = {
        u'cronlogger.cronlog': {
            'Meta': {'object_name': 'CronLog'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '3'}),
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
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group


class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        Group.objects.get_or_create(
            name=settings.NOTIFICATIONS_GROUP_NAME
        )

    def backwards(self, orm):
        "Write your backwards methods here."
        Group.objects.filter(
            name=settings.NOTIFICATIONS_GROUP_NAME
        ).delete()

    models = {

    }

    complete_apps = ['suggest']
    symmetrical = True

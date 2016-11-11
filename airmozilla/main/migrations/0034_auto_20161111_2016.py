# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def forwards(apps, schema_editor):
    VidlyTagDomain = apps.get_model('main', 'VidlyTagDomain')
    VidlyTagDomain.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0033_vidlytagdomain_private'),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]

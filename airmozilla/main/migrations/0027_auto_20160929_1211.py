# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0026_auto_20160826_1712'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='recruitmentmessage',
            name='modified_user',
        ),
        migrations.RemoveField(
            model_name='event',
            name='recruitmentmessage',
        ),
        migrations.RemoveField(
            model_name='eventrevision',
            name='recruitmentmessage',
        ),
        migrations.DeleteModel(
            name='RecruitmentMessage',
        ),
    ]

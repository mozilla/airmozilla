# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0014_auto_20160304_1641'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventemail',
            name='to',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='picture',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='picture',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='recruitmentmessage',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='recruitmentmessage',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='vidlysubmission',
            name='email',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
    ]

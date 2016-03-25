# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0017_auto_20160324_2131'),
    ]

    operations = [
        migrations.AlterField(
            model_name='suggestedevent',
            name='privacy',
            field=models.CharField(default=b'public', max_length=40, choices=[(b'public', b'Public'), (b'contributors', b'Contributors'), (b'some_contributors', b'Some Contributors'), (b'company', b'Staff')]),
        ),
    ]

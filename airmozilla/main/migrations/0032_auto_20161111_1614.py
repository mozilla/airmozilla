# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0031_useremailalias'),
    ]

    operations = [
        migrations.CreateModel(
            name='VidlyTagDomain',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tag', models.CharField(max_length=100, db_index=True)),
                ('type', models.CharField(max_length=100)),
                ('domain', models.CharField(max_length=100)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='vidlytagdomain',
            unique_together=set([('tag', 'type')]),
        ),
    ]

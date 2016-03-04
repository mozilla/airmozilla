# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0013_auto_20160223_1757'),
    ]

    operations = [
        migrations.AlterField(
            model_name='template',
            name='content',
            field=models.TextField(help_text=b"The HTML framework for this template.  Use <code>{{ any_variable_name }}</code> for per-event tags. Other Jinja constructs are available, along with the related <code>request</code>, <code>datetime</code>, <code>event</code>  objects, and the <code>md5</code> function. There is also the  <code>poster_url</code> variable which is the full URL to the  poster of the event.<br> You can also reference <code>autoplay</code> and it's always safe. Additionally we have <code>vidly_tokenize(tag, seconds)</code>, <code>edgecast_tokenize([seconds], **kwargs)</code> and  <code>akamai_tokenize([seconds], **kwargs)</code><br> Warning! Changes affect all events associated with this template."),
            preserve_default=True,
        ),
    ]

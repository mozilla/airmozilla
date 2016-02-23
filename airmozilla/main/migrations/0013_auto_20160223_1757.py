# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_auto_20160204_1503'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='eventassignment',
            options={'permissions': (('can_be_assigned', 'Can be assigned to events'),)},
        ),
        migrations.AlterField(
            model_name='suggestedevent',
            name='status',
            field=models.CharField(default=b'created', max_length=40, choices=[(b'created', b'Created'), (b'submitted', b'Submitted'), (b'resubmitted', b'Resubmitted'), (b'rejected', b'Bounced back'), (b'retracted', b'Retracted'), (b'accepted', b'Accepted'), (b'removed', b'Removed')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='template',
            name='content',
            field=models.TextField(help_text=b"The HTML framework for this template.  Use <code>{{ any_variable_name }}</code> for per-event tags. Other Jinja2 constructs are available, along with the related <code>request</code>, <code>datetime</code>, <code>event</code>  objects, and the <code>md5</code> function. You can also reference <code>autoplay</code> and it's always safe. Additionally we have <code>vidly_tokenize(tag, seconds)</code>, <code>edgecast_tokenize([seconds], **kwargs)</code> and  <code>akamai_tokenize([seconds], **kwargs)</code><br> Warning! Changes affect all events associated with this template."),
            preserve_default=True,
        ),
    ]

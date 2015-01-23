# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0007_remove_metadata_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='metadata',
            name='name',
            field=models.CharField(default=0, max_length=80),
            preserve_default=False,
        ),
    ]

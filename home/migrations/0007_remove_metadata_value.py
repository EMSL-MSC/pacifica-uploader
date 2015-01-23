# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0006_metadata'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='metadata',
            name='value',
        ),
    ]

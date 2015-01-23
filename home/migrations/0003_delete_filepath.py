# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0002_auto_20141103_1321'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Filepath',
        ),
    ]

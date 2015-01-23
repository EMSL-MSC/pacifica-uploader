# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_filepath'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='filepath',
            name='id',
        ),
        migrations.AlterField(
            model_name='filepath',
            name='name',
            field=models.CharField(max_length=80, serialize=False, primary_key=True),
        ),
    ]

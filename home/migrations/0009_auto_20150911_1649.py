# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0008_metadata_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='filepath',
            name='pooky',
            field=models.CharField(default=datetime.date(2015, 9, 11), max_length=80, serialize=False, primary_key=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='filepath',
            name='name',
            field=models.CharField(max_length=80, primary_key=True),
        ),
    ]

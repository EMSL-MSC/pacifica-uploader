# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0005_auto_20141103_1337'),
    ]

    operations = [
        migrations.CreateModel(
            name='Metadata',
            fields=[
                ('label', models.CharField(max_length=80, serialize=False, primary_key=True)),
                ('value', models.CharField(max_length=500)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-04-10 06:48
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Manager', '0005_auto_20170410_0641'),
    ]

    operations = [
        migrations.DeleteModel(
            name='transactions',
        ),
    ]

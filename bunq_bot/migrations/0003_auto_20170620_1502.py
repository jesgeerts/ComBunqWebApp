# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-20 13:02
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bunq_bot', '0002_auto_20170620_1430'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='BotInfo',
            new_name='ChatInfo',
        ),
        migrations.RenameField(
            model_name='chatinfo',
            old_name='chat_ids',
            new_name='chat_id',
        ),
    ]

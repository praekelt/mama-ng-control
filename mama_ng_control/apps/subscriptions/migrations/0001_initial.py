# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.hstore
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('version', models.IntegerField(default=1)),
                ('messageset_id', models.IntegerField()),
                ('next_sequence_number', models.IntegerField(default=1)),
                ('lang', models.CharField(max_length=6)),
                ('active', models.BooleanField(default=True)),
                ('completed', models.BooleanField(default=False)),
                ('schedule', models.IntegerField(default=1)),
                ('process_status', models.IntegerField(default=0)),
                ('metadata', django.contrib.postgres.fields.hstore.HStoreField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contact', models.ForeignKey(related_name='subscriptions', to='contacts.Contact')),
            ],
        ),
    ]

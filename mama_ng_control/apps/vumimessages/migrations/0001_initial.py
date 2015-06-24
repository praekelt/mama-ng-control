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
            name='Inbound',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('message_id', models.CharField(max_length=36)),
                ('in_reply_to', models.CharField(max_length=36, null=True, blank=True)),
                ('to_addr', models.CharField(max_length=255)),
                ('from_addr', models.CharField(max_length=255)),
                ('content', models.CharField(max_length=1000, null=True, blank=True)),
                ('transport_name', models.CharField(max_length=200)),
                ('transport_type', models.CharField(max_length=200)),
                ('helper_metadata', django.contrib.postgres.fields.hstore.HStoreField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Outbound',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('version', models.IntegerField(default=1)),
                ('content', models.CharField(max_length=1000, null=True, blank=True)),
                ('vumi_message_id', models.CharField(max_length=36, null=True, blank=True)),
                ('delivered', models.BooleanField(default=False)),
                ('attempts', models.IntegerField(default=0)),
                ('metadata', django.contrib.postgres.fields.hstore.HStoreField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contact', models.ForeignKey(related_name='messages', to='contacts.Contact')),
            ],
        ),
    ]

import uuid

from django.contrib.postgres.fields import HStoreField
from django.db import models

from mama_ng_control.apps.contacts.models import Contact


class Subscription(models.Model):

    """
    Contacts subscriptions and their status
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(Contact,
                                related_name='subscriptions',
                                null=False)
    version = models.IntegerField(default=1)
    messageset_id = models.IntegerField(null=False, blank=False)
    next_sequence_number = models.IntegerField(default=1, null=False,
                                               blank=False)
    lang = models.CharField(max_length=6, null=False, blank=False)
    active = models.BooleanField(default=True)
    completed = models.BooleanField(default=False)
    schedule = models.IntegerField(default=1)
    process_status = models.IntegerField(default=0, null=False, blank=False)
    metadata = HStoreField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  # __unicode__ on Python 2
        return str(self.id)

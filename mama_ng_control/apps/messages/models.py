import uuid

from django.contrib.postgres.fields import HStoreField
from django.db import models

from mama_ng_control.apps.contacts.models import Contact


class Outbound(models.Model):

    """
    Contacts outbound messages and their status
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(Contact,
                                related_name='messages',
                                null=False)
    version = models.IntegerField(default=1)
    content = models.CharField(null=False, blank=False)
    vumi_message_id = models.IntegerField(null=True)
    delivered = models.BooleanField(default=False)
    attempts = models.IntegerField(default=1)
    metadata = HStoreField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  # __unicode__ on Python 2
        return str(self.id)


class Inbound(models.Model):

    """
    Contacts inbound messages from Vumi
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message_id = models.CharField(null=False, blank=False)
    in_reply_to = models.CharField(null=True, blank=True)
    to_addr = models.CharField(null=False, blank=False)
    from_addr = models.CharField(null=False, blank=False)
    content = models.CharField(null=True, blank=True)
    transport_name = models.CharField(null=False, blank=False)
    transport_type = models.CharField(null=False, blank=False)
    helper_metadata = HStoreField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  # __unicode__ on Python 2
        return str(self.id)

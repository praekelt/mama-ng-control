import uuid

from django.contrib.postgres.fields import HStoreField
from django.db import models

from mama_ng_control.apps.contacts.models import Contact


class Outbound(models.Model):

    """
    Contacts outbound messages and their status
    delivered is set to true when ack received because delivery reports patchy
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(Contact,
                                related_name='messages',
                                null=False)
    version = models.IntegerField(default=1)
    content = models.CharField(null=True, blank=True, max_length=1000)
    vumi_message_id = models.CharField(null=True, blank=True, max_length=36)
    delivered = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
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
    message_id = models.CharField(null=False, blank=False, max_length=36)
    in_reply_to = models.CharField(null=True, blank=True, max_length=36)
    to_addr = models.CharField(null=False, blank=False, max_length=255)
    from_addr = models.CharField(null=False, blank=False, max_length=255)
    content = models.CharField(null=True, blank=True, max_length=1000)
    transport_name = models.CharField(null=False, blank=False, max_length=200)
    transport_type = models.CharField(null=False, blank=False, max_length=200)
    helper_metadata = HStoreField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):  # __unicode__ on Python 2
        return str(self.id)

# Make sure new messages are sent
from django.db.models.signals import post_save
from django.dispatch import receiver
from .tasks import send_message


@receiver(post_save, sender=Outbound)
def fire_send_if_new(sender, instance, created, **kwargs):
    if created:
        send_message.delay(str(instance.id))

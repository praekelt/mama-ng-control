from celery.task import Task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from client.messaging_contentstore.contentstore import ContentStoreApiClient

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

logger = get_task_logger(__name__)

from mama_ng_control.apps.vumimessages.models import Outbound
from mama_ng_control.apps.contacts.models import Contact


class Create_Message(Task):

    """
    Task to create and populate a message with content
    """
    name = "mama_ng_control.apps.subscriptions.tasks.create_message"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """

    def contentstore_client(self):
        return ContentStoreApiClient(
            auth_token=settings.CONTENTSTORE_AUTH_TOKEN,
            api_url=settings.CONTENTSTORE_API_URL)

    def run(self, contact_id, messageset_id, sequence_number, lang,
            subscription, **kwargs):
        """
        Returns success message
        """
        l = self.get_logger(**kwargs)
        l.info("Creating Outbound Message and Content")
        try:
            contact = Contact.objects.get(pk=contact_id)
            contentstore = self.contentstore_client()
            params = {
                "messageset": messageset_id,
                "sequence_number": sequence_number,
                "lang": lang
            }
            # should only return one in a list
            messages = contentstore.get_messages(params=params)
            if len(messages) > 0:
                # it more than one matching message in Content store due to
                # poor management then we just use first
                message_id = messages[0]["id"]
                message_details = contentstore.get_message_content(message_id)
                # Create the message which will trigger send task
                new_message = Outbound()
                new_message.contact = contact
                new_message.content = message_details["text_content"]
                new_message.metadata = {}
                new_message.metadata["voice_speech_url"] = \
                    message_details["binary_content"]["content"]
                new_message.metadata["subscription"] = subscription
                new_message.save()
                return "New message created <%s>" % str(new_message.id)
            return "No message found for messageset <%s>, \
                    sequence_number <%s>, lang <%s>" % (
                messageset_id, sequence_number, lang, )
        except ObjectDoesNotExist:
            logger.error('Missing Contact to message', exc_info=True)

        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing message creation task \
                 via Celery.',
                exc_info=True)

create_message = Create_Message()

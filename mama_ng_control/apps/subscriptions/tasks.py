from celery.task import Task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from client.messaging_contentstore.contentstore import ContentStoreApiClient

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

logger = get_task_logger(__name__)

from .models import Subscription
from mama_ng_control.apps.vumimessages.models import Outbound
from mama_ng_control.apps.contacts.models import Contact
from mama_ng_control.scheduler.client import SchedulerApiClient


def contentstore_client():
    return ContentStoreApiClient(
        auth_token=settings.CONTENTSTORE_AUTH_TOKEN,
        api_url=settings.CONTENTSTORE_API_URL)


def scheduler_client():
    return SchedulerApiClient(
        username=settings.SCHEDULER_USERNAME,
        password=settings.SCHEDULER_PASSWORD,
        api_url=settings.SCHEDULER_URL)


class Schedule_Create(Task):

    """
    Task to tell scheduler a new subscription created
    """
    name = "mama_ng_control.apps.subscription.tasks.schedule_create"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """

    def contentstore_client(self):
        return ContentStoreApiClient(
            auth_token=settings.CONTENTSTORE_AUTH_TOKEN,
            api_url=settings.CONTENTSTORE_API_URL)

    def scheduler_client(self):
        return SchedulerApiClient(
            username=settings.SCHEDULER_USERNAME,
            password=settings.SCHEDULER_PASSWORD,
            api_url=settings.SCHEDULER_URL)

    def schedule_to_cron(self, schedule):
        return "%s %s %s %s %s" % (
            schedule["minute"],
            schedule["hour"],
            schedule["day_of_month"],
            schedule["month_of_year"],
            schedule["day_of_week"]
        )

    def run(self, subscription_id, **kwargs):
        """
        Returns scheduler-id
        """
        l = self.get_logger(**kwargs)
        l.info("Creating schedule for <%s>" % (subscription_id,))
        try:
            subscription = Subscription.objects.get(pk=subscription_id)
            scheduler = self.scheduler_client()
            contentstore = self.contentstore_client()
            # get the subscription schedule/protocol from content store
            l.info("Loading contentstore schedule <%s>" % (
                subscription.schedule,))
            csschedule = contentstore.get_schedule(subscription.schedule)
            # Build the schedule POST create object
            schedule = {
                "subscriptionId": subscription_id,
                "frequency": subscription.metadata["frequency"],
                "sendCounter": subscription.next_sequence_number,
                "cronDefinition": self.schedule_to_cron(csschedule),
                "endpoint": "%s/subscriptions/%s/send" % (
                    settings.CONTROL_URL, subscription_id)
            }
            result = scheduler.create_schedule(schedule)
            l.info("Created schedule <%s> on scheduler for sub <%s>" % (
                result["id"], subscription_id))
            subscription.metadata["scheduler_schedule_id"] = result["id"]
            subscription.save()
            return result["id"]

        except ObjectDoesNotExist:
            logger.error('Missing Subscription', exc_info=True)

        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing schedule create \
                 via Celery.',
                exc_info=True)

schedule_create = Schedule_Create()


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

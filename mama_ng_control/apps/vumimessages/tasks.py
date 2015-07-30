from celery.task import Task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from go_http.send import HttpApiSender
from requests.exceptions import HTTPError

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from mama_ng_control.apps.subscriptions.models import Subscription
from mama_ng_control.scheduler.client import SchedulerApiClient

logger = get_task_logger(__name__)

from .models import Outbound


class Send_Metric(Task):

    """
    Task to fire metrics
    TODO: Replace fire with metrics client creation when ready. Issue #8.
    """
    name = "mama_ng_control.apps.vumimessages.tasks.send_metric"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """

    def vumi_client(self):
        return HttpApiSender(
            account_key=settings.VUMI_ACCOUNT_KEY,
            conversation_key=settings.VUMI_CONVERSATION_KEY,
            conversation_token=settings.VUMI_ACCOUNT_TOKEN
        )
        # return LoggingSender('go_http.test')

    def run(self, metric, value, agg, **kwargs):
        """
        Returns count from api
        """
        l = self.get_logger(**kwargs)

        l.info("Firing metric: %r [%s] -> %g" % (metric, agg, float(value)))
        try:
            sender = self.vumi_client()
            result = sender.fire_metric(metric, value, agg=agg)
            l.info("Result of firing metric: %s" % (result["success"]))
            return result

        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing metric fire \
                 via Celery.',
                exc_info=True)

send_metric = Send_Metric()


class Scheduler_Ack(Task):

    """
    Task to tell scheduler message is deemed complete
    """
    name = "mama_ng_control.apps.vumimessages.tasks.scheduler_ack"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """

    def scheduler_client(self):
        return SchedulerApiClient(
            username=settings.SCHEDULER_USERNAME,
            password=settings.SCHEDULER_PASSWORD,
            api_url=settings.SCHEDULER_URL)

    def run(self, subscription_id, **kwargs):
        """
        Returns True if successful
        """
        l = self.get_logger(**kwargs)
        l.info("Marking <%s> as ack on scheduler" % (subscription_id,))
        try:
            subscription = Subscription.objects.get(pk=subscription_id)
            scheduler = self.scheduler_client()
            # Call the scheduler and delete the pending message
            scheduler.delete_message(
                subscription.metadata["scheduler_message_id"])
            l.info("Deleted message <%s> from scheduler id <%s>" % (
                subscription.metadata["scheduler_message_id"],
                subscription.metadata["scheduler_subscription_id"]))
            # remove the message_id in acknowledgement
            subscription.metadata["scheduler_message_id"] = ""
            subscription.save()
            return True

        except ObjectDoesNotExist:
            logger.error('Missing Subscription', exc_info=True)
            return False

        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing scheduler ack \
                 via Celery.',
                exc_info=True)
            return False

scheduler_ack = Scheduler_Ack()


class Send_Message(Task):

    """
    Task to load and contruct message and send them off
    """
    name = "mama_ng_control.apps.vumimessages.tasks.send_message"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """

    def vumi_client(self):
        return HttpApiSender(
            api_url=settings.VUMI_API_URL,
            account_key=settings.VUMI_ACCOUNT_KEY,
            conversation_key=settings.VUMI_CONVERSATION_KEY,
            conversation_token=settings.VUMI_ACCOUNT_TOKEN
        )

    def run(self, message_id, **kwargs):
        """
        Load and contruct message and send them off
        """
        l = self.get_logger(**kwargs)

        l.info("Loading Outbound Message")
        try:
            message = Outbound.objects.get(pk=message_id)
            if message.attempts < settings.MAMA_NG_CONTROL_MAX_RETRIES:
                # send or resend
                sender = self.vumi_client()
                content = message.content
                to_addr = message.contact.address("msisdn")
                if len(to_addr) == 0:
                    l.info("Failed to send message <%s>. No address." % (
                        message_id,))
                    scheduler_ack.delay(
                        message.metadata["subscription"])
                else:
                    try:
                        if "voice_speech_url" in message.metadata:
                            # Voice message
                            speech_url = message.metadata["voice_speech_url"]
                            vumiresponse = sender.send_voice(
                                to_addr[0], content,
                                speech_url=speech_url,
                                session_event="new")
                            l.info("Sent voice message to <%s>" % to_addr)
                        else:
                            # Plain content
                            vumiresponse = sender.send_text(
                                to_addr[0], content,
                                session_event="new")
                            l.info("Sent text message to <%s>" % to_addr)
                        message.attempts += 1
                        message.vumi_message_id = vumiresponse["message_id"]
                        message.save()
                        send_metric.delay(metric="vumimessage.tries", value=1,
                                          agg="sum")
                    except HTTPError as e:
                        # retry message sending if in 500 range (3 default
                        # retries)
                        if 500 < e.response.status_code < 599:
                            raise self.retry(exc=e)
                        else:
                            raise e
                    return vumiresponse
            else:
                l.info("Message <%s> at max retries." % str(message_id))
                send_metric.delay(metric="vumimessage.maxretries", value=1,
                                  agg="sum")
                # send scheduler ack
                scheduler_ack.delay(message.metadata["subscription"])
        except ObjectDoesNotExist:
            logger.error('Missing Outbound message', exc_info=True)

        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing location search \
                 via Celery.',
                exc_info=True)

send_message = Send_Message()

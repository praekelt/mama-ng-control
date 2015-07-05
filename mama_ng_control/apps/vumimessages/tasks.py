from celery.task import Task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded
from go_http.send import HttpApiSender

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

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
    TODO: Replace with HTTP POST. Issue #7
    """
    name = "mama_ng_control.apps.vumimessages.tasks.scheduler_ack"

    class FailedEventRequest(Exception):

        """
        The attempted task failed because of a non-200 HTTP return
        code.
        """

    def run(self, subscription, **kwargs):
        """
        Returns count from api
        """
        l = self.get_logger(**kwargs)
        # load from Subscription
        # subscription.metadata["scheduler_subscription_id"]
        # subscription.metadata["scheduler_message_id"]
        l.info("Marking <%s> as ack on scheduler" % (subscription,))
        try:
            result = True
            l.info("Marked <%s> as ack on scheduler" % (subscription,))
            return result

        except SoftTimeLimitExceeded:
            logger.error(
                'Soft time limit exceed processing scheduler ack \
                 via Celery.',
                exc_info=True)

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
                # TODO - Issue #9 - move voice to
                # helper_metadata = {"voice": {"speech_url": None }}
                # helper_metadata["voice"]["speech_url"] =
                # speech = message.metadata["voice_speech_url"]
                if "speech_url" in message.metadata:
                    content = message.metadata["voice_speech_url"]
                to_addr = message.contact.address("msisdn")
                if len(to_addr) == 0:
                    print to_addr
                    l.info("Failed to send message <%s>. No address." % (
                        message_id,))
                    scheduler_ack.delay(
                        message.metadata["subscription"])
                else:
                    vumiresponse = sender.send_text(
                        to_addr[0], content)
                    l.info("Sent message to <%s>" % to_addr)
                    message.attempts += 1
                    message.vumi_message_id = vumiresponse["message_id"]
                    message.save()
                    send_metric.delay(metric="vumimessage.tries", value=1,
                                      agg="sum")
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

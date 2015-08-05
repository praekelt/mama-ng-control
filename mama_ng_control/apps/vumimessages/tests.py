import json
import uuid
import logging
import responses

from django.test import TestCase
from django.contrib.auth.models import User
from django.db.models.signals import post_save

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from go_http.send import LoggingSender

from .models import Inbound, Outbound, fire_msg_action_if_new
from .tasks import Send_Message, Send_Metric
from mama_ng_control.apps.contacts.models import Contact
from mama_ng_control.apps.subscriptions.models import (
    Subscription, fire_sub_action_if_new)

Send_Metric.vumi_client = lambda x: LoggingSender('go_http.test')
Send_Message.vumi_client = lambda x: LoggingSender('go_http.test')


class RecordingHandler(logging.Handler):

    """ Record logs. """
    logs = None

    def emit(self, record):
        if self.logs is None:
            self.logs = []
        self.logs.append(record)


class APITestCase(TestCase):

    def setUp(self):
        self.client = APIClient()


class AuthenticatedAPITestCase(APITestCase):

    def setUp(self):
        super(AuthenticatedAPITestCase, self).setUp()
        self.username = 'testuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(self.username,
                                             'testuser@example.com',
                                             self.password)
        token = Token.objects.create(user=self.user)
        self.token = token.key
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token)
        details = {
            "name": "Foo Bar",
            "default_addr_type": "msisdn",
            "addresses": "msisdn:+27123 email:foo@bar.com"
        }
        contact = Contact.objects.create(details=details)
        self.contact = contact.id
        self.handler = RecordingHandler()
        logger = logging.getLogger('go_http.test')
        logger.setLevel(logging.INFO)
        logger.addHandler(self.handler)

    def check_logs(self, msg):
        if self.handler.logs is None:  # nothing to check
            return False
        if type(self.handler.logs) != list:
            [logs] = self.handler.logs
        else:
            logs = self.handler.logs
        for log in logs:
            print log.msg
            if log.msg == msg:
                return True
        return False

    def _replace_post_save_hooks_outbound(self):
        has_listeners = lambda: post_save.has_listeners(Outbound)
        assert has_listeners(), (
            "Outbound model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(fire_msg_action_if_new, sender=Outbound)
        assert not has_listeners(), (
            "Outbound model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks_outbound(self):
        has_listeners = lambda: post_save.has_listeners(Outbound)
        assert not has_listeners(), (
            "Outbound model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests.")
        post_save.connect(fire_msg_action_if_new, sender=Outbound)

    def _replace_post_save_hooks_subscription(self):
        has_listeners = lambda: post_save.has_listeners(Subscription)
        assert has_listeners(), (
            "Subscription model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(fire_sub_action_if_new, sender=Subscription)
        assert not has_listeners(), (
            "Subscription model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks_subscription(self):
        has_listeners = lambda: post_save.has_listeners(Subscription)
        assert not has_listeners(), (
            "Subscription model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests.")
        post_save.connect(fire_sub_action_if_new, sender=Subscription)


class TestVumiMessagesAPI(AuthenticatedAPITestCase):

    def make_subscription(self):
        self._replace_post_save_hooks_subscription()  # don't let fixtures fire
        post_data = {
            "contact": "/api/v1/contacts/%s/" % self.contact,
            "messageset_id": "1",
            "next_sequence_number": "1",
            "lang": "en_ZA",
            "active": "true",
            "completed": "false",
            "schedule": "1",
            "process_status": "0",
            "metadata": {
                "source": "RapidProVoice",
                "frequency": 10,
                "scheduler_subscription_id": "1",
                "scheduler_message_id": "1"
            }
        }
        response = self.client.post('/api/v1/subscriptions/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self._restore_post_save_hooks_subscription()  # let tests fire tasks
        return response.data["id"]

    def make_outbound(self):
        self._replace_post_save_hooks_outbound()  # don't let fixtures fire
        subscription = self.make_subscription()
        post_data = {
            "contact": "/api/v1/contacts/%s/" % self.contact,
            "vumi_message_id": "075a32da-e1e4-4424-be46-1d09b71056fd",
            "content": "Simple outbound message",
            "delivered": "false",
            "attempts": 1,
            "metadata": {
                "subscription": subscription
            }
        }
        response = self.client.post('/api/v1/messages/outbound/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        self._restore_post_save_hooks_outbound()  # let tests fire tasks
        self.check_logs(
            "Message: u'Simple outbound message' sent to u'+27123'")
        return response.data["id"]

    def make_inbound(self, in_reply_to):
        post_data = {
            "message_id": str(uuid.uuid4()),
            "in_reply_to": in_reply_to,
            "to_addr": "+27123",
            "from_addr": "020",
            "content": "Call delivered",
            "transport_name": "test_voice",
            "transport_type": "voice",
            "helper_metadata": {}
        }
        response = self.client.post('/api/v1/messages/inbound/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        return response.data["id"]

    def test_login(self):
        request = self.client.post(
            '/api-token-auth/',
            {"username": "testuser",
             "password": "testpass"})
        token = request.data.get('token', None)
        self.assertIsNotNone(
            token, "Could not receive authentication token on login post.")
        self.assertEqual(request.status_code, 200,
                         "Status code on /auth/token/ was %s (should be 200)."
                         % request.status_code)

    def test_create_outbound_data(self):
        post_outbound = {
            "contact": "/api/v1/contacts/%s/" % self.contact,
            "vumi_message_id": "075a32da-e1e4-4424-be46-1d09b71056fd",
            "content": "Say something",
            "delivered": "false",
            "attempts": 0,
            "metadata": {}
        }
        response = self.client.post('/api/v1/messages/outbound/',
                                    json.dumps(post_outbound),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Outbound.objects.last()
        self.assertIsNotNone(d.id)
        self.assertEqual(d.version, 1)
        self.assertEqual(str(d.contact.id), str(self.contact))
        self.assertEqual(d.content, "Say something")
        self.assertEqual(d.delivered, False)
        self.assertEqual(d.attempts, 1)
        self.assertEqual(d.metadata, {})

    def test_create_outbound_data_simple(self):
        post_outbound = {
            "contact": "/api/v1/contacts/%s/" % self.contact,
            "delivered": "false",
            "metadata": {
                "voice_speech_url": "https://foo.com/file.mp3"
            }
        }
        response = self.client.post('/api/v1/messages/outbound/',
                                    json.dumps(post_outbound),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Outbound.objects.last()
        self.assertIsNotNone(d.id)
        self.assertEqual(d.version, 1)
        self.assertEqual(str(d.contact.id), str(self.contact))
        self.assertEqual(d.delivered, False)
        self.assertEqual(d.attempts, 1)
        self.assertEqual(d.metadata, {
            "voice_speech_url": "https://foo.com/file.mp3"
        })

    def test_update_outbound_data(self):
        existing = self.make_outbound()
        patch_outbound = {
            "delivered": "true",
            "attempts": 2
        }
        response = self.client.patch('/api/v1/messages/outbound/%s/' %
                                     existing,
                                     json.dumps(patch_outbound),
                                     content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        d = Outbound.objects.get(pk=existing)
        self.assertEqual(d.version, 1)
        self.assertEqual(str(d.contact.id), str(self.contact))
        self.assertEqual(d.delivered, True)
        self.assertEqual(d.attempts, 2)

    def test_delete_outbound_data(self):
        existing = self.make_outbound()
        response = self.client.delete('/api/v1/messages/outbound/%s/' %
                                      existing,
                                      content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        d = Outbound.objects.filter(id=existing).count()
        self.assertEqual(d, 0)

    def test_create_inbound_data(self):
        existing_outbound = self.make_outbound()
        out = Outbound.objects.get(pk=existing_outbound)
        message_id = str(uuid.uuid4())
        post_inbound = {
            "message_id": message_id,
            "in_reply_to": out.vumi_message_id,
            "to_addr": "+27123",
            "from_addr": "020",
            "content": "Call delivered",
            "transport_name": "test_voice",
            "transport_type": "voice",
            "helper_metadata": {}
        }
        response = self.client.post('/api/v1/messages/inbound/',
                                    json.dumps(post_inbound),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Inbound.objects.last()
        self.assertIsNotNone(d.id)
        self.assertEqual(d.message_id, message_id)
        self.assertEqual(d.to_addr, "+27123")
        self.assertEqual(d.from_addr, "020")
        self.assertEqual(d.content, "Call delivered")
        self.assertEqual(d.transport_name, "test_voice")
        self.assertEqual(d.transport_type, "voice")
        self.assertEqual(d.helper_metadata, {})

    def test_update_inbound_data(self):
        existing_outbound = self.make_outbound()
        out = Outbound.objects.get(pk=existing_outbound)
        existing = self.make_inbound(out.vumi_message_id)

        patch_inbound = {
            "content": "Opt out"
        }
        response = self.client.patch('/api/v1/messages/inbound/%s/' %
                                     existing,
                                     json.dumps(patch_inbound),
                                     content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        d = Inbound.objects.get(pk=existing)
        self.assertEqual(d.to_addr, "+27123")
        self.assertEqual(d.from_addr, "020")
        self.assertEqual(d.content, "Opt out")
        self.assertEqual(d.transport_name, "test_voice")
        self.assertEqual(d.transport_type, "voice")
        self.assertEqual(d.helper_metadata, {})

    def test_delete_inbound_data(self):
        existing_outbound = self.make_outbound()
        out = Outbound.objects.get(pk=existing_outbound)
        existing = self.make_inbound(out.vumi_message_id)
        response = self.client.delete('/api/v1/messages/inbound/%s/' %
                                      existing,
                                      content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        d = Inbound.objects.filter(id=existing).count()
        self.assertEqual(d, 0)

    @responses.activate
    def test_event_ack(self):
        existing = self.make_outbound()

        # Setup response from scheduler
        responses.add(
            responses.DELETE,
            "http://127.0.0.1:8000/mama-ng-scheduler/rest/messages/1",
            json.dumps({}), status=200, content_type='application/json')

        d = Outbound.objects.get(pk=existing)
        ack = {
            "message_type": "event",
            "event_id": "b04ec322fc1c4819bc3f28e6e0c69de6",
            "event_type": "ack",
            "user_message_id": d.vumi_message_id,
            "helper_metadata": {},
            "timestamp": "2015-10-28 16:19:37.485612",
            "sent_message_id": "external-id"
        }
        response = self.client.post('/api/v1/messages/events',
                                    json.dumps(ack),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        d = Outbound.objects.get(pk=existing)
        self.assertEqual(d.delivered, True)
        self.assertEqual(d.attempts, 1)
        self.assertEqual(d.metadata["ack_timestamp"],
                         "2015-10-28 16:19:37.485612")
        self.assertEquals(False, self.check_logs(
            "Message: u'Simple outbound message' sent to u'+27123'"))
        s = Subscription.objects.get(pk=d.metadata["subscription"])
        self.assertEqual(s.metadata["scheduler_message_id"], "")

    def test_event_delivery_report(self):
        existing = self.make_outbound()
        d = Outbound.objects.get(pk=existing)
        dr = {
            "message_type": "event",
            "event_id": "b04ec322fc1c4819bc3f28e6e0c69de6",
            "event_type": "delivery_report",
            "user_message_id": d.vumi_message_id,
            "helper_metadata": {},
            "timestamp": "2015-10-28 16:20:37.485612",
            "sent_message_id": "external-id"
        }
        response = self.client.post('/api/v1/messages/events',
                                    json.dumps(dr),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        d = Outbound.objects.get(pk=existing)
        self.assertEqual(d.delivered, True)
        self.assertEqual(d.attempts, 1)
        self.assertEqual(d.metadata["delivery_timestamp"],
                         "2015-10-28 16:20:37.485612")
        self.assertEquals(False, self.check_logs(
            "Message: u'Simple outbound message' sent to u'+27123'"))

    def test_event_nack_first(self):
        existing = self.make_outbound()
        d = Outbound.objects.get(pk=existing)
        nack = {
            "message_type": "event",
            "event_id": "b04ec322fc1c4819bc3f28e6e0c69de6",
            "event_type": "nack",
            "nack_reason": "no answer",
            "user_message_id": d.vumi_message_id,
            "helper_metadata": {},
            "timestamp": "2015-10-28 16:20:37.485612",
            "sent_message_id": "external-id"
        }
        response = self.client.post('/api/v1/messages/events',
                                    json.dumps(nack),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        c = Outbound.objects.get(pk=existing)
        self.assertEqual(c.delivered, False)
        self.assertEqual(c.attempts, 2)
        self.assertEqual(c.metadata["nack_reason"],
                         "no answer")
        self.assertEquals(True, self.check_logs(
            "Message: u'Simple outbound message' sent to u'+27123' "
            "[session_event: new]"))
        # TODO: Bring metrics back
        # self.assertEquals(
        #     True,
        #     self.check_logs("Metric: 'vumimessage.tries' [sum] -> 1"))

    @responses.activate
    def test_event_nack_last(self):
        existing = self.make_outbound()

        # Setup response from scheduler
        responses.add(
            responses.DELETE,
            "http://127.0.0.1:8000/mama-ng-scheduler/rest/messages/1",
            json.dumps({}), status=200, content_type='application/json')

        d = Outbound.objects.get(pk=existing)
        d.attempts = 3  # fast forward as if last attempt
        d.save()
        nack = {
            "message_type": "event",
            "event_id": "b04ec322fc1c4819bc3f28e6e0c69de6",
            "event_type": "nack",
            "nack_reason": "no answer",
            "user_message_id": d.vumi_message_id,
            "helper_metadata": {},
            "timestamp": "2015-10-28 16:20:37.485612",
            "sent_message_id": "external-id"
        }
        response = self.client.post('/api/v1/messages/events',
                                    json.dumps(nack),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        d = Outbound.objects.get(pk=existing)
        self.assertEqual(d.delivered, False)
        self.assertEqual(d.attempts, 3)  # not moved on as last attempt passed
        self.assertEqual(d.metadata["nack_reason"],
                         "no answer")
        self.assertEquals(False, self.check_logs(
            "Message: u'Simple outbound message' sent to u'+27123'"
            "[session_event: new]"))
        # TODO: Bring metrics back
        # self.assertEquals(
        #     False,
        #     self.check_logs("Metric: 'vumimessage.tries' [sum] -> 1"))
        # self.assertEquals(
        #     True,
        #     self.check_logs("Metric: 'vumimessage.maxretries' [sum] -> 1"))
        s = Subscription.objects.get(pk=d.metadata["subscription"])
        self.assertEqual(s.metadata["scheduler_message_id"], "")

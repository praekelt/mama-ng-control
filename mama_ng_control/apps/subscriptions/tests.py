import json
import uuid
import logging
import responses

from django.test import TestCase
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models.signals import post_save

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token


from .models import Subscription, fire_sub_action_if_new
from mama_ng_control.apps.contacts.models import Contact
from mama_ng_control.apps.vumimessages.models import Outbound
from .tasks import Create_Message, schedule_create

# override Vumi sending handlers
from go_http.send import LoggingSender
from mama_ng_control.apps.vumimessages.tasks import Send_Message, Send_Metric
Send_Metric.vumi_client = lambda x: LoggingSender('go_http.test')
Send_Message.vumi_client = lambda x: LoggingSender('go_http.test')

# from requests import HTTPError
from requests.adapters import HTTPAdapter
from requests_testadapter import TestSession, Resp
from verified_fake.fake_contentstore import Request, FakeContentStoreApi

from client.messaging_contentstore.contentstore import ContentStoreApiClient


class RecordingHandler(logging.Handler):

    """ Record logs. """
    logs = None

    def emit(self, record):
        if self.logs is None:
            self.logs = []
        self.logs.append(record)


class FakeContentStoreApiAdapter(HTTPAdapter):

    """
    Adapter for FakeContentStoreApi

    This inherits directly from HTTPAdapter instead of using TestAdapter
    because it overrides everything TestAdaptor does.
    """

    def __init__(self, contentstore_api):
        self.contentstore_api = contentstore_api
        super(FakeContentStoreApiAdapter, self).__init__()

    def send(self, request, stream=False, timeout=None,
             verify=True, cert=None, proxies=None):
        req = Request(
            request.method, request.path_url, request.body, request.headers)
        resp = self.contentstore_api.handle_request(req)
        response = Resp(resp.body, resp.code, resp.headers)
        r = self.build_response(request, response)
        return r


make_messageset_dict = FakeContentStoreApi.make_messageset_dict
make_message_dict = FakeContentStoreApi.make_message_dict
make_schedule_dict = FakeContentStoreApi.make_schedule_dict


class APITestCase(TestCase):

    def make_cs_client(self):
        return ContentStoreApiClient(
            settings.CONTENTSTORE_AUTH_TOKEN,
            api_url=settings.CONTENTSTORE_API_URL,
            session=self.session)

    def make_fixtures(self):
        schedule = make_schedule_dict({
            "minute": "1",
            "hour": "2",
            "day_of_week": "3",
            "day_of_month": "4",
            "month_of_year": "5",
        })
        self.schedule_data[schedule[u"id"]] = schedule
        messageset = make_messageset_dict({
            u"short_name": u"Full Set",
            u"notes": u"A full set of messages.",
            u"default_schedule": schedule['id']
        })
        self.messageset_data[messageset[u"id"]] = messageset
        self.message1 = make_message_dict({
            "messageset": messageset['id'],
            "sequence_number": 1,
            "lang": "en_ZA",
            "text_content": "Message one",
            "binary_content": {
                "content": "http://foo.com/message1.mp3"
            }
        })
        self.message_data[self.message1[u'id']] = self.message1

    def setUp(self):
        self.client = APIClient()
        self.messageset_data = {}
        self.schedule_data = {}
        self.message_data = {}
        self.binary_content_data = {}
        self.make_fixtures()
        self.contentstore_backend = FakeContentStoreApi(
            "contentstore/", settings.CONTENTSTORE_AUTH_TOKEN,
            messageset_data=self.messageset_data,
            schedule_data=self.schedule_data, message_data=self.message_data,
            binary_content_data=self.binary_content_data)
        self.session = TestSession()
        adapter = FakeContentStoreApiAdapter(self.contentstore_backend)
        self.session.mount(settings.CONTENTSTORE_API_URL, adapter)
        # self.contentstore = self.make_cs_client()
        Create_Message.contentstore_client = lambda x: self.make_cs_client()
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
            if log.msg == msg:
                return True
        return False

    def _replace_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(Subscription)
        assert has_listeners(), (
            "Subscription model has no post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")
        post_save.disconnect(fire_sub_action_if_new, sender=Subscription)
        assert not has_listeners(), (
            "Subscription model still has post_save listeners. Make sure"
            " helpers cleaned up properly in earlier tests.")

    def _restore_post_save_hooks(self):
        has_listeners = lambda: post_save.has_listeners(Subscription)
        assert not has_listeners(), (
            "Subscription model still has post_save listeners. Make sure"
            " helpers removed them properly in earlier tests.")
        post_save.connect(fire_sub_action_if_new, sender=Subscription)


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


class TestSubscriptionsAPI(AuthenticatedAPITestCase):

    def setUp(self):
        super(TestSubscriptionsAPI, self).setUp()
        self._replace_post_save_hooks()  # don't let fixtures fire tasks

    def tearDown(self):
        super(TestSubscriptionsAPI, self).tearDown()
        self._restore_post_save_hooks()  # restore hooks

    def make_subscription(self):
        post_data = {
            "contact": "/api/v1/contacts/%s/" % self.contact,
            "messageset_id": "2",
            "next_sequence_number": "1",
            "lang": "en_ZA",
            "active": "true",
            "completed": "false",
            "schedule": "1",
            "process_status": "0",
            "metadata": {
                "source": "RapidProVoice"
            }
        }
        response = self.client.post('/api/v1/subscriptions/',
                                    json.dumps(post_data),
                                    content_type='application/json')
        return response.data["id"]

    def test_login(self):
        request = self.client.post(
            '/api-token-auth/',
            {"username": "testuser", "password": "testpass"})
        token = request.data.get('token', None)
        self.assertIsNotNone(
            token, "Could not receive authentication token on login post.")
        self.assertEqual(request.status_code, 200,
                         "Status code on /auth/token/ was %s (should be 200)."
                         % request.status_code)

    @responses.activate
    def test_create_subscription_data(self):

        schedule = {
            "class": "mama.ng.scheduler.Schedule",
            "id": "1",
            "cronDefinition": "1 2 3 4 5",
            "dateCreated": "2015-04-05T21:59:28Z",
            "endpoint": "http://examplecontrol.com/api/v1",
            "frequency": 10,
            "messages": None,
            "nextSend": "2015-04-05T22:00:00Z",
            "sendCounter": 0,
            "subscriptionId": "1234"
        }

        responses.add(
            responses.GET,
            "http://127.0.0.1:8000/mama-ng-scheduler/rest/schedules",
            json.dumps(schedule),
            status=200, content_type='application/json')

        post_subscription = {
            "contact": "/api/v1/contacts/%s/" % self.contact,
            "messageset_id": "1",
            "next_sequence_number": "1",
            "lang": "en_ZA",
            "active": "true",
            "completed": "false",
            "schedule": "1",
            "process_status": "0",
            "metadata": {
                "source": "RapidProVoice"
            }
        }
        response = self.client.post('/api/v1/subscriptions/',
                                    json.dumps(post_subscription),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Subscription.objects.last()
        self.assertIsNotNone(d.id)
        self.assertEqual(d.version, 1)
        self.assertEqual(d.messageset_id, 1)
        self.assertEqual(d.next_sequence_number, 1)
        self.assertEqual(d.lang, "en_ZA")
        self.assertEqual(d.active, True)
        self.assertEqual(d.completed, False)
        self.assertEqual(d.schedule, 1)
        self.assertEqual(d.process_status, 0)
        self.assertEqual(d.metadata["source"], "RapidProVoice")

    def test_update_subscription_data(self):
        existing = self.make_subscription()
        patch_subscription = {
            "next_sequence_number": "10",
            "active": "false",
            "completed": "true"
        }
        response = self.client.patch('/api/v1/subscriptions/%s/' % existing,
                                     json.dumps(patch_subscription),
                                     content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        d = Subscription.objects.get(pk=existing)
        self.assertEqual(d.active, False)
        self.assertEqual(d.completed, True)
        self.assertEqual(d.next_sequence_number, 10)
        self.assertEqual(d.lang, "en_ZA")

    def test_delete_subscription_data(self):
        existing = self.make_subscription()
        response = self.client.delete('/api/v1/subscriptions/%s/' % existing,
                                      content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        d = Subscription.objects.filter(id=existing).count()
        self.assertEqual(d, 0)

    def test_trigger_subscription_send(self):
        existing = self.make_subscription()
        post_trigger = {
            "send-counter": 2,
            "message-id": "4",
            "schedule-id": "3"
        }
        response = self.client.post('/api/v1/subscriptions/%s/send' % existing,
                                    json.dumps(post_trigger),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        o = Outbound.objects.last()
        self.assertIsNotNone(o.id)
        self.assertEqual(o.version, 1)
        self.assertEqual(str(o.contact.id), str(self.contact))
        self.assertEqual(o.content, "Message one")
        self.assertEqual(o.delivered, False)
        self.assertEqual(o.attempts, 1)
        self.assertEqual(o.metadata["subscription"], existing)
        s = Subscription.objects.last()
        self.assertEqual(s.metadata["scheduler_message_id"], "4")
        self.assertEqual(s.metadata["scheduler_schedule_id"], "3")

        s = Subscription.objects.get(id=existing)
        self.assertEqual(s.next_sequence_number, 2)

    def test_trigger_subscription_send_missing_subscription(self):
        post_trigger = {
            "send-counter": 2,
            "message-id": "4",
            "schedule-id": "3"
        }
        missing = str(uuid.uuid4())
        response = self.client.post('/api/v1/subscriptions/%s/send' % missing,
                                    json.dumps(post_trigger),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["accepted"], False)
        self.assertEqual(response.data["reason"],
                         "Missing subscription in control")

    def test_trigger_subscription_send_missing_keys(self):
        existing = self.make_subscription()
        post_trigger = {
            "send-counter": 2,
            "schedule-id": "3"
        }
        response = self.client.post('/api/v1/subscriptions/%s/send' % existing,
                                    json.dumps(post_trigger),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["accepted"], False)
        self.assertEqual(response.data["reason"],
                         "Missing expected body keys")

    @responses.activate
    def test_create_schedule_data(self):
        # create existing but surpress post save hook
        existing = self.make_subscription()
        # from the content store
        schedule_get = {
            "id": 1,
            "minute": "1",
            "hour": "6",
            "day_of_week": "1",
            "day_of_month": "*",
            "month_of_year": "*"
        }

        messageset = {
            "id": 2,
            "short_name": "pregnancy",
            "notes": "Base pregancy set",
            "next_set": None,
            "default_schedule": 1,
            "messages": [
                {"id": 1},
                {"id": 2}
            ]
        }

        responses.add(
            responses.GET,
            "http://127.0.0.1:8000/contentstore/schedule/1",
            json.dumps(schedule_get),
            status=200, content_type='application/json')

        responses.add(
            responses.GET,
            "http://127.0.0.1:8000/contentstore/messageset/2/messages",
            json.dumps(messageset),
            status=200, content_type='application/json')

        # to the scheduler
        schedule_post = {
            "class": "mama.ng.scheduler.Schedule",
            "id": "11",
            "cronDefinition": "1 6 1 * *",
            "dateCreated": "2015-04-05T21:59:28Z",
            "endpoint": "http://examplecontrol.com/api/v1/%s/send" % existing,
            "frequency": 10,
            "messages": None,
            "nextSend": "2015-04-05T22:00:00Z",
            "sendCounter": 0,
            "subscriptionId": existing
        }
        responses.add(responses.POST,
                      "http://127.0.0.1:8000/mama-ng-scheduler/rest/schedules",
                      json.dumps(schedule_post),
                      status=200, content_type='application/json')

        result = schedule_create.delay(existing)
        self.assertEqual(int(result.get()), 11)

        d = Subscription.objects.get(pk=existing)
        self.assertIsNotNone(d.id)
        self.assertEqual(d.metadata["scheduler_schedule_id"], "11")

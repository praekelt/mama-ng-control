import json
import uuid

from django.test import TestCase
from django.contrib.auth.models import User
from django.conf import settings

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token


from .models import Subscription
from mama_ng_control.apps.contacts.models import Contact
from mama_ng_control.apps.vumimessages.models import Outbound
from .tasks import Create_Message

# from requests import HTTPError
from requests.adapters import HTTPAdapter
from requests_testadapter import TestSession, Resp
from verified_fake.fake_contentstore import Request, FakeContentStoreApi

from client.messaging_contentstore.contentstore import ContentStoreApiClient


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
        contact = Contact.objects.create(details={"to_addr": "+27123"})
        self.contact = contact.id


class TestSubscriptionsAPI(AuthenticatedAPITestCase):

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

    def test_create_subscription_data(self):
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

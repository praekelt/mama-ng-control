import json

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token


from .models import Contact


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


class TestContactsAPI(AuthenticatedAPITestCase):

    def make_contact(self):
        post_data = {
            "details": {
                "name": "Test Name"
            }
        }
        response = self.client.post('/api/v1/contacts/',
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

    def test_create_contact_data(self):
        post_contact = {
            "details": {
                "name": "Test Name"
            }
        }
        response = self.client.post('/api/v1/contacts/',
                                    json.dumps(post_contact),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Contact.objects.last()
        self.assertEqual(d.details["name"], "Test Name")
        self.assertEqual(d.version, 1)

    def test_update_contact_data(self):
        existing = self.make_contact()
        put_contact = {
            "details": {
                "name": "Test Changed"
            }
        }
        response = self.client.put('/api/v1/contacts/%s/' % existing,
                                   json.dumps(put_contact),
                                   content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        d = Contact.objects.get(pk=existing)
        self.assertEqual(d.details["name"], "Test Changed")

    def test_delete_contact_data(self):
        existing = self.make_contact()
        response = self.client.delete('/api/v1/contacts/%s/' % existing,
                                      content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        d = Contact.objects.filter(id=existing).count()
        self.assertEqual(d, 0)

    def test_create_contact_data_v1_format_address_getting(self):
        """
        v1 expects at minimum:
        addresses: addr_type:addr_value pairs
            (e.g. "msisdn:+27001 msisdn:+27002 email:foo@bar.com")
        default_addr_type: which addr_type to default to if not given
        which is used with address function for smart lookups
        """
        post_contact = {
            "details": {
                "name": "Test Name",
                "default_addr_type": "msisdn",
                "addresses": "msisdn:+27123 email:foo@bar.com"
            }
        }
        response = self.client.post('/api/v1/contacts/',
                                    json.dumps(post_contact),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Contact.objects.last()
        self.assertEqual(d.details["name"], "Test Name")
        self.assertEqual(d.version, 1)
        self.assertEqual(d.address(), ["+27123"])
        self.assertEqual(d.address("email"), ["foo@bar.com"])

    def test_create_contact_data_v1_format_no_default_address_getting(self):
        """
        v1 expects at minimum:
        addresses: addr_type:addr_value pairs
            (e.g. "msisdn:+27001 msisdn:+27002 email:foo@bar.com")
        default_addr_type: which addr_type to default to if not given
        which is used with address function for smart lookups
        """
        post_contact = {
            "details": {
                "name": "Test Name",
                "addresses": "msisdn:+27123"
            }
        }
        response = self.client.post('/api/v1/contacts/',
                                    json.dumps(post_contact),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Contact.objects.last()
        self.assertEqual(d.details["name"], "Test Name")
        self.assertEqual(d.version, 1)
        self.assertEqual(d.address(), ["+27123"])

    def test_create_contact_data_v1_format_no_address_getting(self):
        """
        v1 expects at minimum:
        addresses: addr_type:addr_value pairs
            (e.g. "msisdn:+27001 msisdn:+27002 email:foo@bar.com")
        default_addr_type: which addr_type to default to if not given
        which is used with address function for smart lookups
        """
        post_contact = {
            "details": {
                "name": "Test Name",
            }
        }
        response = self.client.post('/api/v1/contacts/',
                                    json.dumps(post_contact),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        d = Contact.objects.last()
        self.assertEqual(d.details["name"], "Test Name")
        self.assertEqual(d.version, 1)
        self.assertEqual(d.address(), [])

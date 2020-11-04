import jwt
import logging

from django.test import TestCase, Client
from rest_framework import status


logger = logging.getLogger(__name__)


class TestAuthenticator(TestCase):
    def setUp(self):
        self.client = Client()

        raw_token = jwt.encode({
                'userId': 1,
                'email': 'email@example.com'
            },
            'secret'
        )
        self.token = f"Bearer {raw_token.decode('utf-8')}"

    def tearDown(self):
        pass

    def test_token_must_be_provided(self):
        res = self.client.get('/workspace/')

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res.content, b'"No authorization header found"')

    def test_token_must_be_valid(self):
        headers = {
            'HTTP_AUTHORIZATION': 'not_valid_token'
        }
        res = self.client.get('/workspace/', **headers)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.content, b'"Unable to decode authentication header"')

    def test_should_call_view_method(self):
        # Mock the view to assert that it's called
        headers = {
            'HTTP_AUTHORIZATION': self.token
        }
        res = self.client.get('/workspace/', **headers)

        # Assert view has been called (workspace/ will return 200 and empty array)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

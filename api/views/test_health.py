from unittest import mock
from django.test import TestCase, Client
from rest_framework import status

from api.views.health import Health


error_mock = mock.Mock()
error_mock.side_effect = Exception('Database failed')


class TestHealth(TestCase):
    def setUp(self):
        self.client = Client()

    def tearDown(self):
        pass

    def test_ping_should_always_200(self):
        res = self.client.get('/ping')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_health_should_200_if_db_reachable(self):
        res = self.client.get('/health')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    @mock.patch.object(Health, 'get_object', error_mock)
    def test_health_should_500_if_db_not_reachable(self):
        res = self.client.get('/health')
        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

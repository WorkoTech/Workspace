import logging
logger = logging.getLogger(__name__)
import jwt
import json
from unittest import mock

from rest_framework import status
from django.test import TestCase, Client

from api.views import (
    InvitationList,
    InvitationDetail
)
from api.models import (
    Workspace,
    Invitation,
    InvitationStatus,
    User
)
from api.externals.iam import ExternalUsers, ExternalWorkspacePermission
from api.externals.sendgrid import ExternalMail
from api.externals.notifier import ExternalNotify


class TestInvitationList(TestCase):
    def setUp(self):
        self.client = Client()

        # Authorization
        raw_token = jwt.encode({
                'userId': 1,
                'email': 'email@example.com'
            },
            'secret'
        )
        self.headers = {
            'HTTP_AUTHORIZATION': f"Bearer {raw_token.decode('utf-8')}"
        }

        # Fixtures : 2 invitations sent to user 1 on two different workspaces
        self.workspaces = [
            Workspace.objects.create(name='Workspace'),
            Workspace.objects.create(name='Workspace 2'),
        ]
        self.invitations = [
            Invitation.objects.create(workspace=self.workspaces[0], sender="email@example.com", user_id=1),
            Invitation.objects.create(workspace=self.workspaces[1], sender="email@example.com", user_id=1, status=InvitationStatus.ACCEPTED.name)
        ]

    def tearDown(self):
        Workspace.objects.all().hard_delete()

    def test_list_all(self):
        # Send request
        res = self.client.get('/invitation/', **self.headers)

        # Assert status code
        self.assertEqual(res.status_code, 200)

        # Assert that it well returns 2 invitations with their workspaces
        self.assertEqual(len(res.json()), 2)
        self.assertEqual(res.json()[0].get('id'), self.invitations[0].id)
        self.assertEqual(res.json()[0].get('status'), self.invitations[0].status)
        self.assertEqual(res.json()[0].get('workspace').get('id'), self.workspaces[0].id)
        self.assertEqual(res.json()[1].get('id'), self.invitations[1].id)
        self.assertEqual(res.json()[1].get('status'), self.invitations[1].status)
        self.assertEqual(res.json()[1].get('workspace').get('id'), self.workspaces[1].id)

    def test_list_by_status(self):
        # Send request
        res = self.client.get('/invitation/status/PENDING', **self.headers)

        # Assert status code
        self.assertEqual(res.status_code, 200)

        # Assert that it well returns 2 invitations with their workspaces
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0].get('id'), self.invitations[0].id)
        self.assertEqual(res.json()[0].get('status'), self.invitations[0].status)
        self.assertEqual(res.json()[0].get('workspace').get('id'), self.workspaces[0].id)

    @mock.patch.object(ExternalUsers, 'get_by_email', return_value=User(3, 'invited@example.com'))
    def test_create(self, mock_users):
        res = self.client.post(
            '/invitation/',
            {
                'email': 'invited@example.com',
                'workspace': Workspace.objects.first().id
            },
            **self.headers
        )

        # Assert HTTP status
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Assert invitation details
        self.assertEqual(res.json().get('id'), Invitation.objects.last().id) # 3 because of the two invitation we create in setUp
        self.assertEqual(res.json().get('status'), 'PENDING') # Must always be PENDING
        self.assertEqual(res.json().get('user_id'), 3) # user id from IAM mock
        self.assertEqual(res.json().get('workspace'), Workspace.objects.first().id) # workspace from request
        self.assertEqual(res.json().get('sender'), 'email@example.com') # from token defined in setUp

    @mock.patch.object(ExternalUsers, 'get_by_email', return_value=User(1, 'invited@example.com'))
    def test_create_user_invite_himself(self, mock_user):
        res = self.client.post(
            '/invitation/',
            {
                'email': 'invited@example.com',
                'workspace': Workspace.objects.first().id
            },
            **self.headers
        )

        # Assert HTTP status
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.content, b'"You can\'t invite yourself"')

    def test_create_user_invite_not_known_user(self):
        res = self.client.post(
            '/invitation/',
            {
                'email': 'invited@example.com',
                'workspace': Workspace.objects.first().id
            },
            **self.headers
        )

        # Assert HTTP status
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.content, b'"Unable to retrieve invited user (invited@example.com)"')

    @mock.patch.object(ExternalUsers, 'get_by_email', return_value=User(3, 'invited@example.com'))
    @mock.patch.object(ExternalMail, 'send')
    def test_create_notify_invited_user_by_mail(self, mock_email, mock_users):
        self.client.post(
            '/invitation/',
            {
                'email': 'invited@example.com',
                'workspace': Workspace.objects.first().id
            },
            **self.headers
        )
        mock_email.assert_called();

    @mock.patch.object(ExternalUsers, 'get_by_email', return_value=User(3, 'invited@example.com'))
    @mock.patch.object(ExternalNotify, 'send')
    def test_create_notify_invited_user_by_notification(self, mock_notify, mock_users):
        self.client.post(
            '/invitation/',
            {
                'email': 'invited@example.com',
                'workspace': Workspace.objects.first().id
            },
            **self.headers
        )
        mock_notify.assert_called();


class TestInvitationDetail(TestCase):
    def setUp(self):
        self.client = Client()

        # Authorization
        raw_token = jwt.encode({
                'userId': 1,
                'email': 'email@example.com'
            },
            'secret'
        )
        self.headers = {
            'HTTP_AUTHORIZATION': f"Bearer {raw_token.decode('utf-8')}"
        }

        self.workspace = Workspace.objects.create(name='Workspace')
        self.invitation = Invitation.objects.create(workspace=self.workspace, sender="email@example.com", user_id=1)
        self.unauth_invitation = Invitation.objects.create(workspace=self.workspace, sender="email@example.com", user_id=2)

    def tearDown(self):
        Workspace.objects.all().hard_delete()

    def test_retrieve_detail(self):
        res = self.client.get(
            f'/invitation/{self.invitation.id}/',
            **self.headers
        )

        # Assert status code
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Assert invitation details
        self.assertEqual(res.json().get('id'), self.invitation.id) # 3 because of the two invitation we create in setUp
        self.assertEqual(res.json().get('status'), 'PENDING') # Must always be PENDING
        self.assertEqual(res.json().get('user_id'), 1) # user id from IAM mock
        self.assertEqual(res.json().get('workspace').get('id'), self.workspace.id) # workspace from request
        self.assertEqual(res.json().get('sender'), 'email@example.com') # from token defined in setUp

    def test_retrieve_detail_unauthorized(self):
        res = self.client.get(
            f'/invitation/{self.unauth_invitation.id}/',
            **self.headers
        )

        # Assert status code
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.content, b'"Permission denied"')

    def test_retrieve_not_found(self):
        res = self.client.get(
            '/invitation/12345678/',
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch.object(ExternalWorkspacePermission, 'set', return_value=True)
    def test_update_success(self, mock):
        res = self.client.put(
            f'/invitation/{self.invitation.id}/',
            { 'status': 'ACCEPTED' },
            content_type="application/json",
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json(), { 'status': 'ACCEPTED' })

    def test_user_not_invited_update(self):
        res = self.client.put(
            f'/invitation/{self.unauth_invitation.id}/',
            { 'status': 'ACCEPTED' },
            **self.headers
        )

        # Assert status code
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.content, b'"Permission denied"')

    def test_update_not_pending(self):
        workspace = Workspace.objects.create(name="test_update_not_pending")
        invitation = Invitation.objects.create(
            workspace=workspace,
            sender="email@example.com",
            user_id=1,
            status=InvitationStatus.ACCEPTED.name
        )

        res = self.client.put(
            f'/invitation/{invitation.id}/',
            { 'status': 'DELETED' },
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.content, b'"Can\'t update a Invitation that is not pending"')

    def test_update_to_pending(self):
        res = self.client.put(
            f'/invitation/{self.invitation.id}/',
            { 'status': 'PENDING' },
            content_type="application/json",
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.content, b'"Unable to set invitation status to PENDING"')

    @mock.patch.object(ExternalWorkspacePermission, 'set', return_value=False)
    def test_update_accepted_workspace_permissions_fail(self, mock):
        res = self.client.put(
            f'/invitation/{self.invitation.id}/',
            { 'status': 'ACCEPTED' },
            content_type="application/json",
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(res.content, b'"Unable to set user workspace permissions"')

    def test_update_malformed_request(self):
        res = self.client.put(
            f'/invitation/{self.invitation.id}/',
            { 'status': 'NOT_VALID_STATUS' },
            content_type="application/json",
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(json.dumps(res.json()), json.dumps({
            'status': ['"NOT_VALID_STATUS" is not a valid choice.']
        }))

    def test_delete_success(self):
        res = self.client.delete(
            f'/invitation/{self.invitation.id}/',
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_unauthorized(self):
        res = self.client.delete(
            f'/invitation/{self.unauth_invitation.id}/',
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.content, b'"Permission denied"')

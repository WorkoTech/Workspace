import logging
logger = logging.getLogger(__name__)
from unittest import mock
import jwt
from django.test import TestCase, Client
from rest_framework import status

from api.views.workspace import (
    WorkspaceList,
    WorkspaceDetail
)
from api.models import (
    Workspace,
    User,
    WorkspacePermission,
    Invitation,
    InvitationStatus
)
from api.externals.iam import (
    ExternalWorkspacePermission,
    ExternalUsers
)
from api.externals.notifier.notify import ExternalNotify


class TestWorkspaceList(TestCase):
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

        # Fixtures
        self.workspace = Workspace.objects.create(name="Workspace", users=[1])

    def tearDown(self):
        Workspace.objects.all().hard_delete()

    @mock.patch.object(ExternalUsers, 'get_by_ids', return_value=[
        User(1, 'email@example.com')
    ])
    def test_list_success(self, mock):
        res = self.client.get('/workspace/', **self.headers)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0].get('id'), self.workspace.id)
        self.assertEqual(res.json()[0].get('name'), self.workspace.name)

    @mock.patch.object(ExternalWorkspacePermission, 'set', return_value=True)
    def test_create_success(self, mock):
        res = self.client.post(
            '/workspace/',
            { 'name': 'test_create_success' },
            content_type='application/json',
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.json().get('id'), Workspace.objects.last().id)
        self.assertEqual(res.json().get('name'), 'test_create_success')
        self.assertEqual(res.json().get('users'), [1])

    @mock.patch.object(ExternalWorkspacePermission, 'set', return_value=False)
    def test_create_unable_to_set_permission(self, mock):
        res = self.client.post(
            '/workspace/',
            { 'name': 'test_create_unable_to_set_permission' },
            content_type='application/json',
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(res.content, b'"Unable to set workspace permission"')

    def test_create_malformed(self):
        res = self.client.post(
            '/workspace/',
            { 'field_not_required': 'fail' },
            content_type='application/json',
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json(), {'name': ['This field is required.']})


class TestWorkspaceDetail(TestCase):
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

        # Fixtures
        self.workspace = Workspace.objects.create(name="Workspace", users=[1])

    def tearDown(self):
        Workspace.objects.all().hard_delete()

    @mock.patch.object(ExternalUsers, 'get_by_ids', return_value=[
        User(1, 'email@example.com')
    ])
    @mock.patch.object(
        ExternalWorkspacePermission,
        'get',
        return_value=WorkspacePermission.USER
    )
    def test_retrieve_success(self, mock_get_by_id, mock_get):
        res = self.client.get(f'/workspace/{self.workspace.id}/', **self.headers)

        # Assert status code
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Assert workspace details
        self.assertEqual(res.json().get('id'), self.workspace.id)
        self.assertEqual(res.json().get('name'), self.workspace.name)
        # Assert workspace users details
        self.assertEqual(len(res.json().get('users')), 1)
        user = res.json().get('users')[0]
        self.assertEqual(user.get('id'), 1)
        self.assertEqual(user.get('email'), 'email@example.com')

    @mock.patch.object(
        ExternalWorkspacePermission,
        'get',
        return_value=WorkspacePermission.NONE
    )
    def test_retrieve_unauthorized(self, mock):
        res = self.client.get(f'/workspace/{self.workspace.id}/', **self.headers)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.content, b'"Permission denied"')

    @mock.patch.object(ExternalWorkspacePermission, 'get', return_value=None)
    def test_retrieve_unable_to_get_workspace_permission(self, mock):
        res = self.client.get(f'/workspace/{self.workspace.id}/', **self.headers)

        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(res.content, b'"Unable to retrieve workspace permission"')

    @mock.patch.object(ExternalWorkspacePermission, 'get', return_value=WorkspacePermission.USER)
    def test_retrieve_not_found(self, mock):
        res = self.client.get(
            '/workspace/12345678/',
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_success(self):
        pass

    @mock.patch.object(
        ExternalWorkspacePermission,
        'get',
        return_value=WorkspacePermission.USER
    )
    def test_update_not_creator(self, mock):
        res = self.client.put(
            f'/workspace/{self.workspace.id}/',
            { 'name': 'test_update_not_creator' },
            content_type='application/json',
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.content, b'"You are not allowed to update this workspace"')

    @mock.patch.object(ExternalUsers, 'get_by_ids', return_value=[
        User(1, 'email@example.com')
    ])
    @mock.patch.object(
        ExternalWorkspacePermission,
        'get',
        return_value=WorkspacePermission.CREATOR
    )
    def test_update_delete_invitation_on_user_remove(self, mock_get_by_id, mock_get):
        # User has invite user 2 to self.workspace
        Invitation.objects.create(workspace=self.workspace, sender="email@example.com", user_id=2, status=InvitationStatus.ACCEPTED.name)
        # User 2 is in workspace
        self.workspace.users.append(2)
        self.workspace.save()

        # Update workspace to remove user 2
        res = self.client.put(
            f'/workspace/{self.workspace.id}/',
            { 'name': 'test', 'users': [1] },
            content_type='application/json',
            **self.headers
        )

        # Assert status code
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Assert workspace details
        self.assertEqual(res.json().get('id'), self.workspace.id)
        self.assertEqual(len(res.json().get('users')), 1)
        # Assert users
        user = res.json().get('users')[0]
        self.assertEqual(user.get('id'), 1)
        self.assertEqual(user.get('email'), 'email@example.com')
        # Assert invitation has been removed
        self.assertEqual(len(Invitation.objects.all()), 0)

    @mock.patch.object(ExternalUsers, 'get_by_ids', return_value=[
        User(1, 'email@example.com')
    ])
    @mock.patch.object(
        ExternalWorkspacePermission,
        'get',
        return_value=WorkspacePermission.CREATOR
    )
    @mock.patch.object(ExternalNotify, 'send')
    def test_update_send_notification(self, mock_notify, mock_get, mock_get_by_ids):
        res = self.client.put(
            f'/workspace/{self.workspace.id}/',
            { 'name': 'test_update_send_notification' },
            content_type='application/json',
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        mock_notify.assert_called_with(
            f'workspace {self.workspace.id}',
            'workspace updated',
            { 'name': 'test_update_send_notification' }
        )

    @mock.patch.object(
        ExternalWorkspacePermission,
        'get',
        return_value=WorkspacePermission.CREATOR
    )
    def test_update_malformed(self, mock):
        res = self.client.put(
            f'/workspace/{self.workspace.id}/',
            { 'not_a_field_name': 'test_update_send_notification' },
            content_type='application/json',
            **self.headers
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json(),  {"name":["This field is required."]})

    @mock.patch.object(
        ExternalWorkspacePermission,
        'get',
        return_value=WorkspacePermission.CREATOR
    )
    def test_delete_success(self, mock):
        res = self.client.delete(f'/workspace/{self.workspace.id}/', **self.headers)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(Workspace.objects.all()), 0)

    @mock.patch.object(
        ExternalWorkspacePermission,
        'get',
        return_value=None
    )
    def test_delete_error_retrieve_permission(self, mock):
        res = self.client.delete(f'/workspace/{self.workspace.id}/', **self.headers)

        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(res.content, b'"Unable to retrieve user workspace permissions"')

    @mock.patch.object(
        ExternalWorkspacePermission,
        'get',
        return_value=WorkspacePermission.NONE
    )
    def test_delete_no_permission(self, mock):
        res = self.client.delete(f'/workspace/{self.workspace.id}/', **self.headers)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.content, b'"Permission denied"')

    @mock.patch.object(
        ExternalWorkspacePermission,
        'get',
        return_value=WorkspacePermission.CREATOR
    )
    @mock.patch.object(ExternalNotify, 'send')
    def test_delete_send_notification(self, mock_notify, mock_get):
        res = self.client.delete(f'/workspace/{self.workspace.id}/', **self.headers)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        mock_notify.assert_called_with(f'workspace {self.workspace.id}', 'workspace deleted')

    @mock.patch.object(
        ExternalWorkspacePermission,
        'get',
        return_value=WorkspacePermission.USER
    )
    def test_delete_user_permission(self, mock):
        res = self.client.delete(f'/workspace/{self.workspace.id}/', **self.headers)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Workspace.objects.first().users, [])



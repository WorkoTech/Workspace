import logging
logger = logging.getLogger(__name__)

from django.http import Http404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.externals.iam import (
    ExternalWorkspacePermission,
    ExternalUsers
)
from api.externals.notifier import ExternalNotify
from api.externals.gamification import ExternalGamification
from api.externals.billing import ExternalBilling
from api.serializers import (
    UserFilledWorkspaceSerializer,
    WorkspaceSerializer,
    EditableWorkspaceSerializer,
)
from api.authenticator import authenticate
from api.models import (
    Workspace,
    Invitation,
    WorkspacePermission
)


class WorkspaceList(APIView):
    """
    List all workspace, or create a new workspace.
    """
    @authenticate
    def get(self, request, format=None, user=None, token=None):
        """
        List every users workspace with users informations filled
        """
        workspaces = Workspace.objects.filter(users__contains=[user.id])
        workspaces = ExternalUsers.fill_workspaces_users(workspaces)

        logger.debug(f"User workspaces : {workspaces}")
        serializer = UserFilledWorkspaceSerializer(workspaces, many=True)
        return Response(serializer.data)

    @authenticate
    def post(self, request, format=None, user=None, token=None):
        """
        Create a workspace and set user as CREATOR
        """
        logger.info("Creating workspace..")
        request.data['users'] = [user.id]

        serializer = WorkspaceSerializer(data=request.data)
        if serializer.is_valid():
            logger.info("Workspace is valid")

            serializer.save()
            workspace_id = serializer.data['id']

            try:
                ExternalBilling.send(token, ExternalBilling.BILLING_WORKSPACE_CREATED_EVENT, workspace_id)
            except Exception as e:
                logger.error("Error while sending billing event", e)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                ExternalGamification.send(token, True)
            except Exception as e:
                logger.error("Error while sending gamification event", e)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            perm_set_sucess = ExternalWorkspacePermission.set(
                token,
                workspace_id,
                WorkspacePermission.CREATOR
            )
            if not perm_set_sucess:
                logger.info("Error while setting workspace permissions")
                w = Workspace.objects.get(pk=workspace_id).hard_delete()

                return Response(
                    "Unable to set workspace permission",
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            logger.info(f"Workspace ({serializer.data}) successfully created")
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        logger.info("here")
        logger.error(f"Error while creating workspace : {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkspaceDetail(APIView):
    """
    Retrieve, update or delete a workspace instance.
    """
    def get_object(self, pk):
        try:
            return Workspace.objects.get(pk=pk)
        except Workspace.DoesNotExist:
            raise Http404

    @authenticate
    def get(self, request, pk, format=None, user=None, token=None):
        """
        Retrieve a specific workspace with users information filled
        """
        permission = ExternalWorkspacePermission.get(token, pk)
        if permission == None:
            return Response("Unable to retrieve workspace permission", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if permission == WorkspacePermission.NONE:
            return Response("Permission denied", status=status.HTTP_403_FORBIDDEN)

        workspace = self.get_object(pk)
        workspace = ExternalUsers.fill_workspace_users(workspace)

        serializer = UserFilledWorkspaceSerializer(workspace)
        return Response(serializer.data)

    @authenticate
    def put(self, request, pk, format=None, user=None, token=None):
        """
        Update workspace
        """
        permission = ExternalWorkspacePermission.get(token, pk)
        if not permission == WorkspacePermission.CREATOR:
            logger.error("Unable to update workspace, permission denied")
            return Response(
                "You are not allowed to update this workspace",
                status=status.HTTP_403_FORBIDDEN
            )

        workspace = self.get_object(pk)
        old_workspace_users = workspace.users.copy() # Used to know if user has been deleted

        serializer = EditableWorkspaceSerializer(workspace, data=request.data)
        if serializer.is_valid():
            serializer.save()

            # Allow users to be invited after been removed
            if "users" in request.data:
                deleted_user_ids = set(old_workspace_users) - set(workspace.users)
                if len(deleted_user_ids) > 0:
                    for deleted_user_id in deleted_user_ids:
                        Invitation.objects.filter(workspace=workspace, user_id=deleted_user_id).delete()

            # Send notification
            ExternalNotify.send(
                f'workspace {pk}',
                'workspace updated',
                serializer.validated_data
            )

            workspace = ExternalUsers.fill_workspace_users(workspace)
            response_serializer = UserFilledWorkspaceSerializer(workspace)
            logger.debug(f"Workspace {pk} successfully updated")
            return Response(response_serializer.data)

        logger.debug(f"Workspace {pk} failed to be updated: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @authenticate
    def delete(self, request, pk, format=None, user=None, token=None):
        """
        Delete a workspace if the CREATOR calls this route
        Remove user from workspace if an USER calls this route
        """
        logger.info(f"Trying to delete workpace {pk}")

        permission = ExternalWorkspacePermission.get(token, pk)

        # An error occured while getting permissions
        if permission == None:
            logger.error(f"Unable to retrieve permission for user {user.id} on workspace {pk}")
            return Response(
                "Unable to retrieve user workspace permissions",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        # User has no permission on this workspace
        if permission == WorkspacePermission.NONE:
            logger.error(f"User {user.id} does not have any permissions on workspace {pk}")
            return Response(
                "Permission denied",
                status=status.HTTP_403_FORBIDDEN
            )

        # Creator permission, will delete the whole workspace
        workspace = self.get_object(pk)
        if permission == WorkspacePermission.CREATOR:
            logger.info("Deleting workspace {pk}")
            workspace.delete()

            # Send notification
            ExternalNotify.send(f'workspace {pk}', 'workspace deleted')

            # Send billing event
            ExternalBilling.send(
                token,
                ExternalBilling.BILLING_WORKSPACE_DELETED_EVENT,
                pk
            )

            # Send gamification event
            ExternalGamification.send(token, False)

            return Response(status=status.HTTP_204_NO_CONTENT)

        # User permission, will remove user from workspace
        if permission == WorkspacePermission.USER:
            logger.info(f"Removing user {user.id} from workspace {pk}")
            workspace.users.remove(user.id)
            workspace.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

import logging
logger = logging.getLogger(__name__)

from django.http import Http404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.externals.iam import ExternalUsers, ExternalWorkspacePermission
from api.externals.sendgrid import ExternalMail
from api.externals.notifier import ExternalNotify
from api.authenticator import authenticate
from api.models import (
    Invitation,
    InvitationStatus,
    WorkspacePermission
)
from api.serializers import (
    FullInvitationSerializer,
    CreateInvitationSerializer,
    InvitationSerializer,
    UpdateInvitationStatusSerializer
)


class InvitationList(APIView):
    """
    List all invitations, or create a new one.
    """
    @authenticate
    def get(self, request, status=None, format=None, user=None, token=None):
        """
        Retrieve every users invitation. Can be filtered with status param
        """
        invitations = Invitation.objects.filter(user_id=user.id)
        if status != None:
            invitations = invitations.filter(status=status)

        serializer = FullInvitationSerializer(invitations, many=True)
        return Response(serializer.data)

    @authenticate
    def post(self, request, format=None, user=None, token=None):
        """
        Invite user to a workspace
        """
        logger.info("Creating invitation")
        # Validate Invitation request data
        serializer = CreateInvitationSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Unable to validate invitation request : {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve invited user from IAM
        invited_user = ExternalUsers.get_by_email(
            token,
            serializer.validated_data['email']
        )
        if not invited_user:
            logger.warning("Unable to retrieve invited user")
            return Response(f"Unable to retrieve invited user ({serializer.validated_data['email']})", status=status.HTTP_404_NOT_FOUND)

        # User cannot invite himself
        if user.id == invited_user.id:
            logger.warning(f"{user.id} sent an invitation to itself")
            return Response("You can't invite yourself", status=status.HTTP_400_BAD_REQUEST)

        # Save the invitation
        serializer = InvitationSerializer(data={
            'workspace': serializer.validated_data["workspace"].id,
            'sender': user.email,
            'user_id': invited_user.id,
            'status': InvitationStatus.PENDING.name
        })
        if not serializer.is_valid():
            logger.warning(f"Unable to save invitation : {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        invitation = serializer.save()

        # Send email to the invited user
        ExternalMail.send(
            to=invited_user.email,
            template_id="d-45db8f85eeaf43e9944db49a5777d9f7",
            template_data={ 'url': 'https://app.worko.tech/#workspace' }
        )

        # Build data that will be send
        result = InvitationSerializer(invitation).data

        # Notify user that it has been invited
        ExternalNotify.send(
            f"user {invited_user.id}",
            'invitation recieved',
            result
        )
        return Response(result, status=status.HTTP_201_CREATED)


class InvitationDetail(APIView):
    """
    Retrieve, update or delete a invitation instance.
    """
    def get_object(self, pk):
        try:
            return Invitation.objects.get(pk=pk)
        except Invitation.DoesNotExist:
            raise Http404

    @authenticate
    def get(self, request, pk, format=None, user=None, token=None):
        invitation = self.get_object(pk)
        if not invitation.user_id == user.id:
            return Response("Permission denied", status=status.HTTP_403_FORBIDDEN)

        serializer = FullInvitationSerializer(invitation)
        return Response(serializer.data)

    @authenticate
    def put(self, request, pk, format=None, user=None, token=None):
        logger.info(f"Updating invitation {pk}")
        invitation = self.get_object(pk)

        # Only invited user can update an Invitation
        if not invitation.user_id == user.id:
            logger.warning(f"Only invited user ({invitation.user_id}) can update invitation but {user.id} tried")
            return Response("Permission denied", status=status.HTTP_403_FORBIDDEN)

        # Can't update a Invitation that is not pending
        if not invitation.status == InvitationStatus.PENDING.name:
            logger.warning(f"Invitation {pk} can't be updated because not PENDING")
            return Response(
                "Can't update a Invitation that is not pending",
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UpdateInvitationStatusSerializer(
            invitation,
            data=request.data
        )
        if serializer.is_valid():
            # This route is only to accept or refuse a invitation not creating it
            if serializer.validated_data["status"] == InvitationStatus.PENDING.name:
                logger.warning("Unable to set invitation status to PENDING")
                return Response(
                    "Unable to set invitation status to PENDING",
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Set invited user permission on workspace
            if serializer.validated_data["status"] == InvitationStatus.ACCEPTED.name:
                logger.info("Invitation will be accepted, trying to set invited user workspace permissions")
                workspace = invitation.workspace

                perm_set_sucess = ExternalWorkspacePermission.set(
                    token,
                    workspace.id,
                    WorkspacePermission.USER
                )
                if not perm_set_sucess:
                    logger.error(f"Failed to set user ({user.id}) permissions on workspace ({workspace.id})")
                    return Response("Unable to set user workspace permissions", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                workspace.users.append(user.id)
                workspace.save()

                # Send notification to workspace to force refresh
                ExternalNotify.send(
                    f"workspace ${workspace.id}",
                    'need refresh'
                )

            serializer.save()
            logger.info(f"Invitation {pk} successfully updated")
            return Response(serializer.validated_data)
        logger.warning(f"Invitation {pk} unable to be updated: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @authenticate
    def delete(self, request, pk, format=None, user=None, token=None):
        logger.info(f"Deleting invitation {pk}")

        invitation = self.get_object(pk)
        if not invitation.user_id == user.id:
            logger.warning(f"Unable to delete invitation, user {user.id} is not the invited one ({invitation.user_id})")
            return Response("Permission denied", status=status.HTTP_403_FORBIDDEN)

        invitation.delete()
        logger.info(f"Invitation {pk} successfully deleted")
        return Response(status=status.HTTP_204_NO_CONTENT)


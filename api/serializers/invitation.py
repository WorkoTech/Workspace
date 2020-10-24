from rest_framework import serializers

from api.serializers import FkWorkspaceRelatedField
from api.models import Invitation, InvitationStatus


class FullInvitationSerializer(serializers.ModelSerializer):
    workspace = FkWorkspaceRelatedField(read_only=True)

    class Meta:
        model = Invitation
        fields = '__all__'


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = '__all__'


class CreateInvitationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()

    class Meta:
        model = Invitation
        fields = ['workspace', 'email']


class UpdateInvitationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ['status']

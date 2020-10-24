from rest_framework import serializers

from api.models import Workspace
from api.serializers.user import UserSerializer


class UserFilledWorkspaceSerializer(serializers.ModelSerializer):
    users = UserSerializer(many=True)

    class Meta:
        model = Workspace
        fields = '__all__'

class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = '__all__'


class EditableWorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ['name', 'users']


class FkWorkspaceRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        return WorkspaceSerializer(value).data

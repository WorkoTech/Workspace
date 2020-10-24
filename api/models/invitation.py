from enum import Enum

from django.db import models

from .abstract_model import AbstractModel
from .workspace import Workspace


class InvitationStatus(Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)


class Invitation(AbstractModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    sender = models.EmailField(max_length=255, null=False, blank=False)
    user_id = models.IntegerField(null=False, blank=False)

    status = models.CharField(
        max_length=255,
        choices=InvitationStatus.choices(),
        default=InvitationStatus.PENDING.name
    )

    class Meta:
        unique_together = ('user_id', 'workspace')

    def __repr__(self):
        return f'<Invitation workspace={self.workspace} userId={self.userId} status={self.status}>'

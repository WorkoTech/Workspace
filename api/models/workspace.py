from django.db import models
from django.contrib.postgres.fields import ArrayField

from .abstract_model import AbstractModel


class Workspace(AbstractModel):
    name = models.CharField(
        max_length=256,
        blank=False,
        null=False,
        unique=True
    )
    users = ArrayField(
        models.IntegerField(
            blank=False,
            null=False
        ),
        default=list
    )

    def __repr__(self):
        return f'<Workspace name={self.name}>'


from django.db import models
from django.utils import timezone


class AbstractModelQuerySet(models.QuerySet):
    """
    Prevents objects from being hard-deleted. Instead, sets the
    ``date_deleted``, effectively soft-deleting the object.
    """

    def delete(self):
        for obj in self:
            obj.delete()

    def hard_delete(self):
        for obj in self:
            obj.hard_delete()


class AbstractModelManager(models.Manager):
    """
    Only exposes objects that have NOT been soft-deleted.
    """

    def get_queryset(self):
        return AbstractModelQuerySet(self.model, using=self._db).filter(
            deleted_at__isnull=True)


class AbstractModel(models.Model):
    """
    Model on which any api.models should inherit.
    Add created_at, updated_at and soft_delete to any models
    """
    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = AbstractModelManager()
    raw_objects = models.Manager()

    def delete(self):
        self.deleted_at=timezone.now()
        self.save()

    def hard_delete(self):
        super().delete()

    def undelete(self):
        self.deleted_at=None
        self.save()

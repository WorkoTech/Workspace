import logging
logger = logging.getLogger(__name__)

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.models import Workspace


class Ping(APIView):
    """
    This route always return 200, used for kubernetes liviness
    """
    def get(self, request, format=None):
        return Response(status=status.HTTP_200_OK)


class Health(APIView):
    def get_object(self):
        return Workspace.objects.all()

    def get(self, request, format=None):
        """
        This route always return 200 if database is reachable, 500 otherwise
        Used for kubernetes readiness
        """
        try:
            list(self.get_object())
        except Exception as e:
            logger.error("Health failed, database access failed")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(status=status.HTTP_200_OK)

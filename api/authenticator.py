import jwt
import logging

from api.models import User

from rest_framework import status
from rest_framework.response import Response


logger = logging.getLogger(__name__)


def authenticate(func):
    def wrapper(*args, **kwargs):
        request = args[1]
        encoded_jwt = request.headers.get('Authorization')
        logger.info(f"Authorizing {encoded_jwt}")
        if not encoded_jwt:
            logger.info("No Authorization header found")
            return Response("No authorization header found", status=status.HTTP_401_UNAUTHORIZED)

        try:
            _, raw_jwt = encoded_jwt.split()  # Remove "Bearer"
            decoded = jwt.decode(raw_jwt, algorithms=['HS256'], verify=False)

            user = User(
                int(decoded['userId']),
                decoded['email']
            )
            token = encoded_jwt

        except Exception:
            logger.warning(f"Unable to decode authentication header {encoded_jwt}")
            return Response("Unable to decode authentication header", status=status.HTTP_403_FORBIDDEN)

        return func(*args, **kwargs, user=user, token=token)

    return wrapper

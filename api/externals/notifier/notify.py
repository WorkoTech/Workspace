import os
import logging
logger  = logging.getLogger(__name__)

from api.externals.http import Http
from api.externals.notifier.abstract import AbstractExternalNotifier


class ExternalNotify(AbstractExternalNotifier):
    __NOTIFIER_BASE_URL = f"http://{os.getenv('NOTIFIER_HOST', 'localhost')}:{os.getenv('NOTIFIER_PORT', 3000)}"

    @staticmethod
    def __get_notifier_url():
        return f"{ExternalNotify.__NOTIFIER_BASE_URL}/notify"

    @staticmethod
    def send(channel, event, data=None):
        body = { 'channel': channel, 'event': event, 'data': data }
        logger.info(f"Sending notification to {body}")

        try:
            response = Http.post(
                ExternalNotify.__get_notifier_url(),
                body=body
            )
        except Exception as e:
            logger.error(f"Unable to send notification ({body}), ({e})")
            return False

        if response.status_code == 201:
            logger.info(f"Notification ({body}) successfully sent")
            return True
        return False

import os
import logging
logger  = logging.getLogger(__name__)

from api.externals.http import Http


class ExternalGamification:
    __GAMIFICATION_BASE_URL = f"http://{os.getenv('GAMIFICATION_HOST', 'localhost')}:{os.getenv('GAMIFICATION_PORT', 3008)}"

    @staticmethod
    def __get_url(done):
        if done:
            return f"{ExternalGamification.__GAMIFICATION_BASE_URL}/action/done"
        return f"{ExternalGamification.__GAMIFICATION_BASE_URL}/action/undone"

    @staticmethod
    def send(token, done=True):
        try:
            logger.info("GAMIFICATION EVENT")
            response = Http.post(
                ExternalGamification.__get_url(done),
                token=token,
                body={
                    'actionTitle': 'Workspaces created'
                }
            )
            if response.status_code == 200:
                logger.info("Gamification event successfully sent.")
                return True

        except Exception as e:
            logger.error("Unable to send gamification event : %r", e)

        logger.error("An error occured while sending gamification event.")
        return False

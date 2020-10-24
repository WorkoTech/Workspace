import os
import logging
logger  = logging.getLogger(__name__)

from api.externals.billing.abstract import AbstractExternalBilling
from api.externals.http import Http


class ExternalBilling(AbstractExternalBilling):
    __BILLING_BASE_URL = f"http://{os.getenv('BILLING_HOST', 'localhost')}:{os.getenv('BILLING_PORT', 3008)}"
    BILLING_WORKSPACE_CREATED_EVENT = 'WORKSPACE_CREATED',
    BILLING_WORKSPACE_DELETED_EVENT = 'WORKSPACE_DELETED',

    @staticmethod
    def __get_billing_url():
        return f"{ExternalBilling.__BILLING_BASE_URL}/billing/event"

    @staticmethod
    def send(token, event, workspace_id):
        try:
            logger.info("BILLING EVENT : %r", event)
            response = Http.post(
                ExternalBilling.__get_billing_url(),
                token=token,
                body={
                    'type': event[0],
                    'workspaceId': workspace_id
                }
            )
            if response.status_code == 200:
                logger.info("Billing event successfully sent.")
                return True

        except Exception as e:
            logger.error("Unable to send billing event : %r", e)

        logger.error("An error occured while sending billing event.")
        return False

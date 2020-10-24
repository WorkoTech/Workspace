import os
import logging
logger = logging.getLogger(__name__)

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


class ExternalMail():

    @staticmethod
    def send(
        to=None,
        template_id=None,
        template_data=None
    ):
        logger.info(f"Sending mail to {to} ({template_id})")

        api_key = os.environ.get('SENDGRID_API_KEY')
        # Send email to the invited user
        if not api_key:
            logger.warning("SENDGRID_API_KEY not defined")
            return False

        message = Mail(
            from_email='contact@worko.tech',
            to_emails=to,
        )
        message.dynamic_template_data = template_data
        message.template_id = template_id
        try:
            sendgrid_client = SendGridAPIClient(api_key)
            response = sendgrid_client.send(message)
            logger.info("Mail successfully sent")
            return True
        except Exception as e:
            logger.info(f"Unable to send mail ({e})")
            return False

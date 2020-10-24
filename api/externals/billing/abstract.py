import os
from abc import ABC


class AbstractExternalBilling(ABC):
    __BILLING_BASE_URL = f"http://{os.getenv('BILLING_HOST', 'localhost')}:{os.getenv('BILLING_PORT', 3008)}"

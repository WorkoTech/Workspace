import os
from abc import ABC


class AbstractExternalIAM(ABC):
    IAM_BASE_URL = f"http://{os.getenv('IAM_HOST', 'localhost')}:{os.getenv('IAM_PORT', 3000)}"

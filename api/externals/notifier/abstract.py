import os
from abc import ABC


class AbstractExternalNotifier(ABC):
    __NOTIFIER_BASE_URL = f"http://{os.getenv('NOTIFIER_HOST', 'localhost')}:{os.getenv('NOTIFIER_PORT', 3000)}"

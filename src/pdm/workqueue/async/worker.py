import sys

import requests
from requests.exceptions import Timeout

from pdm.utils import Daemon
from pdm.utils.config import getConfig

class Worker(Daemon):
    def __init__(self):
        super(Worker, self).__init__(target=self.run)
        config = getConfig('workqueue')
        self._url = config.get('manager_url', 'http://localhost:45005')
        self._timeout = config.get('worker_timeout', 5)
        self._logger = logging.getLogger("Worker")

    def run(self):
        while True:
            try:
                r = requests.get(self._url, timeout=self._timeout)
            except Timeout:
                self._logger.debug("Timed out connecting to %s...retrying.", self._url)
                continue
            except Exception:
                logger.exception("Error getting job from %s." % self._url)
                break
            job = r.json()
            # do work

if __name__ == '__main__':
    Worker().start()

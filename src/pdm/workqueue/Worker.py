#!/usr/bin/env python
"""Worker script."""
import os
import time
import uuid
import random
# import json
# import shlex
import socket
import subprocess
from urlparse import urlsplit, urlunsplit
from tempfile import NamedTemporaryFile
from contextlib import contextmanager

from requests.exceptions import Timeout

from pdm.framework.RESTClient import RESTClient, RESTException
from pdm.cred.CredClient import CredClient
from pdm.endpoint.EndpointClient import EndpointClient
from pdm.utils.daemon import Daemon
from pdm.utils.config import getConfig

from .WorkqueueDB import COMMANDMAP, PROTOCOLMAP, JobType


@contextmanager
def TempX509Files(token):
    """Create temporary grid credential files."""
    cert, key = CredClient().get_cred(token)
    with NamedTemporaryFile() as proxyfile:
        proxyfile.write(key)
        proxyfile.write(cert)
        proxyfile.flush()
        os.fsync(proxyfile.fileno())
        yield proxyfile


class Worker(RESTClient, Daemon):
    """Worker Daemon."""

    def __init__(self, debug=False, one_shot=False):
        """Initialisation."""
        RESTClient.__init__(self, 'workqueue')
        conf = getConfig('worker')
        self._uid = uuid.uuid4()
        Daemon.__init__(self,
                        pidfile='/tmp/worker-%s.pid' % self._uid,
                        logfile='/tmp/worker-%s.log' % self._uid,
                        target=self.run,
                        debug=debug)
        self._one_shot = one_shot
        self._types = [JobType[type_.upper()] for type_ in  # pylint: disable=unsubscriptable-object
                       conf.pop('types', ('LIST', 'COPY', 'REMOVE'))]
        self._interpoll_sleep_time = conf.pop('poll_time', 2)
        self._script_path = conf.pop('script_path', None)
        if self._script_path:
            self._script_path = os.path.abspath(self._script_path)
        else:
            code_path = os.path.abspath(os.path.dirname(__file__))
            self._script_path = os.path.join(code_path, 'scripts')
        self._logger.info("Script search path is: %s", self._script_path)
        self._current_process = None
        # Check for unused config options
        if conf:
            keys = ', '.join(conf.keys())
            raise ValueError("Unused worker config params: '%s'" % keys)

    def terminate(self, *_):
        """Terminate worker daemon."""
        Daemon.terminate(self, *_)
        if self._current_process is not None:
            self._current_process.terminate()

    def _abort(self, job_id, message):
        """Abort job cycle."""
        self._logger.error("Error with job %d: %s", job_id, message)
        try:
            self.put('worker/%s' % job_id,
                     data={'log': message,
                           'returncode': 1,
                           'host': socket.gethostbyaddr(socket.getfqdn())})
        except RESTException:
            self._logger.exception("Error trying to PUT back abort message")

    def run(self):
        """Daemon main method."""
        endpoint_client = EndpointClient()
        run = True
        while run:
            if self._one_shot:
                run = False
            try:
                response = self.post('worker', data={'types': self._types})
            except Timeout:
                self._logger.warning("Timed out contacting the WorkqueueService.")
                continue
            except RESTException as err:
                if err.code == 404:
                    self._logger.debug("No work to pick up.")
                    time.sleep(self._interpoll_sleep_time)
                else:
                    self._logger.exception("Error trying to get job from WorkqueueService.")
                continue
            job, token = response
#            try:
#                job, token = json.loads(response.data())
#            except ValueError:
#                self._logger.exception("Error decoding JSON job.")
#                continue
            src_site = endpoint_client.get_site(job['src_siteid'])
            src_endpoints = [urlsplit(site) for site
                             in src_site['endpoints'].itervalues()]
            src = [urlunsplit(site._replace(path=job['src_filepath'])) for site in src_endpoints
                   if site.scheme == PROTOCOLMAP[job['protocol']]]
            if not src:
                self._abort(job['id'], "Protocol '%s' not supported at src site with id %d"
                            % (job['protocol'], job['src_siteid']))
                continue
            command = "%s %s" % (COMMANDMAP[job['type']][job['protocol']], random.choice(src))

            if job['type'] == JobType.COPY:
                if job['dst_siteid'] is None:
                    self._abort(job['id'], "No dst site id set for copy operation")
                    continue
                if job['dst_filepath'] is None:
                    self._abort(job['id'], "No dst site filepath set for copy operation")
                    continue

                dst_site = endpoint_client.get_site(job['dst_siteid'])
                dst_endpoints = [urlsplit(site) for site
                                 in dst_site['endpoints'].itervalues()]
                dst = [urlunsplit(site._replace(path=job['dst_filepath'])) for site in dst_endpoints
                       if site.scheme == PROTOCOLMAP[job['protocol']]]
                if not dst:
                    self._abort(job['id'], "Protocol '%s' not supported at dst site with id %d"
                                % (job['protocol'], job['dst_siteid']))
                    continue
                command += " %s" % random.choice(dst)

            with TempX509Files(job['credentials']) as proxyfile:
                self._current_process = subprocess.Popen('(set -x && %s)' % command,
                                                         shell=True,
                                                         stdout=subprocess.PIPE,
                                                         stderr=subprocess.STDOUT,
                                                         env=dict(os.environ,
                                                                  PATH=self._script_path,
                                                                  X509_USER_PROXY=proxyfile.name))
                log, _ = self._current_process.communicate()
                self.set_token(token)
                try:
                    self.put('worker/%s' % job['id'],
                             data={'log': log,
                                   'returncode': self._current_process.returncode,
                                   'host': socket.gethostbyaddr(socket.getfqdn())})
                except RESTException:
                    self._logger.exception("Error trying to PUT back output from subcommand.")
                finally:
                    self.set_token(None)


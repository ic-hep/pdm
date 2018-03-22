#!/usr/bin/env python
"""Worker script."""
import os
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

from pdm.framework.RESTClient import RESTClient
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
        self._uid = uuid.uuid4()
        Daemon.__init__(self,
                        pidfile='/tmp/worker-%s.pid' % self._uid,
                        logfile='/tmp/worker-%s.log' % self._uid,
                        target=self.run,
                        debug=debug)
        self._one_shot = one_shot
        self._types = [JobType[type_.upper()] for type_ in  # pylint: disable=unsubscriptable-object
                       getConfig('worker').get('types', ('LIST', 'COPY', 'REMOVE'))]
        self._current_process = None

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
        except RuntimeError:
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
                continue
            except RuntimeError:
                self._logger.exception("Error getting job from workqueue.")
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
                                                                  X509_USER_PROXY=proxyfile.name))
                log, _ = self._current_process.communicate()
                self.set_token(token)
                try:
                    self.put('worker/%s' % job['id'],
                             data={'log': log,
                                   'returncode': self._current_process.returncode,
                                   'host': socket.gethostbyaddr(socket.getfqdn())})
                except RuntimeError:
                    self._logger.exception("Error trying to PUT back output from subcommand.")
                finally:
                    self.set_token(None)


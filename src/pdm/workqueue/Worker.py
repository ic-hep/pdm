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

from requests.exceptions import Timeout

from pdm.framework.RESTClient import RESTClient, RESTException
from pdm.cred.CredClient import CredClient
from pdm.endpoint.EndpointClient import EndpointClient
from pdm.utils.daemon import Daemon
from pdm.utils.config import getConfig

from .WorkqueueDB import COMMANDMAP, PROTOCOLMAP, JobType


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
        self._script_path = conf.pop('script_path',
                                     os.path.join(os.path.dirname(__file__), 'scripts'))
        self._script_path = os.path.abspath(self._script_path)
        self._logger.info("Script search path is: %r", self._script_path)
        self._current_process = None

        # Check for unused config options
        if conf:
            raise ValueError("Unused worker config params: '%s'" % ', '.join(conf.keys()))

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
        finally:
            self.set_token(None)

    def run(self):
        """Daemon main method."""
        cred_client = CredClient()
        endpoint_client = EndpointClient()
        run = True
        while run:
            if self._one_shot:
                run = False
            self._logger.info("Getting job from WorkqueueService.")
            try:
                job, token = self.post('worker', data={'types': self._types})
            except Timeout:
                self._logger.warning("Timed out contacting the WorkqueueService.")
                continue
            except RESTException as err:
                if err.code == 404:
                    self._logger.info("WorkqueueService reports no jobs to be done.")
                else:
                    self._logger.exception("Error trying to get job from WorkqueueService.")
                time.sleep(self._interpoll_sleep_time)
                continue

            self._logger.info("%s job id=%d acquired from WorkqueueService.",
                              JobType(job['type']).name,  # pylint: disable=no-member
                              job['id'])
            self.set_token(token)

            src_site = endpoint_client.get_site(job['src_siteid'])
            src_endpoints = (urlsplit(site) for site
                             in src_site['endpoints'].itervalues())
            src = [urlunsplit(site._replace(path=job['src_filepath'])) for site in src_endpoints
                   if site.scheme == PROTOCOLMAP[job['protocol']]]
            if not src:
                self._abort(job['id'], "Protocol '%s' not supported at src site with id %d"
                            % (job['protocol'], job['src_siteid']))
                continue
            script_env = dict(os.environ,
                              PATH=self._script_path,
                              SRC_PATH=random.choice(src))
            self._logger.info("Random SRC_PATH: '%s' chosen.", script_env['SRC_PATH'])

            if job['type'] == JobType.COPY:
                if job['dst_siteid'] is None:
                    self._abort(job['id'], "No dst site id set for copy operation")
                    continue
                if job['dst_filepath'] is None:
                    self._abort(job['id'], "No dst site filepath set for copy operation")
                    continue

                dst_site = endpoint_client.get_site(job['dst_siteid'])
                dst_endpoints = (urlsplit(site) for site
                                 in dst_site['endpoints'].itervalues())
                dst = [urlunsplit(site._replace(path=job['dst_filepath'])) for site in dst_endpoints
                       if site.scheme == PROTOCOLMAP[job['protocol']]]
                if not dst:
                    self._abort(job['id'], "Protocol '%s' not supported at dst site with id %d"
                                % (job['protocol'], job['dst_siteid']))
                    continue
                script_env['DST_PATH'] = random.choice(dst)
                self._logger.info("Random DST_PATH: '%s' chosen.", script_env['DST_PATH'])

            self._logger.info("Getting user's credentials.")
            try:
                cert, key = cred_client.get_cred(job['credentials'])
            except RESTException:
                self._abort(job['id'], "Error getting user's credentials.")
                continue

            command = COMMANDMAP[job['type']][job['protocol']]
            with NamedTemporaryFile() as proxyfile:
                proxyfile.write(key)
                proxyfile.write(cert)
                proxyfile.flush()
                os.fsync(proxyfile.fileno())
                script_env['X509_USER_PROXY'] = proxyfile.name

                self._logger.info("Running job in subprocess.")
                self._current_process = subprocess.Popen('(set -x && %s)' % command,
                                                         shell=True,
                                                         stdout=subprocess.PIPE,
                                                         stderr=subprocess.STDOUT,
                                                         env=script_env)
                log, _ = self._current_process.communicate()

            self._logger.info("Job complete, uploading output log to WorkqueueService.")
            try:
                self.put('worker/%s' % job['id'],
                         data={'log': log,
                               'returncode': self._current_process.returncode,
                               'host': socket.gethostbyaddr(socket.getfqdn())})
            except RESTException:
                self._logger.exception("Error trying to PUT back output from subcommand.")
                continue
            finally:
                self.set_token(None)

            if job['attempts'] >= job['max_tries'] - 1:
                self._logger.info("Final attempt complete, deleting users credentials.")
                try:
                    cred_client.del_cred(job['credentials'])
                except RESTException:
                    self._logger.exception("Error trying to delete user credentials.")

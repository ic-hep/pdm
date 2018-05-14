#!/usr/bin/env python
"""Worker script."""
import os
import time
import uuid
import random
import json
import select
import shlex
import socket
import stat
import subprocess
from collections import deque
from urlparse import urlsplit, urlunsplit
from tempfile import NamedTemporaryFile

from requests.exceptions import Timeout

from pdm.framework.RESTClient import RESTClient, RESTException
from pdm.cred.CredClient import CredClient
from pdm.endpoint.EndpointClient import EndpointClient
from pdm.utils.daemon import Daemon
from pdm.utils.config import getConfig

from .WorkqueueDB import COMMANDMAP, PROTOCOLMAP, JobType, JobProtocol


def is_list_part(job):
    return len(job['elements']) == 1 and job['elements'][0]['type'] == JobType.LIST


def listing_parser(obj):
    files = []
    for root, items in json.loads(obj).iteritems():
        for name, stat_dict in items:
            if stat.S_ISREG(int(stat_dict["st_mode"])):
                files.append(os.path.join(root, name))

class Worker(RESTClient, Daemon):
    """Worker Daemon."""

    def __init__(self, debug=False, n_shot=None):
        """Initialisation."""
        RESTClient.__init__(self, 'workqueue')
        conf = getConfig('worker')
        self._uid = uuid.uuid4()
        Daemon.__init__(self,
                        pidfile='/tmp/worker-%s.pid' % self._uid,
                        logfile='/tmp/worker-%s.log' % self._uid,
                        target=self.run,
                        debug=debug)
        self._n_shot = n_shot
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

    @property
    def should_run(self):
        if self._n_shot is None:
            return True
        n_shot = max(self._n_shot, 0)
        self._n_shot -= 1
        return n_shot

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

    # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    def run(self):
        """Daemon main method."""
        # remove any proxy left around as will mess up copy jobs.
        try:
            os.remove("/tmp/x509up_u%d" % os.getuid())
        except OSError:
            pass

        while self.should_run:

            self._logger.info("Getting workload from WorkqueueService.")
            try:
                workload = self.post('worker/jobs', data={'types': self._types})
            except Timeout:
                self._logger.warning("Timed out contacting the WorkqueueService.")
                continue
            except RESTException as err:
                if err.code == 404:
                    self._logger.info("WorkqueueService reports no work to be done.")
                else:
                    self._logger.exception("Error trying to get work from WorkqueueService.")
                time.sleep(self._interpoll_sleep_time)
                continue
            self._logger.info("Workload of %d job elements acquired from WorkqueueService.",
                              sum(len(job['elements']) for job in workload))

            for job in workload:
                files = []
                elements = {}
                is_copy = False
                for element in job['elements']:
                    elements[element['id']] = element
                    if element['type'] == JobType.COPY:
                        is_copy = True
                        files.append((element['src_filepath'], element['dst_filepath']))
                    else:
                        files.append(element['src_filepath'])

                script_env = dict(os.environ, PATH=self._script_path)
                with NamedTemporaryFile() as src_proxyfile, NamedTemporaryFile() as dst_proxyfile:
                    src_proxyfile.write(job['src_credentials'])
                    src_proxyfile.flush()
                    os.fsync(src_proxyfile.fileno())
                    src_proxy_env_var = 'X509_USER_PROXY'
                    if is_copy:
                        dst_proxyfile.write(job['dst_credentials'])
                        dst_proxyfile.flush()
                        os.fsync(dst_proxyfile.fileno())
                        script_env['X509_USER_PROXY_DST'] = dst_proxyfile.name
                        src_proxy_env_var = 'X509_USER_PROXY_SRC'
                    script_env[src_proxy_env_var] = src_proxyfile.name

                    self._logger.info("Running elements in subprocess.")
                    self._current_process = subprocess.Popen(shlex.split(COMMANDMAP[job['type']][job['protocol']]),
                                                             bufsize=0,
                                                             stdin=subprocess.PIPE,
                                                             stdout=subprocess.PIPE,
                                                             stderr=subprocess.PIPE,
                                                             env=script_env)
                    print "HERE"
#                    json.dump({'files': files, 'options': job['extra_opts']},
#                              self._current_process.stdin)
#                    self._current_process.stdin.flush()
                    log = ''
                    while True:
                        print "HERE LOOPING"
                        readfps, writefps, _ = select.select([self._current_process.stdout,
                                                       self._current_process.stderr], [self._current_process.stdin], [], 1.0)
                        if writefps:
                            print "WRITEPFS"
                            json.dump({'files': files, 'options': job['extra_opts']},
                                      self._current_process.stdin)
                            self._current_process.stdin.flush()

                        if self._current_process.poll() is not None:
                            print "BREAKING"
                            break

                        if self._current_process.stderr in readfps:
                            print "STDERR ADDING"
                            log = '\n'.join((log, self._current_process.stderr.read()))

                        if self._current_process.stdout in readfps:
                            print "STDOUT"
                            try:
                                done_element = json.load(self._current_process.stdout)
                            except ValueError:
                                self._logger.exception("Error json loading from child process.")
                                continue
                            if done_element["Code"] != 0:
                                log = '\n'.join((log, done_element["Reason"]))

                            self._logger.info("Uploading output log to WorkqueueService.")
                            data = {'log': log,
                                    'returncode': done_element['Code'],
                                    'host': socket.gethostbyaddr(socket.getfqdn())}
                            if elements[done_element['id']]['type'] == JobType.LIST:
                                data.update(listing=done_element['Listing'])

                            self.set_token(elements[done_element['id']]['token'])
                            try:
                                self.put('worker/jobs/%d/elements/%d'
                                         % (job['id'], done_element['id']),
                                         data=data)
                            except RESTException:
                                self._logger.exception("Error trying to PUT back output from subcommand.")
                                continue
                            finally:
                                log = ''
                                self.set_token(None)
                assert False

#!/usr/bin/env python
"""Worker script."""
import os
import time
import uuid
import random
import json
import shlex
import socket
import subprocess
import shutil
import asyncore
import logging
from cStringIO import StringIO
from collections import defaultdict
from pprint import pformat
from datetime import datetime
from contextlib import contextmanager
from urlparse import urlsplit, urlunsplit
from tempfile import NamedTemporaryFile

from requests.exceptions import Timeout

from pdm.framework.RESTClient import RESTClient, RESTException
from pdm.site.SiteClient import SiteClient
from pdm.utils.X509 import X509Utils
from pdm.utils.daemon import Daemon
from pdm.utils.config import getConfig

from .WorkqueueDB import COMMANDMAP, PROTOCOLMAP, JobType


@contextmanager
def temporary_ca_dir(cas, dir_path=None, template_dir=None):
    """
    Context for creating a temporary CA directory.

    Temporary directory is automatically removed when exiting context.

    Args:
        cas (list): List of CA certs in string form.
        dir_path (str): Path to use for temporary ca directory. If None (default) then a
                        random dir_path is created.
        template_dir (str): Path to a directory to use as a template for the temporary
                            ca dir. All certs in this directory are duplicated in the new one.
                            If None (default) then don't use a template directory.

    Returns:
        str: The temporary ca dir.
    """
    ca_dir = X509Utils.add_ca_to_dir(cas,
                                     dir_path=dir_path,
                                     template_dir=template_dir)
    yield ca_dir
    shutil.rmtree(ca_dir, ignore_errors=True)


@contextmanager
def temporary_proxy_files(src_credentials, dst_credentials=None):
    """
    Context for creating temporary proxy files.

    Temporary proxy files are automatically removed when exiting context.

    Args:
        src_credentials (str): The credentials for the source target as a string.
        dst_credentials (str): The credentials for the destination target as a string.
                               If None (default) then only source proxy file is created.

    Returns:
        dict: A dictionary containing the proxy environment variables to set which point to the
              newly created temporary proxy files.
    """
    with NamedTemporaryFile() as src_proxyfile:
        src_proxyfile.write(src_credentials)
        src_proxyfile.flush()
        os.fsync(src_proxyfile.fileno())
        if dst_credentials is None:
            yield {'X509_USER_PROXY': src_proxyfile.name}
            return
        with NamedTemporaryFile() as dst_proxyfile:
            dst_proxyfile.write(dst_credentials)
            dst_proxyfile.flush()
            os.fsync(dst_proxyfile.fileno())
            yield {'X509_USER_PROXY_SRC': src_proxyfile.name,
                   'X509_USER_PROXY_DST': dst_proxyfile.name}


class BufferingDispatcher(asyncore.file_dispatcher):
    """
    Asynchronous buffering dispatcher.

    This dispatcher essentially buffers the output from the given fd until the buffer is read.
    At this point the buffer is blanked and starts again.
    """

    def __init__(self, fd):
        """Initialisation."""
        asyncore.file_dispatcher.__init__(self, fd)
        self._logger = logging.getLogger(self.__class__.__name__)
        self._buffer = ''

    @property
    def buffer(self):
        """Retrieve buffer content and reset buffer."""
        buffer_, self._buffer = self._buffer, ''
        return buffer_

    def writable(self):
        """Writeable status of fd."""
        return False

    def handle_read(self):
        """Handle read events."""
        self._buffer += self.recv(8192)


class StdOutDispatcher(asyncore.file_dispatcher):
    """Asynchronous dispatcher for subprocess stdout."""

    def __init__(self, fd, tokens, stderr_dispatcher, callback):
        """Initialisation."""
        asyncore.file_dispatcher.__init__(self, fd)
        self._fd = fd
        self._tokens = tokens
        self._stderr_dispatcher = stderr_dispatcher
        self._callback = callback
        self._logger = logging.getLogger(self.__class__.__name__)
        self._buffer = ''
        self._monitoring_dict = {}
        self._log_dict = defaultdict(StringIO)

    def writable(self):
        """Writeable status of fd."""
        return False

    def readable(self):
        """Readable status of fd."""
        # Note as we use self._fd directly (rather than self.recv) close is not called automatically
        if not self._tokens:
            self.close()
            return False
        return True

    def handle_read(self):
        """Handle read events."""
        self._buffer += self.recv(8192)
        buffered_elements = self._buffer.split('\n')
        self._buffer = buffered_elements.pop()

        for buffered_element in buffered_elements:
            try:
                done_element = json.loads(buffered_element)
            except ValueError:
                self._logger.exception("Problem json loading done element.")
                self.close()
                return

            element_id = done_element['id']
            if 'domain' in done_element:
                self._log_dict[element_id].write('{domain} -- {stage} -- {desc}\n'
                                                 .format(**done_element))
            elif 'transferred' in done_element:
                self._monitoring_dict[element_id] = done_element
            elif 'Code' in done_element:
                log = self._log_dict.pop(element_id, StringIO())
                log.write(self._stderr_dispatcher.buffer)
                log.write('\n')
                returncode = done_element['Code']
                data = {'log': log.getvalue(),
                        'returncode': returncode,
                        'timestamp': datetime.utcnow().isoformat(),
                        'host': socket.gethostbyaddr(socket.getfqdn()),
                        'monitoring': self._monitoring_dict.get(element_id, {})}
                log.close()

                if returncode:
                    self._logger.warning("Subprocess for job.element %s failed with exit code %s",
                                         element_id, returncode)
                self._logger.debug("Subprocess output for job.element %s: %s", element_id, log)

                if not element_id:  # whole job failure
                    for element_id, token in self._tokens.iteritems():
                        self._callback(*element_id.split('.'), token=token, data=data)
                    self._tokens.clear()  # will cause readable to close fd on next iteration.
                    return

                if 'Listing' in done_element:
                    data['listing'] = {}
                    for root, listing in done_element['Listing'].iteritems():
                        root = urlsplit(root).path
                        if root.startswith('/~'):
                            root = root.lstrip('/')
                        data['listing'][root] = listing
                token = self._tokens.pop(element_id)
                self._callback(*element_id.split('.'), token=token, data=data)
            else:
                self._logger.error("Unknown dictionary type returned from script: %s", done_element)


class Worker(RESTClient, Daemon):  # pylint: disable=too-many-instance-attributes
    """Worker Daemon."""

    def __init__(self, debug=False, n_shot=None, loglevel=logging.INFO):
        """Initialisation."""
        RESTClient.__init__(self, 'workqueue')
        uid = uuid.uuid4()
        Daemon.__init__(self,
                        pidfile='/tmp/worker-%s.pid' % uid,
                        logfile='/tmp/worker-%s.log' % uid,
                        loglevel=loglevel,
                        target=self.run,
                        debug=debug)
        conf = getConfig('worker')
        self._types = [JobType[type_.upper()] for type_ in  # pylint: disable=unsubscriptable-object
                       conf.pop('types', ('LIST', 'COPY', 'REMOVE', 'MKDIR', 'RENAME'))]
        self._alg = conf.pop('algorithm', 'BY_NUMBER').upper()
        self._alg_args = conf.pop('algorithm.args', {})
        self._interpoll_sleep_time = conf.pop('poll_time', 2)
        self._system_ca_dir = conf.pop('system_ca_dir',
                                       os.environ.get('X509_CERT_DIR',
                                                      '/etc/grid-security/certificates'))
        self._script_path = conf.pop('script_path',
                                     os.path.join(os.path.dirname(__file__), 'scripts'))
        self._script_path = os.path.abspath(self._script_path)
        self._site_client = SiteClient()
        self._n_shot = n_shot
        self._current_process = None

        # Check for unused config options
        if conf:
            raise ValueError("Unused worker config params: '%s'" % ', '.join(conf.keys()))

    @property
    def should_run(self):
        """Return if the daemon loop should run."""
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

    def _upload(self, job_id, element_id, token, data):
        """Upload results to WorkqueueService."""
        self._logger.info("Uploading output log for job.element %s.%s to WorkqueueService.",
                          job_id, element_id)
        self._logger.debug("Uploading following data for job.element %s.%s to WorkqueueService: %s",
                           job_id, element_id, pformat(data))
        self.set_token(token)
        try:
            self.put('worker/jobs/%s/elements/%s' % (job_id, element_id), data=data)
        except RESTException:
            self._logger.exception("Error trying to PUT back output from subcommand.")
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
                workload = self.post('worker/jobs', data={'types': self._types,
                                                          'algorithm': self._alg,
                                                          'algorithm.args': self._alg_args})
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
                self._logger.info("Processing job %d", job['id'])
                self._logger.debug("Job %d: %s", job['id'], pformat(job))
                # Get CAs and endpoints for job.
                cas = []
                credentials = [job['src_credentials']]
                template_ca_dir = self._system_ca_dir
                src_endpoint_dict = self._site_client.get_endpoints(job['src_siteid'])
                src_endpoints = src_endpoint_dict['endpoints']
                if 'cas' in src_endpoint_dict:
                    cas.extend(src_endpoint_dict['cas'])
                    template_ca_dir = None

                if job['type'] in (JobType.COPY, JobType.RENAME):
                    dst_endpoint_dict = self._site_client.get_endpoints(job['dst_siteid'])
                    dst_endpoints = dst_endpoint_dict['endpoints']

                if job['type'] == JobType.COPY:
                    credentials.append(job['dst_credentials'])
                    template_ca_dir = self._system_ca_dir
                    if 'cas' in dst_endpoint_dict:
                        cas.extend(dst_endpoint_dict['cas'])
                        template_ca_dir = None

                # Set up element id/token map and job stdin data
                token_map = {}
                data = {'files': []}
                options = job['extra_opts']
                if options is not None:
                    data.update(options=options)
                protocol = PROTOCOLMAP[job['protocol']]
                for element in job['elements']:
                    element_id = "%d.%d" % (job['id'], element['id'])
                    token_map[element_id] = element['token']
                    src = (element_id,
                           urlunsplit((protocol,
                                       random.choice(src_endpoints),
                                       element['src_filepath'], '', '')))
                    if element['type'] in (JobType.COPY, JobType.RENAME):
                        data['files'].append(src + (urlunsplit((protocol,
                                                                random.choice(dst_endpoints),
                                                                element['dst_filepath'], '', '')),))
                    # pylint: disable=bad-continuation
                    elif element['type'] == JobType.MKDIR\
                            or (element['type'] == JobType.REMOVE and
                                element['src_filepath'].endswith('/')):
                        data.setdefault('dirs', []).append(src)
                    else:
                        data['files'].append(src)

                # Correct command, data options and credentials for LIST component of
                # COPY/REMOVE/RENAME jobs.
                command = shlex.split(COMMANDMAP[job['type']][job['protocol']])
                if job['type'] != JobType.LIST\
                        and len(job['elements']) == 1\
                        and job['elements'][0]['type'] == JobType.LIST:
                    command = shlex.split(COMMANDMAP[JobType.LIST][job['protocol']])
                    data.pop('options', None)  # don't pass COPY/REMOVE options to scripts.
                    if job['type'] == JobType.COPY and len(credentials) == 2:
                        credentials.pop()  # remove dst_creds to get correct proxy env var
                command[0] = os.path.join(self._script_path, command[0])
                self._logger.info("Running elements in subprocess (%s).", command[0])

                # run job in subprocess with temporary proxy files and ca dir
                with temporary_proxy_files(*credentials) as proxy_env_vars,\
                        temporary_ca_dir(cas, template_dir=template_ca_dir) as ca_dir:
                    script_env = dict(os.environ, X509_CERT_DIR=ca_dir, **proxy_env_vars)
                    if self._logger.isEnabledFor(logging.DEBUG):
                        extra_env = {key: script_env[key] for key in
                                     set(script_env.iterkeys()).difference(os.environ.iterkeys())}
                        self._logger.debug("Extra environment variables: %s", pformat(extra_env))
                    self._logger.debug("Sending subprocess the following data: %s", pformat(data))
                    self._current_process = subprocess.Popen(command,
                                                             bufsize=0,
                                                             stdin=subprocess.PIPE,
                                                             stdout=subprocess.PIPE,
                                                             stderr=subprocess.PIPE,
                                                             env=script_env)
                    json.dump(data, self._current_process.stdin)
                    self._current_process.stdin.write('\n')
                    self._current_process.stdin.flush()
                    # We have to close stdin to force the subprocess to handle the input
                    # Otherwise it assumes there may be more data and hangs...
                    self._current_process.stdin.close()
                    stderr_dispatcher = BufferingDispatcher(self._current_process.stderr)
                    StdOutDispatcher(self._current_process.stdout, token_map,
                                     stderr_dispatcher, self._upload)
                    asyncore.loop(timeout=2)
                    if self._current_process.wait():
                        self._logger.error("Job %s failed", job['id'])
                        self._logger.info("Job stderr:\n%s", stderr_dispatcher.buffer)

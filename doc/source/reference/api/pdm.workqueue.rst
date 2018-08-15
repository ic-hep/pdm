pdm.workqueue package
=====================

.. automodule:: pdm.workqueue
    :members:
    :undoc-members:
    :show-inheritance:

Submodules
----------

pdm.workqueue.WorkqueueClient module
------------------------------------

.. autoclass:: pdm.workqueue.WorkqueueClient.WorkqueueClient
    :members:
    :undoc-members:
    :show-inheritance:

------------------------

pdm.workqueue.WorkqueueDB module
--------------------------------

.. autoclass:: pdm.workqueue.WorkqueueDB.JobType
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: pdm.workqueue.WorkqueueDB.JobProtocol
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: pdm.workqueue.WorkqueueDB.JobStatus
    :members:
    :undoc-members:
    :show-inheritance:

Job DB model
++++++++++++

.. .. data:: d={} Was going to add the jobs as data here

.. literalinclude:: ../../../../src/pdm/workqueue/WorkqueueDB.py
    :language: python
    :lines: 152-181
    :dedent: 8

JobElement DB model
+++++++++++++++++++

.. literalinclude:: ../../../../src/pdm/workqueue/WorkqueueDB.py
    :language: python
    :lines: 281-305
    :dedent: 8

------------------------

pdm.workqueue.WorkqueueService module
-------------------------------------

.. note:: All URLs are to be prefixed with **/workqueue/api/v1.0**. If in doubt look at the **Example request** for your desired api.

.. http:get:: /jobs

   Get all registered jobs for user or empty array.

   :reqheader Accept: the response content type depends on
                      :mailheader:`Accept` header
   :resheader Content-Type: this depends on :mailheader:`Accept`
                            header of request
   :>jsonarr int id: job id
   :>jsonarr int user_id: user's id
   :>jsonarr int src_siteid: source site's id
   :>jsonarr int dst_siteid: destination site's id
   :>jsonarr string src_filepath: the path to the file/dir on the source filesystem
   :>jsonarr string dst_filepath: the desired path to the file/dir on the destination filesystem
   :>jsonarr string type: the job's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>jsonarr string status: the job's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>jsonarr object extra_opts: any additional options passed on to the command execution scripts
   :>jsonarr int priority: the job's priority 0-9
   :>jsonarr string protocol: the protocol to use for the job (see :class:`pdm.workqueue.WorkqueueDB.JobProtocol`)
   :>jsonarr string log_uid: a unique hash string where the job's logs will be kept
   :>jsonarr string timestamp: iso-formatted timestamp of last change in DB
   :statuscode 200: no error

   **Example request**:

   .. sourcecode:: http

      GET /workqueue/api/v1.0/jobs HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      [
        {
          "id": 12345,
          "user_id": 123,
          "src_siteid": 13,
          "dst_siteid": 15,
          "src_filepath": "~/file1.txt",
          "dst_filepath": "~/file2.txt",
    	  "type": "COPY",
    	  "status": "DONE",
    	  "extra_opts": {},
    	  "priority": 5,
    	  "protocol": "GRIDFTP",
    	  "log_uid": "somelonghash",
    	  "timestamp": "2012-03-21T13:35"
        },
      ]

.. http:get:: /jobs/<int:job_id>

   Get specific job with id `job_id`.

   :>json int id: job id, this will be `job_id`
   :>json int user_id: user's id
   :>json int src_siteid: source site's id
   :>json int dst_siteid: destination site's id
   :>json string src_filepath: the path to the file/dir on the source filesystem
   :>json string dst_filepath: the desired path to the file/dir on the destination filesystem
   :>json string type: the job's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>json string status: the job's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>json object extra_opts: any additional options passed on to the command execution scripts
   :>json int priority: the job's priority 0-9
   :>json string protocol: the protocol to use for the job (see :class:`pdm.workqueue.WorkqueueDB.JobProtocol`)
   :>json string log_uid: a unique hash string where the job's logs will be kept
   :>json string timestamp: iso-formatted timestamp of last change in DB
   :statuscode 200: no error
   :statuscode 404: no job with id `job_id` found

   **Example request**:

   .. sourcecode:: http

      GET /workqueue/api/v1.0/jobs/12345 HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "id": 12345,
        "user_id": 123,
        "src_siteid": 13,
        "dst_siteid": 15,
        "src_filepath": "~/file1.txt",
        "dst_filepath": "~/file2.txt",
        "type": "COPY",
        "status": "DONE",
        "extra_opts": {},
        "priority": 5,
        "protocol": "GRIDFTP",
        "log_uid": "somelonghash",
        "timestamp": "2012-03-21T13:35"
      }

.. http:get:: /jobs/<int:job_id>/elements

   Get the job elements for job with id `job_id`

   :>jsonarr int id: job element id
   :>jsonarr int job_id: parent job's id, this will be `job_id`
   :>jsonarr string src_filepath: the path to the file/dir on the source filesystem
   :>jsonarr string dst_filepath: the desired path to the file/dir on the destination filesystem
   :>jsonarr int size: the size of the file on disk
   :>jsonarr int max_tries: maximum number of times to try this element
   :>jsonarr int attempts: number of times the element has been processed
   :>jsonarr string type: the job element's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>jsonarr string status: the job element's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>jsonarr string timestamp: iso-formatted timestamp of last change in DB
   :>jsonarr object listing: listing of a root directory in the form {"root": ["file1", "file2",],}
   :statuscode 200: no error

   **Example request**:

   .. sourcecode:: http

      GET /workqueue/api/v1.0/jobs/12345/elements HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      [
        {
          "id": 1,
          "job_id": 12345,
    	  "src_filepath": "~/file1.txt",
      	  "dst_filepath": "~/file2.txt",
          "size": 123354523,
          "max_tries": 2,
          "attempts": 1,
    	  "type": "COPY",
          "status": "DONE",
          "timestamp": "2012-03-21T13:35",
          "listing": {"root": ["file1", "file2"]}
        },
      ]

.. http:get:: /jobs/<int:job_id>/elements/<int:element_id>

   Get element `element_id` for job with id `job_id`

   :>json int id: job element id, this will be `element_id`
   :>json int job_id: parent job's id, this will be `job_id`
   :>json string src_filepath: the path to the file/dir on the source filesystem
   :>json string dst_filepath: the desired path to the file/dir on the destination filesystem
   :>json int size: the size of the file on disk
   :>json int max_tries: maximum number of times to try this element
   :>json int attempts: number of times the element has been processed
   :>json string type: the job element's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>json string status: the job element's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>json string timestamp: iso-formatted timestamp of last change in DB
   :>json object listing: listing of a root directory in the form {"root": ["file1", "file2",],}
   :statuscode 200: no error
   :statuscode 404: no job with id `job_id` or element with id `element_id` found

   **Example request**:

   .. sourcecode:: http

      GET /workqueue/api/v1.0/jobs/12345/elements/1 HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "id": 1,
        "job_id": 12345,
        "src_filepath": "~/file1.txt",
        "dst_filepath": "~/file2.txt",
        "size": 123354523,
        "max_tries": 2,
        "attempts": 1,
    	"type": "COPY",
        "status": "DONE",
        "timestamp": "2012-03-21T13:35",
        "listing": {"root": ["file1", "file2"]}
      }

.. http:get:: /jobs/<int:job_id>/output

   Get the output from all attempts of all elements for a job with given `job_id`. Outer array is list of elements while inner array is list of attempts as JSON objects.

   .. note:: Only *LIST* type jobs get an extra listing key (see example below).

   :>jsonarr int jobid: the id of the parent job requested, this will be `job_id`
   :>jsonarr int elementid: the id of the element
   :>jsonarr int attempt: the latest attempt number
   :>jsonarr string type: the job element's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>jsonarr string status: the job element's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>jsonarr string log: the job element's output (comming from the command execution script run on the worker)
   :>jsonarr object listing: listing of a root directory in the form {"root": ["file1", "file2",],} (**Only** for *LIST* type jobs)
   :statuscode 200: no error
   :statuscode 404: no job with id `job_id` found

   **Example request**:

   .. sourcecode:: http

      GET /workqueue/api/v1.0/jobs/12/output HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      [
        [
          {
            "jobid": 12,
            "elementid": 0,
            "attempt": 1,
            "type": "LIST",
            "status": "DONE",
            "log": "The output from the LIST command for file1 run on the worker",
            "listing": {"root": ["file1", "file2"]}
          }
        ],
        [
          {
            "jobid": 12,
            "elementid": 1,
            "attempt": 1,
            "type": "COPY",
            "status": "FAILED",
            "log": "The output from the COPY command run on the worker"
          },
          {
            "jobid": 12,
            "elementid": 1,
            "attempt": 2,
            "type": "COPY",
            "status": "DONE",
            "log": "The output from the COPY command run on the worker"
          }
        ]
      ]


.. http:get:: /jobs/<int:job_id>/elements/<int:element_id>/output

   Get the output from all attempts for element `element_id` of a job with given `job_id`

   .. note:: Only *LIST* type jobs get an extra listing key (see example below).

   :>jsonarr int jobid: the id of the parent job requested, this will be `job_id`
   :>jsonarr int elementid: the id of the element, this will be `element_id`
   :>jsonarr int attempt: the attempt number
   :>jsonarr string type: the job element's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>jsonarr string status: the job element's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>jsonarr string log: the job element's output (comming from the command execution script run on the worker)
   :>jsonarr object listing: listing of a root directory in the form {"root": ["file1", "file2",],} (**Only** for *LIST* type jobs)
   :statuscode 200: no error
   :statuscode 404: no job with id `job_id` or element with id `element_id` found. Also returned if no attempts have yet been made for specified element

   **Example request**:

   .. sourcecode:: http

      GET /workqueue/api/v1.0/jobs/12/elements/1/output HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      [
        {
          "jobid": 12,
          "elementid": 1,
          "attempt": 1,
          "type": "COPY",
          "status": "FAILED",
          "log": "The output from the copy command run on the worker"
        },
        {
          "jobid": 12,
          "elementid": 1,
          "attempt": 2,
          "type": "COPY",
          "status": "DONE",
          "log": "The output from the copy command run on the worker"
        },
      ]

.. http:get:: /jobs/<int:job_id>/elements/<int:element_id>/output/<int:attempt>

   Get the output of attempt `attempt` for element `element_id` of a job with given `job_id`. `attempt` may be a negative integer in order to index from the back.

   .. note:: Only *LIST* type jobs get an extra listing key (see example below).

   :>json int jobid: the id of the parent job requested, this will be `job_id`
   :>json int elementid: the id of the element, this will be `element_id`
   :>json int attempt: the requested attempt, this will be `attempt`
   :>json string type: the job element's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>json string status: the job element's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>json string log: the job element's output (comming from the command execution script run on the worker)
   :>json object listing: listing of a root directory in the form {"root": ["file1", "file2",],} (**Only** for *LIST* type jobs)
   :statuscode 200: no error
   :statuscode 400: attempt is not an integer
   :statuscode 404: no job with id `job_id` or element with id `element_id` or attempt `attempt` found. Also returned if no attempts have yet been made for specified element
   :statuscode 500: couldn't find the requested output file for attempt `attempt` on disk.

   **Example request**:

   .. sourcecode:: http

      GET /workqueue/api/v1.0/jobs/12/elements/1/output/1 HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "jobid": 12,
        "elementid": 1,
        "attempt": 1,
        "type": "COPY",
        "status": "FAILED",
        "log": "The output from the copy command run on the worker"
      }	

.. http:get:: /jobs/<int:job_id>/status

   Get the status of job with id `job_id`

   :>json int jobid: the id of the job requested, this will be `job_id`
   :>json string status:  the job's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :statuscode 200: no error
   :statuscode 404: no job with id `job_id` found

   **Example request**:

   .. sourcecode:: http

      GET /workqueue/api/v1.0/jobs/12/status HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "jobid": 12,
        "status": "DONE"
      }	

.. http:get:: /jobs/<int:job_id>/elements/<int:element_id>/status

   Get the status of element `element_id` for job with id `job_id`

   :>json int jobid: the id of the parent job requested, this will be `job_id`
   :>json int elementid: the id of the element, this will be `element_id`
   :>json string status:  the job's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>json int attempts: the number of times the element has been processed
   :statuscode 200: no error
   :statuscode 404: no job with id `job_id` or element with id `element_id` found

   **Example request**:

   .. sourcecode:: http

      GET /workqueue/api/v1.0/jobs/12/elements/1/status HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "jobid": 12,
        "elementid": 1,
        "status": "DONE",
        "attempts": 2
      }	

.. http:post:: /jobs

   Register a new job.

   :<json int src_siteid: source site's id
   :<json int dst_siteid: destination site's id (**Only** for COPY type jobs)
   :<json string src_filepath: the path to the file/dir on the source filesystem
   :<json string dst_filepath: the desired path to the file/dir on the destination filesystem (**Only** for COPY/RENAME type jobs)
   :<json int/string type: the job's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :<json object extra_opts: any additional options passed on to the command execution scripts (optional)
   :<json int priority: the job's priority 0-9 (optional default: 5)
   :<json int/string protocol: the protocol to use for the job (optional default: :attr:`~pdm.workqueue.WorkqueueDB.JobProtocol.GRIDFTP`)
   :>json int id: job id
   :>json int user_id: user's id
   :>json int src_siteid: source site's id
   :>json int dst_siteid: destination site's id
   :>json string src_filepath: the path to the file/dir on the source filesystem
   :>json string dst_filepath: the desired path to the file/dir on the destination filesystem
   :>json string type: the job's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>json string status: the job's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>json object extra_opts: any additional options passed on to the command execution scripts
   :>json int priority: the job's priority 0-9
   :>json string protocol: the protocol to use for the job (see :class:`pdm.workqueue.WorkqueueDB.JobProtocol`)
   :>json string log_uid: a unique hash string where the job's logs will be kept
   :>json string timestamp: iso-formatted timestamp of last change in DB
   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

   **Example request**:

   .. sourcecode:: http

      POST /workqueue/api/v1.0/jobs HTTP/1.1
      Host: example.com
      Accept: application/json
      Data: {
              "src_siteid": 12,
              "src_filepath": "somefile",
              "type": "LIST",
            }

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "id": 1,
        "user_id": 123,
        "src_siteid": 12,
        "src_filepath": "somefile",
        "type": "LIST",
        "status": "SUBMITTED",
        "extra_opts": {},
        "priority": 5,
        "protocol": "GRIDFTP",
        "log_uid": "somelonghash",
        "timestamp": "2012-03-21T13:35"
      }

.. http:post:: /list

   Register a listing job.

   :<json int src_siteid: source site's id
   :<json string src_filepath: the path to the file/dir on the source filesystem
   :<json object extra_opts: any additional options passed on to the command execution scripts (optional)
   :<json int priority: the job's priority 0-9 (optional default: 5)
   :<json int/string protocol: the protocol to use for the job (optional default: :attr:`~pdm.workqueue.WorkqueueDB.JobProtocol.GRIDFTP`)
   :>json int id: job id
   :>json int user_id: user's id
   :>json int src_siteid: source site's id
   :>json int dst_siteid: destination site's id
   :>json string src_filepath: the path to the file/dir on the source filesystem
   :>json string dst_filepath: the desired path to the file/dir on the destination filesystem
   :>json string type: the job's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>json string status: the job's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>json object extra_opts: any additional options passed on to the command execution scripts
   :>json int priority: the job's priority 0-9
   :>json string protocol: the protocol to use for the job (see :class:`pdm.workqueue.WorkqueueDB.JobProtocol`)
   :>json string log_uid: a unique hash string where the job's logs will be kept
   :>json string timestamp: iso-formatted timestamp of last change in DB
   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

   **Example request**:

   .. sourcecode:: http

      POST /workqueue/api/v1.0/list HTTP/1.1
      Host: example.com
      Accept: application/json
      Data: {
              "src_siteid": 12,
              "src_filepath": "somefile"
            }

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "id": 1,
        "user_id": 123,
        "src_siteid": 12,
        "src_filepath": "somefile",
        "type": "LIST",
        "status": "SUBMITTED",
        "extra_opts": {},
        "priority": 5,
        "protocol": "GRIDFTP",
        "log_uid": "somelonghash",
        "timestamp": "2012-03-21T13:35"
      }

.. http:post:: /copy

   Register a copy job.

   :<json int src_siteid: source site's id
   :<json int dst_siteid: destination site's id
   :<json string src_filepath: the path to the file/dir on the source filesystem
   :<json string dst_filepath: the desired path to the file/dir on the destination filesystem
   :<json object extra_opts: any additional options passed on to the command execution scripts (optional)
   :<json int priority: the job's priority 0-9 (optional default: 5)
   :<json int/string protocol: the protocol to use for the job (optional default: :attr:`~pdm.workqueue.WorkqueueDB.JobProtocol.GRIDFTP`)
   :>json int id: job id
   :>json int user_id: user's id
   :>json int src_siteid: source site's id
   :>json int dst_siteid: destination site's id
   :>json string src_filepath: the path to the file/dir on the source filesystem
   :>json string dst_filepath: the desired path to the file/dir on the destination filesystem
   :>json string type: the job's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>json string status: the job's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>json object extra_opts: any additional options passed on to the command execution scripts
   :>json int priority: the job's priority 0-9
   :>json string protocol: the protocol to use for the job (see :class:`pdm.workqueue.WorkqueueDB.JobProtocol`)
   :>json string log_uid: a unique hash string where the job's logs will be kept
   :>json string timestamp: iso-formatted timestamp of last change in DB
   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

   **Example request**:

   .. sourcecode:: http

      POST /workqueue/api/v1.0/copy HTTP/1.1
      Host: example.com
      Accept: application/json
      Data: {
              "src_siteid": 12,
              "dst_siteid": 14,
              "src_filepath": "somefile",
              "dst_filepath": "someotherfile"
            }

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "id": 1,
        "user_id": 123,
        "src_siteid": 12,
        "dst_siteid": 14,
        "src_filepath": "somefile",
        "dst_filepath": "someotherfile",
        "type": "COPY",
        "status": "SUBMITTED",
        "extra_opts": {},
        "priority": 5,
        "protocol": "GRIDFTP",
        "log_uid": "somelonghash",
        "timestamp": "2012-03-21T13:35"
      }

.. http:post:: /remove

   Register a remove job.

   :<json int src_siteid: source site's id
   :<json string src_filepath: the path to the file/dir on the source filesystem
   :<json object extra_opts: any additional options passed on to the command execution scripts (optional)
   :<json int priority: the job's priority 0-9 (optional default: 5)
   :<json int/string protocol: the protocol to use for the job (optional default: :attr:`~pdm.workqueue.WorkqueueDB.JobProtocol.GRIDFTP`)
   :>json int id: job id
   :>json int user_id: user's id
   :>json int src_siteid: source site's id
   :>json int dst_siteid: destination site's id
   :>json string src_filepath: the path to the file/dir on the source filesystem
   :>json string dst_filepath: the desired path to the file/dir on the destination filesystem
   :>json string type: the job's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>json string status: the job's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>json object extra_opts: any additional options passed on to the command execution scripts
   :>json int priority: the job's priority 0-9
   :>json string protocol: the protocol to use for the job (see :class:`pdm.workqueue.WorkqueueDB.JobProtocol`)
   :>json string log_uid: a unique hash string where the job's logs will be kept
   :>json string timestamp: iso-formatted timestamp of last change in DB
   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

   **Example request**:

   .. sourcecode:: http

      POST /workqueue/api/v1.0/remove HTTP/1.1
      Host: example.com
      Accept: application/json
      Data: {
              "src_siteid": 12,
              "src_filepath": "somefile"
            }

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "id": 1,
        "user_id": 123,
        "src_siteid": 12,
        "src_filepath": "somefile",
        "type": "REMOVE",
        "status": "SUBMITTED",
        "extra_opts": {},
        "priority": 5,
        "protocol": "GRIDFTP",
        "log_uid": "somelonghash",
        "timestamp": "2012-03-21T13:35"
      }

.. http:post:: /rename

   Register a rename job.

   :<json int src_siteid: source site's id
   :<json string src_filepath: the path to the file/dir on the source filesystem
   :<json string dst_filepath: the desired path to the file/dir on the source filesystem
   :<json object extra_opts: any additional options passed on to the command execution scripts (optional)
   :<json int priority: the job's priority 0-9 (optional default: 5)
   :<json int/string protocol: the protocol to use for the job (optional default: :attr:`~pdm.workqueue.WorkqueueDB.JobProtocol.GRIDFTP`)
   :>json int id: job id
   :>json int user_id: user's id
   :>json int src_siteid: source site's id
   :>json int dst_siteid: destination site's id
   :>json string src_filepath: the path to the file/dir on the source filesystem
   :>json string dst_filepath: the desired path to the file/dir on the destination filesystem
   :>json string type: the job's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>json string status: the job's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>json object extra_opts: any additional options passed on to the command execution scripts
   :>json int priority: the job's priority 0-9
   :>json string protocol: the protocol to use for the job (see :class:`pdm.workqueue.WorkqueueDB.JobProtocol`)
   :>json string log_uid: a unique hash string where the job's logs will be kept
   :>json string timestamp: iso-formatted timestamp of last change in DB
   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB
   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

   **Example request**:

   .. sourcecode:: http

      POST /workqueue/api/v1.0/rename HTTP/1.1
      Host: example.com
      Accept: application/json
      Data: {
              "src_siteid": 12,
              "src_filepath": "somefile",
              "dst_filepath": "someotherfile"
            }

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "id": 1,
        "user_id": 123,
        "src_siteid": 12,
        "dst_siteid": 12,
        "src_filepath": "somefile",
        "dst_filepath": "someotherfile",
        "type": "RENAME",
        "status": "SUBMITTED",
        "extra_opts": {},
        "priority": 5,
        "protocol": "GRIDFTP",
        "log_uid": "somelonghash",
        "timestamp": "2012-03-21T13:35"
      }

.. http:post:: /mkdir

   Register a mkdir job.

   :<json int src_siteid: source site's id
   :<json string src_filepath: the path to the file/dir on the source filesystem
   :<json object extra_opts: any additional options passed on to the command execution scripts (optional)
   :<json int priority: the job's priority 0-9 (optional default: 5)
   :<json int/string protocol: the protocol to use for the job (optional default: :attr:`~pdm.workqueue.WorkqueueDB.JobProtocol.GRIDFTP`)
   :>json int id: job id
   :>json int user_id: user's id
   :>json int src_siteid: source site's id
   :>json int dst_siteid: destination site's id
   :>json string src_filepath: the path to the file/dir on the source filesystem
   :>json string dst_filepath: the desired path to the file/dir on the destination filesystem
   :>json string type: the job's type (see :class:`pdm.workqueue.WorkqueueDB.JobType`)
   :>json string status: the job's status (see :class:`pdm.workqueue.WorkqueueDB.JobStatus`)
   :>json object extra_opts: any additional options passed on to the command execution scripts
   :>json int priority: the job's priority 0-9
   :>json string protocol: the protocol to use for the job (see :class:`pdm.workqueue.WorkqueueDB.JobProtocol`)
   :>json string log_uid: a unique hash string where the job's logs will be kept
   :>json string timestamp: iso-formatted timestamp of last change in DB
   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB
   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

   **Example request**:

   .. sourcecode:: http

      POST /workqueue/api/v1.0/mkdir HTTP/1.1
      Host: example.com
      Accept: application/json
      Data: {
              "src_siteid": 12,
              "src_filepath": "~/somedir"
            }

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "id": 1,
        "user_id": 123,
        "src_siteid": 12,
        "src_filepath": "~/somedir",
        "type": "MKDIR",
        "status": "SUBMITTED",
        "extra_opts": {},
        "priority": 5,
        "protocol": "GRIDFTP",
        "log_uid": "somelonghash",
        "timestamp": "2012-03-21T13:35"
      }

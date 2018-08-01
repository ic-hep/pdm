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

   :reqheader Accept: the response content type depends on
                      :mailheader:`Accept` header
   :resheader Content-Type: this depends on :mailheader:`Accept`
                            header of request
   :statuscode 200: no error

.. http:get:: /jobs/<int:job_id>

   Get specific job with id `job_id`.

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

   :statuscode 200: no error
   :statuscode 404: no job with id `job_id` found

.. http:get:: /jobs/<int:job_id>/elements

   Get the job elements for job with id `job_id`

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
	  "listing": [{"root": ["file1", "file2"]}]
        },
      ]

   :statuscode 200: no error

.. http:get:: /jobs/<int:job_id>/elements/<int:element_id>

   Get element `element_id` for job with id `job_id`

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
	"listing": [{"root": ["file1", "file2"]}]
      }

   :statuscode 200: no error
   :statuscode 404: no job with id `job_id` or element with id `element_id` found

.. http:get:: /jobs/<int:job_id>/output

   Get the latest available output of all elements for a job with given `job_id`.

   .. note:: Only *LIST* type jobs get an extra listing key (see example below).

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
        {
          "jobid": 12,
	  "elementid": 0,
	  "attempt": 1,
          "type": "LIST",
	  "status": "DONE",
	  "log": "The output from the list command run on the worker",
	  "listing": {"root": ["file1", "file2"]}
        },
        {
          "jobid": 12,
	  "elementid": 1,
	  "attempt": 2,
          "type": "COPY",
	  "status": "DONE",
	  "log": "The output from the copy command for file1 run on the worker"
        },	
      ]

   :statuscode 200: no error
   :statuscode 404: no job with id `job_id` found
   :statuscode 500: couldn't find the requested output file on disk. 

.. http:get:: /jobs/<int:job_id>/elements/<int:element_id>/output

   Get the latest available output for element `element_id` of a job with given `job_id`

   **Example request**:

   .. sourcecode:: http

      GET /workqueue/api/v1.0/jobs/12/elements/1/output HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "jobid": 12,
	"elementid": 1,
	"attempt": 2,
        "type": "COPY",
	"status": "DONE",
	"log": "The output from the copy command run on the worker"
      }	

   :statuscode 200: no error
   :statuscode 400: element output not yet ready
   :statuscode 404: no job with id `job_id` or element with id `element_id` found
   :statuscode 500: couldn't find the requested output file on disk. 


.. http:get:: /jobs/<int:job_id>/elements/<int:element_id>/output/<int:attempt>

   Get the output of attempt `attempt` for element `element_id` of a job with given `job_id`

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

   :statuscode 200: no error
   :statuscode 400: element output not yet ready or invalid attempt
   :statuscode 404: no job with id `job_id` or element with id `element_id` found
   :statuscode 500: couldn't find the requested output file on disk. 


.. http:get:: /jobs/<int:job_id>/status

   Get the status of job with id `job_id`

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

   :statuscode 200: no error
   :statuscode 404: no job with id `job_id` found

.. http:get:: /jobs/<int:job_id>/elements/<int:element_id>/status

   Get the status of element `element_id` for job with id `job_id`

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

   :statuscode 200: no error
   :statuscode 404: no job with id `job_id` or element with id `element_id` found

.. http:post:: /jobs

   Register a new job.

   .. note:: The job type must be given in integer form as described by the enum :class:`pdm.workqueue.WorkqueueDB.JobType`. If you know the type of job that you require you can use the shorthand job registration methods below to avoid having to pass this parameter.

   **Example request**:

   .. sourcecode:: http

      POST /workqueue/api/v1.0/jobs HTTP/1.1
      Host: example.com
      Accept: application/json
      Data: {
	      "src_siteid": 12,
	      "src_filepath": "somefile",
	      "type": "0",
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

   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

.. http:post:: /list

   Register a listing job.

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

   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

.. http:post:: /copy

   Register a copy job.

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

   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

.. http:post:: /remove

   Register a remove job.

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

   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

.. http:post:: /rename

   Register a rename job.

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

   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

.. http:post:: /mkdir

   Register a mkdir job.

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

   :statuscode 200: no error
   :statuscode 400: client error with input data
   :statuscode 500: unexpected server error either creating job or registering it in DB

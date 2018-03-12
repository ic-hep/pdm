#!/usr/bin/env python
"""Workqueue Application Run script."""
import asyncore
from multiprocessing import Process, Semaphore
import logging
logging.basicConfig(level=logging.DEBUG)
from flask import Flask, current_app

#from pdm.utils.config import getConfig
from pdm.workqueue.sql import db
#from pdm.workqueue.sql.models import Job, Log
from pdm.workqueue.async.worker_manager import QueueManager
from pdm.workqueue.api import list

def getConfig(b):
    return {}

app = Flask(__name__)
dburl = getConfig('Workqueue').get('dburl', 'sqlite:////home/hep/arichard/git/pdm/src/pdm/workqueue/bin/test.db')
with app.app_context():
    current_app.config['SQLALCHEMY_DATABASE_URI'] = dburl
    db.init_app(current_app)
    db.create_all()

    current_app.semaphore = Semaphore(0)
    # 0 = let the kernel give us a port
    manager = QueueManager(address=('localhost', 0), semaphore=current_app.semaphore)
    p = Process(target=asyncore.loop)
    p.start()

    list(12, 'blah')
    list(12, 'blah')
    current_app.run()

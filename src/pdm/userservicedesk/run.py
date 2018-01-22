__author__ = 'martynia'

import os

#from pdm.userservicedesk.app import create_app
from app import create_app
from app import human_resources
#
import logging

logging.basicConfig(level=logging.DEBUG)

config_name = os.getenv('APP_SETUP', default = 'development') # config_name = "development"
logging.info(" Running in the setup: %s ", config_name)
app = create_app(config_name)
app = human_resources.manage(app)

if __name__ == '__main__':
    app.run()

# Flask
from flask import Flask
# API
from server.apis import api
# Database
from database.mqtt_manager import MqttManager
from database.version import Version_sch
# Association Rules
from server.arules.association_rules import ARDiscoverer
# Dependencies
from database.version import PcaServerMetadata
# Logging
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class PcaServer:

    def __init__(self):
        logger.info(f"Starting PCA Server version {PcaServerMetadata.version()}")
        self.app = Flask(__name__) # Defining 
        logger.info(f"Flask App initialized")
        self.mqttmanager = MqttManager() # Creating MQTT Manager
        logger.info(f"MQTT Manager initialized")
        self.ardiscoverer = ARDiscoverer() # Creating AR Discoverer
        logger.info(f"AR Discoverer initialized")
        api.init_app(self.app) # Initializing APIs in App
        logger.info(f"API initialized")

    def run(self, hostname:str, pport:int, pdebug:bool):
        return self.app.run(host= hostname, port=pport, debug=pdebug)
    
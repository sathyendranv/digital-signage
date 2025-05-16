#Flask
from flask import Flask
#API
from server.apis import api
from database.mqtt_manager import MqttManager

__version__ = "0.1.0"

class PcaServer:
    def __init__(self):
        self.app = Flask(__name__) # Defining 
        self.mqttmanager = MqttManager() # Creating MQTT Manager
        api.init_app(self.app) # Initializing APIs in App

    def run(self, hostname:str, pport:int, pdebug:bool):
        return self.app.run(host= hostname, port=pport, debug=pdebug)
    
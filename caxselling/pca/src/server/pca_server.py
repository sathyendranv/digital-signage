#Flask
from flask import Flask
#API
from server.apis import api

__version__ = "0.1.0"

class PcaServer:
    def __init__(self):
        self.app = Flask(__name__) # Defining 
        api.init_app(self.app) # Initializing APIs in App

    def run(self, hostname:str, pport:int, pdebug:bool):
        return self.app.run(host= hostname, port=pport, debug=pdebug)
    
# Flask
from flask import Flask
# API
from server.apis import api
# Database
from database.mqtt_manager import MqttManager
from database.preferences_manager import PreferencesManager
# Dependencies
from database.version import BorServerMetadata, ServerEnvironment
# Multi-thread
import threading
# Logging
import logging
logger = logging.getLogger(__name__)

class BorServer:
    def __init__(self):
        logger.info(f"Starting BOR Server version {BorServerMetadata.version()}")
        self.app = Flask(__name__) # Defining 
        logger.info(f"Flask App initialized")
        self.prefmanager = PreferencesManager() # Creating Preferences Manager
        logger.info(f"Preferences Manager initialized")        
        self.mqttmanager = MqttManager() # Creating MQTT Manager
        logger.info(f"MQTT Manager initialized")
        api.init_app(self.app) # Initializing APIs in App
        logger.info(f"API initialized")
        
        if ServerEnvironment.get_bor_sync_enabled():
            # Start the background sync thread
            self._stop_event = threading.Event()
            self.mqtt_lock = threading.Lock()  # Create a lock for mqttmanager access
            self.sync_thread = threading.Thread(target=self._sync_mqtt_periodically, daemon=True)
            self.sync_thread.start()        
        else:
            self._stop_event = None
            self.mqtt_lock = None
            self.sync_thread = None

    def _sync_mqtt_periodically(self):
        while self._stop_event is not None and not self._stop_event.is_set():
            try:
                logger.info("Syncing MQTT clients...")
                with self.mqtt_lock:
                    self.mqttmanager.sync_with_pca()  # Only one thread can access this at a time
            except Exception as e:
                logger.error(f"Error syncing MQTT clients: {e}")
            
            # Wait with timeout so we can check the stop event periodically
            self._stop_event.wait(ServerEnvironment.get_bor_sync_interval())

    def stop_sync_thread(self):
        if self.sync_thread is not None and self._stop_event is not None and self.sync_thread.is_alive():
            self._stop_event.set()
            self.sync_thread.join()
    
    def closeConnections(self):
        if self.prefmanager is not None:
            self.prefmanager.closeConnections()
            logger.info("Preferences Manager connections closed.")        

    def shutdown(self):
        logger.info("Shutting down BOR Server...")
        self.stop_sync_thread()
        self.closeConnections()
        logger.info("BOR Server shutdown complete.")
        
    def run(self, hostname:str, pport:int, pdebug:bool):
        return self.app.run(host=hostname, port=pport, debug=pdebug)        
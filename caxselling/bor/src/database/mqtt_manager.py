import paho.mqtt.client as mqtt
import json
import re
import requests
from database.version import ServerEnvironment
from database.QueueManager import QueueManager, QueueItem
from database.preferences_manager import PreferencesManager
from server.ad_processing_policy import AddProcessingPolicy
import logging
import threading
import weakref
from datetime import datetime

logger = logging.getLogger(__name__)

class MqttClient:
    _instances = weakref.WeakSet()  # Weak reference set to keep track of instances

    @staticmethod
    def check_mqtt_endpoint(host,port) -> bool:
        """
        Check if the MQTT endpoint is reachable.
        :param host: MQTT Broker Host
        :param port: MQTT Broker Port
        :return: True if reachable, False otherwise
        """
        client = None
        result = False
        try:
            client = mqtt.Client()
            client.connect(host, port, 5)  # Connect with a timeout of 5 seconds
            
            if client.is_connected():
                logger.info(f"[MQTT] Successfully connected to MQTT endpoint {host}:{port}")
                result = True
        except Exception as e:
            logger.error(f"[MQTT] Error checking MQTT endpoint {host}:{port} - {str(e)}")
            return False
        finally:
            if client is not None:
                try:
                    client.disconnect()  # Disconnect the client
                except Exception as e:
                    logger.error(f"[MQTT] Error disconnecting from MQTT endpoint {host}:{port} - {str(e)}")
        
        return result
        
    def __init__(self, host:str, port:int, topic:str, pmessage:str, queue_manager: QueueManager): 
        logger.info(f"[Init] Creating MQTT Client for {host}:{port} - {topic}")

        if queue_manager is None:
            logger.error("[Init] Queue Manager is not provided. It is required to manage the queues for the MQTT topics.")
            raise ValueError("Queue Manager is not provided. It is required to manage the queues for the MQTT topics.")
        
        self.preferences_manager = PreferencesManager() #It gets the created instance if exist
        if self.preferences_manager is None:
            errorMessage = "[Init] Preferences Manager is not initialized. It is required to manage the preferences for the MQTT topics."
            logger.error(errorMessage)
            raise ValueError(errorMessage)

        MqttClient._instances.add(self)  # Add the instance to the weak reference set

        self.prefmanager = PreferencesManager() # Preferences Manager to manage the preferences for the MQTT topics
        self.host = host # MQTT Broker Host
        self.port = port # MQTT Broker Port
        self.topic = topic # Topic to listen in the MQTT Broker
        self.chk_and_upd_preferences() # Check and update the topic_out with the output suffix from the preferences manager
        
        self.concept = pmessage # Concept to be used in the processing policy (optional)
        if self.concept is None or self.concept == "":
            self.concept = self.prefmanager.getValue(PreferencesManager.CATEGORY_DIGITAL_SIGNAGE, PreferencesManager.DS_DEFAULT_CONCEPT) # Default concept if not provided
            if self.concept is None or self.concept == "":
                self.concept = "Healthy"

        self.subscribed = False # Flag to check if the client is subscribed
        self.connected = False # Flag to check if the client is connected        
        self.queue_manager = queue_manager # Queue Manager to manage the queues for the MQTT topics
       
        if self.host is None or self.port is None or self.topic is None:
            logger.error(f"[Init] MQTT Client parameters are not set. Host: {self.host}, Port: {self.port}, Topic: {self.topic}")
            raise ValueError("MQTT Client parameters are not set. Host, Port, and Topic must be provided.")
        
        if not isinstance(self.host, str) or not isinstance(self.port, int) or not isinstance(self.topic, str):
            logger.error(f"[Init] MQTT Client parameters are not valid. Host: {self.host}, Port: {self.port}, Topic: {self.topic}")
            raise ValueError("MQTT Client parameters are not valid. Host and Topic must be strings, and Port must be an integer.")

        # Set up the MQTT client
        self.client = mqtt.Client()
        
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        self.client.on_unsubscribe = self.on_unsubscribe
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish

        try:
            self.connect()                                    
        except Exception as e:
            errorMessage = f"[Init] Failed to connect to MQTT Broker ({self.host}:{self.port}) and Topic: {self.topic}. Error: {str(e)}"
            logger.error(errorMessage)
            raise errorMessage

        if queue_manager.add_queue(self.host, self.port, self.topic) == False:
            errorMessage = f"[Init] Failed to create the Queue for MQTT Broker ({self.host}:{self.port}) and Topic: {self.topic}."
            logger.error(errorMessage)
            raise errorMessage
        
        self.__output_lastItem:QueueItem = None # Last item sent to the output
    
    def chk_and_upd_preferences(self):
        """
        Check and update local variables based on preferences (the topic_out with the output suffix from the preferences manager. It checks time between ads submission.
        It is used to update the topic_out when the preferences manager is initialized or when the output suffix is changed.
        The same for time between ads submission.
        """
        if self.preferences_manager is None:
            errorMessage = "[__chk_and_upd_topic_out] Preferences Manager is not initialized. It is required to manage the preferences for the MQTT topics."
            logger.error(errorMessage)
            raise Exception(errorMessage)
        
        suffix = self.preferences_manager.getValue(PreferencesManager.CATEGORY_DIGITAL_SIGNAGE, PreferencesManager.DS_OUTPUT_SUFFIX) # Default topic for output if not provided
        suffix_cleaned = re.sub(r'[^a-zA-Z0-9_]', '', suffix)
        if len(suffix_cleaned)==0:
            suffix_cleaned = "_out"
        
        self.topic_out = f"{self.topic}{suffix_cleaned}"  # Update the topic_out with the new suffix
        self.time_between_ads = self.preferences_manager.getValue(PreferencesManager.CATEGORY_DIGITAL_SIGNAGE, PreferencesManager.DS_MIN_TIME_BETWEEN_ADS_SUBMISSION) # Default time between ads submission if not provided
        if self.time_between_ads is None or not isinstance(self.time_between_ads, (int)):
            self.time_between_ads = 90

    def subscribe(self):
        if self.client is None:
            logger.error("[Subscribe] MQTT client is not initialized.")
            raise Exception("[Subscribe] MQTT client is not initialized.")
                
        try:
            self.client.subscribe(self.topic)
            logger.warning(f"[Subscribe] Subscribed to topic: {self.topic} Broker: {self.host}:{self.port}")
            self.subscribed = True
        except Exception as e:
            logger.error(f"[Subscribe] Failed to subscribe to topic {self.topic}. Broker: {self.host}:{self.port}. Error: {str(e)}")
            self.subscribed = False
            raise

    def unsubscribe(self):
        if self.client is None:
            logger.error("[Unsubscribe] MQTT client is not initialized.")
            raise Exception("[Unsubscribe] MQTT client is not initialized.")
        
        try:
            self.client.unsubscribe(self.topic)
            logger.warning(f"[Unsubscribe] Unsubscribed from topic: {self.topic} Broker: {self.host}:{self.port}")
            self.subscribed = False
        except Exception as e:
            logger.error(f"[Unsubscribe] Failed to unsubscribe from topic {self.topic}. Broker: {self.host}:{self.port}. Error: {str(e)}")
            raise
    
    def start_queue_monitoring(self):
        # Only start if not already running
        if hasattr(self, '_monitor_thread') and self._monitor_thread.is_alive():
            return
        self._monitor_stop_event = threading.Event()
        self._monitor_thread = threading.Thread(target=self._monitor_queue, daemon=True)
        self._monitor_thread.start()

    def stop_queue_monitoring(self):
        if hasattr(self, '_monitor_stop_event'):
            self._monitor_stop_event.set()
        if hasattr(self, '_monitor_thread') and self._monitor_thread.is_alive():
            self._monitor_thread.join()

    def restart_queue_monitoring(self):
        self.stop_queue_monitoring()
        self.start_queue_monitoring()

    def _monitor_queue(self):
        while not self._monitor_stop_event.is_set():
            # ... your monitoring logic ...
            item = self.queue_manager.get_item_from_queue(self.host, self.port, self.topic)

            if item is not None:                        
                rdos:list=AddProcessingPolicy.apply_policy(self.host, self.port, self.topic, item, self.concept)  # Apply the processing policy to the item

                if rdos is not None and len(rdos) > 0:
                    if self.__output_lastItem is None or (self.__output_lastItem is not None and isinstance(self.__output_lastItem,QueueItem) and self.__output_lastItem.label_id != item.label_id):
                        # There are results different from the last item sent to the output -> Proceed
                        
                        # Check the time and wait the required time before pushing the output            
                        elapsed_seconds = self.queue_manager.elapsed_seconds_last_output(self.host, self.port, self.topic) 
                        if elapsed_seconds is not None and elapsed_seconds < self.time_between_ads:
                            #Wait to reach the time between ads submission
                            logger.info(f"[Monitor Queue] Waiting for the time between ads submission: {self.time_between_ads} seconds. Elapsed: {elapsed_seconds} seconds.")
                            self._monitor_stop_event.wait(self.time_between_ads-elapsed_seconds)
                    
                        logger.info(f"[Monitor Queue] Publishing output for item: {item} with rdos: {rdos}")
                        # Update this output organizing the results
                        output={}
                        about_item={}
                        about_item["label_id"] = item.label_id
                        about_item["label"] = item.label
                        about_item["confidence"] = item.confidence

                        output["images"] = rdos
                        output["item"] = about_item
                        output["topic_concept"] = item.concept      
                        output["timestamp"] = datetime.now().isoformat()  # Add a timestamp to the output         

                        #check and update last category sent
                        prdo,pmessage = self.publish_output(output) # Publish the output to the MQTT Broker
                        if prdo:
                            self.__output_lastItem = item  # Update the last item sent to the output            
                            self.queue_manager.update_last_output(self.host, self.port, self.topic) # Update the last output time
                        else:
                            logger.error(f"[Monitor Queue] Failed to publish output for item: {item}. Error: {pmessage}")
                            # If the output failed, we do not update the last item sent to the output
                    else:
                        logger.info(f"[Monitor Queue] Item {item} is the same as the last item sent to the output. Skipping output.")
                        
                else:
                    logger.info(f"[Monitor Queue] No items to publish for item: {item}. Waiting for next item.")            
            else:
                self._monitor_stop_event.wait(5)  # wait 5 seconds when no items in the queue

    def publish_output(self, message:dict) -> tuple[bool, str]:
        """
        Publish a message to the specified MQTT topic_out (topic + output_suffix)
        """
        if self.client is None:
            errorMessage = "[publish_output] MQTT client is not initialized."
            logger.error(errorMessage)
            return False, errorMessage
        
        self.chk_and_upd_preferences()  # Ensure the topic_out is updated with the output suffix from the preferences manager        
        
        if message is None or not isinstance(message, dict) or len(message) == 0:
            errorMessage = "[publish_output] Message is None or empty. Cannot publish."
            logger.error(errorMessage)
            return False, errorMessage
        
        try:            
            result = self.client.publish(self.topic_out, json.dumps(message), qos=1)  # Publish with QoS 1
            message = f"[publish_output] Message published to {self.host}:{self.port} - {self.topic_out}. Result: {result}"
            logger.info(message)
            return True, message
        except Exception as e:
            message = f"[publish_output] Failed to publish message to {self.host}:{self.port} - {self.topic_out}. Error: {str(e)}"
            logger.error(message)
            return False, message

    def connect(self):
        if self.client is None:            
            logger.error("[Connect] MQTT client is not initialized.")
            raise Exception("[Connect] MQTT client is not initialized.")

        try:
            self.client.reconnect_delay_set(min_delay=1, max_delay=30) # Set the delay for reconnection
            self.client.connect(self.host, self.port, 60)
            self.client.loop_start() # It starts a background thread
            logger.info(f"[Connect] Connected to MQTT Broker & Loop Started: {self.host}:{self.port}")
            self.connected = True
            self.start_queue_monitoring()
        except Exception as e:
            self.connected = False
            logger.error(f"[Connect] Failed to connect to MQTT Broker ({self.host}:{self.port}). Error: {str(e)}")
            raise

    def disconnect(self):
        if self.client is None:
            logger.error("[Disconnect] MQTT client is not initialized.")
            raise Exception("[Disconnect] MQTT client is not initialized.")

        try:            
            self.client.disconnect()            
            self.client.loop_stop()  # It stops a background thread,
            logger.info(f"[Disconnect] Loop Stopped and Disconnected from MQTT Broker: {self.host}:{self.port}")
            self.connected = False
            self.stop_queue_monitoring()
        except Exception as e:
            logger.error(f"[Disconnect] Failed to disconnect from MQTT Broker ({self.host}:{self.port}). Error: {str(e)}")
            raise

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.warning("[on_connect] Connected to MQTT Broker > %s:%s and Topic: %s", self.host, self.port, self.topic)            
            self.connected = True
            self.subscribe() # Subscribe to the topic after successful connection
        else:            
            logger.error(f"[on_connect] Failed to connect to MQTT Broker ({self.host}:{self.port}) and Topic: {self.topic}, return code: {rc}")

    def on_disconnect(self, client, userdata, rc):
        if rc == 0:
            logger.info("[on_disconnect] Disconnected to MQTT Broker > %s:%s and Topic: %s", self.host, self.port, self.topic)
        else:
            logger.error(f"[on_disconnect] Unexpected disconnection from MQTT Broker ({self.host}:{self.port}) and Topic: {self.topic}, return code: {rc}")
            
        self.connected = False

    def on_publish(self,client, userdata, mid):
        logger.info(f"[on_publish] Message Published in Broker: {self.host}:{self.port} Topic: {self.topic_out}. Message ID: {mid}")

    def on_subscribe(client, userdata, mid, reason_code_list, properties):
        # a single entry
        logger.info(f"[on_subscribe] mid: {mid} and QoS: {reason_code_list}")
    
    def on_unsubscribe(client, userdata, mid, reason_code_list, properties):
        # Since we subscribed only for a single channel, reason_code_list contains
        # a single entry
        logger.info(f"[on_unsubscribe] mid: {mid} and QoS: {reason_code_list}")        

    def get_status(self):
        if self.client is None:
            return "Uninitialized"            

        # Method 2: Use paho-mqtt's is_connected() if available
        if hasattr(self.client, "is_connected"):
            return "<Connected>" if self.client.is_connected() else "<Disconnected>"
        
        if self.connected:
            if self.subscribed:
                return "Connected and Subscribed"
            else:
                return "Connected but not Subscribed"
        else:
            return "Disconnected"

    def on_message(self, client, userdata, message):
        try:
            # Decode the message payload
            msg = json.loads(message.payload.decode())
            maincols = ["objects", "resolution", "tags", "timestamp"]

            # Check if the message contains the expected keys            
            msg_resolution_height = None
            msg_resolution_width = None            
            if "resolution" in msg:
                myresolution = msg["resolution"]
                if "width" in myresolution and "height" in myresolution:
                    msg_resolution_height = myresolution["height"]
                    msg_resolution_width = myresolution["width"]

            if "objects" in msg:
                    # Items in the same frame
                    for item in msg["objects"]:
                        if "detection" in item:
                            mydetection = item["detection"]

                            d_labelid = mydetection["label_id"] 
                            d_label = mydetection["label"]
                            d_confidence = mydetection["confidence"]
                            d_boundingbox = mydetection["bounding_box"]

                            queueitem=QueueItem(label_id=d_labelid,
                                                label=d_label,
                                                confidence=d_confidence,
                                                boundingbox=d_boundingbox,
                                                concept=self.concept)
                            
                            self.queue_manager.add_item_in_queue(self.host, self.port, self.topic, queueitem) # Add the item to the queue (or increase the frequency if it already exists)
                    
        except Exception as e:
            logging.error(f"[on_message] Error processing message: {str(e)}")


class MqttManager:    
    def __new__(cls):
        """Singleton pattern to ensure only one instance of MqttManager exists."""
        if not hasattr(cls, 'instance'):
            cls.instance = super(MqttManager, cls).__new__(cls)
        return cls.instance
    
    def __init__(self):
        # It avoids re-initialization of the instance for the singleton pattern
        if not hasattr(self, 'clients'):
            self.clients = {}
            self.queue_manager = QueueManager()

            self.conn = None
            self.sync_with_pca() # Reload the MQTT clients from the database
    
    def sync_with_pca(self):
        """
        Synchronize the MQTT clients with the PCA Server. It is used to reload the clients when the application starts.
        When the topic was removed from the PCA Server, it is removed from the MQTT Manager.
        When the topic was added to the PCA Server, it is added to the MQTT Manager.
        """       
        logger.info("[sync_with_pca] Synchronizing MQTT clients with PCA Server...")
        error = False
        pcaresult = {}

        try:
            # Query PCA and Process the reponse
            url=f"{ServerEnvironment.get_pca_server_protocol()}{ServerEnvironment.get_pca_server_host()}:{ServerEnvironment.get_pca_server_port()}/pca/mqtt/{ServerEnvironment.get_mqtt_broker_host()}"
            
            results = requests.get(url, timeout=5) # Replace with the actual PCA server URL
            if results is None or results.status_code != 200:
                raise Exception(f"[PCA] No result for MQTT Broker Host ({url}). Status code: {results.status_code}")
            
            mqtt_data = results.json()  # Assuming the response is in JSON format
            if not isinstance(mqtt_data, list):
                raise Exception(f"[PCA] Invalid response format for MQTT Broker Host ({url}). Expected a list, got {type(mqtt_data)}")
            
            for item in mqtt_data:
                if "host" in item and "port" in item and "topic" in item:
                    host = item["host"]
                    port = item["port"]
                    topic = item["topic"]
                    pmessage = item.get("message", None)  # Optional message field
                    
                    if not self.add_client(host, port, topic,pmessage): #it adds the quesue
                        logger.error(f"[sync_with_pca] Failed to add MQTT Client for {host}:{port} - {topic}")
                    else:                                                
                        logger.warning(f"[sync_with_pca] Successfully added MQTTClient and Queue for {host}:{port} - {topic}")
                        pcaresult[(host, port, topic)] = 1 #Key added (or existing) in the BOR Server
                else:
                    logger.error(f"[sync_with_pca] Invalid MQTT data format: {item}")

            # Remove clients that are not in the PCA Server response
            for key in list(self.clients.keys()):
                if key not in pcaresult:
                    logger.warning(f"[sync_with_pca] Removing MQTT Client for {key[0]}:{key[1]} - {key[2]} as it is not in PCA Server response")
                    if self.remove_client(key[0], key[1], key[2]):
                        self.queue_manager.remove_queue(key[0], key[1], key[2])

        except Exception as e:
            logger.error(f"[sync_with_pca] Error reloading MQTT clients: {str(e)}")
            error = True
        finally:
            if pcaresult is not None:
                pcaresult.clear()
        
        return not error
    
    def add_client(self, host:str, port:int, topic:str,pmessage:str) -> bool:
        """
        Add a client to the MQTT manager when it does not exist. It gets added when the connection and subscription are successful. TRUE if added, FALSE if not.
        """
        if (host, port, topic) not in self.clients:
            client = None
            try:
                client = MqttClient(host, port, topic, pmessage, self.queue_manager) # Create a new MQTT Client instance (Topic consumer and Output producer))
            except Exception as e:
                logger.error(f"[add_client] Failed to create MQTT Client for {host}:{port} - {topic}. Error: {str(e)}")
                return False

            self.clients[(host, port, topic)] = client
            logger.info(f"[add_client] Added MQTT Client for {host}:{port} - {topic}")
        else:
            logger.warning(f"[add_client] MQTT Client for {host}:{port} - {topic} already exists.")

        return True
    
    def remove_client(self, host, port, topic) -> bool:
        """
        Remove a client from the MQTT manager and its queue when it exists. It unsubscribes, disconnects, and stops the corresponding loop. TRUE if removed, FALSE if not.
        """
        if (host, port, topic) in self.clients:
            try:
                client:MqttClient = self.clients[(host, port, topic)] #Get object
                client.unsubscribe()
                client.disconnect()

                client = self.clients.pop((host, port, topic)) #Remove once unsubscribed and disconnected
                self.queue_manager.remove_queue(host, port, topic) #Remove the queue for the MQTT topic
                logger.info(f"[remove_client] Removed MQTT Client amd queue for {host}:{port} - {topic}")
                return True
            except Exception as e:
                logger.error(f"[remove_client] Failed to remove MQTT Client for {host}:{port} - {topic}. Error: {str(e)}")
                return False
        else:
            logger.warning(f"[remove_client] MQTT Client for {host}:{port} - {topic} does not exist.")
            return True

    def regenerate_client(self, host, port, topic):        
        if (host, port, topic) in self.clients:
            try:
                client:MqttClient = self.clients.pop((host, port, topic))                
                client.disconnect() # Disconnect the client                    
                
                self.add_client(host, port, topic) #Add the client again
                
                logger.info(f"[regenerate_client] Regenerated MQTT Client for {host}:{port} - {topic}")
            except Exception as e:
                logger.error(f"[regenerate_client] Failed to remove MQTT Client for {host}:{port} - {topic}. Error: {str(e)}")
                return False
        else:
            logger.warning(f"[regenerate_client] MQTT Client for {host}:{port} - {topic} does not exist.")
            return False
        
        self.detect_orphan_clients()        
        return True

    def exist_client(self, host, port, topic):        
        return (host, port, topic) in self.clients
        
    def get_client(self, host, port, topic):
        if self.exist_client(host, port, topic):
            return self.clients[(host, port, topic)]
        else:
            return None

    def detect_orphan_clients(self):
        """
        Detect orphan clients and remove them jointly with their queues. It is used to remove the clients that are not connected or subscribed.
        """
        referenced = set(self.clients.values())
        all_clients = set(MqttClient._instances)
        orphan_clients = all_clients - referenced

        for orphan in orphan_clients:
            try:
                logger.warning(f"Host: {orphan.host}, Port: {orphan.port}, Topic: {orphan.topic}")
                if isinstance(orphan, MqttClient):
                    orphan.disconnect()
                    orphan.unsubscribe()
                    orphan.client.loop_stop()  # Stop the loop
                    logger.info(f"[detect_orphan_clients] Removed orphan MQTT Client: {orphan.host}:{orphan.port} - {orphan.topic}")
                else:
                    logger.warning(f"[detect_orphan_clients] Orphan is not an instance of MqttClient: {orphan}")

            except Exception as e:
                logger.error(f"[detect_orphan_clients] Failed to remove orphan MQTT Client: {str(e)}")
            orphan.disconnect()
            self.queue_manager.remove_queue(orphan.host, orphan.port, orphan.topic)
            
    def get_item_from_queue(self, host, port, topic) -> QueueItem:
        """
        Retrieves and removes an item from the specified queue if it exists.
        Returns None if the queue is empty or does not exist.
        """
        if self.queue_manager is None:            
            return None
        
        return self.queue_manager.get_item_from_queue(host, port, topic)

    @staticmethod
    def get_MqttManager():
        return MqttManager()

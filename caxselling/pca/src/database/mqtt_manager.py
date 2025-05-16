import paho.mqtt.client as mqtt
from database.db_manager import DatabaseConnection
import json
import time
import logging
import weakref

logger = logging.getLogger(__name__)

class MqttClient:
    _instances = weakref.WeakSet()  # Weak reference set to keep track of instances

    def __init__(self, host, port, topic):               
        logger.info(f"[Init] Creating MQTT Client for {host}:{port} - {topic}")

        MqttClient._instances.add(self)  # Add the instance to the weak reference set

        self.host = host # MQTT Broker Host
        self.port = port # MQTT Broker Port
        self.topic = topic # Topic to listen in the MQTT Broker
        self.subscribed = False # Flag to check if the client is subscribed
        self.connected = False # Flag to check if the client is connected
       
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

        try:
            self.connect()                        
            
        except Exception as e:
            logger.error(f"[Init] Failed to connect to MQTT Broker ({self.host}:{self.port}) and Topic: {self.topic}. Error: {str(e)}")
            raise

    def subscribe(self):
        if self.client is None:
            logger.error("[Subscribe] MQTT client is not initialized.")
            raise Exception("[Subscribe] MQTT client is not initialized.")
                
        try:
            self.client.subscribe(self.topic)
            logger.info(f"[Subscribe] Subscribed to topic: {self.topic} Broker: {self.host}:{self.port}")
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
            logger.info(f"[Unsubscribe] Unsubscribed from topic: {self.topic} Broker: {self.host}:{self.port}")
            self.subscribed = False
        except Exception as e:
            logger.error(f"[Unsubscribe] Failed to unsubscribe from topic {self.topic}. Broker: {self.host}:{self.port}. Error: {str(e)}")
            raise
    
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
        except Exception as e:
            logger.error(f"[Disconnect] Failed to disconnect from MQTT Broker ({self.host}:{self.port}). Error: {str(e)}")
            raise

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("[on_connect] Connected to MQTT Broker > %s:%s and Topic: %s", self.host, self.port, self.topic)            
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
        conn = None
        try:
            conn = DatabaseConnection.connect()
            if conn is None:
                raise Exception("Database connection error")

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
                with conn.cursor() as curs:

                    # Items in the same frame
                    for item in msg["objects"]:
                        if "detection" in item:
                            mydetection = item["detection"]

                            d_labelid = mydetection["label_id"] 
                            d_label = mydetection["label"]
                            d_confidence = mydetection["confidence"]
                            d_boundingbox = mydetection["bounding_box"]

                            myinsert = """
                                INSERT INTO mqtt_topics_trxs
                                (hostname, port, topic, frameID, label_class, label_id, confidence, video_height, video_width, boundingbox)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            values = (
                                self.host,
                                self.port,
                                self.topic,
                                1,  # frameID as integer
                                d_label,
                                d_labelid,
                                d_confidence,
                                msg_resolution_height if msg_resolution_height is not None else None,
                                msg_resolution_width if msg_resolution_width is not None else None,
                                json.dumps(d_boundingbox)
                            )
                            curs.execute(myinsert, values)


                            logging.info(f"[on_message] {self.topic} {d_labelid} - {d_label} Conf: {d_confidence} {msg_resolution_width}x{msg_resolution_height} BB: {d_boundingbox}") #change
                    
                    conn.commit()

        except Exception as e:
            logging.error(f"[on_message] Error processing message: {str(e)}")
        finally:
            if conn is not None:
                conn.close()
                logger.info(f"[on_message] Connection closed to PostgreSQL database.")
            else:
                logger.error(f"[on_message] Connection to PostgreSQL database was not established.")

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
            self.conn = None
            self.__reloadMqttClients() # Reload the MQTT clients from the database
    
    def __reloadMqttClients(self):
        """
        Reload the MQTT clients from the database and Initialize the Mqtt Clients. It is used to reload the clients when the application starts.
        """
        conn = None
        error = False
        try:
            conn = DatabaseConnection.connect()
            if conn is None:
                logger.error("[__reloadMqttClients] Failed to connect to PostgreSQL database.")
                return False

            with conn.cursor() as curs:
                curs.execute("SELECT hostname, port, topic FROM mqtt_topics;")
                results = curs.fetchall()

                for row in results:
                    host, port, topic = row
                    self.add_client(host, port, topic)
        except Exception as e:
            logger.error(f"[__reloadMqttClients] Error reloading MQTT clients: {str(e)}")
            error = True
        finally:
            if self.conn is not None:
                conn.close()
                logger.info("[__reloadMqttClients] Connection closed to PostgreSQL database.")
        
        return not error
    
    def add_client(self, host, port, topic):
        """
        Add a client to the MQTT manager when it does not exist. It gets added when the connection and subscription are successful. TRUE if added, FALSE if not.
        """
        if (host, port, topic) not in self.clients:
            client = None
            try:
                client = MqttClient(host, port, topic)
            except Exception as e:
                logger.error(f"[add_client] Failed to create MQTT Client for {host}:{port} - {topic}. Error: {str(e)}")
                return False

            self.clients[(host, port, topic)] = client
            logger.info(f"[add_client] Added MQTT Client for {host}:{port} - {topic}")
        else:
            logger.warning(f"[add_client] MQTT Client for {host}:{port} - {topic} already exists.")

        return True
    
    def remove_client(self, host, port, topic):
        """
        Remove a client from the MQTT manager when it exists. It unsubscribes, disconnects, and stops the corresponding loop. TRUE if removed, FALSE if not.
        """
        if (host, port, topic) in self.clients:
            try:
                client = self.clients[(host, port, topic)] #Get object
                client.unsubscribe()
                client.disconnect()
                client = self.clients.pop((host, port, topic)) #Remove once unsubscribed and disconnected
                logger.info(f"[remove_client] Removed MQTT Client for {host}:{port} - {topic}")
            except Exception as e:
                logger.error(f"[remove_client] Failed to remove MQTT Client for {host}:{port} - {topic}. Error: {str(e)}")
                return False
        else:
            logger.warning(f"[remove_client] MQTT Client for {host}:{port} - {topic} does not exist.")
            return True

    def regenerate_client(self, host, port, topic):        
        if (host, port, topic) in self.clients:
            try:
                client = self.clients.pop((host, port, topic))                
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
        Detect orphan clients and remove them. It is used to remove the clients that are not connected or subscribed.
        """
        referenced = set(self.clients.values())
        all_clients = set(MqttClient._instances)
        orphan_clients = all_clients - referenced

        for orphan in orphan_clients:
            try:
                logger.warning(f"Host: {orphan.host}, Port: {orphan.port}, Topic: {orphan.topic}")
                orphan.disconnect()
                orphan.unsubscribe()
                orphan.client.loop_stop()  # Stop the loop
                logger.info(f"[detect_orphan_clients] Removed orphan MQTT Client: {orphan.host}:{orphan.port} - {orphan.topic}")
            except Exception as e:
                logger.error(f"[detect_orphan_clients] Failed to remove orphan MQTT Client: {str(e)}")
            orphan.disconnect()
            
    """Get the singleton instance of MqttManager."""
    @staticmethod
    def get_MqttManager():
        return MqttManager()

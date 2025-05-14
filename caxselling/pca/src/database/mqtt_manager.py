from db_manager import DatabaseConnection
import paho.mqtt.subscribe as subscribe
import paho.mqtt.client as mqtt
import json
import base64
import numpy as np
import logging
logger = logging.getLogger(__name__)

class MqttClient:
    def __init__(self, host, port, topic):       
        logger.info(f"Creating MQTT Client for {host}:{port} - {topic}")
        self.host = host
        self.port = port
        self.topic = topic
       
        subscribe.callback(self.on_message, topic, hostname=host, port=port)

        self.client = subscribe.Client()
        self.client.on_message = self.on_message
        self.client.connect(host, port)
        self.client.subscribe(topic)
        self.client.loop_start()

    def on_subscribe(client, userdata, mid, reason_code_list, properties):
        #https://pypi.org/project/paho-mqtt/#network-loop
        # Since we subscribed only for a single channel, reason_code_list contains
        # a single entry
        if reason_code_list[0].is_failure:
            logger.error(f"Broker rejected you subscription: {reason_code_list[0]}")
        else:
            logger.info(f"Broker granted the following QoS: {reason_code_list[0].value}")
    
    def on_message(self, client, userdata, message):
        try:
            # Decode the message payload
            payload = base64.b64decode(message.payload).decode('utf-8')
            data = json.loads(payload)
            
            # Process the data (example: convert to numpy array)
            data_array = np.array(data['data'])
            
            # Log the received data
            logging.info(f"Received data: {data_array}")
            
            # Store the data in PostgreSQL
            conn = DatabaseConnection.connect()
            if conn is not None:
                with conn.cursor() as curs:
                    curs.execute("INSERT INTO mqtt_topics (hostname, port, topic, message) VALUES (%s, %s, %s, %s)",
                                 (self.host, self.port, self.topic, json.dumps(data_array.tolist())))
                    conn.commit()
                conn.close()
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")

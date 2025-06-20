import paho.mqtt.client as mqtt
from PIL import Image
import json
import os
import base64
import io

class TopicReader:
    MQTT_BROKER = "localhost"
    MQTT_PORT = 1883
    MQTT_TOPIC = "topic_od_mjd_output"
    MESSAGE=0
    def __init__(self, topic=MQTT_TOPIC):
        self.topic = topic
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.MQTT_BROKER, self.MQTT_PORT, 60)
        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code", rc)
        self.client.subscribe(self.MQTT_TOPIC)

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)

            list_images = data.get("images", [])
            metadata_item = data.get("item", {})
            metadata_ts = data.get("timestamp", None)

            print(f"[{metadata_ts}] LabelID: {metadata_item.get('label_id', 'N/A')} Class: {metadata_item.get('label', 'N/A')} Confidence: {metadata_item.get('confidence', 'N/A')}")
            counter=0
            for item_image in list_images:
                img_bytes = base64.b64decode(item_image)
                image = Image.open(io.BytesIO(img_bytes))                                

                namedir = "~"
                directory = os.path.expanduser(namedir)
                filename = f"image_msg{self.MESSAGE}_{counter}.{image.format.lower()}"
                filepath = os.path.join(directory, f"{filename}")                

                image.save(filepath)
                counter += 1              
                        
            self.MESSAGE += 1
        except Exception as e:
            print("Error processing message:", e)        

    def read(self):
        # Simulate reading the topic
        print(f"Reading topic: {self.topic}")
        return f"Content of {self.topic}"
    
if __name__ == "__main__":
    topic_reader = TopicReader()
    print("Starting MQTT client loop...")
    topic_reader.client.loop_start()  # Start the MQTT client loop in a separate thread
    try:
        while True:
            pass  # Keep the script running to listen for messages
    except KeyboardInterrupt:
        print("Exiting...")
        topic_reader.client.loop_stop()  # Stop the MQTT client loop
        topic_reader.client.disconnect()




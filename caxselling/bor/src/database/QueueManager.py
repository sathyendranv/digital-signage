import threading
import queue
from datetime import datetime

class QueueItem:
    def __init__(self, label_id, label,confidence,boundingbox,concept=None):
        self.label_id = label_id
        self.label = label
        self.confidence = confidence
        self.boundingbox = boundingbox
        self.concept = None  # This can be used for additional context or related concepts
        self.frequency = 1
        self._lock = threading.Lock()

    def __str__(self):  
        return f"QueueItem(label_id={self.label_id}, label={self.label}, confidence={self.confidence}, boundingbox={self.boundingbox}, frequency={self.frequency}, concept={self.concept})" 

    def increment_frequency(self):
        with self._lock:
            self.frequency += 1

    def get_frequency(self):
        with self._lock:
            return self.frequency        

class CheckableQueue(queue.Queue):
    def __contains__(self, item:QueueItem):
        with self.mutex:
            return item in self.queue
    
    def has_label_id(self, label_id):
        """
        Checks if any item in the queue has the specified label_id.
        Returns True if found, False otherwise.
        """
        with self.mutex:
            return any(getattr(qitem, 'label_id', None) == label_id for qitem in self.queue)        
    
    def increment_frequency_by_label_id(self, label_id):
        """
        Increments the frequency of the item with the specified label_id.
        Returns True if the item was found and frequency incremented, False otherwise.
        """
        with self.mutex:
            for qitem in self.queue:
                if getattr(qitem, 'label_id', None) == label_id:
                    if isinstance(qitem, QueueItem):
                        # Increment frequency in a thread-safe manner
                        qitem.increment_frequency()  # This is thread-safe for the item
                        return True
        return False        

class QueueMQTTopic:
    def __init__(self, mqtt_host, mqtt_port, mqtt_topic):
        self.mqtt_host_input = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_topic = mqtt_topic
        self.queue_detection = CheckableQueue()
        self.last_output=None
        self._lock = threading.Lock()

    def put(self,item: QueueItem):
        """
        Adds an item to the queue if it does not already exist based on label_id.
        When the item already exists, it increments the frequency of that item.
        """
        if not self.queue_detection.has_label_id(item.label_id):
            self.queue_detection.put(item)
        else:
            self.queue_detection.increment_frequency_by_label_id(item.label_id)

        return True
    
    def get(self):
        """
        Retrieves an item from the queue if available.
        Returns None if the queue is empty.
        """
        if not self.queue_detection.empty():
            return self.queue_detection.get()
        
        return None    
    
    def update_last_output(self) -> bool:
        """
        Updates the last output item.
        """
        with self._lock:
            self.last_output = datetime.now()
            return True
    
    def elapsed_seconds_last_output(self) -> int:
        """
        Returns the elapsed seconds since the last output.
        If there is no last output, returns None.
        """
        with self._lock:
            if self.last_output is None:
                return None
            
            now = datetime.now()
            dt_diff = now - self.last_output
            diff_seconds = dt_diff.total_seconds()
            
            return diff_seconds if diff_seconds >= 0 else 0

class QueueManager:
    def __init__(self):
        self.queues = {}
        self._lock = threading.Lock()

    def add_queue(self, mqtt_host, mqtt_port, mqtt_topic) -> bool:
        key = (mqtt_host, mqtt_port, mqtt_topic)
        with self._lock:
            if key not in self.queues:
                self.queues[key] = QueueMQTTopic(mqtt_host, mqtt_port, mqtt_topic)
            
            return True

        return False

    def get_queue(self, mqtt_host, mqtt_port, mqtt_topic)->QueueMQTTopic:
        """
        Returns the queue for the specified MQTT host, port, and topic.
        If the queue does not exist, it returns None.
        """
        key = (mqtt_host, mqtt_port, mqtt_topic)
        with self._lock:
            return self.queues.get(key)
        
        return None

    def remove_queue(self, mqtt_host, mqtt_port, mqtt_topic):
        """
        Removes the queue for the specified MQTT host, port, and topic.
        If the queue does not exist, it does nothing.
        """
        key = (mqtt_host, mqtt_port, mqtt_topic)
        with self._lock:
            if key in self.queues:
                del self.queues[key]

    def get_all_queues(self) -> list:
        """
        Returns a list of (key, QueueMQTTopic) tuples for all queues.
        """
        with self._lock:
            return list(self.queues.items())    
        
    def add_item_in_queue(self, mqtt_host, mqtt_port, mqtt_topic, item: QueueItem) -> bool:
        """
        Adds an item to the specified queue if it exists.
        Returns True if the item was added or frequency incremented, False otherwise.
        """
        queue_mqtt_topic = self.get_queue(mqtt_host, mqtt_port, mqtt_topic)
        if queue_mqtt_topic:
            return queue_mqtt_topic.put(item)
        
        return False
    
    def get_item_from_queue(self, mqtt_host, mqtt_port, mqtt_topic) -> QueueItem:
        """
        Retrieves and remove an item from the specified queue if it exists.
        Returns None if the queue is empty or does not exist.
        """
        queue_mqtt_topic = self.get_queue(mqtt_host, mqtt_port, mqtt_topic)
        if queue_mqtt_topic:
            return queue_mqtt_topic.get()
        
        return None

    def update_last_output(self, mqtt_host, mqtt_port, mqtt_topic) -> bool:
        """
        Updates the last output time for the specified queue.
        Returns True if the queue exists and the last output was updated, False otherwise.
        """
        queue_mqtt_topic = self.get_queue(mqtt_host, mqtt_port, mqtt_topic)
        if queue_mqtt_topic:
            return queue_mqtt_topic.update_last_output()
        
        return False

    def elapsed_seconds_last_output(self, mqtt_host, mqtt_port, mqtt_topic) -> int:
        """
        Returns the elapsed seconds since the last output for the specified queue.
        If the queue does not exist or has no last output, returns None.
        """

        queue_mqtt_topic = self.get_queue(mqtt_host, mqtt_port, mqtt_topic)
        if queue_mqtt_topic:
            return queue_mqtt_topic.elapsed_seconds_last_output()
        
        return None

import importlib.metadata
from datetime import datetime
import os
import requests 
import random
# MQTT
import paho.mqtt.client as mqtt
# Log
import logging
logger = logging.getLogger(__name__)


class Version_sch(object):
    """
    Version schema to describe a component's version information."""
    component:str=None
    version:str=None
    observation:str=None
    lastverification:str=None

class BorServerMetadata:
    """
    Metadata for BOR Server.
    """
    __version__ = "0.1.0"
    __name_short = "BOR Server"
    __name_extended = "Business Offer Recommender (BOR) Server"
    __description_short = "It organizes ads (predefined or dynamically generated) based on detected items in the digital signage based on user preferences and guidelines."

    @staticmethod
    def version():
        return BorServerMetadata.__version__
    
    @staticmethod
    def name_short():
        return BorServerMetadata.__name_short

    @staticmethod
    def name_extended():
        return BorServerMetadata.__name_extended

    @staticmethod
    def description_short():
        return BorServerMetadata.__description_short
    
    @staticmethod
    def get_bor_versioninfo() -> Version_sch:
        borversion = Version_sch()
        borversion.component = BorServerMetadata.name_short()
        borversion.version = BorServerMetadata.version()
        borversion.observation = BorServerMetadata.description_short()
        borversion.lastverification = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        return borversion

class ServerEnvironment:
    @staticmethod
    def get_dependencies() -> list[Version_sch]:
        """
        Get the BOR dependencies and their versions.
        """
        dependencies = []
        for dist in importlib.metadata.distributions():
                dep = Version_sch()
                dep.component = dist.metadata['Name']
                dep.version = dist.version
                dep.observation = dist.metadata['Summary']
                dep.lastverification = datetime.now().strftime("%Y-%m-%d %H:%M")
                dependencies.append(dep)        
        return dependencies
    
    @staticmethod
    def get_bor_with_dependencies() -> list[Version_sch]:
        """
        Get the BOR version and dependencies.
        """
        bor = BorServerMetadata.get_bor_versioninfo()
        dependencies = ServerEnvironment.get_dependencies()
        return [bor] + dependencies

    def get_bor_parameter_string(param:str, default_value:str)-> str:
        """
        Get the Parameter from environment variable or default .
        """
        if default_value is None:
            raise ValueError("Default value cannot be None.")            
        
        value = None
        try:
            value = os.getenv(param, default_value)
            if value is None or not isinstance(value, str) or not value:
                raise ValueError("Value must be a non-empty string.")
            
            if len(str(value).strip()) == 0:
                raise ValueError("Value cannot be an empty string.")
            
        except ValueError as e:
            logger.error(f"[Environment] Invalid {param} environment variable ({value}). Using default '{default_value}'.")
            # Default to 'pca-server' if the environment variable is invalid
            return default_value
        
        return value

    def get_bor_parameter_int(param:str, default_value:int, min:int=None, max:int=None)->int:
        """
        Get the Parameter from environment variable or default .
        """
        if default_value is None:
            raise ValueError("Default value cannot be None.")            

        value = None
        try:
            value = os.getenv(param, default_value)
            if value is None:
                raise ValueError("Value must be a a valid int.")
            
            value = int(value)
            
            if min is not None and value < min:
                raise ValueError(f"Value must be greater than or equal to {min}.")
            
            if max is not None and value > max:
                raise ValueError(f"Value must be less than or equal to {max}.")            
        except ValueError as e:
            logger.error(f"[Environment] Invalid {param} environment variable ({value}). Using default '{default_value}'. Error: {str(e)}")
            # Default to 'pca-server' if the environment variable is invalid
            return default_value
        
        return value

    @staticmethod
    def check_server(protocol,host, port, uri, testvalue:int) -> bool:
        """
        Check if the server:port is reachable.
        parameters:
        - host: The server host (string).
        - port: The server port (int).
        - uri: The URI to check (string). Include initial "/" but not ending "/". For example, /pca/hstatus
        - testvalue: An integer value to test the server response.
        """
        if protocol is None or not isinstance(protocol, str):
            return False
        
        if host is None or not isinstance(host, str):
            return False
        
        if port is None or not isinstance(port, int):
            return False
        
        if not (1 <= port <= 65535):
            return False
        
        try:
            response = requests.get(f'{protocol}{host}:{port}{uri}/{testvalue}', timeout=5)
            rjson = response.json()
            if 'status' in rjson and rjson['status'] == 'ok' and \
               'id' in rjson and rjson['id'] == testvalue:
                    return True
            else:
                return False

        except requests.RequestException as e:
            logger.error(f"Error checking server status: {e}")
            return False
    
    @staticmethod
    def check_pca_server() -> bool:
        """
        Check if the PCA server is reachable.
        """
        protocol = ServerEnvironment.get_pca_server_protocol()
        host = ServerEnvironment.get_pca_server_host()
        port = ServerEnvironment.get_pca_server_port()
        uri = '/pca/hstatus'
        testvalue = random.randint(1, 1000)  # Random test value for the request
        
        return ServerEnvironment.check_server(protocol,host, port, uri, testvalue)
    
    @staticmethod
    def check_aig_server() -> bool:
        """
        Check if the AIG server is reachable.
        """
        protocol= ServerEnvironment.get_aig_server_protocol()
        host = ServerEnvironment.get_aig_server_host()
        port = ServerEnvironment.get_aig_server_port()
        uri = '/aig/hstatus'
        testvalue = random.randint(1, 1000)

        return ServerEnvironment.check_server(protocol,host, port, uri, testvalue)

    @staticmethod
    def check_mqtt_broker() -> bool:
        """
        Check if the MQTT Broker is reachable.
        """        
        host = ServerEnvironment.get_mqtt_broker_host()
        port = ServerEnvironment.get_mqtt_broker_port()

        result = False 
        client = None       
        try:
            client = mqtt.Client()
            client.connect(host, port, 5)  # Connect with a timeout of 5 seconds
            # If no exception, connection was initiated successfully
            result = True                
        except Exception as e:
            logger.error(f"[MQTT] Error checking MQTT endpoint {host}:{port} - {str(e)}")
            result = False
        finally:
            if client is not None:
                try:
                    client.disconnect()  # Disconnect the client
                except Exception as e:
                    logger.error(f"[MQTT] Error disconnecting from MQTT endpoint {host}:{port} - {str(e)}")

        return result        
            
    @staticmethod
    def get_bor_server_port():
        """
        Get the Bot server port from environment variable or default to '5014'.
        """
        return ServerEnvironment.get_bor_parameter_int('BOR_SERVER_PORT', 5014, min=1, max=65535)
    
    @staticmethod
    def get_pca_server_protocol() -> str:
        """
        Get the PCA server protocol from environment variable or default to 'http'.
        """
        return ServerEnvironment.get_bor_parameter_string('PCA_SERVER_PROTOCOL', 'http://')
    
    @staticmethod
    def get_pca_server_host() -> str:
        """
        Get the PCA server host from environment variable or default to 'localhost'.
        """
        return ServerEnvironment.get_bor_parameter_string('PCA_SERVER_HOST', 'pca-server')

    @staticmethod
    def get_pca_server_port():
        """
        Get the PCA server port from environment variable or default to 'localhost'.
        """
        return ServerEnvironment.get_bor_parameter_int('PCA_SERVER_PORT', 5002, min=1, max=65535)
#
    @staticmethod
    def get_mqtt_broker_protocol() -> str:
        """
        Get the MQTT Broker Protocol from environment variable or default to 'mqtt://'.
        """
        return ServerEnvironment.get_bor_parameter_string('MQTT_BROKER_PROTOCOL', 'mqtt://')
    
    @staticmethod
    def get_mqtt_broker_host() -> str:
        """
        Get the MQTT Broker Host from environment variable or default to 'mqtt'.
        """
        return ServerEnvironment.get_bor_parameter_string('MQTT_BROKER_HOST', 'mqtt')

    @staticmethod
    def get_mqtt_broker_port():
        """
        Get the MQTT Broker port from environment variable or default to '1883'.
        """
        return ServerEnvironment.get_bor_parameter_int('MQTT_BROKER_PORT', 1883, min=1, max=65535)

    @staticmethod
    def get_aig_server_protocol() -> str:
        """
        Get the AIG server protocol from environment variable or default to 'http'.
        """
        return ServerEnvironment.get_bor_parameter_string('AIG_SERVER_PROTOCOL', 'http://')
    
    @staticmethod
    def get_aig_server_host() -> str:
        """
        Get the AIG server host from environment variable or default to 'aig-server'.
        """
        return ServerEnvironment.get_bor_parameter_string('AIG_SERVER_HOST', 'aig-server')

    @staticmethod
    def get_aig_server_port():
        """
        Get the AIG server port from environment variable or default to '5003'.
        """
        return ServerEnvironment.get_bor_parameter_int('AIG_SERVER_PORT', 5003, min=1, max=65535)
    
    @staticmethod
    def get_bor_sync_enabled() -> bool:
        """
        Get the BOR sync enabled from environment variable or default to 'True'.
        """
        value = ServerEnvironment.get_bor_parameter_string('BOR_SYNC_ENABLED', '1')
        if value.lower() in ['true', '1', 'yes']:
            return True

        return False    

    @staticmethod
    def get_bor_sync_interval() -> int:
        """
        Get the BOR sync interval from environment variable or default to '300' seconds.
        """
        return ServerEnvironment.get_bor_parameter_int('BOR_SYNC_INTERVAL',300)
    
    @staticmethod
    def get_bor_default_pref_db() -> str:
        """
        Get the BOR default preferences and guidelines DB name from environment variable or default to 'bor_pref_db'.
        """
        return ServerEnvironment.get_bor_parameter_string('BOR_DEFAULT_PREF_DB', 'bor_pref_db')
#Arguments
import sys
import argparse
#Server
sys.path.append('./src')
from server.bor_server import BorServer
from database.version import ServerEnvironment
import logging
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=ServerEnvironment.get_bor_server_port())
    args = parser.parse_args()

    borserver = BorServer()    
    borserver.run(hostname="0.0.0.0", pport=5014, pdebug=True,)
    
    #Once finished th
    if borserver:
        borserver.shutdown() #Thread and DB connections
  
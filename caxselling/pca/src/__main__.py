#Arguments
import sys
import os
import argparse
#OneDAL
import daal4py as d4p 
#Server
sys.path.append('./src')
from server.pca_server import PcaServer
from database.db_manager import createTrxTables

# MQTT
# setup topics to listen and insert in trx (insert)
# query and show status for topic
# multiple topics in parallel
# delete topic (and recorded history?)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5002)
    args = parser.parse_args()

    ## PG Database
    createTrxTables()

    pcaserver = PcaServer()
    #Registering the clean up function    
    pcaserver.run(hostname="0.0.0.0", pport=args.port, pdebug=True,)

# Why image is created as docker-pca-server? [Pending]
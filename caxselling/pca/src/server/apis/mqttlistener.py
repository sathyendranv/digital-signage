import os
#Flask API
from flask_restx import Namespace, Resource, fields
#PostgresSQL
from database.db_manager import DatabaseConnection
#Logging
import logging
logger = logging.getLogger(__name__)

api = Namespace('PCA_MQTT', description='Listener definition related operations')

## Schemas
    ##Status
mqtttopic_sch = api.model('mqttdefinition', {
    'host': fields.String(required=True, 
                            readonly=True,
                            description="The MQTT Broker Host.",
                            example="http://192.168.1.2"),
    'port': fields.Integer(required=True, 
                         readonly=True,
                         description="The port number in the MQTT Broker Host.", 
                         example="1883"),
    'topic': fields.String(required=True, 
                         readonly=True,
                         description="Topic to listen in the MQTT Broker.", 
                         example="mytopic"),                         
    'status': fields.String(required=False, 
                         readonly=True,
                         description="Last Known Status for the Topic in the MQTT Broker.", 
                         example="[YYYY-MM-DD HH:MM:SS] - Active {#Elements/min}"),                        
})

class Mqtttopic_sch(object):
    host:str=None
    port:int=None
    topic:str=None
    status:str=None

@api.route('/mqtt/')
class Mqtttopic(Resource):
    @api.doc('Define a new topic to listen given a MQTT broker - Put')
    @api.response(200, 'Success')
    @api.response(202, 'Accepted request but existent')
    @api.response(500, 'Accepted but it could not be processed/stored')
    @api.expect(mqtttopic_sch, validate=True)
    @api.marshal_with(mqtttopic_sch)
    def put(self):
        data = api.payload
        conn = None
        try:
            conn = DatabaseConnection.connect()            
            if conn is None:                
                message=f"PG Connection Error"
                logger.error(message)
                ret=Mqtttopic_sch()
                ret.status=message                
                return ret, 500
                        
            with conn.cursor() as curs:
                phost=data["host"]
                pport=data["port"]
                ptopic=data["topic"]

                curs.execute(f"SELECT hostname, port, topic from mqtt_topics where hostname like '{phost}' and port={pport} and topic like '{ptopic}' limit 1;")
                results = curs.fetchall()
                
                if len(results)>0:
                    conn.close()
                    message=f"Topic {ptopic} already defined for the MQTT Broker: {phost}:{pport}"
                    logger.info(message)
                    ret=Mqtttopic_sch()
                    ret.status=message                    
                    return ret, 202
                
                curs.execute(f"INSERT INTO mqtt_topics(hostname, port, topic, message) VALUES('{phost}','{pport}','{ptopic}','');")
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Putting topic {data} for the MQTT Broker")            
            message=f"PG Exception: {str(e)}"
            logger.error(message)
            ret=Mqtttopic_sch()
            ret.status=message
            return ret, 500
        finally:
            if conn is not None:
                conn.close()
                
        return data, 200
    
    @api.doc('It removes the mentioned topic for the host:port MQTT Broker. PCA will not listen to it anymore')
    @api.response(200, 'Success')
    @api.response(404, 'No Topics for the mentioned MQTT broker:port and topic')
    @api.response(500, 'Accepted but it could not be processed/recovered')    
    @api.expect(mqtttopic_sch, validate=True)
    @api.marshal_with(mqtttopic_sch)
    def delete(self):
        data = api.payload

        conn = None
        try:
            conn = DatabaseConnection.connect()            
            if conn is None:
                message=f"PG Connection Error"
                logger.error(message)
                ret=Mqtttopic_sch()
                ret.status=message
                return ret, 500
            
            with conn.cursor() as curs:
                phost=data["host"]
                pport=data["port"]
                ptopic=data["topic"]

                curs.execute(f"SELECT hostname, port, topic from mqtt_topics where hostname like '{phost}' and port={pport} and topic like '{ptopic}' limit 1;")
                results = curs.fetchall()
                
                if len(results)==0:
                    conn.close()
                    message=f"Topic {ptopic} does not exist in the MQTT Broker: {phost}:{pport}"
                    ret=Mqtttopic_sch()
                    ret.status=message
                    return ret, 404
                
                curs.execute(f"DELETE FROM mqtt_topics where hostname like '{phost}' and port={pport} and topic like '{ptopic}';")
                
                conn.commit()
        except Exception as e:
            logger.error(f"Deleting topic {data} for the MQTT Broker")
            message=f"PG Exception: {str(e)}"
            logger.error(message) 
            ret=Mqtttopic_sch()
            ret.status=message            
            return ret, 500
        finally:
            if conn is not None:
                conn.close()
                
        return data, 200
    
@api.route('/mqtt/<string:host>')
@api.param('host','MQTT Broker Host to filter the topics')
class MqtttopicQuery(Resource):
    @api.doc('It returns the list of all topics to listen for the mentioned MQTT broker (Host). Hard limit to 50 topics.')
    @api.response(200, 'Success')
    @api.response(404, 'No Topics for the mentioned MQTT broker')
    @api.response(500, 'Accepted but it could not be processed/recovered')    
    @api.marshal_list_with(mqtttopic_sch)
    def get(self,host):
        #To Do
        list=[]
        conn = None
        try:
            conn = DatabaseConnection.connect()            
            if conn is None:
                message=f"PG Connection Error"
                logger.error(message)
                ret=Mqtttopic_sch()
                ret.status=message                
                return ret, 500
            
            with conn.cursor() as curs:
                curs.execute(f"SELECT hostname, port, topic from mqtt_topics where hostname like '{host}' order by hostname, port, topic limit 50;")
                results = curs.fetchall()

                while results:
                    row = results.pop(0)
                    data=Mqtttopic_sch()
                    data.host=str(row[0])
                    data.port=int(row[1])
                    data.topic=str(row[2])
                    data.status=""
                    
                    list.append(data)

        except Exception as e:
            logger.error(f"Query topics based on the host ({host}) for the MQTT Broker")            
            message=f"PG Exception: {str(e)}"
            logger.error(message)
            ret=Mqtttopic_sch()
            ret.status=message            
            return ret, 500
        finally:
            if conn is not None:
                conn.close()

        if len(list)==0:
            ret=Mqtttopic_sch()
            ret.status=f"No topics for the mentioned MQTT broker: {host}"
            return ret, 404
                
        return list, 200

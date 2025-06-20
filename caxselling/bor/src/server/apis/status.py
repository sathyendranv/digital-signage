from flask_restx import Namespace, Resource, fields
from database.version import ServerEnvironment

api = Namespace('BOR - Status', description='Status related operations')

## Schemas
    ##Status
status_sch = api.model('status_test', {
    'component': fields.String(required=True, default=None, description="The name of the component being checked.", example="BOR Server"),
    'status': fields.String(required=True, default=None, description="ok: the id was read. failure: the id has not been received.", example="ok"),
    'id': fields.Integer(required=True, default=7, description="An integer ID as an example to check the reading/response procedure.", example="7"),
})

class Status_sch(object):
    component:str = None
    status:str = None
    id:int = None

@api.route('/hstatus/<int:id>', 
           doc={"description":"It replies with the indicated parameter to check the server status."})
@api.param('id','An integer ID as an example to check the reading/response procedure.')
class HStatus(Resource):
    @api.doc('Check the Health Status - Get')
    @api.marshal_with(status_sch)
    def get(self, id):
        return self.common(id)
    
    def common(self,id):        
        curr=Status_sch()
        curr.component="BOR Server"

        if id is None or not isinstance(id,int):            
            curr.id=id
            curr.status="failure"
        else:
            curr.id=id
            curr.status="ok"

        return curr

@api.route('/hstatus', 
           doc={"description":"It replies with a list of component statuses."})
class HStatuses(Resource):
    @api.marshal_list_with(status_sch)
    def get(self):
        rdo=[]

        item = Status_sch()
        item.component = "BOR Server"
        item.status = "ok"
        item.id = 0
        rdo.append(item)

        item = Status_sch()
        item.component = f"PCA Server ({ServerEnvironment.get_pca_server_protocol()}{ServerEnvironment.get_pca_server_host()}:{ServerEnvironment.get_pca_server_port()})"
        item.id = 0        
        if ServerEnvironment.check_pca_server():
            item.status = "ok"
        else:
            item.status = "failure"
        rdo.append(item)

        item = Status_sch()
        item.component = f"AIG Server ({ServerEnvironment.get_aig_server_protocol()}{ServerEnvironment.get_aig_server_host()}:{ServerEnvironment.get_aig_server_port()})"
        item.id = 0
        if ServerEnvironment.check_aig_server():
            item.status = "ok"
        else:
            item.status = "failure"
        rdo.append(item)

        item = Status_sch()
        item.component = f"MQTT Broker ({ServerEnvironment.get_mqtt_broker_protocol()}{ServerEnvironment.get_mqtt_broker_host()}:{ServerEnvironment.get_mqtt_broker_port()})"
        item.id = 0
        if ServerEnvironment.check_mqtt_broker():
            item.status = "ok"
        else:
            item.status = "failure"
        rdo.append(item)

        return rdo
        

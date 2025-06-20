from flask_restx import Namespace, Resource, fields
import random

api = Namespace('BOR - Price Simulator', description='It is a a price simulator for the BOR Server. It is used to test the server and its components. It is understood for demo only.')

## Schemas
    ##Status
price_simulator_sch = api.model('price_simulator_sch', {
    'labelid': fields.String(required=True, default=None, description="The name of the component being checked.", example="BOR Server"),
    'price': fields.Float(required=False, default=None, description="The price of the component.", example=5.34),
    'unit': fields.String(required=False, default=None, description="The unit of the price.", example="$/lb"),
    'promotional_text' : fields.String(required=False, default=None, description="The promotional text for the particular labelidcomponent.", example="Special offer for this month!"),
})

class Price_Simulator_sch(object):
    labelid:str = None
    price:float = None
    unit:str = None
    promotional_text:str = None

@api.route('/price/<string:id>', 
           doc={"description":"It replies with the simulated price and promotional text."})
@api.param('id','An integer ID as an example to check the reading/response procedure.')
class PriceSimulator(Resource):
    @api.doc('It returns a random simulated price with a promotional text - Get')
    @api.marshal_with(price_simulator_sch)
    def get(self, id):
        return self.common(id)
    
    def common(self,id):        
        curr=Price_Simulator_sch()

        curr.labelid = id
        curr.price = int(random.uniform(1.0, 100.0) * 100) / 100.0  # Simulating a random price between 1.0 and 100.0
        curr.unit = "$/lb"
        curr.promotional_text = "Special offer for this month!"

        return curr

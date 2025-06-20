from flask_restx import Api

from .status import api as bor_status
from .version import api as bor_version
from .preferences import api as bor_preferences
from .price_simulator import api as bor_price_simulator

#API DOC
api = Api(
    title='BOR Server',
    version='0.1',
    description='Business Offer Recommender (BOR) Server',
    # All API metadatas
)

# Add Namespaces into the API with URL prefixes
api.add_namespace(bor_status, path='/bor') 
api.add_namespace(bor_version, path='/bor')
api.add_namespace(bor_preferences, path='/bor')
api.add_namespace(bor_price_simulator, path='/bor')

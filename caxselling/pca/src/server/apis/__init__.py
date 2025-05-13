from flask_restx import Api

from .status import api as pca_status
from .version import api as pca_version

#API DOC
api = Api(
    title='PCA Server',
    version='0.1',
    description='Product Consumption Analyzer Server',
    # All API metadatas
)

# Add Namespaces into the API with URL prefixes
api.add_namespace(pca_status, path='/pca') 
api.add_namespace(pca_version, path='/pca')
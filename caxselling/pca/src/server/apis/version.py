from flask_restx import Namespace, Resource, fields

api = Namespace('PCA_Version', description='Version related operations')

#Version schema
version_sch = api.model('version', {
    'flask': fields.String(required=True, 
                            readonly=True,
                            description="Flask library Version",
                            example="2.2.5"),
    'flask_restx': fields.String(required=True, 
                            readonly=True,
                            description="Flask-Restx library Version",
                            example="1.3.0"),
    'oneDAL': fields.String(required=True, 
                            readonly=True,
                            description="oneDAL library Version",
                            example="2024.7.0"),
    'PCAServer': fields.String(required=True, 
                               readonly=True,
                               description="PCA Server Version",
                               example="0.1.0"),
})

class Version_sch(object):
    flask:str=None
    flask_restx:str=None
    oneDAL:str=None
    PCAServer:str=None

@api.route('/versions')
class HStatus(Resource):
    @api.doc('Return the version of the PCA Server and associated libraries')
    @api.marshal_with(version_sch)
    def get(self):
        curr=Version_sch()
        curr.flask="2.2.5x"
        curr.flask_restx="xx"
        curr.oneDAL=""
        curr.PCAServer="0.0.1"

        return curr

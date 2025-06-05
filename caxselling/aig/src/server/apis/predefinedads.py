import io
import os
#Flask API
from flask import send_file, request
from flask_restx import Namespace, Resource, fields
# GenAI
import openvino_genai
from PIL import Image
#Logging
import math
import logging
logger = logging.getLogger(__name__)
#AIGServer Environment
from database.version import AseServerMetadata
from imgproc.img_frame import ImgDecorator
import base64

api = Namespace('ASE - Advertise Searcher', description='It provides functionalities to define and search predefined ads.')

## Schemas
predef_ad_schema = api.model('PredefinedAd', {
    'id': fields.Integer(readOnly=False, description='The unique identifier of the ad. If not defined, the server proposes one ID in add operations.', example=1),
    'description': fields.String(required=True, description='The description of the ad. It is essential to determine when it is applicable.', example="It shows fruits such as oranges and bananas..."),
    'imgb64': fields.String(required=True, description='Base64-encoded image'), 
    'source': fields.String(required=False, description='Source of the ad', example="Marketing Department"),
})

predef_ad_query_schema = api.model('PredefinedAdQuery', {
    'query': fields.String(required=True, description='The query text to search for predefined ads', example="What is the ad most related to oranges?"),
    'n_results': fields.Integer(required=True, default=1, description='Number of results to return', example=1)
})

class Predef_ad_schema(object):
    id:int
    description:str
    imgb64:str
    source:str = None  # Optional field, can be None

class Predef_ad_query_schema(object):
    query:str
    n_results:int

@api.route('/predef/',
           doc={'description':'Add or Update predefined ads. JPEG images are supported.'}
           )
class PredefAdResource(Resource):
    @api.response(200, 'Success')
    @api.response(400, 'Invalid Parameters or not found')
    @api.response(500, 'Accepted but it could not be processed/recovered')    
    @api.expect(predef_ad_schema, validate=True, description='Add/Update predefined ads or post new ones.')
    def post(self):
        data = api.payload
        server = AseServerMetadata()

        # process the image_file as needed
        image_id = data.get('id', None)
        if image_id is None:
            # If no ID is provided, generate a new one
            image_id = server.get_ase_img_id()

        image_description = data.get('description', None)
        img_b64 = data.get('imgb64',None)
        img_source = data.get('source', None)

        if not img_b64:
            return {"error": "imgb64 field is required"}, 400
        
        image=None
        try:
            img_bytes = base64.b64decode(img_b64)
            image = Image.open(io.BytesIO(img_bytes))
        except Exception as e:
            return {"error": f"Invalid base64 image: {e}"}, 400

        image_format = image.format  # This will be 'JPEG', 'PNG', etc.
        if image_format not in ['JPEG']:
            return {"error": "Unsupported image format. Only JPEG is allowed."}, 400
        

        try:
            if server.chromadb_exists(image_id):
                server.chromadb_update(image_id, image_description, image, img_source)
            else:
                server.chromadb_add(image_id,image_description, image, img_source)    
        except Exception as e:
            logger.error(f"Error while adding/updating predefined ad: {e}")
            return {"error": "Failed to add/update predefined ad"}, 500
        
        return {"message": "Success"}, 200

@api.route('/predef/<string:id>',
           doc={'description':'It gets or removes the predefined ad with the given ID.'}
           )
@api.param('id', 'The unique identifier of the predefined ad to be get or removed')
class PredefAdResourceDeleteGet(Resource):
    @api.response(200, 'Success')
    @api.response(404, 'Not found')
    @api.response(500, 'Accepted but it could not be processed')    
    def delete(self,id):        
        try:
            server = AseServerMetadata()
            if not server.chromadb_exists(id):
                return {"error": "Predefined ad not found"}, 404
            server.chromadb_remove(id)

        except Exception as e:
            return {"error": f" {e}"}, 500
        
        return {"message": "Success"}, 200

    @api.response(200, 'Success')
    @api.response(404, 'Not found')
    @api.response(500, 'Accepted but it could not be recovered')    
    @api.marshal_with(predef_ad_schema, description='Predefined ad details (Base64-encoded image).')
    def get(self,id):                               
        server = AseServerMetadata()
        item = Predef_ad_schema()
        if not server.chromadb_exists(id):
            logger.error(f"[ASE-Chromadb] Predefined ad with ID {id} not found.")
            item.description = f"Predefined ad with ID {id} not found."
            return item, 404
        item = None
        try:        
            results=server.chromadb_get(id)
            if not results:
                item.description = f"Predefined ad with ID {id} not found."
                return item, 404
                
            if 'metadatas' not in results or 'ids' not in results :
                item.description=f"[ASE-Chromadb Result] 'metadatas' or 'ids' not found in results: {results}"
                logger.error(f"[ASE-Chromadb Result] 'metadatas' or 'ids' not found in results: {results}")
                return {"error": "Incomplete Response from the Vector DB"}, 500

            ids = results.get('ids',[])
            metadatas = results.get('metadatas',[])

            for query_index, (id_list, metadata_list) in enumerate (zip(ids, metadatas)):
                for doc_index, doc_id in enumerate(id_list):
                    id_int = None
                    try:
                        id_int = int(doc_id)
                    except Exception as e:
                        continue # when id is not int, discard from result and move to the next one
                    
                    logger.error("Step 7. ")
                    # Get the metadata for the document    
                    doc_metadata = metadata_list #metadata_list is the dictionary of metadata for the document
                    if doc_metadata is None:
                        logger.error(f"[ASE-Chromadb Result] Metadata for ID {id_int} is None.")
                        item.description = f"Metadata for ID {id_int} is None."
                        return item, 404
                    

                    description = doc_metadata.get('description',None)
                    img_path = doc_metadata.get('img_path',None)
                    source = doc_metadata.get('source', None)
                    # Get the image from the server

                    img = server.get_image_file_from_path(img_path)
                    img_b64 = None
                    if img is not None:
                        buffered = io.BytesIO()                        
                        img.save(buffered, format="JPEG")
                        img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    # Check if all required fields are present
                    # and add to the records list
                    if img_b64 is not None and id_int is not None and description is not None:
                        item = Predef_ad_schema()
                        item.id = id_int
                        item.description = description
                        item.source = source if source else None
                        item.imgb64 = img_b64                        
                    else:
                        logger.error(f"[ASE-Chromadb Result] Incomplete Record. id: {id_int} description: {description} image_path: {img_path}")
                        item.description = f"Incomplete Record. id: {id_int} description: {description} image_path: {img_path}"
        except Exception as e:
            item = Predef_ad_schema()
            item.description=f"Error: {e}"
            return item, 500

        return item, 200


@api.route('/predef/query',
           doc={'description':'Query predefined ads. It returns the most similar predefined ads based on the query text.'}
           )
class PredefAdResourceQuery(Resource):
    @api.response(200, 'Success')
    @api.response(404, 'No content found for the query')
    @api.response(500, 'Accepted but it could not be processed/recovered')    
    @api.expect(predef_ad_query_schema, validate=True, description='Query the catalog and return the most similar .')
    @api.marshal_list_with(predef_ad_schema, description='List of predefined ads that match the query (Base64-encoded image).')
    def post(self):
        data = api.payload
        
        # process the image_file as needed
        query = data.get('query', None)
        n_results = data.get('n_results', 1)
        if not query:
            return {"error": "query field is required"}, 400

        records=[]                
        server = AseServerMetadata()
        try:
            results=server.chromadb_querytxt(query, n_results=n_results)
            if results is None or len(results) == 0:
                return {"error": "No results found"}, 404

            if 'metadatas' not in results or 'ids' not in results:
                logger.error(f"[ASE-Chromadb Result] 'metadatas' or 'ids' not found in results: {results}")
                return {"error": "Incomplete Response from the Vector DB"}, 500

            ids = results.get('ids',[])
            metadatas = results.get('metadatas',[])

            for query_index, (id_list, metadata_list) in enumerate (zip(ids, metadatas)):
                for doc_index, doc_id in enumerate(id_list):
                    id_int = None
                    try:
                        id_int = int(doc_id)
                    except Exception as e:
                        continue # when id is not int, discard from result and move to the next one

                    # Get the metadata for the document    
                    doc_metadata = metadata_list[doc_index]                    
                    description = doc_metadata.get('description',None)
                    img_path = doc_metadata.get('img_path',None)
                    img_source = doc_metadata.get('source', None)
                    # Get the image from the server
                    img = server.get_image_file_from_path(img_path)
                    img_b64 = None
                    if img is not None:
                        buffered = io.BytesIO()
                        img.save(buffered, format="JPEG")
                        img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    # Check if all required fields are present
                    # and add to the records list
                    if img_b64 is not None and id_int is not None and description is not None:
                        item = Predef_ad_schema()
                        item.id = id_int
                        item.description = description
                        item.imgb64 = img_b64
                        item.source = img_source if img_source else None
                        records.append(item)
                    else:
                        logger.error(f"[ASE-Chromadb Result] Incomplete Record. id: {id_int} description: {description} image_path: {img_path}")

        except Exception as e:
            logger.error(f"Error while querying predefined ad: {e}")
            return {"error": "Failed to query predefined ad"}, 500
        
        return records, 200
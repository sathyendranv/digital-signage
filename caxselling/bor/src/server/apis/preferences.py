from flask_restx import Namespace, Resource, fields
from database.version import ServerEnvironment
from database.preferences_manager import PreferencesManager
import requests
import re
import io
from flask import send_file
import base64
from PIL import Image

api = Namespace('BOR - Preferences & Guidelines', description='Preferences and Guidelines Operations')

# Schema
preferences_request_sch_ads = api.model('Preferences_request_ads', {
    'enable_logo': fields.Boolean(required=True, default=True, description="Decide whether to enable the logo in ads.", example=True),
    'logo_halign': fields.String(required=False, default="left", description="Logo horizontal alignment (left, center, or right)", example="left", enum=["left", "center", "right"]),
    'logo_valign': fields.String(required=False, default="top", description="Logo vertical alignment (top, middle, or bottom)", example="top", enum=["top", "middle", "bottom"]),
    'logo_percentage': fields.Float(required=False, default=15, description="Logo proportion", example=15.0, min=0.0, max=100.0),
    'logo_margin_px': fields.Integer(required=False, default=10, description="Margin separation in px between the logo and border", example=10, min=0),

    'enable_slogan_definition': fields.Boolean(required=True, default=True, description="Decide whether to enable the slogan definition in ads.", example=True),
    'slogan_text': fields.String(required=False, default="Your Slogan Here", description="Slogan text", example="Your Slogan Here"),
    'slogan_text_color': fields.String(required=False, default="black", description="Slogan text color (Named color from PIL -ImageColor-)", example="blue"),
    'slogan_font_size': fields.Integer(required=False, default=18, description="Slogan font size", example=20, min= 10, max=100),
    'slogan_halign': fields.String(required=False, default="right", description="Slogan horizontal alignment (left, center, or right)", example="center", enum=["left", "center", "right"]),
    'slogan_valign': fields.String(required=False, default="bottom", description="Slogan vertical alignment (top, middle, or bottom)", example="bottom", enum=["top", "middle", "bottom"]),
    'slogan_marperc_from_border': fields.Float(required=False, default=5.0, description="Slogan margin percentage from the border", example=5.0, min=0),
    'slogan_line_width': fields.Integer(required=False, default=20, description="Slogan line width in px", example=20, min=5),

    'enable_price': fields.Boolean(required=True, default=True, description="Decide whether to enable the price in ads.", example=True),
    'price_text_color': fields.String(required=False, default="black", description="Price text color (Named color from PIL -ImageColor-)", example="black"),
    'price_font_size': fields.Integer(required=False, default=24, description="Price font size", example=24, min=10, max=100),
    'price_line_width': fields.Integer(required=False, default=5, description="Price line width", example=5, min=5),
    'price_in_circle': fields.Boolean(required=False, default=True, description="Decide whether to put the price in a circle.", example=True),
    'price_circle_color': fields.String(required=False, default="black", description="Price circle color (Named color from PIL -ImageColor-)", example="white"),
    'price_halign': fields.String(required=False, default="right", description="Price horizontal alignment (left, center, or right)", example="right", enum=["left", "center", "right"]),
    'price_valign': fields.String(required=False, default="bottom", description="Price vertical alignment (top, middle, or bottom)", example="top", enum=["top", "middle", "bottom"]),
    'price_marperc_from_border': fields.Float(required=False, default=10.0, description="Price margin percentage from the border", example=10.0, min=0),

    'enable_promotional_text': fields.Boolean(required=True, default=True, description="Decide whether to enable the promotional text in ads.", example=True),
    'promo_text': fields.String(required=False, default="Promo Text", description="Promotional text", example="Promo Text"),
    'promo_text_color': fields.String(required=False, default="white", description="Promotional text color (Named color from PIL -ImageColor-)", example="black"),
    'promo_font_size': fields.Integer(required=False, default=20, description="Promotional text font size", example=20, min=10, max=100),
    'promo_line_width': fields.Integer(required=False, default=10, description="Promotional text line width", example=10, min=5),
    'promo_rect_color': fields.String(required=False, default="black", description="Promotional text rectangle color (Named color from PIL -ImageColor-)", example="red"),
    'promo_rect_padding': fields.Integer(required=False, default=10, description="Promotional text rectangle padding in px", example=10, min=0),
    'promo_rect_radius': fields.Integer(required=False, default=20, description="Promotional text rectangle radius in px", example=20, min=0),
    'promo_halign': fields.String(required=False, default="left", description="Promotional text horizontal alignment (left, center, or right)", example="left", enum=["left", "center", "right"]),
    'promo_valign': fields.String(required=False, default="top", description="Promotional text vertical alignment (top, middle, or bottom)", example="top", enum=["top", "middle", "bottom"]),
    'promo_marperc_from_border': fields.Float(required=False, default=10.0, description="Promotional text margin percentage from the border", example=10.0, min=0),

    'enable_frame': fields.Boolean(required=True, default=True, description="Decide whether to enable the frame in ads.", example=True),
    'frame_marperc_from_border': fields.Float(required=False, default=5.0, description="Frame margin percentage from the border", example=5.0, min=0),

    'query_device': fields.String(required=True, default="GPU", description="Requested device to process the ad", example="desktop", enum=["CPU", "GPU", "NPU"]),
    'query_complement': fields.String(required=True, default="8k", description="Complementary specification to be added to the ad query", example="8K"),
    'service_path': fields.String(required=True, default="", description="Service path to query or generate the ad", example="/aig/minf"),
})

preferences_request_sch_digsig = api.model('Preferences_request_digsig', {
    'min_time_between_adsubmission': fields.Integer(required=True, default=60, description="Minimum time in seconds between ad submissions", example=60, min=30),
    'output_sequence': fields.String(required=True, default="[PREDEFINED,DYNAMIC,PREDEFINED]", description="Number and type of ads to generate and submit in the output", example="[PREDEFINED,DYNAMIC,PREDEFINED]"),
    'output_suffix': fields.String(required=True, default="_output", description="Suffix to add to the topic name to push the output (Only letters, numbers, and '_')", example="_output"),
    'output_add_animation': fields.Boolean(required=True, default=True, description="Decide whether to add animation as an extra to the output", example=True),
    'output_animation_min_ms_per_img': fields.Integer(required=True, default=1000, description="Minimum milliseconds per image in the animation", example=1000, min=500),   
    'default_concept': fields.String(required=True, default="Healthy food", description="Default concept for a topic when nothing is defined", example="healthy food"),
    'use_default_ad_when_emptyresult': fields.Boolean(required=True, default=True, description="Decide whether to use the default ad when no results are found", example=True),
})

preferences_request_sch_price_endpoint = api.model('Preferences_request_price_endpoint', {    
    'endpoint': fields.String(required=True, default="http://localhost:5014/bor/price", description="Endpoint for the price service", example="http://localhost:5014/bor/price"),
    'pricetag': fields.String(required=True, default="price", description="Tag indicating the price in the JSON response from the endpoint", example="price"),
    'unittag': fields.String(required=True, default="unit", description="Tag indicating the unit related to the price in the JSON response from the endpoint", example="unit"),
    'gral_percentage_discount': fields.Float(required=True, default=1.0, description="General percentage discount for all product prices", example=1.0, min=0.0, max=100.0),
})

preferences_request_sch = api.model('Preferences_request', {
    'predefined_ads': fields.Nested(preferences_request_sch_ads, required=True, description="Preferences for predefined ads", example={
        "enable_logo": True,
        "logo_halign": "left",
        "logo_valign": "top",
        "logo_percentage": 15.0,
        "logo_margin_px": 10,
        "enable_slogan_definition": True,
        "slogan_text": "Your Slogan Here",
        "slogan_text_color": "black",
        "slogan_font_size": 18,
        "slogan_halign": "right",
        "slogan_valign": "bottom",
        "slogan_marperc_from_border": 5.0,
        "slogan_line_width": 20,
        "enable_price": True,
        "price_text_color": "black",
        "price_font_size": 24,
        "price_line_width": 5,
        "price_in_circle": True,
        "price_circle_color": "white",
        "price_halign": "right",
        "price_valign": "top",
        "price_marperc_from_border": 10.0,
        "enable_promotional_text": True,
        "promo_text": "Promo Text",
        "promo_text_color": "black",
        "promo_font_size": 20,
        "promo_line_width": 10,
        "promo_rect_color": "red",
        "promo_rect_padding": 10,
        "promo_rect_radius": 20,
        "promo_halign": "left",
        "promo_valign": "top",
        "promo_marperc_from_border": 10.0,
        "enable_frame": True,
        "frame_marperc_from_border": 5.0,
        "query_device": "GPU",
        "query_complement": "8k",
        "service_path": "/ase/predef/query/ad"
    }),
    'dynamic_ads': fields.Nested(preferences_request_sch_ads, required=True, description="Preferences for dynamic ads", example={
        "enable_logo": True,
        "logo_halign": "left",
        "logo_valign": "top",
        "logo_percentage": 15.0,
        "logo_margin_px": 10,
        "enable_slogan_definition": True,
        "slogan_text": "Your Slogan Here",
        "slogan_text_color": "black",
        "slogan_font_size": 18,
        "slogan_halign": "right",
        "slogan_valign": "bottom",
        "slogan_marperc_from_border": 5.0,
        "slogan_line_width": 20,
        "enable_price": True,
        "price_text_color": "black",
        "price_font_size": 24,
        "price_line_width": 5,
        "price_in_circle": True,
        "price_circle_color": "white",
        "price_halign": "right",
        "price_valign": "top",
        "price_marperc_from_border": 10.0,
        "enable_promotional_text": True,
        "promo_text": "Promo Text",
        "promo_text_color": "black",
        "promo_font_size": 20,
        "promo_line_width": 10,
        "promo_rect_color": "red",
        "promo_rect_padding": 10,
        "promo_rect_radius": 20,
        "promo_halign": "left",
        "promo_valign": "top",
        "promo_marperc_from_border": 10.0,
        "enable_frame": True,
        "frame_marperc_from_border": 5.0,
        "query_device": "GPU",
        "query_complement": "8k",
        "service_path": "/aig/minf"
    }),
    'digital_signage': fields.Nested(preferences_request_sch_digsig, required=True, description="Preferences for digital signage", example={
        "min_time_between_adsubmission": 60,
        "output_sequence": "[PREDEFINED,DYNAMIC,PREDEFINED]",
        "output_suffix": "_output",
        "output_add_animation": True,
        "output_animation_min_ms_per_img": 1000,
        "default_concept": "Healthy food",
        "use_default_ad_when_emptyresult": True
    }),
    'price': fields.Nested(preferences_request_sch_price_endpoint, required=True, description="Preferences for price endpoint", example={
        "endpoint": "http://localhost:5014/bor/price",
        "pricetag": "price",
        "unittag": "unit",
        "gral_percentage_discount": 1.0
    }),
})

preferences_testrequest_sch = api.model('Preferences_test_request', {
    'price': fields.String(required=True, default="5.34 $/lb", description="Price and unit to show in the ad", example="5.34 $/lb"),    
    'predefined_ads': fields.Boolean(required=True, default=True, description="Decide whether to use predefined ad preferences (TRUE) or dynamic ad preferences (FALSE) for testing", example=True),
})

# Object
class Preferences_request_sch_ads(object):
    enabe_logo: bool
    logo_halign: str
    logo_valign: str
    logo_percentage: float 
    logo_margin_px: int
    enable_slogan_definition: bool
    slogan_text: str
    slogan_text_color: str
    slogan_font_size: int
    slogan_halign: str
    slogan_valign: str
    slogan_marperc_from_border: float
    slogan_line_width: int
    enable_price: bool
    price_text_color: str
    price_font_size: int
    price_line_width: int
    price_in_circle: bool
    price_circle_color: str
    price_halign: str
    price_valign: str
    price_marperc_from_border: float
    enable_promotional_text: bool
    promo_text: str
    promo_text_color: str
    promo_font_size: int
    promo_line_width: int
    promo_rect_color: str
    promo_rect_padding: int
    promo_rect_radius: int
    promo_halign: str
    promo_valign: str
    promo_marperc_from_border: float
    enable_frame: bool
    frame_marperc_from_border: float
    query_device:str
    query_complement: str
    service_path: str

class Preferences_request_sch_digsig(object):
    min_time_between_adsubmission: int
    output_sequence: str
    output_suffix: str
    output_add_animation: bool
    default_concept: str
    use_default_ad_when_emptyresult: bool

class Preferences_request_sch_price_endpoint(object):
    endpoint: str
    pricetag: str
    unittag: str
    gral_percentage_discount: float

class Preferences_request_sch(object):
    predefined_ads: Preferences_request_sch_ads
    dynamic_ads: Preferences_request_sch_ads
    digital_signage: Preferences_request_sch_digsig
    price: Preferences_request_sch_price_endpoint

class Preferences_testrequest_sch(object):
    price: str
    predefined_ads: bool
    
@api.route('/pref_upd/',
           doc={"description":"It updates the preferences and guidelines according to the indicated parameters."
                })
class PreferencesManagement(Resource):
    @api.response(200, 'Success')
    @api.response(400, 'Bad Request - Invalid input data')
    @api.response(500, 'Accepted but it could not be processed/recovered')    
    @api.expect(preferences_request_sch, validate=True, description="It expects A JSON document with the preferences and guidelines to rule the BOR Server.")
    def post(self):
        data=api.payload
        if data is None or not isinstance(data,dict):
            return {"message": "Invalid input data format. Expected a JSON object."}, 400

        prefmanager = PreferencesManager()

        # Predefined Ads    
        predefined_ads = data.get(PreferencesManager.CATEGORY_PREDEFINED_ADS, {})        
        colorlist = prefmanager.get_color_list()
        if PreferencesManager.AD_SLOGAN_TEXT_COLOR in predefined_ads:
            tmpcolor = predefined_ads[PreferencesManager.AD_SLOGAN_TEXT_COLOR]
            if not PreferencesManager.is_color_valid(tmpcolor):                
                return {"message": f"Invalid color '{tmpcolor}' for {PreferencesManager.AD_SLOGAN_TEXT_COLOR}. Choose one of the following ones: {colorlist}"}, 400
        
        if PreferencesManager.AD_PRICE_TEXT_COLOR in predefined_ads:
            tmpcolor = predefined_ads[PreferencesManager.AD_PRICE_TEXT_COLOR]
            if not PreferencesManager.is_color_valid(tmpcolor):                
                return {"message": f"Invalid color '{tmpcolor}' for {PreferencesManager.AD_PRICE_TEXT_COLOR}. Choose one of the following ones: {colorlist}"}, 400
        
        if PreferencesManager.AD_PRICE_CIRCLE_COLOR in predefined_ads:
            tmpcolor = predefined_ads[PreferencesManager.AD_PRICE_CIRCLE_COLOR]
            if not PreferencesManager.is_color_valid(tmpcolor):                
                return {"message": f"Invalid color '{tmpcolor}' for {PreferencesManager.AD_PRICE_CIRCLE_COLOR}. Choose one of the following ones: {colorlist}"}, 400
        
        if PreferencesManager.AD_PROMO_TEXT_COLOR in predefined_ads:
            tmpcolor = predefined_ads[PreferencesManager.AD_PROMO_TEXT_COLOR]
            if not PreferencesManager.is_color_valid(tmpcolor):                
                return {"message": f"Invalid color '{tmpcolor}' for {PreferencesManager.AD_PROMO_TEXT_COLOR}. Choose one of the following ones: {colorlist}"}, 400        

        if PreferencesManager.AD_PROMO_RECT_COLOR in predefined_ads:
            tmpcolor = predefined_ads[PreferencesManager.AD_PROMO_RECT_COLOR]
            if not PreferencesManager.is_color_valid(tmpcolor):                
                return {"message": f"Invalid color '{tmpcolor}' for {PreferencesManager.AD_PROMO_RECT_COLOR}. Choose one of the following ones: {colorlist}"}, 400    

        if PreferencesManager.AD_QUERY_DEVICE in predefined_ads:
            query_device = predefined_ads[PreferencesManager.AD_QUERY_DEVICE]
            if query_device not in ["CPU", "GPU", "NPU"]:
                return {"message": f"Invalid query device '{query_device}'. Choose one of the following ones: ['CPU', 'GPU', 'NPU']"}, 400

        if PreferencesManager.AD_QUERY_COMPLEMENT in predefined_ads:
            query_complement = predefined_ads[PreferencesManager.AD_QUERY_COMPLEMENT]
            if not isinstance(query_complement, str) or not query_complement or len(query_complement.strip()) == 0:
                return {"message": f"Invalid query complement '{query_complement}'. It should be a non-empty string."}, 400            
            
        # Dynamic Ads
        dynamic_ads = data.get(PreferencesManager.CATEGORY_DYNAMIC_ADS, {})
        if PreferencesManager.AD_SLOGAN_TEXT_COLOR in dynamic_ads:
            tmpcolor = dynamic_ads[PreferencesManager.AD_SLOGAN_TEXT_COLOR]
            if not PreferencesManager.is_color_valid(tmpcolor):                
                return {"message": f"Invalid color '{tmpcolor}' for {PreferencesManager.AD_SLOGAN_TEXT_COLOR}. Choose one of the following ones: {colorlist}"}, 400
        
        if PreferencesManager.AD_PRICE_TEXT_COLOR in dynamic_ads:
            tmpcolor = dynamic_ads[PreferencesManager.AD_PRICE_TEXT_COLOR]
            if not PreferencesManager.is_color_valid(tmpcolor):                
                return {"message": f"Invalid color '{tmpcolor}' for {PreferencesManager.AD_PRICE_TEXT_COLOR}. Choose one of the following ones: {colorlist}"}, 400
        
        if PreferencesManager.AD_PRICE_CIRCLE_COLOR in dynamic_ads:
            tmpcolor = dynamic_ads[PreferencesManager.AD_PRICE_CIRCLE_COLOR]
            if not PreferencesManager.is_color_valid(tmpcolor):                
                return {"message": f"Invalid color '{tmpcolor}' for {PreferencesManager.AD_PRICE_CIRCLE_COLOR}. Choose one of the following ones: {colorlist}"}, 400
        
        if PreferencesManager.AD_PROMO_TEXT_COLOR in dynamic_ads:
            tmpcolor = dynamic_ads[PreferencesManager.AD_PROMO_TEXT_COLOR]
            if not PreferencesManager.is_color_valid(tmpcolor):                
                return {"message": f"Invalid color '{tmpcolor}' for {PreferencesManager.AD_PROMO_TEXT_COLOR}. Choose one of the following ones: {colorlist}"}, 400        

        if PreferencesManager.AD_PROMO_RECT_COLOR in dynamic_ads:
            tmpcolor = dynamic_ads[PreferencesManager.AD_PROMO_RECT_COLOR]
            if not PreferencesManager.is_color_valid(tmpcolor):                
                return {"message": f"Invalid color '{tmpcolor}' for {PreferencesManager.AD_PROMO_RECT_COLOR}. Choose one of the following ones: {colorlist}"}, 400

        if PreferencesManager.AD_QUERY_DEVICE in dynamic_ads:
            query_device = dynamic_ads[PreferencesManager.AD_QUERY_DEVICE]
            if query_device not in ["CPU", "GPU", "NPU"]:
                return {"message": f"Invalid query device '{query_device}'. Choose one of the following ones: ['CPU', 'GPU', 'NPU']"}, 400

        if PreferencesManager.AD_QUERY_COMPLEMENT in dynamic_ads:
            query_complement = dynamic_ads[PreferencesManager.AD_QUERY_COMPLEMENT]
            if not isinstance(query_complement, str) or not query_complement or len(query_complement.strip()) == 0:
                return {"message": f"Invalid query complement '{query_complement}'. It should be a non-empty string."}, 400            

        # Digital Signage
        digital_signage = data.get(PreferencesManager.CATEGORY_DIGITAL_SIGNAGE, {})
        if PreferencesManager.DS_OUTPUT_SEQUENCE in digital_signage:
            output_sequence = digital_signage[PreferencesManager.DS_OUTPUT_SEQUENCE]
            if not isinstance(output_sequence, str):
                return {"message": f"Invalid output sequence format. Expected a string."}, 400
            if not PreferencesManager.is_only_predefined_or_dynamic(output_sequence):
                return {"message": f"Invalid output sequence '{output_sequence}'. It should be a comma-separated list of 'PREDEFINED' and 'DYNAMIC'."}, 400

        if PreferencesManager.DS_OUTPUT_SUFFIX in digital_signage:
            output_suffix = digital_signage[PreferencesManager.DS_OUTPUT_SUFFIX]             
            if not isinstance(output_suffix, str):
                return {"message": f"Invalid output suffix '{output_suffix}'. It should be a valid string suffix (Only letters, numbers, or _)."}, 400

            if re.search(r'[^a-zA-Z0-9_]', output_suffix):
                return {"message": f"Invalid output suffix '{output_suffix}'. It should be a valid string suffix (Only letters, numbers, or _)."}, 400
            
        rdo, message = prefmanager.update_preferences(data)
        
        if rdo:
            return {"message": "Preferences updated successfully."}, 200
        else:
            return {"message": f"Error updating preferences: {message}"}, 500

@api.route('/pref_read/',
           doc={"description":"It returns the current preferences and guidelines."
                })
class PreferencesManagementGet(Resource):
    @api.response(200, 'Success')
    @api.response(500, 'Accepted but it could not be processed/recovered')    
    @api.marshal_with(preferences_request_sch, code=200, description="Returns the current preferences and guidelines.")
    def get(self):
        prefmanager = PreferencesManager()

        return prefmanager.getAPreferencesCopy(), 200, {'Content-Type': 'application/json'}

@api.route('/prefm/test',
           doc={"description":"It tests layout calibration based on preferences using predefined ads. It uses the default concept to drive the search.",
                "produces": ['image/jpeg']
                })
class PreferencesManagement(Resource):
    @api.response(200, 'Success')
    @api.response(400, 'Bad Request - Invalid input data')
    @api.response(500, 'Accepted but it could not be processed/recovered')    
    @api.expect(preferences_testrequest_sch, validate=True, description="It expects A JSON document with the price and unit to show in the ad.")
    def post(self):
        data=api.payload
        if data is None or not isinstance(data,dict):
            return {"message": "Invalid input data format. Expected a JSON object."}, 400

        prefmanager = PreferencesManager()
        
        aig_protocol = ServerEnvironment.get_aig_server_protocol()
        aig_host = ServerEnvironment.get_aig_server_host()
        aig_port = ServerEnvironment.get_aig_server_port()
        preferences:dict = prefmanager.getAPreferencesCopy()
        if preferences is None or not isinstance(preferences, dict):
            return {"message": "Invalid preferences format. Expected a JSON object."}, 400

        predefined_ads = preferences.get(PreferencesManager.CATEGORY_PREDEFINED_ADS, {})
        dynamic_ads = preferences.get(PreferencesManager.CATEGORY_DYNAMIC_ADS, {})
        ds = preferences.get(PreferencesManager.CATEGORY_DIGITAL_SIGNAGE, {})
        cprice = preferences.get(PreferencesManager.CATEGORY_PRICE, {})        

        #Data to receive
        input_query=ds.get(PreferencesManager.DS_DEFAULT_CONCEPT, "Healthy food")
        input_price=data.get("price", "5.34 $/lb")  # Default price if not provided
        input_usepredefined_ads = data.get("predefined_ads", True)  # Default to True if not provided

        ad_preferences = None
        if input_usepredefined_ads:
            ad_preferences = predefined_ads
        else:
            ad_preferences = dynamic_ads

        json={}
        json["query"] = input_query
        json["n_results"] = 1
        json["use_default_ad_onempty"] = ds.get(PreferencesManager.DS_USE_DEFAULT_AD_WHEN_EMPTYRESULT, True)

        if ad_preferences.get(PreferencesManager.AD_ENABLE_PRICE, True):
            # The price is enabled
            price_details={}
            price_details["price"] = input_price
            price_details["align"] = ad_preferences.get(PreferencesManager.AD_PRICE_HALIGN, "center")
            price_details["valign"] = ad_preferences.get(PreferencesManager.AD_PRICE_VALIGN, "bottom")
            price_details["marperc_from_border"] = ad_preferences.get(PreferencesManager.AD_PRICE_MARPERF_FROM_BORDER, 10.0)
            price_details["font_size"] = ad_preferences.get(PreferencesManager.AD_PRICE_FONT_SIZE, 24)
            price_details["line_width"] = ad_preferences.get(PreferencesManager.AD_PRICE_LINE_WIDTH, 5)
            price_details["price_color"] = ad_preferences.get(PreferencesManager.AD_PRICE_TEXT_COLOR, "white")
            price_details["price_in_circle"] = ad_preferences.get(PreferencesManager.AD_PRICE_IN_CIRCLE, True)
            price_details["price_circle_color"] = ad_preferences.get(PreferencesManager.AD_PRICE_CIRCLE_COLOR, "black")
            json["price_details"] = price_details

        if ad_preferences.get(PreferencesManager.AD_ENABLE_PROMOTIONAL_TEXT, True):
            # The promotional text is enabled
            promo_details={}
            promo_details["promo_text"] = ad_preferences.get(PreferencesManager.AD_PROMO_TEXT, "Promo Text")
            promo_details["align"] = ad_preferences.get(PreferencesManager.AD_PROMO_HALIGN, "left")
            promo_details["valign"] = ad_preferences.get(PreferencesManager.AD_PROMO_VALIGN, "bottom")
            promo_details["marperc_from_border"] = ad_preferences.get(PreferencesManager.AD_PROMO_MARPERF_FROM_BORDER, 10.0)
            promo_details["font_size"] = ad_preferences.get(PreferencesManager.AD_PROMO_FONT_SIZE, 20)
            promo_details["line_width"] = ad_preferences.get(PreferencesManager.AD_PROMO_LINE_WIDTH, 10)
            promo_details["text_color"] = ad_preferences.get(PreferencesManager.AD_PROMO_TEXT_COLOR, "white")
            promo_details["rect_color"] = ad_preferences.get(PreferencesManager.AD_PROMO_RECT_COLOR, "red")
            promo_details["rect_padding"] = ad_preferences.get(PreferencesManager.AD_PROMO_RECT_PADDING, 10)
            promo_details["rect_radius"] = ad_preferences.get(PreferencesManager.AD_PROMO_RECT_RADIUS, 20)
            json["promo_details"] = promo_details
        
        if ad_preferences.get(PreferencesManager.AD_ENABLE_LOGO, True):
            # The logo is enabled
            logo_details={}
            logo_details["align"] = ad_preferences.get(PreferencesManager.AD_LOGO_HALIGN, "left")
            logo_details["valign"] = ad_preferences.get(PreferencesManager.AD_LOGO_VALIGN, "top")
            logo_details["logo_percentage"] = ad_preferences.get(PreferencesManager.AD_LOGO_PERCENTAGE, 15.0)
            logo_details["margin_px"] = ad_preferences.get(PreferencesManager.AD_LOGO_MARGIN_PX, 10)
            json["logo_details"] = logo_details

        if ad_preferences.get(PreferencesManager.AD_ENABLE_SLOGAN_DEFINITION, True):
            # The slogan is enabled
            slogan_details={}
            slogan_details["slogan_text"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_TEXT, "Your Slogan Here")
            slogan_details["align"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_HALIGN, "right")
            slogan_details["valign"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_VALIGN, "bottom")
            slogan_details["marperc_from_border"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_MARPERF_FROM_BORDER, 5.0)
            slogan_details["font_size"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_FONT_SIZE, 18)
            slogan_details["line_width"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_LINE_WIDTH, 20)
            slogan_details["text_color"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_TEXT_COLOR, "black")
            json["slogan_details"] = slogan_details

        if ad_preferences.get(PreferencesManager.AD_ENABLE_FRAME, True):
            # The frame is enabled
            frame_details={}
            frame_details["activate"] = True
            frame_details["marperc_from_border"] = ad_preferences.get(PreferencesManager.AD_FRAME_MARPERF_FROM_BORDER, 5.0)
            json["frame_details"] = frame_details
        
        url= f"{aig_protocol}{aig_host}:{aig_port}/ase/predef/query/firstad"

        try:
            response = requests.post(url, json=json, timeout=10)
            if response.status_code == 200:
                # Return the image directly
                buffered = io.BytesIO(response.content) #R eceives binary data
                buffered.seek(0) #Positioning at the start

                return send_file(buffered, mimetype='image/jpeg', download_name='test_preferences_image.jpg')
            else:
                return {"message": f"Error from AIG server ({url}): {response.text}"}, 500
        except requests.RequestException as e:
            return {"message": f"Error connecting to AIG server ({url}): {str(e)}"}, 500
        

@api.route('/prefm/test_animated',
           doc={"description":"It tests layout calibration based on preferences using predefined ads. It uses the default concept to drive the search. It returns an animated image using 3 predefined ads.",
                "produces": ['image/gif']
                })
class PreferencesManagement(Resource):
    @api.response(200, 'Success')
    @api.response(400, 'Bad Request - Invalid input data')
    @api.response(500, 'Accepted but it could not be processed/recovered')    
    @api.expect(preferences_testrequest_sch, validate=True, description="It expects A JSON document with the price and unit to show in the ad.")
    def post(self):
        data=api.payload
        if data is None or not isinstance(data,dict):
            return {"message": "Invalid input data format. Expected a JSON object."}, 400

        prefmanager = PreferencesManager()

        aig_protocol = ServerEnvironment.get_aig_server_protocol()
        aig_host = ServerEnvironment.get_aig_server_host()
        aig_port = ServerEnvironment.get_aig_server_port()
        
        preferences:dict = prefmanager.getAPreferencesCopy()
        if preferences is None or not isinstance(preferences, dict):
            return {"message": "Invalid preferences format. Expected a JSON object."}, 400

        predefined_ads = preferences.get(PreferencesManager.CATEGORY_PREDEFINED_ADS, {})
        dynamic_ads = preferences.get(PreferencesManager.CATEGORY_DYNAMIC_ADS, {})
        ds = preferences.get(PreferencesManager.CATEGORY_DIGITAL_SIGNAGE, {})
        cprice = preferences.get(PreferencesManager.CATEGORY_PRICE, {})        

        if predefined_ads is None or not isinstance(predefined_ads, dict):
            return {"message": "Invalid predefined ads format. Missing in the Preferences."}, 500
        if dynamic_ads is None or not isinstance(dynamic_ads, dict):
            return {"message": "Invalid dynamic ads format. Missing in the Preferences."}, 500
        if ds is None or not isinstance(ds, dict):
            return {"message": "Invalid digital signage preferences format. Missing in the Preferences."}, 500
        if cprice is None or not isinstance(cprice, dict):
            return {"message": "Invalid price preferences format. Missing in the Preferences."}, 500
        
        #Data to receive
        input_query=ds.get(PreferencesManager.DS_DEFAULT_CONCEPT, "Healthy food")
        input_price=data.get("price", "5.34 $/lb")  # Default price if not provided
        input_usepredefined_ads = data.get("predefined_ads", True)  # Default to True if not provided

        ad_preferences = None
        if input_usepredefined_ads:
            ad_preferences = predefined_ads
        else:
            ad_preferences = dynamic_ads

        json={}
        json["query"] = input_query
        json["n_results"] = 3
        json["use_default_ad_onempty"] = ds.get(PreferencesManager.DS_USE_DEFAULT_AD_WHEN_EMPTYRESULT, True)

        if ad_preferences.get(PreferencesManager.AD_ENABLE_PRICE, True):
            # The price is enabled
            price_details={}
            price_details["price"] = input_price
            price_details["align"] = ad_preferences.get(PreferencesManager.AD_PRICE_HALIGN, "center")
            price_details["valign"] = ad_preferences.get(PreferencesManager.AD_PRICE_VALIGN, "bottom")
            price_details["marperc_from_border"] = ad_preferences.get(PreferencesManager.AD_PRICE_MARPERF_FROM_BORDER, 10.0)
            price_details["font_size"] = ad_preferences.get(PreferencesManager.AD_PRICE_FONT_SIZE, 24)
            price_details["line_width"] = ad_preferences.get(PreferencesManager.AD_PRICE_LINE_WIDTH, 5)
            price_details["price_color"] = ad_preferences.get(PreferencesManager.AD_PRICE_TEXT_COLOR, "white")
            price_details["price_in_circle"] = ad_preferences.get(PreferencesManager.AD_PRICE_IN_CIRCLE, True)
            price_details["price_circle_color"] = ad_preferences.get(PreferencesManager.AD_PRICE_CIRCLE_COLOR, "black")
            json["price_details"] = price_details

        if ad_preferences.get(PreferencesManager.AD_ENABLE_PROMOTIONAL_TEXT, True):
            # The promotional text is enabled
            promo_details={}
            promo_details["promo_text"] = ad_preferences.get(PreferencesManager.AD_PROMO_TEXT, "Promo Text")
            promo_details["align"] = ad_preferences.get(PreferencesManager.AD_PROMO_HALIGN, "left")
            promo_details["valign"] = ad_preferences.get(PreferencesManager.AD_PROMO_VALIGN, "bottom")
            promo_details["marperc_from_border"] = ad_preferences.get(PreferencesManager.AD_PROMO_MARPERF_FROM_BORDER, 10.0)
            promo_details["font_size"] = ad_preferences.get(PreferencesManager.AD_PROMO_FONT_SIZE, 20)
            promo_details["line_width"] = ad_preferences.get(PreferencesManager.AD_PROMO_LINE_WIDTH, 10)
            promo_details["text_color"] = ad_preferences.get(PreferencesManager.AD_PROMO_TEXT_COLOR, "white")
            promo_details["rect_color"] = ad_preferences.get(PreferencesManager.AD_PROMO_RECT_COLOR, "red")
            promo_details["rect_padding"] = ad_preferences.get(PreferencesManager.AD_PROMO_RECT_PADDING, 10)
            promo_details["rect_radius"] = ad_preferences.get(PreferencesManager.AD_PROMO_RECT_RADIUS, 20)
            json["promo_details"] = promo_details
        
        if ad_preferences.get(PreferencesManager.AD_ENABLE_LOGO, True):
            # The logo is enabled
            logo_details={}
            logo_details["align"] = ad_preferences.get(PreferencesManager.AD_LOGO_HALIGN, "left")
            logo_details["valign"] = ad_preferences.get(PreferencesManager.AD_LOGO_VALIGN, "top")
            logo_details["logo_percentage"] = ad_preferences.get(PreferencesManager.AD_LOGO_PERCENTAGE, 15.0)
            logo_details["margin_px"] = ad_preferences.get(PreferencesManager.AD_LOGO_MARGIN_PX, 10)
            json["logo_details"] = logo_details

        if ad_preferences.get(PreferencesManager.AD_ENABLE_SLOGAN_DEFINITION, True):
            # The slogan is enabled
            slogan_details={}
            slogan_details["slogan_text"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_TEXT, "Your Slogan Here")
            slogan_details["align"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_HALIGN, "right")
            slogan_details["valign"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_VALIGN, "bottom")
            slogan_details["marperc_from_border"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_MARPERF_FROM_BORDER, 5.0)
            slogan_details["font_size"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_FONT_SIZE, 18)
            slogan_details["line_width"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_LINE_WIDTH, 20)
            slogan_details["text_color"] = ad_preferences.get(PreferencesManager.AD_SLOGAN_TEXT_COLOR, "black")
            json["slogan_details"] = slogan_details

        if ad_preferences.get(PreferencesManager.AD_ENABLE_FRAME, True):
            # The frame is enabled
            frame_details={}
            frame_details["activate"] = True
            frame_details["marperc_from_border"] = ad_preferences.get(PreferencesManager.AD_FRAME_MARPERF_FROM_BORDER, 5.0)
            json["frame_details"] = frame_details
        
        url= f"{aig_protocol}{aig_host}:{aig_port}{ad_preferences.get(PreferencesManager.AD_SERVICE_PATH)}"
        
        try:
            response = requests.post(url, json=json, timeout=10)

            if response.status_code != 200:
                return {"message": f"Error from AIG server ({url}): {response.text}"}, 500
            # Process the response to extract the animated image
            
            items = response.json()   
            image_list=[]        
            for item in items:
                img_bytes = base64.b64decode(item['imgb64'])
                image = Image.open(io.BytesIO(img_bytes))
                image_list.append(image)

            if len(image_list) == 0:
                return {"message": "No images returned from AIG server."}, 500
            
            # Return the image directly
            buffered = io.BytesIO()
            image_list[0].save(buffered, 
                               format="GIF", save_all=True, 
                               append_images=image_list[1:], duration=ds.get(PreferencesManager.DS_OUTPUT_ANIMATION_MIN_MS_PER_IMG, 1000), loop=0)            
            buffered.seek(0) #Positioning at the start

            return send_file(buffered, mimetype='image/gif', download_name='test_preferences_image_anim.gif')
        except requests.RequestException as e:
            return {"message": f"Error connecting to AIG server ({url}): {str(e)}"}, 500
        

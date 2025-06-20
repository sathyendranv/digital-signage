from datetime import datetime
from database.QueueManager import QueueItem
from database.preferences_manager import PreferencesManager
from database.version import ServerEnvironment
from PIL import Image
import requests
import json as jsonlib
import io
import time
import base64
import logging
logger = logging.getLogger(__name__)

class AddProcessingPolicy:
    @staticmethod
    def apply_policy(host:str=None,port:int=None,topic:str=None,item:QueueItem=None, gral_concept:str="Healthy food") -> list:
        """
        Default processing policy that returns an empty list.
        relateConcept is used to look for institutional ads related to the topic
        This means no additional processing is applied to the data.
        """
        if host is None or len(host) == 0:
            logger.error("[apply_policy] Host is None or empty.")
            return None
        if port is None or port <= 0:
            logger.error("[apply_policy] Port is None or invalid.")
            return None
        if topic is None or len(topic) == 0:
            logger.error("[apply_policy] Topic is None or empty.")
            return None
        if item is None:
            logger.warning("[apply_policy] No item provided to apply policy.")
            # If no item is provided, we can return an empty list or None
            return None
        
        related_items = None
        # Cross-selling items
        if item is not None:
            logger.warning(f"[Monitor] Processing item from queue: {item.label} with ID: {item.label_id} and Confidence: {item.confidence} Concept: {item.concept}")
            # Cross-selling items
            related_items = AddProcessingPolicy.look_for_crossselling_items(host, port, topic, item)

        # If no related items found, check PCA using day and hour
        if related_items is None or len(related_items) == 0:
            #Check PCA using day and hour (1. No item, 2. No related items -no associations or missing transactions in PCA-)
            related_items = AddProcessingPolicy.look_for_items_by_day_hour(host, port, topic)
        
        # If still no related items found, check PCA using day
        if related_items is None or len(related_items) == 0:
            #Check PCA using day (1. No item, 2. No related items, 3. No associations or missing transactions in PCA)
            related_items = AddProcessingPolicy.look_for_items_by_day(host, port, topic)

        # If still no related items found, return an empty list
        # All predefined using the topic concept
        if gral_concept is None or len(gral_concept) == 0:
            gral_concept = "Healthy food"  # Default concept if none provided

        # Preferences Manager
        prefManager = PreferencesManager()
        if prefManager is None:
            errorMessgage = "[apply_policy] Preferences Manager is not initialized."
            logger.error(errorMessgage)
            return None
                
        # Sequence and types
        output_sequence_draft=prefManager.getValue(PreferencesManager.CATEGORY_DIGITAL_SIGNAGE, PreferencesManager.DS_OUTPUT_SEQUENCE)
        osequence = prefManager.get_predefined_or_dynamic_output_list(output_sequence_draft)
        if osequence is None or len(osequence) == 0 or isinstance(osequence, list) is False:
            errorMessage = "[apply_policy] Output sequence is not defined."
            logger.error(errorMessage)
            return None
        
        predefined_number= osequence.count(PreferencesManager.DS_TYPE_PREDEFINED)
        dynamic_number= osequence.count(PreferencesManager.DS_TYPE_DYNAMIC)

        if predefined_number <= 0 and dynamic_number <= 0:
            errorMessage = "[apply_policy] No predefined or dynamic ads defined in the output sequence."
            logger.error(errorMessage)
            return None                   

        # Generate the sequence
        img_list=[]        
        related_item_used=0
        for img_type in osequence:
            input_query = None
            label_id = None

            if img_type == PreferencesManager.DS_TYPE_DYNAMIC:
                #Dynamic
                query_complement = prefManager.getValue(PreferencesManager.CATEGORY_DYNAMIC_ADS, PreferencesManager.AD_QUERY_COMPLEMENT)       
                if related_items is None:                                 
                    input_query = f"{gral_concept}, {query_complement}"                    
                else:
                    idx = related_item_used % len(related_items)
                    related_item_used += 1
                    input_query = ""                

                    label_id = related_items[idx].label_id
                    input_query += f" {related_items[idx].label}. {query_complement}"


                rdo:str=AddProcessingPolicy.gen_dynamic_ad(prefManager, input_query, label_id)
                
                if rdo is not None and isinstance(rdo, str) and len(rdo) > 0:
                    img_list.append(rdo)                

            else:
                query_complement = prefManager.getValue(PreferencesManager.CATEGORY_PREDEFINED_ADS, PreferencesManager.AD_QUERY_COMPLEMENT)       
                if related_items is None:                                 
                    input_query = f"{gral_concept}. {query_complement}"
                else:
                    input_query = "Benefits of "
                    first_item = True
                    for oneitem in related_items:                    
                        if first_item:
                            first_item = False
                            label_id = oneitem.label_id
                        else:
                            input_query += ","

                        input_query += f" {oneitem.label}"                
                    input_query += f". {query_complement}"

                #Predefined
                rdo:list=AddProcessingPolicy.gen_predefined_ad(prefManager, input_query, label_id, 1)
                if rdo is not None and isinstance(rdo, list) and len(rdo) > 0:
                    img_list.extend(rdo)

        # Check preferences for GIF creation
        animatedgift=prefManager.getValue(PreferencesManager.CATEGORY_DIGITAL_SIGNAGE, PreferencesManager.DS_OUTPUT_ADD_ANIMATION)
        pduration=prefManager.getValue(PreferencesManager.CATEGORY_DIGITAL_SIGNAGE, PreferencesManager.DS_OUTPUT_ANIMATION_MIN_MS_PER_IMG)
        if animatedgift and len(img_list) > 0:
            # Create animated GIF from the list of images
            gif_b64 = AddProcessingPolicy.create_animated_gif_from_imgb64list(img_list, pduration if pduration is not None and pduration > 1000 else 1000)
            if gif_b64 is not None and len(gif_b64) > 0:
                img_list.append(gif_b64)

        return img_list if len(img_list) > 0 else None
    
    @staticmethod    
    def gen_predefined_ad(preferences:PreferencesManager, input_query:str, label_id:str=None, nresults:int=1) -> list[str]:
        """
        Generate predefined ads and return them as a list of Images (Base64-encoded string). It uses label_id to get the price from the endpoint.
        If label_id is None, it will not include the price in the ad.
        """
        if nresults is None or nresults <= 1:
            nresults = 1

        xpreferences=preferences.getAPreferencesCopy()
        ad_preferences = xpreferences.get(PreferencesManager.CATEGORY_PREDEFINED_ADS,{})
        ds = xpreferences.get(PreferencesManager.CATEGORY_DIGITAL_SIGNAGE,{})
        
        if ad_preferences is None or len(ad_preferences) == 0:
            logger.warning("[gen_predefined_ad] No predefined ads configuration found in preferences.")
            return None
        if ds is None or len(ds) == 0:
            logger.warning("[gen_predefined_ad] No digital signage configuration found in preferences.")
            return None
        if input_query is None or len(input_query) == 0:
            logger.warning("[gen_predefined_ad] Input query is empty or None.")
            return None

        #Get item price, unit, and discount when defined
        price,unit,discount,promotional_text = AddProcessingPolicy.get_price_by_labelID(label_id) 
        input_price = None
        if price is not None:
            price_upd=price
            if discount is not None and discount > 0 and discount < 100:
                # Apply discount
                price_upd = price * (1 - discount / 100.0)

            input_price = f"{price_upd:.2f} {unit}"        

        # Prepare the JSON Request for the ad
        json={}
        json["query"] = input_query
        json["n_results"] = nresults
        json["use_default_ad_onempty"] = ds.get(PreferencesManager.DS_USE_DEFAULT_AD_WHEN_EMPTYRESULT, True)

        if ad_preferences.get(PreferencesManager.AD_ENABLE_PRICE, True) and input_price is not None:
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

            if promotional_text is not None and len(promotional_text) > 0:
                promo_details["promo_text"] = promotional_text # Priority to promotional text from the item
            else:
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

        service_path = ad_preferences.get(PreferencesManager.AD_SERVICE_PATH, "/ase/predef/query/ad")
        url= f"{ServerEnvironment.get_aig_server_protocol()}{ServerEnvironment.get_aig_server_host()}:{ServerEnvironment.get_aig_server_port()}{service_path}"
        img_list = []
        try:
            counter = 0
            max_retries = 3
            while counter < max_retries:
                res = requests.post(url, json=json)
                if res.status_code == 503: # Busy server
                    counter += 1
                    time.sleep(5) # Retry in 5 seconds
                else:
                    break #break the loop if not 503                

            if res.status_code != 200:
                logger.error(f"[gen_predefined_ad] Error generating predefined ad: {res.status_code} - {res.text}")
                logger.error(f"[gen_predefined_ad] JSON Request: {jsonlib.dumps(json)}")
                return None
            
            items = res.json()
            for item in items:
                if item is None or 'imgb64' not in item:
                    logger.warning("[gen_predefined_ad] Item is None or does not contain 'imgb64'.")
                    continue
                
                img_b64 = item['imgb64']
                if img_b64 is not None and len(img_b64) > 0:               
                    img_list.append(img_b64)
        except requests.RequestException as e:
            logger.error(f"[gen_predefined_ad] Error making request to AIG server ({url}): {e}")
            return None
        
        return img_list if len(img_list) > 0 else None

    @staticmethod    
    def gen_dynamic_ad(preferences:PreferencesManager, input_query:str, label_id:str=None) -> str:
        """
        Generate a dynamic ads and return it as a Base64-encoded string. It uses label_id to get the price from the endpoint.
        If label_id is None, it will not include the price in the ad.
        """

        xpreferences=preferences.getAPreferencesCopy()
        ad_preferences = xpreferences.get(PreferencesManager.CATEGORY_DYNAMIC_ADS,{})
        ds = xpreferences.get(PreferencesManager.CATEGORY_DIGITAL_SIGNAGE,{})
        
        if ad_preferences is None or len(ad_preferences) == 0:
            logger.warning("[gen_dynamic_ad] No predefined ads configuration found in preferences.")
            return None
        if ds is None or len(ds) == 0:
            logger.warning("[gen_dynamic_ad] No digital signage configuration found in preferences.")
            return None
        if input_query is None or len(input_query) == 0:
            logger.warning("[gen_dynamic_ad] Input query is empty or None.")
            return None

        #Get item price, unit, and discount when defined
        price,unit,discount,promotional_text = AddProcessingPolicy.get_price_by_labelID(label_id) 
        input_price = None
        if price is not None:
            price_upd=price
            if discount is not None and discount > 0 and discount < 100:
                # Apply discount
                price_upd = price * (1 - discount / 100.0)

            input_price = f"{price_upd:.2f} {unit}"        

        # Prepare the JSON Request for the ad
        json={}
        json["description"] = input_query
        json["device"] = "GPU"

        if ad_preferences.get(PreferencesManager.AD_ENABLE_PRICE, True) and input_price is not None:
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

            if promotional_text is not None and len(promotional_text) > 0:
                promo_details["promo_text"] = promotional_text # Priority to promotional text from the item
            else:
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

        service_path = ad_preferences.get(PreferencesManager.AD_SERVICE_PATH, "/aig/minf")
        url= f"{ServerEnvironment.get_aig_server_protocol()}{ServerEnvironment.get_aig_server_host()}:{ServerEnvironment.get_aig_server_port()}{service_path}"
        img_b64 = None
        
        max_retries = 3
        counter = 0
        try:
            while counter < max_retries:
               # Make the request to the AIG server
                res = requests.post(url, json=json)

                if res.status_code == 503: # Busy server
                    counter += 1
                    time.sleep(5) # Retry in 5 seconds
                else:
                    break #break the loop if not 503

            if res.status_code != 200:
                logger.error(f"[gen_dynamic_ad] Error generating dynamic ad: {res.status_code} - {res.text}")
                logger.error(f"[gen_dynamic_ad] JSON Request: {jsonlib.dumps(json)}")
                return None

            buffered = io.BytesIO(res.content) #Receives binary data
            buffered.seek(0) #Positioning at the start
            img_bytes = buffered.getvalue()
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        except requests.RequestException as e:
            
            logger.error(f"[gen_dynamic_ad] Error making request to AIG server ({url}): {e}")
            return None
        
        return img_b64 if img_b64 is not None and len(img_b64) > 0 else None

    @staticmethod
    def get_price_by_labelID(preferences:PreferencesManager,label_id:str=None) -> tuple[float,str,float,str]:
        """
        Get the price of an item by its label ID.
        This method can be extended to include more complex logic.
        """        
        if label_id is None or len(label_id) == 0:            
            return None, None, None, None
        
        xpreferences=preferences.getAPreferencesCopy()
        cprice:dict = xpreferences.get(PreferencesManager.CATEGORY_PRICE,{})
        if cprice is None or len(cprice) == 0:
            logger.warning("[get_price_by_labelID] No price configuration found in preferences.")
            return None, None, None, None
        
        price_endpoint=cprice.get('endpoint',None)
        price_tag=cprice.get('pricetag',None)
        price_unittag=cprice.get('unittag',None)
        price_gral_percentage_discount=cprice.get('gral_percentage_discount',0.0)

        url = f"{price_endpoint}/{label_id}"
        try:
            res = requests.get(url)
            if res.status_code != 200:
                logger.error(f"[get_price_by_labelID] Error getting price for label ID {label_id}: {res.status_code} - {res.text}")
                return None, None, None, None
            
            data = res.json()
            if price_tag not in data or price_unittag not in data:
                logger.error(f"[get_price_by_labelID] Price tag or unit tag not found in response for label ID {label_id}.")
                return None, None, None, None
            
            price = float(data[price_tag])
            unit = data[price_unittag]
            promotional_text = data.get("promotional_text", "")

            discount = price_gral_percentage_discount if price_gral_percentage_discount is not None else 0.0

            return price, unit, discount, promotional_text
        except requests.RequestException as e:
            logger.error(f"[get_price_by_labelID] Error making request to price endpoint ({url}): {e}")
            return 9.99,"$/lb",0.0,"" # To be implemented (price, unit, discount)

        
    
    @staticmethod
    def look_for_crossselling_items(host:str,port:int,topic:str,item:QueueItem) -> list[QueueItem]:
        """
        Look for related items based on the concept of the item. if no related items are found, it returns the item itself.
        None is returned when item, item.label_id, or item.label are None or empty.
        This method can be extended to include more complex logic.
        """
        if item is None or item.label_id is None or item.label is None or len(item.label) == 0:
            logger.warning("[Monitor] No item provided to look for related items.")
            return None

        if host is None or len(host) == 0:
            logger.error("[look_for_crossselling_items] Host is None or empty.")
            return [item]
        if port is None or port <= 0:
            logger.error("[look_for_crossselling_items] Port is None or invalid.")
            return [item]
        if topic is None or len(topic) == 0:
            logger.error("[look_for_crossselling_items] Topic is None or empty.")
            return [item]

        url= f"{ServerEnvironment.get_pca_server_protocol()}{ServerEnvironment.get_pca_server_host()}:{ServerEnvironment.get_pca_server_port()}/pca/prd/assocrules/get_antecedents_for/{item.label_id}"
        # Get all items that has the label_id as a consequent (if any)
        items=None
        try:
            res = requests.get(url)
            if res.status_code != 200:
                logger.error(f"[look_for_crossselling_items] Error getting related items: {res.status_code} - {res.text}")
                return [item]
            
            items = res.json()
            if items is None or len(items) == 0:
                logger.warning("[look_for_crossselling_items] No related items found.")
                return [item]
            
            if not isinstance(items, list):
                logger.error("[look_for_crossselling_items] Response is not a list.")
                return [item]

            if not all(isinstance(i, int) for i in items):
                # Convert item IDs to QueueItem objects
                logger.warning("[look_for_crossselling_items] Items are not all integers, converting to QueueItem objects.")
                return [item]
        except requests.RequestException as e:
            logger.error(f"[look_for_crossselling_items] Error making request to PCA server ({url}): {e}")
            return [item]

        #Obtaining the items from the database
        url= f"{ServerEnvironment.get_pca_server_protocol()}{ServerEnvironment.get_pca_server_host()}:{ServerEnvironment.get_pca_server_port()}/pca/prd/getproduct/"
        json_req={}
        json_req["Product_IDs"] = items
        rdo = []
        try:
            res = requests.post(url, json=json_req)
            if res.status_code != 200:
                logger.error(f"[look_for_crossselling_items] Error getting items by IDs: {res.status_code} - {res.text}")
                return [item]
            
            items_data = res.json()
            if items_data is None or len(items_data) == 0:
                logger.warning("[look_for_crossselling_items] No items found for the provided IDs.")
                return [item]
            
            for item_data in items_data:
                pboundingbox = None
                plabel_id = str(item_data.get("idproduct", ""))
                plabel = item_data.get("pname", "")

                var = QueueItem(plabel_id,plabel,1,pboundingbox)
                rdo.append(var)
        except requests.RequestException as e:  
            logger.error(f"[look_for_crossselling_items] Error making request to PCA server ({url}): {e}")
            return [item]

        return rdo if rdo is not None and len(rdo)>0 else [item]

    @staticmethod
    def look_for_items_by_day_hour(host:str,port:int,topic:str) -> list[QueueItem]:
        """
        Look for items based on the current day and hour.
        This method can be extended to include more complex logic.
        """        
        if host is None or len(host) == 0:
            logger.error("[look_for_items_by_day_hour] Host is None or empty.")
            return None
        if port is None or port <= 0:
            logger.error("[look_for_items_by_day_hour] Port is None or invalid.")
            return None
        if topic is None or len(topic) == 0:
            logger.error("[look_for_items_by_day_hour] Topic is None or empty.")
            return None

        now = datetime.now()
        dayofweek= now.isoweekday()
        hour= now.hour

        url= f"{ServerEnvironment.get_pca_server_protocol()}{ServerEnvironment.get_pca_server_host()}:{ServerEnvironment.get_pca_server_port()}/pca/mqtt/probweekhh24/"
        json_req={}
        json_req["host"] = host
        json_req["port"] = port
        json_req["topic"] = topic
        json_req["dow"] = dayofweek
        json_req["hh24"] = hour

        rdo=[]
        try:
            res = requests.post(url, json=json_req)
            if res.status_code != 200:
                logger.error(f"[look_for_items_by_day_hour] Error getting items by day and hour {url}: {res.status_code} - {res.text}")
                return None
            
            items = res.json()
            if items is None or len(items) == 0:
                logger.warning("[look_for_items_by_day_hour] No items found for the current day and hour.")
                return None
            
            for item in items:
                pboundingbox = None
                plabel_id = item.get("label_id", None)
                plabel = item.get("label_class", "")
                pconfidence = item.get("probability", 0.0)
                var = QueueItem(plabel_id,plabel,pconfidence,pboundingbox)
                rdo.append(var)

        except requests.RequestException as e:
            logger.error(f"[look_for_items_by_day_hour] Error making request to PCA server ({url}): {e}")
            return None

        return rdo if rdo is not None and len(rdo)>0 else None  
    
    @staticmethod
    def look_for_items_by_day(host:str,port:int,topic:str) -> list[QueueItem]:
        """
        Look for items based on the current day.
        This method can be extended to include more complex logic.
        """
        if host is None or len(host) == 0:
            logger.error("[look_for_items_by_day] Host is None or empty.")
            return None
        if port is None or port <= 0:
            logger.error("[look_for_items_by_day] Port is None or invalid.")
            return None
        if topic is None or len(topic) == 0:
            logger.error("[look_for_items_by_day] Topic is None or empty.")
            return None

        now = datetime.now()
        dayofweek= now.isoweekday()

        url= f"{ServerEnvironment.get_pca_server_protocol()}{ServerEnvironment.get_pca_server_host()}:{ServerEnvironment.get_pca_server_port()}/pca/mqtt/probweek/"
        json_req={}
        json_req["host"] = host
        json_req["port"] = port
        json_req["topic"] = topic
        json_req["dow"] = dayofweek

        rdo=[]
        try:
            res = requests.post(url, json=json_req)
            if res.status_code != 200:
                logger.error(f"[look_for_items_by_day] Error getting items by day and hour {url}: {res.status_code} - {res.text}")
                return None
            
            items = res.json()
            if items is None or len(items) == 0:
                logger.warning("[look_for_items_by_day] No items found for the current day and hour.")
                return None
            
            for item in items:
                pboundingbox = None
                plabel_id = item.get("label_id", None)
                plabel = item.get("label_class", "")
                pconfidence = item.get("probability", 0.0)
                var = QueueItem(plabel_id,plabel,pconfidence,pboundingbox)
                rdo.append(var)

        except requests.RequestException as e:
            logger.error(f"[look_for_items_by_day] Error making request to PCA server ({url}): {e}")
            return None

        return rdo if rdo is not None and len(rdo)>0 else None  
    
    @staticmethod
    def create_animated_gif_from_imgb64list(imglist:list, pduration:int=500)->str:
        if imglist is None or len(imglist) == 0:
            logger.warning("[create_gif_from_imgb64list] No images provided to create GIF.")
            return None
        if pduration is None or pduration <= 500:
            logger.warning("[create_gif_from_imgb64list] Invalid duration provided for GIF creation. Using default 500ms.")
            return None
        
        try:
            images = []
            for img_b64 in imglist:
                if img_b64 is None or len(img_b64) == 0:
                    continue
                img_data = base64.b64decode(img_b64)
                image = Image.open(io.BytesIO(img_data))
                images.append(image)

            if len(images) == 0:
                logger.warning("[create_gif_from_imgb64list] No valid images found to create GIF.")
                return None
            
            gif_buffer = io.BytesIO()
            images[0].save(gif_buffer, 
                           format='GIF', save_all=True, 
                           append_images=images[1:], duration=pduration, loop=0)
            gif_buffer.seek(0)
            gif_b64 = base64.b64encode(gif_buffer.getvalue()).decode('utf-8')
            return gif_b64
        except Exception as e:
            logger.error(f"[create_gif_from_imgb64list] Error creating GIF from images: {e}")
            return None
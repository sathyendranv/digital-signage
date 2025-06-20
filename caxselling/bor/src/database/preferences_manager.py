import re
import sqlite3
from database.version import ServerEnvironment
# Treading
import threading
# Deepcopy
import copy
# Image 
import PIL.ImageColor as ImageColor
# Logging
import logging
logger = logging.getLogger(__name__)

class PreferencesManager: 
    CATEGORY_PREDEFINED_ADS = "predefined_ads"
    CATEGORY_DYNAMIC_ADS = "dynamic_ads"
    CATEGORY_DIGITAL_SIGNAGE = "digital_signage"
    CATEGORY_PRICE = "price"

    # Ads
    AD_ENABLE_LOGO = "enable_logo"
    AD_LOGO_HALIGN = "logo_halign"
    AD_LOGO_VALIGN = "logo_valign"
    AD_LOGO_PERCENTAGE = "logo_percentage"
    AD_LOGO_MARGIN_PX = "logo_margin_px"
    AD_ENABLE_SLOGAN_DEFINITION = "enable_slogan_definition"
    AD_SLOGAN_TEXT = "slogan_text"
    AD_SLOGAN_TEXT_COLOR = "slogan_text_color"
    AD_SLOGAN_FONT_SIZE = "slogan_font_size"
    AD_SLOGAN_HALIGN = "slogan_halign"
    AD_SLOGAN_VALIGN = "slogan_valign"
    AD_SLOGAN_MARPERF_FROM_BORDER = "slogan_marperc_from_border"
    AD_SLOGAN_LINE_WIDTH = "slogan_line_width"
    AD_ENABLE_PRICE = "enable_price"
    AD_PRICE_TEXT_COLOR = "price_text_color"
    AD_PRICE_FONT_SIZE = "price_font_size"     
    AD_PRICE_LINE_WIDTH = "price_line_width"
    AD_PRICE_IN_CIRCLE = "price_in_circle"
    AD_PRICE_CIRCLE_COLOR = "price_circle_color"
    AD_PRICE_HALIGN = "price_halign"
    AD_PRICE_VALIGN = "price_valign"
    AD_PRICE_MARPERF_FROM_BORDER = "price_marperc_from_border"
    AD_ENABLE_PROMOTIONAL_TEXT = "enable_promotional_text"
    AD_PROMO_TEXT = "promo_text"
    AD_PROMO_TEXT_COLOR = "promo_text_color"
    AD_PROMO_FONT_SIZE = "promo_font_size"
    AD_PROMO_LINE_WIDTH = "promo_line_width"
    AD_PROMO_RECT_COLOR = "promo_rect_color"
    AD_PROMO_RECT_PADDING = "promo_rect_padding"
    AD_PROMO_RECT_RADIUS = "promo_rect_radius"
    AD_PROMO_HALIGN = "promo_halign"
    AD_PROMO_VALIGN = "promo_valign"
    AD_PROMO_MARPERF_FROM_BORDER = "promo_marperc_from_border"
    AD_ENABLE_FRAME = "enable_frame"
    AD_FRAME_MARPERF_FROM_BORDER = "frame_marperc_from_border"  
    AD_QUERY_DEVICE = "query_device"  #
    AD_QUERY_COMPLEMENT = "query_complement"  # Complement to the query for ads. For example, 8k or picture quality
    AD_SERVICE_PATH = "service_path"  # Path to the service that provides ads    
    # Digital Signage
    DS_MIN_TIME_BETWEEN_ADS_SUBMISSION = "min_time_between_adsubmission"
    DS_TYPE_PREDEFINED = 'PREDEFINED'
    DS_TYPE_DYNAMIC = 'DYNAMIC'
    DS_OUTPUT_SEQUENCE = "output_sequence"
    DS_OUTPUT_SUFFIX = "output_suffix"
    DS_OUTPUT_ADD_ANIMATION = "output_add_animation"    
    DS_OUTPUT_ANIMATION_MIN_MS_PER_IMG = "output_animation_min_ms_per_img"  # Minimum milliseconds per image in the output animation
    DS_DEFAULT_CONCEPT="default_concept"  # Default concept for digital signage    
    DS_USE_DEFAULT_AD_WHEN_EMPTYRESULT = "use_default_ad_when_emptyresult"  # Use default ad when the result is empty

    # Price
    PRICE_ENDPOINT = "endpoint"
    PRICE_TAG_PRICE = "pricetag"
    PRICE_TAG_UNIT = "unittag"
    PRICE_GRAL_PERC_DISCOUNT = "gral_percentage_discount"  # General percentage discount for all products

    def __new__(cls):
        """Singleton pattern to ensure only one instance of PreferencesManager exists."""
        if not hasattr(cls, 'instance'):
            cls.instance = super(PreferencesManager, cls).__new__(cls)
        return cls.instance
    
    def __init__(self):
        # It avoids re-initialization of the instance for the singleton pattern
        if not hasattr(self, 'connection'):           
            try:
                self.connection = sqlite3.connect(ServerEnvironment.get_bor_default_pref_db(), check_same_thread=False)
            except sqlite3.Error as e:
                errorMessage = f"[Preferences] SQLite connection error for {ServerEnvironment.get_bor_default_pref_db()}: {str(e)}"
                logger.error(errorMessage)
                raise sqlite3.Error(errorMessage)
            
            PreferencesManager.chk_or_init_database(self.connection)

            self.preferences = {}
            self._lock = threading.Lock()  # Thread-safe lock for preferences access
            self.__define_preferences() # Initialize with predefined preferences
            rdo, error = self.load_update_preferences()  # Load preferences from the database
            if not rdo:
                errorMessage = f"[Preferences] Error loading preferences from database: {error}"
                logger.error(errorMessage)
            else:
                logger.info("[Preferences] Preferences loaded successfully from the database.")
                

    def closeConnections(self):
        """
        Close the database connection.
        """
        with self._lock:  # Ensure thread-safe access to the connection
            if self.connection is not None:
                try:
                    self.connection.close()
                    self.connection = None
                except sqlite3.Error as e:
                    errorMessage = f"[Preferences] SQLite close connection error: {str(e)}"
                    logger.error(errorMessage)

    def __define_preferences(self):
        if self.preferences is None:
            errorMessage = "Preferences dictionary is None"
            logger.error(errorMessage)
            raise ValueError(errorMessage)

        predefined_ads={}
        predefined_ads[PreferencesManager.AD_ENABLE_LOGO] = True
        predefined_ads[PreferencesManager.AD_LOGO_HALIGN] = "left"
        predefined_ads[PreferencesManager.AD_LOGO_VALIGN] = "top"
        predefined_ads[PreferencesManager.AD_LOGO_PERCENTAGE] = 15.0
        predefined_ads[PreferencesManager.AD_LOGO_MARGIN_PX] = 10
    
        predefined_ads[PreferencesManager.AD_ENABLE_SLOGAN_DEFINITION] = True
        predefined_ads[PreferencesManager.AD_SLOGAN_TEXT] = "The Best price in town"
        predefined_ads[PreferencesManager.AD_SLOGAN_TEXT_COLOR] = "white"
        predefined_ads[PreferencesManager.AD_SLOGAN_FONT_SIZE] = 18
        predefined_ads[PreferencesManager.AD_SLOGAN_HALIGN] = "right"
        predefined_ads[PreferencesManager.AD_SLOGAN_VALIGN] = "top"
        predefined_ads[PreferencesManager.AD_SLOGAN_MARPERF_FROM_BORDER] = 5.0
        predefined_ads[PreferencesManager.AD_SLOGAN_LINE_WIDTH] = 20

        predefined_ads[PreferencesManager.AD_ENABLE_PRICE] = True
        predefined_ads[PreferencesManager.AD_PRICE_TEXT_COLOR] = "white"
        predefined_ads[PreferencesManager.AD_PRICE_FONT_SIZE] = 24
        predefined_ads[PreferencesManager.AD_PRICE_LINE_WIDTH] = 5
        predefined_ads[PreferencesManager.AD_PRICE_IN_CIRCLE] = True	
        predefined_ads[PreferencesManager.AD_PRICE_CIRCLE_COLOR] = "black"
        predefined_ads[PreferencesManager.AD_PRICE_HALIGN] = "right"
        predefined_ads[PreferencesManager.AD_PRICE_VALIGN] = "bottom"
        predefined_ads[PreferencesManager.AD_PRICE_MARPERF_FROM_BORDER] = 10

        predefined_ads[PreferencesManager.AD_ENABLE_PROMOTIONAL_TEXT] = True
        predefined_ads[PreferencesManager.AD_PROMO_TEXT] = "Get one pound and get 50%% off in the second!"
        predefined_ads[PreferencesManager.AD_PROMO_TEXT_COLOR] = "white"
        predefined_ads[PreferencesManager.AD_PROMO_FONT_SIZE] = 20
        predefined_ads[PreferencesManager.AD_PROMO_LINE_WIDTH] = 10
        predefined_ads[PreferencesManager.AD_PROMO_RECT_COLOR] = "black"
        predefined_ads[PreferencesManager.AD_PROMO_RECT_PADDING] = 10
        predefined_ads[PreferencesManager.AD_PROMO_RECT_RADIUS] = 20
        predefined_ads[PreferencesManager.AD_PROMO_HALIGN] = "left"
        predefined_ads[PreferencesManager.AD_PROMO_VALIGN] = "bottom"
        predefined_ads[PreferencesManager.AD_PROMO_MARPERF_FROM_BORDER] = 10

        predefined_ads[PreferencesManager.AD_ENABLE_FRAME] = True
        predefined_ads[PreferencesManager.AD_FRAME_MARPERF_FROM_BORDER] = 5.0 

        predefined_ads[PreferencesManager.AD_QUERY_DEVICE] = "GPU"  
        predefined_ads[PreferencesManager.AD_QUERY_COMPLEMENT] = "8k"  # Complement to the query for ads. For example, 8k or picture quality      
        
        self.preferences[PreferencesManager.CATEGORY_PREDEFINED_ADS] = predefined_ads
        self.preferences[PreferencesManager.CATEGORY_DYNAMIC_ADS] = predefined_ads.copy()  # Idem in
        # Service Path
        self.preferences[PreferencesManager.CATEGORY_PREDEFINED_ADS][PreferencesManager.AD_SERVICE_PATH] = "/ase/predef/query/ad"  # Path to the service that provides predefined ads
        self.preferences[PreferencesManager.CATEGORY_DYNAMIC_ADS][PreferencesManager.AD_SERVICE_PATH] = "/aig/minf"  # Path to the service that provides dynamic ads

        digital_signage={}
        digital_signage[PreferencesManager.DS_MIN_TIME_BETWEEN_ADS_SUBMISSION] = 90  # 60 seconds
        digital_signage[PreferencesManager.DS_OUTPUT_SEQUENCE] = [PreferencesManager.DS_TYPE_PREDEFINED, PreferencesManager.DS_TYPE_DYNAMIC, PreferencesManager.DS_TYPE_PREDEFINED]
        digital_signage[PreferencesManager.DS_OUTPUT_SUFFIX] = "_output"
        digital_signage[PreferencesManager.DS_OUTPUT_ADD_ANIMATION] = True  # Add animation to the output
        digital_signage[PreferencesManager.DS_OUTPUT_ANIMATION_MIN_MS_PER_IMG] = 1000  # Minimum milliseconds per image in the output animation
        digital_signage[PreferencesManager.DS_DEFAULT_CONCEPT] = "healthy food"  # Add animation to the output
        digital_signage[PreferencesManager.DS_USE_DEFAULT_AD_WHEN_EMPTYRESULT] = True  # Use default ad when the result is empty 
        self.preferences[PreferencesManager.CATEGORY_DIGITAL_SIGNAGE] = digital_signage

        price={}
        price[PreferencesManager.PRICE_ENDPOINT] = "http://localhost:5000/bor/price"
        price[PreferencesManager.PRICE_TAG_PRICE] = "price"
        price[PreferencesManager.PRICE_TAG_UNIT] = "unit"
        price[PreferencesManager.PRICE_GRAL_PERC_DISCOUNT] = 1.0  # General percentage discount for all products
        self.preferences[PreferencesManager.CATEGORY_PRICE] = price
       
        return True
    
    def getValue(self,category:str, parameter:str):
        """
        Get the value of a specific parameter in a specific category.
        """        
        with self._lock:  # Ensure thread-safe access to preferences
            return self.__getValue(category, parameter)

    def __getValue(self,category:str, parameter:str):
        """
        Get the value of a specific parameter in a specific category.
        """
        if category not in self.preferences:
            errorMessage = f"[Preferences] Category {category} does not exist"
            logger.error(errorMessage)
            return None
        
        if parameter not in self.preferences[category]:
            errorMessage = f"[Preferences] Parameter {parameter} does not exist in category {category}"
            logger.error(errorMessage)
            return None
        
        return self.preferences[category][parameter]

    def setValue(self,category:str, parameter:str, value)->bool:        
        """
        Set the value of a specific parameter in a specific category.
        """
        with self._lock:  # Ensure thread-safe access to preferences
            return self.__setValue(category, parameter, value)

    def __setValue(self,category:str, parameter:str, value)->bool:        
        """
        Get the value of a specific parameter in a specific category.
        """
        if category not in self.preferences:
            errorMessage = f"[Preferences] Category {category} does not exist"
            logger.error(errorMessage)
            return False
        
        if parameter not in self.preferences[category]:
            errorMessage = f"[Preferences] Parameter {parameter} does not exist in category {category}"
            logger.error(errorMessage)
            return False        

        self.preferences[category][parameter]=value

        return self.preferences[category][parameter]==value

    def save_preferences(self) -> tuple[bool,str]:
        """
        Save the preferences to the database.
        """
        with self._lock:
            return self.__save_preferences()
        
    def __save_preferences(self) -> tuple[bool,str]:
        """
        Save the preferences to the database.
        """
        if self.connection is None:
            errorMessage = "[Preferences] Connection is None"
            logger.error(errorMessage)
            return False, errorMessage

        cursor = None
        try:
            cursor = self.connection.cursor()
            for category in self.preferences.keys():
                if not isinstance(category, str):
                    errorMessage = f"[Preferences] Category {category} is not a string"
                    logger.error(errorMessage)
                    return False, errorMessage
                
                params = self.preferences[category]
                if params is None or not isinstance(params, dict):
                    errorMessage = f"[Preferences] Parameters for category {category} are None or not a dictionary"
                    logger.error(errorMessage)
                    return False, errorMessage
                
                for parameter, value in params.items():
                    insert_sql = """ 
                        INSERT INTO preferences (category, parameter, value, type)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(category, parameter) DO UPDATE SET value=excluded.value, type=excluded.type
                        """
                    processed_value = value
                    if isinstance(value, list):
                        processed_value = ",".join(value)  # Convert list to comma-separated string
                    elif isinstance(value, bool):
                        processed_value = str(value).lower()

                    values = (category, parameter, str(processed_value), type(value).__name__)

                    cursor.execute(insert_sql, values)      
                    self.connection.commit()
            
        except sqlite3.Error as e:
            errorMessage = f"[Preferences] SQLite error: {str(e)}"
            logger.error(errorMessage)
            return False, errorMessage
        finally:
            if cursor is not None:
                cursor.close()

        return True, 'Success'

    def update_preferences(self, updated:dict) -> tuple[bool, str]:
        """
        Update the preferences in the memory dictionary and save them to the database.
        """
        if self.connection is None:
            errorMessage = "[Preferences] Connection is None (Update)"
            logger.error(errorMessage)
            return False, errorMessage

        if updated is None or not isinstance(updated, dict):
            errorMessage = "[Preferences] Updated preferences are None or not a dictionary"
            logger.error(errorMessage)
            return False, errorMessage
        
        if PreferencesManager.CATEGORY_DIGITAL_SIGNAGE not in updated and \
            PreferencesManager.CATEGORY_PREDEFINED_ADS not in updated and \
            PreferencesManager.CATEGORY_DYNAMIC_ADS not in updated and \
            PreferencesManager.CATEGORY_PRICE not in updated:
            errorMessage = "[Preferences] No valid categories to update"
            logger.error(errorMessage)
            return False, errorMessage
        
        with self._lock:
            for category in updated.keys():
                if category not in self.preferences:
                    errorMessage = f"[Preferences] Category {category} does not exist"
                    logger.error(errorMessage)
                    return False, errorMessage
                
                category_hash = updated[category]
                if isinstance(category_hash, dict):
                    for parameter, value in category_hash.items():
                        if not self.__setValue(category, parameter, value):
                            errorMessage = f"[Preferences] Failed to set value for {category}.{parameter}. Partial Update."
                            logger.error(errorMessage)

            return self.__save_preferences()

    def load_update_preferences(self) -> tuple [bool, str]:
        """
        Load the preferences from the database and update it in the memory dictionary.
        """
        with self._lock:
            return self.__load_update_preferences()

    def __load_update_preferences(self) -> tuple[bool, str]:
        """
        Load the preferences from the database and update it in the memory dictionary.
        """
        if self.connection is None:
            errorMessage = "[Preferences] Connection is None (Load)"
            logger.error(errorMessage)
            return False, errorMessage

        cursor = None
        try:
            cursor = self.connection.cursor()
                
            select_sql = "SELECT category, parameter, value, type  From preferences Order by category, parameter"                        
            cursor.execute(select_sql)      
            logger.warning(f"[Preferences] Executing SQL: {select_sql}")
            rows = cursor.fetchall()
            count = 0
            for category,parameter,value, type in rows:
                processed_value = value
                if type == "int":
                    processed_value = int(value)
                if type == "float":
                    processed_value = float(value)
                if type == "bool":
                    processed_value = value.lower() == 'true'
                if type == "list":
                    processed_value = value.split(",") if value else []
                
                self.preferences[category][parameter] = processed_value
                count += 1

            logger.warning(f"[Preferences] Loaded {count} preferences from the database.")
        except sqlite3.Error as e:
            errorMessage = f"[Preferences] SQLite error: {str(e)} (Load)"
            logger.error(errorMessage)
            return False, errorMessage
        finally:
            if cursor is not None:
                cursor.close()

        return True, 'Success'

    @staticmethod
    def chk_or_init_database(connection:sqlite3.Connection):
        """
        Check if the database exists, if not, create it.
        """
        if connection is None:
            errorMessage = "[Preferences] Connection is None"
            logger.error(errorMessage)
            return False

        cursor = None
        try:
            cursor = connection.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preferences (
                    category text not null,
                    parameter text not null,
                    value text not null,
                    type text not null,
                    constraint pk_preferences primary key(category,parameter)
                )
            ''')

            connection.commit()
        except sqlite3.Error as e:
            errorMessage = f"[Preferences] SQLite error: {str(e)}"
            logger.error(errorMessage)
            return False
        finally:
            if cursor is not None:
                cursor.close()
        
        return True

    def getAPreferencesCopy(self) -> dict:
        """
        Returns a copy of the preferences dictionary.
        This is useful to avoid direct modifications to the original preferences.
        """
        with self._lock:
            return copy.deepcopy(self.preferences)

    @staticmethod
    def is_only_predefined_or_dynamic(text):
        # Remove brackets, commas, and whitespace
        cleaned = re.sub(r"[\[\],'\s]", '', text)
        # Split by 'PREDEFINED' and 'DYNAMIC', remove empty strings
        tokens = re.split(r'(PREDEFINED|DYNAMIC)', cleaned)
        tokens = [t for t in tokens if t and t not in ('PREDEFINED', 'DYNAMIC')]
        # If tokens is empty, only PREDEFINED/DYNAMIC are present
        return len(tokens) == 0
    
    @staticmethod
    def get_predefined_or_dynamic_output_list(text)->list:
        """
        Extracts the predefined or dynamic type from a string.
        If the string contains both types, it returns 'PREDEFINED,DYNAMIC'.
        If it contains only one type, it returns that type.
        If it contains neither, it returns None.
        """        
        if text is None or len(text)==0 or not isinstance(text, str):
            return None
        
        if PreferencesManager.is_only_predefined_or_dynamic(text):
            # Remove only [ and ] (if present)
            cleaned = text.replace('[', '').replace(']', '').replace("'", '')
            return [item.strip() for item in cleaned.split(',') if item.strip()]
        else:
            return [PreferencesManager.DS_TYPE_PREDEFINED, PreferencesManager.DS_TYPE_DYNAMIC,PreferencesManager.DS_TYPE_PREDEFINED]

    @staticmethod
    def is_color_valid(color: str) -> bool:
        """
        Checks if the given color string is a valid color name in PIL.
        """
        if color is None or not isinstance(color, str):
            return False
        
        return color.lower() in ImageColor.colormap
    
    @staticmethod
    def get_color_list():
        return list(ImageColor.colormap.keys())  # Returns a list of all available color names in PIL

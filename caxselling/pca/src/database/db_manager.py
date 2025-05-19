import os
#DB Library
import psycopg2
# Logging
import logging
#Modin
import modin.pandas as pd
logger = logging.getLogger(__name__)

class DatabaseConnection:
    @staticmethod
    def connect():
        pghost=os.getenv('POSTGRES_HOST')
        pgdb=os.getenv('POSTGRES_DB')
        pguser=os.getenv('POSTGRES_USER')
        pgpwd=os.getenv('POSTGRES_PASSWORD')

        try:
            conn = psycopg2.connect(f"dbname='{pgdb}' user='{pguser}' host='{pghost}' password='{pgpwd}'")
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            return None
        
        return conn

def createTrxTables():
    logger.info(f"Reading PG Metadata")

    try:        
        conn = DatabaseConnection().connect()
        if conn is None:
            logger.error(f"PG Connection Error")
            return False
        
        with conn.cursor() as curs:
            # Create table
            logger.info(f"Creating table mqtt_topics")            
            curs.execute("""
                CREATE TABLE IF NOT EXISTS mqtt_topics (
                    id SERIAL PRIMARY KEY,
                    hostname VARCHAR(255) NOT NULL,
                    port INTEGER NOT NULL,
                    topic VARCHAR(255) NOT NULL,                    
                    message TEXT NOT NULL,
                    constraint trx_unique UNIQUE (hostname, port, topic),
                    created_at TIMESTAMP not null DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.info(f"Creating Sequence trxbyday")            
            curs.execute("""
                CREATE SEQUENCE IF NOT EXISTS trxbyday
                    AS INTEGER 
                    INCREMENT BY 1
                    MINVALUE 1 
                    START WITH 1 CYCLE;
            """)            
            logger.info(f"Creating table trx")
            curs.execute("""                        
                CREATE TABLE IF NOT EXISTS mqtt_topics_trxs (
                    hostname VARCHAR(255) NOT NULL,
                    port INTEGER NOT NULL,
                    topic VARCHAR(255) NOT NULL, 
                    hpt_order integer NOT NULL default nextval('trxbyday'),		
                    frameID INTEGER NOT NULL,
                    label_class varchar(255) NOT NULL,
                    label_id varchar(255) NOT NULL,
                    confidence float NOT NULL,
                    video_height integer,
                    video_width integer,
                    boundingbox json,                        
                    created_at TIMESTAMP not null default CURRENT_TIMESTAMP,
                    trx_dd integer not null default Extract(DAY from CURRENT_TIMESTAMP),		
                    trx_mm integer not null default Extract(MONTH from CURRENT_TIMESTAMP),		
                    trx_yyyy integer not null default Extract(ISOYEAR from CURRENT_TIMESTAMP),		
                    trx_quarter integer not null default Extract(QUARTER from CURRENT_TIMESTAMP),
                    trx_dayofweek integer not null default Extract(ISODOW from CURRENT_TIMESTAMP), /*1: Monday 7:Sunday*/
                    trx_dayofyear integer not null default Extract(DOY from CURRENT_TIMESTAMP),
                    trx_hh24 integer not null default Extract(hour from CURRENT_TIMESTAMP),
                    trx_minute integer not null default Extract(minute from CURRENT_TIMESTAMP),
                    trx_timezone integer not null default Extract(timezone from CURRENT_TIMESTAMP),
                    constraint pk_mqtt_topics_trxs primary key(hostname, port, topic, hpt_order, created_at)
                    );
            """)                             
            logger.info(f"Creating table products")
            curs.execute("""                        
                CREATE TABLE IF NOT EXISTS PRODUCTS(
                    IDPRODUCT INTEGER NOT NULL,
                    PNAME VARCHAR(255) NOT NULL,
                    PDESCRIPTION TEXT,
                    PRICE FLOAT,
                    CONSTRAINT PK_PRODUCT PRIMARY KEY(IDPRODUCT)
                );
            """)
            logger.info(f"Creating table products_trxs")
            curs.execute("""                        
                CREATE TABLE IF NOT EXISTS PRODUCTSTRX(
                    IDTRANSACTION INTEGER NOT NULL,
                    IDPRODUCT INTEGER NOT NULL,
                    QUANTITY INTEGER NOT NULL DEFAULT 1,
                    UNITARYPRICE FLOAT DEFAULT NULL,
                    CONSTRAINT CHK_QUANTITY CHECK (QUANTITY>=1),
                    CONSTRAINT PK_PRODUCTRX PRIMARY KEY(IDTRANSACTION,IDPRODUCT),
                    CONSTRAINT FK_TRXTOPRODUCT FOREIGN KEY(IDPRODUCT) REFERENCES PRODUCTS(IDPRODUCT)
                );            
            """)
            logger.info(f"Creating table MQTTLabelDayProb")
            curs.execute("""               
                CREATE TABLE IF NOT EXISTS MQTTLabelDayProb(
                        hostname varchar(255) not null,
                        port integer not null,
                        topic varchar(255) not null,
                        label_class varchar(255) not null,
                        label_id varchar(255) not null,
                        dow integer not null,
                        probability float default 0,	
                        constraint fk_labeldayTomqtt foreign key (hostname, port, topic) references mqtt_topics (hostname, port, topic),
                        constraint pk_MQTTLabelDayProb primary key(hostname,port,topic,label_class,dow),
                        constraint chk_MQTTLabelDayProb_dow check (dow >=1 and dow<=7)
                );
            """)
            logger.info(f"Creating table MQTTLabelDayHourProb")
            curs.execute("""
                CREATE TABLE IF NOT EXISTS MQTTLabelDayHourProb(
                        hostname varchar(255) not null,
                        port integer not null,
                        topic varchar(255) not null,
                        label_class varchar(255) not null,
                        label_id varchar(255) not null,
                        dow integer not null,
                        hh24 integer not null,
                        probability float default 0,	
                        constraint fk_labeldayhourTomqtt foreign key (hostname, port, topic) references mqtt_topics (hostname, port, topic),
                        constraint pk_MQTTLabelDayHourProb primary key(hostname,port,topic,label_class,dow,hh24),
                        constraint chk_MQTTLabelDayHourProb_dow check (dow >=1 and dow<=7),
                        constraint chk_MQTTLabelDayHourProb_hh24 check (hh24 >=0 and hh24<=23)
                );
            """)    		
            logger.info(f"Creating function WEEKPROB_MATRIX()")
            curs.execute("""
                CREATE or REPLACE FUNCTION WEEKPROB_MATRIX()
                    RETURNS boolean
                    LANGUAGE plpgsql
                AS $$
                DECLARE
                    --Variable initialization
                    precord RECORD;
                    
                    total_day_items integer;
                BEGIN
                    -- Last 6 months transactions
                    CREATE TEMP TABLE tmp_myview AS
                    SELECT * FROM mqtt_topics_trxs Where created_at >= (now() - interval '6 months');
                    
                    --Clean any previous probabilities
                    truncate MQTTLabelDayProb; 
                    
                    --1: Monday 7: Sunday (Isodow) 
					FOR precord IN (SELECT DISTINCT hostname,port,topic,trx_dayofweek FROM tmp_myview) LOOP
						Select into total_day_items count(*)
						from tmp_myview
						Where hostname = precord.hostname and
							port = precord.port and
							topic = precord.topic and
							trx_dayofweek = precord.trx_dayofweek;
						
						if total_day_items is not null and total_day_items > 0 then
							--There are items in this day
							insert into MQTTLabelDayProb(hostname,port,topic,label_class,label_id,dow,probability)		
							Select hostname,port, topic,label_class, label_id,trx_dayofweek, count(*)::float/total_day_items::float
							from tmp_myview
							Where hostname = precord.hostname and
								port = precord.port and
								topic = precord.topic and
								trx_dayofweek = precord.trx_dayofweek
							group by hostname,port, topic,label_class,label_id,trx_dayofweek;
						End if;			
					END LOOP;
                    
                    DROP TABLE tmp_myview;
                    
                    return true;
                END;
                $$;
            """)
            logger.info(f"Creating function WEEKPROB_MATRIX_HH24()")
            curs.execute("""
                CREATE or REPLACE FUNCTION WEEKHH24PROB_MATRIX()
                    RETURNS boolean
                    LANGUAGE plpgsql
                AS $$
                DECLARE
                    --Variable initialization
                    precord RECORD;
                    
                    total_hh24_items integer;
                BEGIN
                    -- Last 6 months transactions
                    CREATE TEMP TABLE tmp_myview AS
                    SELECT * FROM mqtt_topics_trxs Where created_at >= (now() - interval '6 months');
                    
                    --Clean any previous probabilities
                    truncate MQTTLabelDayHourProb; 
                    
                    --1: Monday 7: Sunday (Isodow) 
                    FOR precord IN (SELECT DISTINCT hostname,port,topic,trx_dayofweek,trx_hh24 FROM tmp_myview) LOOP
                        Select into total_hh24_items count(*)
                        from tmp_myview
                        Where hostname = precord.hostname and
                            port = precord.port and
                            topic = precord.topic and
                            trx_dayofweek = precord.trx_dayofweek and
                            trx_hh24 = precord.trx_hh24;
                        
                        if total_hh24_items is not null and total_hh24_items > 0 then
                            --There are items in this hh24 and day
                            insert into MQTTLabelDayHourProb(hostname,port,topic,label_class,label_id,dow,hh24,probability)		
                            Select hostname,port, topic,label_class, label_id,trx_dayofweek, trx_hh24, count(*)::float/total_hh24_items::float
                            from tmp_myview
                            Where hostname = precord.hostname and
                                port = precord.port and
                                topic = precord.topic and
                                trx_dayofweek = precord.trx_dayofweek and 
                                trx_hh24 = precord.trx_hh24
                            group by hostname,port, topic,label_class,label_id,trx_dayofweek, trx_hh24;
                        End if;			
                    END LOOP;
                    
                    DROP TABLE tmp_myview;
                    
                    return true;
                END;
                $$;
		    """)                         


            conn.commit()
            conn.close()
            logger.info(f"Commited PG transaction")
    except Exception as e:
        logger.error(f"PG Exception: {str(e)}")
        return False

    return True

def populateSampleData():
    if os.getenv('PCA_SAMPLEDATA') == "YES":
        logger.info(f"[SAMPLE DATA] Reading Yolov11 Classes from COCO Dataset (Products)...")
    else:
        logger.info(f"[Sample Data] Deactivated")
        return True

    df=None
    conn=None
    try:        
        df = pd.read_csv(os.path.dirname(os.path.abspath(__file__))+'/sampledata/ProductsYolov11SEG.csv', sep=",", header=None, names=["idproduct","pdescription"])        
        
        conn = DatabaseConnection().connect()

        with conn.cursor() as curs:
            for i in range(len(df)):
                idproduct = int(df["idproduct"][i])
                pdescription = str(df["pdescription"][i])
                
                insert_sql = """ 
                    INSERT INTO PRODUCTS (IDPRODUCT, PNAME) VALUES(%s, %s) ON CONFLICT (IDPRODUCT) DO NOTHING
                    """
                values = (idproduct, pdescription)

                curs.execute(insert_sql, values)            

        conn.commit()
    except Exception as e:
        if conn is not None:
            conn.rollback()

        logger.error(f"Error reading sample data: {str(e)}")
        return False
    finally:
        if conn is not None:
            conn.close()

    return True
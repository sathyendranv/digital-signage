import os
#DB Library
import psycopg2
# Logging
import logging
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
            conn.commit()
            conn.close()
            logger.info(f"Commited PG transaction")
    except Exception as e:
        logger.error(f"PG Exception: {str(e)}")
        return False

    return True
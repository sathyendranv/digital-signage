import os
#DB Library
import psycopg2
# Logging
import logging
#Modin
import modin.pandas as pd
logger = logging.getLogger(__name__)


def populateSampleData():
    logger.info(f"Reading Yolov11 Classes")

    df=None
    try:        
        df = pd.read_csv(os.path.dirname(os.path.abspath(__file__))+'/sampledata/ProductsYolov11SEG.csv', sep=",", header=None, names=["idproduct","pdescription"])        
        
        for i in range(len(df)):
            idproduct = int(df["idproduct"][i])
            pdescription = str(df["pdescription"][i])
            
            print(f"{idproduct}\t{pdescription}")
            

    except Exception as e:
        logger.error(f"Error reading sample data: {str(e)}")
        return False

def populateSampleDataTrx():
    logger.info(f"Reading Yolov11 Classes")

    df=None
    try:        
        df = pd.read_csv(os.path.dirname(os.path.abspath(__file__))+'/sampledata/Yolov11Trxs.csv', sep=",", header=None, names=["idtransaction","idproduct"])        
        
        for i in range(len(df)):
            idtransaction = int(df["idtransaction"][i])
            idproduct = str(df["idproduct"][i])
            
            print(f"{idtransaction}\t{idproduct}")
            

    except Exception as e:
        logger.error(f"Error reading sample data: {str(e)}")
        return False


if __name__ == "__main__":
    populateSampleDataTrx()
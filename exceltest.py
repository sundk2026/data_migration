import os
import datetime
import logging
import csv
import zipfile
import json
import geopandas as gpd
from  util_services import UTILServices 
from pyogrio import list_layers
import re
import time
import pandas as pd
from shapely import wkb

from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment,PatternFill
from collections import defaultdict
from time import strftime
from time import gmtime
from datetime import datetime
import pandas as pd
import cdif
import logging
import sqlite3
from shapely.geometry import MultiLineString, LineString
from shapely.ops import linemerge
fld=[]
def gen_with_panda():
    data = {'Name': ['Alice', 'Bob', 'Charlie'],
            'Age': [25, 30, 35]}
    df = pd.DataFrame(data)

    df.to_excel(output_pandas.xlsx, index=False)

def arychange():
    fld[2][1]=10


if __name__ == "__main__":
    # gen_with_panda()
    
    # logging.basicConfig(
    # filename=rC:\SaskTel_Bisen\Development\Data_Migration\config\test.log,  # Name of the log file
    # level=logging.INFO,         # Minimum level of messages to log (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)
    # format='%(asctime)s - %(levelname)s - %(message)s', # Format of log messages
    # filemode='a'                # 'a' for append, 'w' for overwrite
    # )
    # logging.info(   ********** CDIF CREATION TASK STARTED **********  )
    
     


    # logging.info(Completed)

   
    # fgdb_path=r'C:\SaskTel_Bisen\SaskTelData\SaskTel.gdb'
    # file_config=r'C:\SaskTel_Bisen\Development\Data_Migration\abc.db'
    # # Example MultiLineString with contiguous lines
    # UTILServices.gdb_to_sqlite(fgdb_path,file_config)
        # conn = sqlite3.connect(r'C:\\SaskTel_Bisen\\SaskTelData\\abc.db')
        # cur = conn.cursor()
        # create_sql = fCREATE TABLE IF NOT EXISTS route_geom ('str_hash' TEXT, 'geom' TEXT);
        # cur.execute(create_sql)
        # conn.commit()
        # conn.close()

    print("hai")

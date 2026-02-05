import os
import json
import geopandas as gpd
import pandas as pd
from pyogrio import list_layers
import shapely
import csv
from shapely.geometry import Polygon
import fiona
from shapely.geometry import shape, LineString, Point,MultiLineString
from shapely.ops import transform
from pyproj import Transformer
import sys
 
import time
import zipfile
from openpyxl import Workbook

from typing import Dict, Optional, Union
import logging
from datetime import datetime
from shapely.ops import linemerge
from shapely.geometry import box
import re
import math
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment,PatternFill
from collections import defaultdict
from time import strftime
from time import gmtime
import io
from  util import util_services
import conduit
 

 

            
def create_conduit_csv(gdb_path, config_json_file_path, folder, route_cdif_file,route_iqgeo_file,str_iqgeo_file ):
    start_time = time.time()
    
    cdif_root_directory = os.getcwd() +"\\output\\"
     
    folder_full_path=cdif_root_directory+folder+"\\" 

    objCDIF=  conduit.IQGeoCDIF(cdif_root_directory,folder,config_json_file_path,gdb_path,"0",route_cdif_file,route_iqgeo_file,str_iqgeo_file)
    objCDIF.InitiateProcess()
    if objCDIF.Initialized ==True:
        objCDIF.ProcessRecords()
        if  objCDIF.DataMigrationStatus==2:
            objCDIF.FinalizeCDIF()
    return

             

if __name__ == "__main__":
    str_cdif_file=""
    cat="CONDUIT"
    str_route_iqgeo_file=""
    print("Task started...")
    if len(sys.argv) > 3:
         
        fgdb_path=sys.argv[1]
        file_config=sys.argv[2]
        output_folder = sys.argv[3]
        
        if len(sys.argv) > 4:
            str_cdif_file = sys.argv[4]
            str_route_iqgeo_file= sys.argv[5]
            str_iqgeo_file= sys.argv[6]
    else:
        # fgdb_path=r'C:\SaskTel_Bisen\SaskTelData\ReginaS84\ReginaS84.gdb'
        # fgdb_path=r'C:\SaskTel_Bisen\SaskTelData\Regina\Test_ArcMap_NE_DATA_fsa.gdb'

        fgdb_path=r'C:\Kishore\SaskTel_Bisen\kranthi\gdb\exchange_SWCRSK_SIMPLE_TELCO_2026_01_20_1769678925118.gdb'
        # fgdb_path=r"C:\SaskTel_Bisen\SaskTelData\latestOct25\NE_DATA08Oct_fsa.gdb"
        # fgdb_path=r"C:\SaskTel_Bisen\SaskTelData\latestOct25\NE_DATA08Oct_exchange.gdb"
        file_config=r"C:\Kishore\SaskTel_Bisen\SaskTel_Bisen\Development\Data_Migration\conduit_kishore\conduit_kishore\conduit.json"

        # C:\SaskTel_Bisen\Development\Data_Migration\config\st_struct_pole.json
        # file_config=r'C:\SaskTel_Bisen\Development\Data_Migration\config\vault.json'
        str_cdif_file=r"C:\Kishore\SaskTel_Bisen\SaskTel_Bisen\Development\Data_Migration\conduit_kishore\conduit_kishore\ug_route_swc.csv"
        route_iqgeo_file=r"C:\Kishore\SaskTel_Bisen\SaskTel_Bisen\Development\Data_Migration\conduit_kishore\conduit_kishore\api_ug_route_ref_1.csv"
        str_iqgeo_file=r"C:\Kishore\SaskTel_Bisen\SaskTel_Bisen\Development\Data_Migration\conduit_kishore\conduit_kishore\api_data_swc_1.csv"
        # output_folder = "structures"
        output_folder = "route"
        
        # pole_config= r"C:\SaskTel_Bisen\Development\Data_Migration\config\pole.json"

    print ("File GDB - "+ fgdb_path)
    print ("File Config   "+ file_config)
    print ("Folder Name   "+ output_folder)

    try:
        current_dir=os.getcwd()  
        folder_path = os.path.join(current_dir,"output")
        if not os.path.exists(folder_path):
            os.makedirs(folder_path ) 
    except:
        logging.error(str(datetime.now())+" | "+"ERROR IN Creating folder | "+folder_path)

    try:
        
        log_folder_path = os.path.join(current_dir,"log")
        if not os.path.exists(log_folder_path):
            os.makedirs(log_folder_path ) 
    except:
        logging.error(str(datetime.now())+" | "+"ERROR IN Creating folder | "+log_folder_path)

    

    
    log_file =  log_folder_path +"\\CDIF_CREATION_LOG_"+     datetime.now().strftime("%Y%m%d_%H%M%S_%f")+".txt"

    logging.basicConfig(
    filename=log_file,  # Name of the log file
    level=logging.INFO,         # Minimum level of messages to log (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s', # Format of log messages
    filemode='a'                # 'a' for append, 'w' for overwrite
    )
    logging.info(str(datetime.now())+" | " + " ********** CDIF CREATION TASK STARTED ********** " )

    create_conduit_csv ( fgdb_path,file_config,output_folder,str_cdif_file,route_iqgeo_file,str_iqgeo_file)
     
    #"structures"
    logging.info(str(datetime.now())+" | " + " ********** CDIF CREATION TASK FINISHED ********** " )

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
from  util_services import UTILServices 
import cdif
# string_truncate_object=[]
# duplicate_geom=[]
# summary_rpt=[]
# bypassed_data=[]
# fields_issues=[]
 

 

def create_route_csv(gdb_path, config_json_file_path, folder):
    start_time = time.time()
    
    cdif_root_directory = os.getcwd() +"\\output\\"
     
    folder_full_path=cdif_root_directory+folder+"\\" 

    objCDIF=  cdif.IQGeoCDIF(cdif_root_directory,folder,config_json_file_path,gdb_path)
    objCDIF.InitiateProcess()
    if objCDIF.Initialized ==True:
        objCDIF.ProcessRecords()
        if  objCDIF.DataMigrationStatus==2:
            objCDIF.FinalizeCDIF()
  
    return




# def get_mapped_value(mapping_str, key):
     
#     mappings = {}
#     default_value = None

#     for pair in mapping_str.split(','):
#         if ':' not in pair:
#             continue
#         left, right = pair.split(':', 1)
#         if left.strip() == '*':
#             default_value = right.strip()
#         else:
#             mappings[left.strip()] = right.strip()

#     return mappings.get(key, default_value if default_value is not None else key)

 

if __name__ == "__main__":
    print("Task started...")
    if len(sys.argv) > 3:
        # sys.argv[0] is the script name, so we need at least 3 elements for 2 arguments
        # xlsfilename = sys.argv[1]
        # folder_path = sys.argv[2]

       

        fgdb_path=sys.argv[1]
        file_config=sys.argv[2]
        output_folder = sys.argv[3]
    else:
        fgdb_path=r'C:\SaskTel_Bisen\SaskTelData\SaskTel.gdb'
        file_config=r'C:\SaskTel_Bisen\Development\Data_Migration\config\st_struct_buried_splice_location.json'
        # file_config=r'C:\SaskTel_Bisen\Development\Data_Migration\config\vault.json'

        output_folder = "structures"
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
    
    #create_design_metadata(fgdb_path)
    # create_structure_csv ( fgdb_path,vault_config,"structures")

    create_route_csv ( fgdb_path,file_config,output_folder)

    #"structures"


    logging.info(str(datetime.now())+" | " + " ********** CDIF CREATION TASK FINISHED ********** " )
# else:
#         print ("Required arguments not provided.  python.exe  export_config  'excel file name'  'output folder path'")

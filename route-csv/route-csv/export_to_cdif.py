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

from typing import Dict, Optional, Union
import logging
from datetime import datetime
from shapely.ops import linemerge
from shapely.geometry import box



def create_folder_for_cdif(folder_name ):
    logging.info(str(datetime.now())+" | "+"Creating folder | "+folder_name)
    try:
        current_dir=os.getcwd() +"\\output"
        folder_path = os.path.join(current_dir,folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path ) 
    except:
        logging.error(str(datetime.now())+" | "+"ERROR IN Creating folder | "+folder_name)
  
    return
    
def create_design_metadata(gdb_path):
    file_name=os.getcwd() +"\\output\\package.metadata"
    logging.info(str(datetime.now())+" | "+"Creating design metadatafile | "+file_name)
    
    data=[
        ["property","value"],
        ["format","cdif"],
        ["coord_system","4326"],
        ["boundary",get_gdb_extent_as_wkb(gdb_path)]
    ]
    try:
        with open(file_name,'w',newline='') as csvfile:
            writer=csv.writer(csvfile)
            writer.writerows(data)
        print("Package Metadata written sucessfully.")
    except Exception as e:
        print("Package metadata file could not be written. Error occured : {e}")
        logging.error(str(datetime.now())+" | "+"Package metadata file could not be written. Error occured : {e} | "+file_name)


def get_gdb_extent_as_wkb(gdb_path, output_crs='EPSG:4326'):
    
    results={'layers':{},
             'combined_extent_wkb':None
             }
    layers = list_layers(gdb_path)
    gdf=gpd.read_file(gdb_path)
    
    # current_extent=gdf.total_bounds
    # gdf=gdf.to_crs(4326)
    

    # minx,miny,maxx,maxy=gdf.total_bounds

    # bbox_polygon=box(minx,miny,maxx,maxy)

    # current_extent=gdf.total_bounds
    
    
    
    layers=gpd.list_layers(gdb_path)
    combined_minx,combined_miny=float('inf'),float('inf')
    combined_maxx,combined_maxy=float('-inf'),float('-inf')

    gdf=gpd.read_file(gdb_path,layers="StructureWGS84")
        
    if gdf.crs is None:
        print(f"Warning: Layer{lyr} has no CRS")
        current_extent=gdf.total_bounds
    else:
        gdf=gdf.to_crs(output_crs)
        current_extent=gdf.total_bounds
        # layer_poly=Polygon([
        #         (current_extent[0],current_extent[1]),
        #         (current_extent[0],current_extent[3]),
        #         (current_extent[2],current_extent[3]),
        #         (current_extent[2],current_extent[1]),
        #         (current_extent[0],current_extent[1])
        #     ])
            # results['layers'][lyr]=layer_poly.wkb_hex
        combined_minx=min(combined_minx,current_extent[0])
        combined_miny=min(combined_miny,current_extent[1])
        combined_maxx=max(combined_maxx,current_extent[2])
        combined_maxy=max(combined_maxy,current_extent[3])
    

    # for lyr in layers:
    #     print(lyr)
    #     if lyr=="StructureWGS84":
    #         gdf=gpd.read_file(gdb_path,layers=lyr)
            
    #         # print(gdf)
    #         if len(gdf)==0:
    #             continue 
    #         if gdf.crs is None:
    #             print(f"Warning: Layer{lyr} has no CRS")
    #             current_extent=gdf.total_bounds
    #         else:
    #             gdf=gdf.to_crs(output_crs)
    #             current_extent=gdf.total_bounds
    #         layer_poly=Polygon([
    #             (current_extent[0],current_extent[1]),
    #             (current_extent[0],current_extent[3]),
    #             (current_extent[2],current_extent[3]),
    #             (current_extent[2],current_extent[1]),
    #             (current_extent[0],current_extent[1])
    #         ])
    #         # results['layers'][lyr]=layer_poly.wkb_hex
    #         combined_minx=min(combined_minx,current_extent[0])
    #         combined_miny=min(combined_miny,current_extent[1])
    #         combined_maxx=max(combined_maxx,current_extent[2])
    #         combined_maxy=max(combined_maxy,current_extent[3])

    if combined_minx!=float('inf'):
        combined_poly=Polygon([
            (combined_minx-0.0001,combined_miny-0.0001),
            (combined_minx-0.0001,combined_maxy+0.0001),
            (combined_maxx+0.0001,combined_maxy+0.0001),
            (combined_maxx+0.0001,combined_miny-0.0001),
            (combined_minx-0.0001,combined_miny-0.0001)
            
        ]
        )
 
    
      

    return combined_poly.wkb_hex


def create_field_mapping_file( folder_name, target_object, object_config_json):
    file_name=os.getcwd() +"\\output\\"+folder_name+"\\"+target_object+".fields"
    
    logging.info(str(datetime.now())+" | "+"Creating field mapping file | "+ file_name)

     

    try:
     
        fields=[]
         
        hdr_info=[["name","type","unit"]]
        fields.append(hdr_info)
        # for flds in type_mapping.items:
         
        mf = object_config_json.get("Attribute_Finalised")

        # link_structure_def =tgt_lyr_json.get("link_structure",None)

        # housing_info =tgt_lyr_json.get("housing_info",None)

        filtered_fields = [flds for flds in mf if (flds["FieldSource"]) =="NE"]
        geo_fields = [flds for flds in mf if (flds["Type"]) =="Geometry"]

        # uqfld=tgt_lyobject_config_jsonr_json.get("Source_ID")
        

        geomfld=geo_fields[0]["Name"]
        geomtype= object_config_json.get("Geometry_Type")

        hdr_info.append(["id","id",""]) #ID field column information 
        hdr_info.append([geomfld,geomtype,""])  

         
        
        for fld in filtered_fields:
            hdr_info.append([fld['Name'].lower(),fld['Field_Type'],])

        
        with open(file_name,'w',newline='') as csvfile:
                writer=csv.writer(csvfile)
                writer.writerows(hdr_info)
        print("Field Metadata written sucessfully for " + target_object)
        logging.info(str(datetime.now())+" | "+"Creating field mapping file completed for | "+ target_object)

    except Exception as e:
        print("Field metadata file could not be written. Error occured : {e}")
        logging.error(str(datetime.now())+" | "+"Error occured in create field mapping file : {e} | "+file_name)

def getEWKB(tempGeo, srcCRS, tgtCRS):


    # Reprojection of data if original data is in other then GCS - WGS84 
    transformer = Transformer.from_crs(srcCRS,tgtCRS,always_xy=True)
    trangeom=transform(transformer.transform,tempGeo)
    shaply_geom=shape(trangeom)
    wkb_data=shaply_geom.wkb_hex
    return wkb_data

def Progress_Bar(progress, total):
    percent = 100*(progress/float(total))
    # bar = '*' * int(percent)+'-'+(100-int(percent))
    print (f"\r| {percent:.2f}%",end="\r")



# ###route###

def create_route_csv(gdb_path, config_json_file_path, folder):
    logging.info("starting Route CSV creation:")

    start_time = time.time()

    with open(config_json_file_path, 'r') as file:
        # Load the JSON data from the file
        config_json = json.load(file)

    # config_json= json.load(config_json_file_path)
    # folder= config_json.get("Folder")
    object_name=config_json.get("Name")
    src_lyr=config_json.get("NE_Table")
    filter_column=config_json.get("Filter")
    filter_val=config_json.get("Filter_Value")

    foler_nm=os.getcwd() +"\\output\\"+folder+"\\" 
    print("Creating folder for CDIF " + foler_nm)
    create_folder_for_cdif(foler_nm)

    print("Creating field mapping file")
    create_field_mapping_file(folder,object_name,config_json)

    file_name=foler_nm+ "\\"+object_name+".csv"
    logging.info(str(datetime.now())+" | "+" creating CSV for route in | "+ file_name )

    try:
         # layers = list_layers(gdb_path)
        print("Opening File GDB " + gdb_path + " Layer "+ src_lyr)

        org_gdf=gpd.read_file(gdb_path,layer=src_lyr)

        print("Filtering for  " + filter_column + " = "+ filter_val)
        # gdf=org_gdf[org_gdf[filter_column]==filter_val]
        filter_values=[v.strip() for v in filter_val.split(',')]
        gdf=org_gdf[org_gdf[filter_column].isin(filter_values)]



        total_records=len(gdf)

        mf = config_json.get("Attribute_Finalised")

        filtered_fields = [flds for flds in mf if flds["FieldSource"]=="NE"]



        reference_fields=[flds for flds in mf if flds["Type"]=="Reference"]
        refset_fields=[flds for flds in mf if flds["Type"]=="Reference Set"]

        

        uqfld=config_json.get("Source_ID")  
        geo_fields = [flds for flds in mf if (flds["Type"]) =="Geometry"]
        # geomfld=config_json.get("Geometry")    
        geomfld=geo_fields[0]["Name"]
        # iqgeo_field_map=tgt_lyr_json.get("iqgeo_field_map")
        # uq_id_prefix=uqfld['uq_id_prefix']
        
        # src_geom_fld_name=geomfld['src_geom_fld_name']
        # iqgeo_ref_id=iqgeo_field_map['iqgeo_ref_id']
        # src_uq_fld=iqgeo_field_map['src_uq_fld']

        csv_data=[]
        clm_name=[]
        src_crs=gdf.crs
        tgt_crs="EPSG:4326"
        
        clm_name.append("id") #ID field column information 
        clm_name.append(geomfld)  

        

        for fld in filtered_fields:
            clm_name.append(fld['Name'].lower())



        ####adding reerence and ref set fields
        for fld in reference_fields+refset_fields:
            clm_name.append(fld['Name'].lower())



        # print("Hello", end="")

        
        rec_processed=0
        # Progress_Bar(0,total_records)
        print (f"\r{rec_processed} of {total_records}",end="\r")
        print("Processing data...  " ,end="")
        for index,row in gdf.iterrows():
            csv_row=[]
            # iqgeo_ref_id_val=uq_id_prefix +'/'+str(index)
            iqgeo_ref_id_val= object_name + str(row[uqfld])  

            # uq_fld_val=row[src_uq_fld]
            str_geom=row["geometry"]  #geomfld

            geom_wkb=getEWKB(str_geom,src_crs,tgt_crs)

            
            csv_row.append(iqgeo_ref_id_val)
            csv_row.append(geom_wkb)
            
            
            
            for fld in filtered_fields:
                fld_nm=fld['Name'].upper()
                fld_type=fld['Field_Type']
                fld_value = row[fld_nm]    
                
                csv_row.append(fld_value)



            #  reference field values
            for fld in reference_fields:
             fld_name = fld['Name'].lower()
             fld_val = f"{object_name}{str(row[uqfld])}_{fld_name}"
             csv_row.append(fld_val)

           #  reference set field values 
            for fld in refset_fields:
             fld_name = fld['Name'].lower()
             fld_val = f"{object_name}{str(row[uqfld])}_{fld_name}"
             csv_row.append(fld_val)
            
            csv_data.append(csv_row)
             
            rec_processed=rec_processed+1
            percent =int(100* (rec_processed / total_records))
            print (f"{rec_processed} of {total_records} - {percent} %",end="\r")


        print( str(rec_processed) + " rows processed." )

        with open(file_name,'w',newline='',encoding='utf-8') as csvfile:
            writer=csv.writer(csvfile)
            writer.writerow(clm_name)        
            writer.writerows(csv_data)
            end_time = time.time()
            elapsed_seconds = end_time - start_time
            if (elapsed_seconds>60):
                elapsed_seconds= int(elapsed_seconds/60)
                print(str(datetime.now())+" |  CSV completed with  - "+ str(rec_processed) +" records | "+ file_name + str(elapsed_seconds) + " minutes" )   

            else:

                print(str(datetime.now())+" |  CSV completed with  - "+ str(rec_processed) +" records | "+ file_name + str(elapsed_seconds) + " seconds" )   
            # logging.info(str(datetime.now())+" | " + " manhole CSV completed with records - "+ str(rec_processed) +" | "+ csvfile  )
            # logging.info(" | " + " manhole CSV completed with records -   "+ file_name  )

            folder_to_zip_from = os.getcwd() +"\\output\\" # Replace with your folder path
            output_zip_file = folder_to_zip_from+folder +'_cdif'+ datetime.now().strftime("%Y%m%d_%H%M%S_%f")+'.zip'
            files_to_include = ['package.metadata', folder +'\\'+object_name+".csv",  folder +'\\'+object_name+".fields"] # Replace with your desired files
            zip_selected_files(folder_to_zip_from, output_zip_file, files_to_include)


            logging.info(str(datetime.now())+" |  CSV completed with  - "+ str(rec_processed) +" records | "+ file_name  )


    except Exception as e:
        print("CSV  file could not be written. Error occured : " + str(e))
        logging.error(str(datetime.now())+" | "+"Error occured in  CSV  file :  " + str(e) +"| " + file_name)

    # gdf.to_file(f"{gdb_path}", layer=src_lyr, driver="OpenFileGDB")

    return


# ?C:\SaskTel_Bisen\SaskTelData\SaskTel.gdb
def zip_selected_files(folder_path, output_zip_name, selected_files):
    """
    Zips selected files from a specified folder into a new ZIP archive.

    Args:
        folder_path (str): The path to the folder containing the files.
        output_zip_name (str): The name of the output ZIP file (e.g., 'my_archive.zip').
        selected_files (list): A list of filenames (strings) to be included in the ZIP.
    """
    with zipfile.ZipFile(output_zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_name in selected_files:
            file_path = os.path.join(folder_path, file_name)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                zipf.write(file_path, arcname=file_name) # arcname ensures only the filename is used in the zip
            else:
                print(f"Warning: File '{file_name}' not found in '{folder_path}' and will not be added to the zip.")

       
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
        fgdb_path=r'C:\Users\PS001094296\Documents\route-csv\sample.gdb'
        file_config=r'C:\Users\PS001094296\Documents\route-csv\Route.json'
        output_folder = "routes"
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
    ########
    create_design_metadata(fgdb_path)
    #create_structure_csv ( fgdb_path,vault_config,"structures")
###############
    create_route_csv ( fgdb_path,file_config,output_folder)

    #"structures"


    logging.info(str(datetime.now())+" | " + " ********** CDIF CREATION TASK FINISHED ********** " )
# else:
#         print ("Required arguments not provided.  python.exe  export_config  'excel file name'  'output folder path'")

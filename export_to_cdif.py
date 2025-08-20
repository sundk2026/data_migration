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
string_truncate_object=[]
duplicate_geom=[]
summary_rpt=[]
bypassed_data=[]
fields_issues=[]
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
        print("Package metadata file could not be written. Error occured : {str(e)}")
        logging.error(str(datetime.now())+" | "+"Package metadata file could not be written. Error occured : {str(e)} | "+file_name)


def get_gdb_extent_as_wkb(gdb_path, output_crs='EPSG:4326'):
    
    results={'layers':{},
             'combined_extent_wkb':None
             }
    lyrList = list_layers(gdb_path)
    # gdf=gpd.read_file(gdb_path)
    
    # current_extent=gdf.total_bounds
    # gdf=gdf.to_crs(4326)
    

    # minx,miny,maxx,maxy=gdf.total_bounds

    # bbox_polygon=box(minx,miny,maxx,maxy)

    # current_extent=gdf.total_bounds
    
    
     
    combined_minx,combined_miny=float('inf'),float('inf')
    combined_maxx,combined_maxy=float('-inf'),float('-inf')

    gdf=gpd.read_file(gdb_path,layers=lyrList[0][0])
        
    if gdf.crs is None:
       
        current_extent=gdf.total_bounds
    else:
        gdf=gdf.to_crs(output_crs)
        current_extent=gdf.total_bounds
        
        combined_minx=min(combined_minx,current_extent[0])
        combined_miny=min(combined_miny,current_extent[1])
        combined_maxx=max(combined_maxx,current_extent[2])
        combined_maxy=max(combined_maxy,current_extent[3])
    
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
    file_name=os.getcwd() +"\\output\\"+folder_name+"\\"+target_object.lower()+".fields"
    
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
        geo_fields = [flds for flds in mf if (flds["Field_Type"]) =="Geometry"]
        if len(geo_fields)>0:
        # uqfld=tgt_lyobject_config_jsonr_json.get("Source_ID")
        

            geomfld=geo_fields[0]["Field_Name"]
            geomtype= object_config_json.get("Geometry_Type")

            hdr_info.append(["id","id",""]) #ID field column information 
            hdr_info.append([geomfld,geomtype,""])  

            
            
            for fld in filtered_fields:
                hdr_info.append([fld['Field_Name'].lower(),fld['Field_Type'],])
                fields_issues.append([fld['Field_Name'],0,0,0,fld['Mandatory']])
            
            with open(file_name,'w',newline='') as csvfile:
                    writer=csv.writer(csvfile)
                    writer.writerows(hdr_info)
            print("Field Metadata written sucessfully for " + target_object)
            logging.info(str(datetime.now())+" | "+"Creating field mapping file completed for | "+ target_object)
        else:
            print("ERROR: Geometry field not found in the config." )
            logging.info(str(datetime.now())+" | "+"ERROR:Geometry field not found in the config. ")

    except Exception as e:
        print('Field metadata file could not be written. Error occured : {str(e)}')
        logging.error(str(datetime.now())+" | "+"Error occured in create field mapping file : {str(e)} | "+file_name)

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

def create_structure_csv(gdb_path, config_json_file_path, folder):
    start_time = time.time()
    folder=folder.lower()
    summary_rpt.append(["records_skipped_due_to_parent_data_mismatch_issue",0])
    summary_rpt.append(["records_skipped_due_to_issue",0])
    summary_rpt.append(["number_of_records_truncated",0])
    summary_rpt.append(["number_of_geometry_duplicate",0])
    summary_rpt.append(["is_any_val_truncated",0])
    summary_rpt.append(["number_of_values_truncated",0])

     
    with open(config_json_file_path, 'r') as file:
        # Load the JSON data from the file
        config_json = json.load(file)

    # config_json= json.load(config_json_file_path)
    # folder= config_json.get("Folder")
    object_name=config_json.get("Name")
    src_lyr=config_json.get("NE_Table")
    filter_column=config_json.get("Filter")
    # filter_val=config_json.get("Filter_Value")

    foler_nm=os.getcwd() +"\\output\\"+folder+"\\" 
    print("Creating folder for CDIF " + foler_nm)
    create_folder_for_cdif(foler_nm)

    print("Creating field mapping file")
    create_field_mapping_file(folder,object_name,config_json)

    file_name=foler_nm+ "\\"+object_name.lower()+".csv"
    logging.info(str(datetime.now())+" | "+" creating CSV for manhole in | "+ file_name )

    try:
         # layers = list_layers(gdb_path)
        print("Opening File GDB " + gdb_path + " Layer "+ src_lyr)

        org_gdf=gpd.read_file(gdb_path,layer=src_lyr)

        print("Filtering for  " + filter_column) 
        gdf=apply_sql_like_filter(org_gdf,filter_column) 



        total_records=len(gdf)

        mf = config_json.get("Attribute_Finalised")

        filtered_fields = [flds for flds in mf if flds["FieldSource"]=="NE"]
        

        uqfld=config_json.get("Source_ID")  
        geo_fields = [flds for flds in mf if (flds["Field_Type"]) =="Geometry"]
        if len(geo_fields)==0:
            print("Geometry field not specified in the config.")

            return
        
        geomfld=geo_fields[0]["Field_Name"]
        
        csv_data=[]
        clm_name=[]
        src_crs=gdf.crs
        tgt_crs="EPSG:4326"
        
        clm_name.append("id") #ID field column information 
        clm_name.append(geomfld)  

        

        for fld in filtered_fields:
            clm_name.append(fld['Field_Name'].lower())

        # print("Hello", end="")

        
        rec_processed=0
        # Progress_Bar(0,total_records)
        # print (f"\r{rec_processed} of {total_records}",end="\r")
        print("Processing data...  " ,end="")
        obj_id_pre_fix=src_lyr.replace(" ", "_")
        for index,row in gdf.iterrows():
            csv_row=[]
            # iqgeo_ref_id_val=uq_id_prefix +'/'+str(index)
            idval=row[uqfld]
            iqgeo_ref_id_val= obj_id_pre_fix +'/'+ str( idval)  

            # uq_fld_val=row[src_uq_fld]
            str_geom=row["geometry"]  #geomfld

            geom_wkb=getEWKB(str_geom,src_crs,tgt_crs)

            
            csv_row.append(iqgeo_ref_id_val)
            csv_row.append(geom_wkb)
            
            
            is_any_val_truncated=False
            fld_indx=0
            for fld in filtered_fields:
                fld_nm=fld['Field_Name'].upper()
                src_nm=fld['Source'].upper()
                if src_nm!="":
                    fld_nm=src_nm
                if len(fld_nm)==0:
                    print(f"Invalid field name '{fld_nm}'. Terminatig the process." )
                    
                    return
                fld_value = row[fld_nm] 
                fld_type=fld['Field_Type']
                fld_mandatory=fld['Mandatory']
                domain_val=fld['DomainValue']
                row_fld_val=row[fld_nm]

                if str(row_fld_val)=='nan':
                    is_passed=True
                    fld_value=''
                else:
                    is_passed=False
                    is_passed, fld_value = check_field_type_and_value(fld_value,fld_type,idval,fld_nm,fld_indx,domain_val)

                if is_passed ==False:
                    bypassed_data.append([idval,fld_nm,row[fld_nm] ])
                    print(f"Value is not as per format for '{fld_value}' for row number '{idval}'. Bypassing the data by keeping it blank" )
                    continue
                
                if fld['ReplaceValue']!="":
                    fld_value = get_mapped_value( fld['ReplaceValue']  ,fld_value)
                
                if str(fld_value) ==  "None" :
                    fld_value=""
                    fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1
                # if fld_mandatory.lower()=='yes' & fld_value=="":
                #     fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1
                

                csv_row.append(fld_value)
                fld_indx+=1
                
            try:
                if is_any_val_truncated==True:
                    number_of_records_truncated+=1
                csv_data.append(csv_row)
                rec_processed+=1
            except:
                summary_rpt[1][1]+=1
                

            percent =int(100* (rec_processed / total_records))
            print (f"{rec_processed} of {total_records} - {percent} %",end="\r")


        print( str(rec_processed) + " rows processed." )

        with open(file_name,'w',newline='',encoding='utf-8') as csvfile:
            writer=csv.writer(csvfile)
            writer.writerow(clm_name)        
            writer.writerows(csv_data)

            number_of_geometry_duplicate,duplicate_geom=find_duplicates(csv_data)

            end_time = time.time()
            elapsed_seconds = end_time - start_time
            if (elapsed_seconds>60):
                elapsed_seconds= int(elapsed_seconds/60)
                print(str(datetime.now())+" |  CSV completed with  - "+ str(rec_processed) +" records | "+ file_name + " in "+ str(elapsed_seconds) + " minutes" )   

            else:

                print(str(datetime.now())+" |  CSV completed with  - "+ str(rec_processed) +" records | "+ file_name +" in "+  str(elapsed_seconds) + " seconds" )   
            # logging.info(str(datetime.now())+" | " + " manhole CSV completed with records - "+ str(rec_processed) +" | "+ csvfile  )
            # logging.info(" | " + " manhole CSV completed with records -   "+ file_name  )

            folder_to_zip_from = os.getcwd() +"\\output\\" # Replace with your folder path
            df_xl1 = pd.DataFrame(string_truncate_object, columns=['Object ID','Field Name', 'Original String', 'Truncated String'])
            df_xl2 = pd.DataFrame(duplicate_geom, columns=['Object ID','Geom'])
            df_xl3 = pd.DataFrame(bypassed_data, columns=['Object ID','Bypassed for Field','Field Value'])
            
            
            excel_file_path = folder_to_zip_from + '\\SummaryReport_'+ object_name.upper() +"_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".xlsx"
            # df_xl.to_excel(excel_file_path, index=False, sheet_name='TruncatedValues')

            with pd.ExcelWriter(excel_file_path, engine='xlsxwriter') as writer:
                df_xl1.to_excel(writer, sheet_name='TruncatedValues', index=False)
                df_xl2.to_excel(writer, sheet_name='DuplicateGeom', index=False)
                df_xl3.to_excel(writer, sheet_name='OutsideDomain', index=False)

            output_zip_file = folder_to_zip_from+folder +'_cdif'+ datetime.now().strftime("%Y%m%d_%H%M%S")+'.zip'
            files_to_include = ['package.metadata', folder +'\\'+object_name+".csv",  folder +'\\'+object_name+".fields"] # Replace with your desired files
            zip_selected_files(folder_to_zip_from, output_zip_file, files_to_include)
            

            prepare_summary_report(excel_file_path,start_time, end_time
                ,gdb_path,src_lyr, output_zip_file,object_name
                ,filter_column,  total_records,  rec_processed, summary_rpt[1][1]
                , summary_rpt[0][1], summary_rpt[2][1],len(string_truncate_object), number_of_geometry_duplicate,  fields_issues)

            logging.info(str(datetime.now())+" |  CSV completed with  - "+ str(rec_processed) +" records | "+ file_name  )


    except Exception as e:
        print("CSV  file could not be written. Error occured : " + str(e))
        logging.error(str(datetime.now())+" | "+"Error occured in  CSV  file :  " + str(e) +"| " + file_name)

    # gdf.to_file(f"{gdb_path}", layer=src_lyr, driver="OpenFileGDB")

    return
def check_domain_value(domain_csv, fld_val):
    try:
        values=[v.strip() for v in domain_csv.split(",")]
        return fld_val.strip() in values
    except Exception as e:
        print(f"Error occured during domain value check '{str(e)}' for domain '{domain_csv}' and value is '{fld_val}'")
         
def find_duplicates(csv_row):
    clm_index=1
    value_map=defaultdict(list)
    for rw in csv_row:
        key=rw[clm_index]
        value_map[key].append(rw)
    duplicate_geom=[]
    duplicates={k:v for k, v in value_map.items() if len(v)>1}
    
    
    for val , rows in duplicates.items():
            for rw in rows:
                csv_string=rw
                # csv_file = io.StringIO(csv_string)
                # csv_reader = csv.reader(csv_file)
                # first_row = next(csv_reader)
                obj_id = csv_string[0]
                geom = csv_string[1]

                duplicate_geom.append([obj_id,geom])

    return len(duplicate_geom)        , duplicate_geom

def check_field_type_and_value(field_value, field_type, obj_id,fld_nm,fld_indx,domain_val):
    value_is_as_per_type = False
    modified_value = None
    if field_value !=None :
        if isinstance(field_value, str) and field_value.strip().lower() in ["nan", ""]:
            
            fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1
            return True, modified_value
        try:
            if field_type in ["integer", "bigint"]:
                try:
                    modified_value = int(field_value)
                    if  math.isnan(field_value):
                        modified_value = None
                        fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1
                    value_is_as_per_type = True          
                except Exception as e:
                    fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                    print(f"Error: failed to parse numric '{field_value}':{e}")
            elif field_type in ["double", "float"]:
                try:
                    modified_value = float(field_value)
                    if  math.isnan(field_value):
                        modified_value = None
                        fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1
                    value_is_as_per_type = True
                except Exception as e:
                        fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                        print(f"Error: failed to parse numric '{field_value}':{e}")
            elif field_type.startswith("numeric"):
                try:
                    modified_value = float(field_value)
                    if  math.isnan(field_value):
                        modified_value = None
                        fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1
                    value_is_as_per_type = True
                except Exception as e:
                        fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                        print(f"Error: failed to parse numric '{field_value}':{e}")
            elif field_type == "boolean":
                try:
                    val = str(field_value).strip().lower()
                    if val in ["true", "1"]:
                        modified_value = True
                        value_is_as_per_type = True
                    elif val in ["false", "0"]:
                        modified_value = False
                        value_is_as_per_type = True
                    else:
                        fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1
                except Exception as e:
                        fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                        print(f"Error: failed to parse boolean '{field_value}':{e}")
            elif field_type.startswith("string"):
                try:
                    match=re.search(r'string\((\d+)\)',field_type)
                    max_len=int(match.group(1))
                    modified_value = str(field_value)
                    value_is_as_per_type = True
                    strlen= len(field_value)

                
                    if max_len<strlen:
                        modified_value = modified_value[:max_len]
                        string_truncate_object.append([obj_id,fld_nm, field_value,modified_value])
                        fields_issues[fld_indx][3]=fields_issues[fld_indx][3]+1
                except Exception as e:
                        fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                        print(f"Error: failed to parse string '{field_value}':{e}")
            elif field_type == "date":
                try:
                    date_val = datetime.strptime(str(field_value), "%Y-%m-%d").date()
                    modified_value = str(date_val)
                    value_is_as_per_type = True
                except Exception as e:
                    fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                    print(f"Error: failed to parse date '{field_value}':{e}")

            elif field_type == "timestamp":
                try:
                    if len(str(field_value))<7:
                        field_value = datetime(int(field_value), 1, 1, 0, 0, 0)
                        # Convert the datetime object to a Unix timestamp
                        # field_value = date_object.timestamp()
                        
                    timestamp_val = datetime.strptime(str(field_value), "%Y-%m-%d %H:%M:%S")
                    modified_value = str(timestamp_val)
                    value_is_as_per_type = True
                except Exception as e:
                    fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                    print(f"Error: failed to parse timestamp '{field_value}':{e}")
            elif field_type == "Foreign Key":
                try:
                    modified_value =  field_value
                    value_is_as_per_type = True
                except Exception as e:
                    fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                    print(f"Error: failed to parse timestamp '{field_value}':{e}")
            else:
                value_is_as_per_type = False
                modified_value = field_value
        except Exception as e:
            print(f"Error: failed to parse timestamp '{field_value}':{e}")
    else:
        value_is_as_per_type =True

    if domain_val !="":
        if field_value!=None:    
            if check_domain_value(domain_val,field_value)==False:
                fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                # if value_is_as_per_type==False:
                bypassed_data.append([obj_id,fld_nm,field_value ])


    return value_is_as_per_type, modified_value

def get_mapped_value(mapping_str, key):
     
    mappings = {}
    default_value = None

    for pair in mapping_str.split(','):
        if ':' not in pair:
            continue
        left, right = pair.split(':', 1)
        if left.strip() == '*':
            default_value = right.strip()
        else:
            mappings[left.strip()] = right.strip()

    return mappings.get(key, default_value if default_value is not None else key)

def get_mapped_value(mapping_str, key):
     
    mappings = {}
    default_value = None

    for pair in mapping_str.split(','):
        if ':' not in pair:
            continue
        left, right = pair.split(':', 1)
        if left.strip() == '*':
            default_value = right.strip()
        else:
            mappings[left.strip()] = right.strip()

    return mappings.get(key, default_value if default_value is not None else key)

def zip_selected_files(folder_path, output_zip_name, selected_files):
    
    with zipfile.ZipFile(output_zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_name in selected_files:
            file_path = os.path.join(folder_path, file_name)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                zipf.write(file_path, arcname=file_name) # arcname ensures only the filename is used in the zip
            else:
                print(f"Warning: File '{file_name}' not found in '{folder_path}' and will not be added to the zip.")

def apply_sql_like_filter(gdf: gpd.GeoDataFrame, condition: str) -> gpd.GeoDataFrame:


        """
        Applies SQL-like condition (e.g., used in ESRI) to a GeoDataFrame.
         Supports: AND, OR, =, <>, (), string/number literals.
         """

         # Step 1: Normalize SQL syntax to Python
        expr = condition
        expr = re.sub(r'\bAND\b', '&', expr, flags=re.IGNORECASE)
        expr = re.sub(r'\bOR\b', '|', expr, flags=re.IGNORECASE)
        expr = expr.replace('<>', '!=')

         # Step 2: Replace column names with gdf["col"]
        for col in gdf.columns:
            expr = re.sub(rf'\b{re.escape(col)}\b', f'gdf["{col}"]', expr)

        # Step 3: Replace '=' with '==', but only if not already part of !=, >=, <=, ==
        expr = re.sub(r'(?<![=!<>])=(?!=)', '==', expr)

        # Step 4: Add parentheses around each comparison for correct operator precedence
        expr = re.sub( r'(gdf\["[^"]+"\]\s*==\s*[^&|()]+)', r'(\1)', expr )
        expr = re.sub( r'(gdf\["[^"]+"\]\s*!=\s*[^&|()]+)', r'(\1)', expr )
        expr = re.sub( r'(gdf\["[^"]+"\]\s*>=\s*[^&|()]+)', r'(\1)', expr )
        expr = re.sub( r'(gdf\["[^"]+"\]\s*<=\s*[^&|()]+)', r'(\1)', expr )
        expr = re.sub( r'(gdf\["[^"]+"\]\s*>\s*[^&|()]+)', r'(\1)', expr )
        expr = re.sub( r'(gdf\["[^"]+"\]\s*<\s*[^&|()]+)', r'(\1)', expr )

    # Step 5: Evaluate
        try:
            mask = eval(expr)
            return gdf[mask]
        except Exception as e:
            raise ValueError(f"Error in data selection criteria, evaluating condition: {e}\nTranslated expression: {expr}")
        

def prepare_summary_report(excel_file_path,process_start_time, process_end_time
                ,source_file_gdb,source_table,cdif_zip_file,iqgeo_object_name
                ,filter_condition, total_records_selected, total_records_processed, records_skipped_due_to_issue
                , records_skipped_due_to_parent_data_mismatch_issue, number_of_records_truncated,
                number_of_values_truncated, number_of_geometry_duplicate,field_ary ):
    
    wb = load_workbook(excel_file_path)
    # Create a new sheet
    ws_openpyxl = wb.create_sheet('Summary',0)

    # Add data to the new sheet using openpyxl
    ws_openpyxl['A1'] = 'NE to IQGeo Object Migration Summary Report : ' + iqgeo_object_name
    ws_openpyxl.merge_cells('A1:D1')
    ws_openpyxl['A1'].font = Font(name='Arial', size=14, bold=True, color="FF0000") 
    ws_openpyxl['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws_openpyxl['A2'] = 'Start Time'
    ws_openpyxl['A3'] = "End Time"
    ws_openpyxl['A4'] = "Total Time Taken (min:sec)"
    ws_openpyxl['A5'] = "NE Source FileGDB"
    ws_openpyxl['A6'] = "NE Source Feature Layer"
    ws_openpyxl['A7'] = "Generated CDIF File"
    ws_openpyxl['A8'] = "IQGeo Object Name"
    ws_openpyxl['A9'] = "Condition Used to Select NE Data"
    ws_openpyxl['A10'] = "Total Records selected as per Condition"
    ws_openpyxl['A11'] = "Total Records Processed"
    ws_openpyxl['A12'] ="Records Skipped due to value / data type issue"
    ws_openpyxl['A13'] ="Records Skipped due to reference /parent data missing reason"
    ws_openpyxl['A14'] ="Number of Records where data trucated due to shorter length"
    ws_openpyxl['A15'] ="Number of values where data trucated due to shorter length"
    ws_openpyxl['A16'] ="Number of Duplicate Geometires"
    
    m, s = divmod(process_end_time-process_start_time, 60)

    ws_openpyxl['B2'] = datetime.fromtimestamp(process_start_time).strftime("%d-%b-%Y %H:%M:%S")
    ws_openpyxl['B3'] = datetime.fromtimestamp(process_end_time).strftime("%d-%b-%Y %H:%M:%S")
    ws_openpyxl['B4'] = str(int(m)) + ":" + str(int(s))
    ws_openpyxl['B5'] = source_file_gdb
    ws_openpyxl['B6'] = source_table
    ws_openpyxl['B7'] = cdif_zip_file
    ws_openpyxl['B8'] = iqgeo_object_name
    ws_openpyxl['B9'] = filter_condition
    ws_openpyxl['B10'] = total_records_selected
    ws_openpyxl['B11'] = total_records_processed
    ws_openpyxl['B12'] = records_skipped_due_to_issue
    ws_openpyxl['B13'] = records_skipped_due_to_parent_data_mismatch_issue
    ws_openpyxl['B14'] = number_of_records_truncated
    ws_openpyxl['B15'] =number_of_values_truncated
    ws_openpyxl['B16'] =number_of_geometry_duplicate

    

    ws_openpyxl.merge_cells('B2:D2')
    ws_openpyxl.merge_cells('B3:D3')
    ws_openpyxl.merge_cells('B4:D4')
    ws_openpyxl.merge_cells('B5:D5')
    ws_openpyxl.merge_cells('B6:D6')
    ws_openpyxl.merge_cells('B7:D7')
    ws_openpyxl.merge_cells('B8:D8')
    ws_openpyxl.merge_cells('B9:D9')
    ws_openpyxl.merge_cells('B10:D10')
    ws_openpyxl.merge_cells('B11:D11')
    ws_openpyxl.merge_cells('B12:D12')
    ws_openpyxl.merge_cells('B13:D13')
    ws_openpyxl.merge_cells('B14:D14')
    ws_openpyxl.merge_cells('B15:D15')
    ws_openpyxl.merge_cells('B16:D16')
     
    ws_openpyxl['A18'] ="Field Wise Abstract"
    ws_openpyxl.merge_cells('A18:D18')
    ws_openpyxl['A18'].font = Font(bold=True)
    ws_openpyxl['A18'].alignment  = Alignment(horizontal='center', vertical='center')

    ws_openpyxl['A19'] = 'Field Name'
    ws_openpyxl['B19'] = 'Mandatory ?'
    ws_openpyxl['C19'] = 'NULL Value Found'
    ws_openpyxl['D19'] = 'Outside Domain/Pick List Value'
    ws_openpyxl['E19'] = 'Data Truncated'
      


    ws_openpyxl.column_dimensions['A'].width = 60
    ws_openpyxl.column_dimensions['B'].width = 17
    ws_openpyxl.column_dimensions['C'].width = 30
    ws_openpyxl.column_dimensions['D'].width = 17
    ws_openpyxl.column_dimensions['E'].width = 17
    
    rwno=20
    for fld in field_ary:
        ws_openpyxl['A'+str(rwno)] = fld[0]
        ws_openpyxl['B'+str(rwno)] = fld[4]
        ws_openpyxl['C'+str(rwno)] = fld[1]
        ws_openpyxl['D'+str(rwno)] = fld[2]
        ws_openpyxl['E'+str(rwno)] = fld[3]
        if  fld[4].lower()=="yes":
            if int(fld[1])>0:
                ws_openpyxl['C'+str(rwno)].font = Font(bold=True, color="FF0000") 
        
        if int(fld[2])>0:
                ws_openpyxl['D'+str(rwno)].fill = PatternFill(start_color="FFFFCC00", end_color="FFFFCC00", fill_type="solid") # Goldenrod yellow

        if int(fld[3])>0:
                ws_openpyxl['E'+str(rwno)].fill = PatternFill(start_color="ff6900", end_color="ff6900", fill_type="solid") 

        rwno+=1
    # Save the modified workbook
    wb.active = ws_openpyxl
    wb.save(excel_file_path)

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
        file_config=r'C:\SaskTel_Bisen\Development\Data_Migration\config\building.json'
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

    create_structure_csv ( fgdb_path,file_config,output_folder)

    #"structures"


    logging.info(str(datetime.now())+" | " + " ********** CDIF CREATION TASK FINISHED ********** " )
# else:
#         print ("Required arguments not provided.  python.exe  export_config  'excel file name'  'output folder path'")

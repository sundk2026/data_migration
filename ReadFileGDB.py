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
from field_mapping import type_mapping,  manhole, ug_route, fiber_nap,conduit
import sqlite3

from typing import Dict, Optional, Union
import logging
from datetime import datetime
from shapely.ops import linemerge


def insert_data_into_sqlite1(conn ,  table_name, src_tbl, iqg_layer, src_clm_nm, iqgeo_clm_nm, data, in_str_fld,out_str_fld):
     
    try:
     
        cursor = conn.cursor()

        # Create table if it doesn't exist (example for a 'users' table)
        
        # Prepare the INSERT statement
        # Using '?' as placeholders for safe parameter substitution
        if isinstance(data, tuple):  # Single record
            insert_sql = f"INSERT INTO {table_name} ("+src_clm_nm+", "+iqgeo_clm_nm+") VALUES (?, ?);"
            cursor.execute(insert_sql, data)
        elif isinstance(data, list):  # Multiple records
            # if len(in_str_fld)==0:
            #     insert_sql = f"INSERT INTO {table_name}  ("+src_tbl+", "+iqg_layer+","+src_clm_nm+", "+iqgeo_clm_nm+")  VALUES (?,?,?, ?);"
            # else:
            insert_sql = f"INSERT INTO {table_name}  ("+src_tbl+", "+iqg_layer+","+src_clm_nm+", "+iqgeo_clm_nm+", "+in_str_fld+", "+out_str_fld+")  VALUES (?,?,?,?,?,?);"
                
            # insert_sql = f"INSERT INTO {table_name}  (?, ?,?,?)  VALUES (?,?,?, ?);"
            cursor.executemany(insert_sql, data)
        else:
            print("Invalid data format. Please provide a tuple or a list of tuples.")
            return

        conn.commit()
         

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()
def insert_data_into_sqlite2(conn ,  table_name, src_tbl, iqg_layer, src_clm_nm, iqgeo_clm_nm, data, str_fld_geom):
     
    try:
     
        cursor = conn.cursor()

        # Create table if it doesn't exist (example for a 'users' table)
        
        # Prepare the INSERT statement
        # Using '?' as placeholders for safe parameter substitution
        if isinstance(data, tuple):  # Single record
            insert_sql = f"INSERT INTO {table_name} ("+src_clm_nm+", "+iqgeo_clm_nm+") VALUES (?, ?);"
            cursor.execute(insert_sql, data)
        elif isinstance(data, list):  # Multiple records
            insert_sql = f"INSERT INTO {table_name}  ("+src_tbl+", "+iqg_layer+","+src_clm_nm+", "+iqgeo_clm_nm+", "+str_fld_geom+ ")  VALUES (?,?,?,?,?);"
                
            # insert_sql = f"INSERT INTO {table_name}  (?, ?,?,?)  VALUES (?,?,?, ?);"
            cursor.executemany(insert_sql, data)
        else:
            print("Invalid data format. Please provide a tuple or a list of tuples.")
            return

        conn.commit()
         

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()
def insert_data_into_sqlite3(conn ,  table_name, src_tbl, iqg_layer, src_clm_nm, iqgeo_clm_nm, data):
     
    try:
     
        cursor = conn.cursor()

        # Create table if it doesn't exist (example for a 'users' table)
        
        # Prepare the INSERT statement
        # Using '?' as placeholders for safe parameter substitution
        if isinstance(data, tuple):  # Single record
            insert_sql = f"INSERT INTO {table_name} ("+src_clm_nm+", "+iqgeo_clm_nm+") VALUES (?, ?);"
            cursor.execute(insert_sql, data)
        elif isinstance(data, list):  # Multiple records
            insert_sql = f"INSERT INTO {table_name}  ("+src_tbl+", "+iqg_layer+","+src_clm_nm+", "+iqgeo_clm_nm+")  VALUES (?,?,?,?);"
                
            # insert_sql = f"INSERT INTO {table_name}  (?, ?,?,?)  VALUES (?,?,?, ?);"
            cursor.executemany(insert_sql, data)
        else:
            print("Invalid data format. Please provide a tuple or a list of tuples.")
            return

        conn.commit()
         

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()


def create_folder_for_cdif(folder_name,lyr=""):
    logging.info(str(datetime.now())+" | "+"Creating folder | "+folder_name)
    try:
        current_dir=os.getcwd() +"\\output"
        folder_path = os.path.join(current_dir,folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path ) 
    except:
        logging.error(str(datetime.now())+" | "+"ERROR IN Creating folder | "+folder_name)
    # if (lyr!=""):
    #     folder_path = os.path.join(current_dir,folder_name+"\\"+lyr)
    #     if not os.path.exists(folder_path):
    #         os.makedirs(folder_path ) 

    
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
    layers = list_layers(gdb_path)
    # layers=gpd.list_layers(gdb_path)
    combined_minx,combined_miny=float('inf'),float('inf')
    combined_maxx,combined_maxy=float('-inf'),float('-inf')
    for lyr in layers:
        gdf=gpd.read_file(gdb_path,layers=lyr)
        # print(gdf)
        if len(gdf)==0:
            continue 
        if gdf.crs is None:
            print(f"Warning: Layer{lyr} has no CRS")
            current_extent=gdf.total_bounds
        else:
            gdf=gdf.to_crs(output_crs)
            current_extent=gdf.total_bounds
        layer_poly=Polygon([
            (current_extent[0],current_extent[1]),
            (current_extent[0],current_extent[3]),
            (current_extent[2],current_extent[3]),
            (current_extent[2],current_extent[1]),
            (current_extent[0],current_extent[1])
        ])
        # results['layers'][lyr]=layer_poly.wkb_hex
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
            # (combined_minx,combined_miny),
            # (combined_minx,combined_maxy),
            # (combined_maxx,combined_maxy),
            # (combined_maxx,combined_miny),
            # (combined_minx,combined_miny)
        ]
        )
    # results['combined_extent_wkb']=combined_poly.wkb_hex
    return combined_poly.wkb_hex
# def create_fields_file(gdb_path, folder_name,src_lyr, tgt_lyr):
#     create_folder_for_cdif(folder_name)
#     file_name=os.getcwd() +"\\output\\"+folder_name+"\\"+tgt_lyr+".fields"
#     # name,type,unit
#     fields=[]
#     gdf=gpd.read_file(gdb_path,layer=src_lyr )
#     schema=[(col,str(dtype)) for col,dtype in gdf.dtypes.items()]
     
#     hdr_info=["name","type","unit"]
#     fields.append(hdr_info)
#     fld_info=["manhole_id_iqg","string",""]
#     fields.append(fld_info)
#     fld_info=["location","point",""]
#     fields.append(fld_info)
#     column_types={}
#     for col,dtype in gdf.dtypes.items():
#             dtype_str=str(dtype)
#             col_type=type_mapping.get(dtype_str,dtype_str)
#             if col_type=='string':
#                  col_type=col_type+'(255)'
#             fld_info=[col,col_type,""]
#             fields.append(fld_info)     
#     try:
#         with open(file_name,'w',newline='') as csvfile:
#             writer=csv.writer(csvfile)
#             writer.writerows(fields)
#         print("Field Metadata written sucessfully for " + src_lyr)
#     except Exception as e:
#         print("Field metadata file could not be written. Error occured : {str(e)}")

def create_field_mapping_file( folder_name, tgt_lyr):
    file_name=os.getcwd() +"\\output\\"+folder_name+"\\"+tgt_lyr+".fields"
    logging.info(str(datetime.now())+" | "+"Creating field mapping file | "+ file_name)

    create_folder_for_cdif(folder_name)

    try:
    # name,type,unit
        fields=[]
        # gdf=gpd.read_file(gdb_path,layer=src_lyr )
        # schema=[(col,str(dtype)) for col,dtype in gdf.dtypes.items()]
        hdr_info=[["name","type","unit"]]
        fields.append(hdr_info)
        # for flds in type_mapping.items:
        tgt_lyr_json=eval(tgt_lyr)
        mf = tgt_lyr_json.get("mapped_fields")

        link_structure_def =tgt_lyr_json.get("link_structure",None)

        housing_info =tgt_lyr_json.get("housing_info",None)

        filtered_fields = [flds for flds in mf if len(flds["src"]) > 0]
        uqfld=tgt_lyr_json.get("iqg_uq_field_ref")
        hdr_info.append([uqfld['uq_fld_name'],uqfld['type'],uqfld['unit']])

        geomfld=tgt_lyr_json.get("geom")
        # iqgeo_field_map=tgt_lyr_json.get("iqgeo_field_map")
        if link_structure_def:
            iqg_in_structure = link_structure_def['iqg_in_structure']
            iqg_out_structure = link_structure_def['iqg_out_structure']
            iqg_in_structure_type = link_structure_def['iqg_in_structure_type']
            iqg_out_structure_type = link_structure_def['iqg_out_structure_type']    
            hdr_info.append([iqg_in_structure,iqg_in_structure_type,""])
            hdr_info.append([iqg_out_structure,iqg_out_structure_type,""])
        
        if housing_info:
            iqg_root_housing_fld = housing_info['iqg_root_housing_fld']
            iqg_housing_fld = housing_info['iqg_housing_fld']
            iqg_root_housing_fld_type = housing_info['iqg_root_housing_type']
            iqg_housing_fld_type = housing_info['iqg_housing_type']

            hdr_info.append([iqg_root_housing_fld,iqg_root_housing_fld_type,""])
            hdr_info.append([iqg_housing_fld,iqg_housing_fld_type,""])
        
        hdr_info.append([geomfld['geom_fld'],geomfld['type'], ""])
        
        for fld in filtered_fields:
            hdr_info.append([fld['iqg_fld'],fld['type'],fld['unit']])

        # for nm in mf:
            # if nm['src']
        with open(file_name,'w',newline='') as csvfile:
                writer=csv.writer(csvfile)
                writer.writerows(hdr_info)
        print("Field Metadata written sucessfully for " + tgt_lyr)
        logging.info(str(datetime.now())+" | "+"Creating field mapping file completed for | "+ tgt_lyr)

    except Exception as e:
        print("Field metadata file could not be written. Error occured : {str(e)}")
        logging.error(str(datetime.now())+" | "+"Error occured in create field mapping file : {str(e)} | "+file_name)

# def create_csv_manhole(gdb_path,src_lyr,clm_name, clm_value,geom_clm,folder_name):
#     create_folder_for_cdif(folder_name)
#     # layers = list_layers(gdb_path)
#     gdf=gpd.read_file(gdb_path,layer=src_lyr)
#     df =pd.DataFrame(gdf.drop(columns=geom_clm))
#     csv_data=[]
#     clm_name=[]
#     src_crs=gdf.crs
#     tgt_crs="EPSG:4326"
#     clm_name.append( "manhole_id_iqg")  
#     clm_name.append("location")
#     for col_name in df.columns:
#         clm_name.append( col_name)  
#     for index,row in gdf.iterrows():

#         add_attribute=pd.Series(['manhole/'+str(index),getEWKB(row['geometry'],src_crs,tgt_crs)])
       
#         attributes=pd.concat([add_attribute,row.drop('geometry')],ignore_index=True)
#         #.combine(add_attribute)
#         csv_data.append(attributes)
#     foler_nm=os.getcwd() +"\\output\\"+folder_name+"\\" 
#     file_name=foler_nm+ "\\"+clm_value+".csv"
#     with open(file_name,'w',newline='') as csvfile:
#         writer=csv.writer(csvfile)
#         writer.writerow(clm_name)        
#         writer.writerows(csv_data)
#         print("Field Metadata written sucessfully for " + src_lyr)   

def create_csv_manhole_adv(gdb_path,src_lyr,clm_name, clm_value,geom_clm,folder_name, db_name):
    foler_nm=os.getcwd() +"\\output\\"+folder_name+"\\" 
    file_name=foler_nm+ "\\"+clm_value+".csv"
    logging.info(str(datetime.now())+" | "+" creating CSV for manhole in | "+ file_name )
    try:
        create_folder_for_cdif(folder_name)
        # layers = list_layers(gdb_path)
        gdf=gpd.read_file(gdb_path,layer=src_lyr)
        df =pd.DataFrame(gdf.drop(columns=geom_clm))
        tgt_lyr_json=eval(clm_value)
        mf = tgt_lyr_json.get("mapped_fields")
        
        filtered_fields = [flds for flds in mf if len(flds["src"]) >0]
        
        filtered_fields = [flds for flds in mf if flds["IQGEO/NE"]=="NE"]
        

        uqfld=tgt_lyr_json.get("iqg_uq_field_ref")
        geomfld=tgt_lyr_json.get("geom")
        iqgeo_field_map=tgt_lyr_json.get("iqgeo_field_map")
        uq_id_prefix=uqfld['uq_id_prefix']
        
        src_geom_fld_name=geomfld['src_geom_fld_name']
        iqgeo_ref_id=iqgeo_field_map['iqgeo_ref_id']
        src_uq_fld=iqgeo_field_map['src_uq_fld']
        csv_data=[]
        clm_name=[]
        src_crs=gdf.crs
        tgt_crs="EPSG:4326"
        
        
        clm_name.append(uqfld['uq_fld_name'] )
        clm_name.append(geomfld['geom_fld'] )

        for fld in filtered_fields:
            clm_name.append(fld['iqg_fld'])
        # for col_name in df.columns:
        #     clm_name.append( col_name)  
        conn = None
        conn = sqlite3.connect(db_name)
        mapping_data_to_insert_in_db=[]
        rec_processed=0
        for index,row in gdf.iterrows():
            csv_row=[]
            # iqgeo_ref_id_val=uq_id_prefix +'/'+str(index)
            iqgeo_ref_id_val=row["OBJ_ID"]  

            uq_fld_val=row[src_uq_fld]
            str_geom=row[src_geom_fld_name]

            geom_wkb=getEWKB(str_geom,src_crs,tgt_crs)

            
            csv_row.append(iqgeo_ref_id_val)
            csv_row.append(geom_wkb)
            for fld in filtered_fields:
                fld_nm=fld['src']
                fld_type=fld['type']
                
                if len(fld_nm)>0:
                    fld_value = row[fld_nm]    
                else:
                    if fld_type=="double" or fld_type=="integer"  or fld_type=="double"  or fld_type=="double"  or fld_type=="double" :
                        fld_value=0
                    else:
                        if fld_type=="date"  :
                            fld_value=""
                        else:
                            fld_value="-"
                csv_row.append(fld_value)
            # add_attribute=pd.Series([iqgeo_ref_id_val,geom_wkb])   
            # attributes=pd.concat([add_attribute,row.drop(src_geom_fld_name)],ignore_index=True)
            # gdf.loc[index, iqgeo_ref_id ] = iqgeo_ref_id
            # "iqgeo_field_map":{"uq_fld_name":"uuid","iqgeo_ref_id":"iqgeo_ref_id"},
            #.combine(add_attribute)
            # csv_data.append(attributes)
            csv_data.append(csv_row)
            mapping_data_to_insert_in_db.append([src_lyr,clm_value, uq_fld_val,iqgeo_ref_id_val,str(str_geom.x) +","+ str(str_geom.y)])
            rec_processed=rec_processed+1
        insert_data_into_sqlite2(conn,'STRUCTURE_id_mapping','src_table','tgt_layer',src_uq_fld,iqgeo_ref_id, mapping_data_to_insert_in_db,'ref_feature_geom')
        # (conn ,  table_name, src_tbl, iqg_layer, src_clm_nm, iqgeo_clm_nm, data):
        # insert_sql = f"INSERT INTO {table_name}  ("+src_tbl+", "+iqg_layer+","+src_clm_nm+", "+iqgeo_clm_nm+")  VALUES (?,?,?, ?);"

        with open(file_name,'w',newline='') as csvfile:
            writer=csv.writer(csvfile)
            writer.writerow(clm_name)        
            writer.writerows(csv_data)
            print("Field Metadata written sucessfully for " + src_lyr)   
            # logging.info(str(datetime.now())+" | " + " manhole CSV completed with records - "+ str(rec_processed) +" | "+ csvfile  )
            # logging.info(" | " + " manhole CSV completed with records -   "+ file_name  )
            logging.info(str(datetime.now())+" | Manhole CSV completed with  - "+ str(rec_processed) +" records | "+ file_name  )


    except Exception as e:
        print("Field manhole CSV  file could not be written. Error occured : {str(e)}")
        logging.error(str(datetime.now())+" | "+"Error occured in manhole CSV  file : {str(e)} | " + file_name)

    # gdf.to_file(f"{gdb_path}", layer=src_lyr, driver="OpenFileGDB")

def export_all_structure():

    export_structure('VAULT')
     
    

    return
def export_structure(for_structure):


    return


def create_csv_ugroute(gdb_path,src_lyr,clm_names, clm_value,geom_clm,folder_name, db_name):
    # declaration local arrays
    foler_nm=os.getcwd() +"\\output\\"+folder_name+"\\" 
    file_name=foler_nm+ "\\"+clm_value+".csv"
    logging.info(str(datetime.now())+" | "+" creating CSV for ugroute in | "+ file_name )
    try:
        create_folder_for_cdif(folder_name)
        # layers = list_layers(gdb_path)
        # gdb_reader = FileGDBReader(gdb_path)
        gdf=gpd.read_file(gdb_path,layer=src_lyr)
        # gdf = gdb_reader.read_layer(src_lyr)
        # df =pd.DataFrame(gdf.drop(columns=geom_clm))
        tgt_lyr_json=eval(clm_value)
        mf = tgt_lyr_json.get("mapped_fields")
        filtered_fields = [flds for flds in mf if len(flds["src"]) > 0]
        uqfld=tgt_lyr_json.get("iqg_uq_field_ref")
        geomfld=tgt_lyr_json.get("geom")
        link_structure_def =tgt_lyr_json.get("link_structure")
        in_st_fld=link_structure_def['in_str_fld']
        out_st_fld=link_structure_def['out_str_fld']
        reference_table=link_structure_def['reference_table']
        iqg_in_structure = link_structure_def['iqg_in_structure']
        iqg_out_structure = link_structure_def['iqg_out_structure']
        

        # ":{"in_str_fld":"from_structure","out_str_fld":"to_structure"},

        iqgeo_field_map=tgt_lyr_json.get("iqgeo_field_map")
        uq_id_prefix=uqfld['uq_id_prefix']
        src_geom_fld_name=geomfld['src_geom_fld_name']
        iqgeo_ref_id=iqgeo_field_map['iqgeo_ref_id']
        src_uq_fld=iqgeo_field_map['src_uq_fld']

        csv_data=[]
        clm_name=[]
        src_crs=gdf.crs
        tgt_crs="EPSG:4326"
        clm_name.append(uqfld['uq_fld_name'] )
        clm_name.append(iqg_in_structure )
        clm_name.append(iqg_out_structure ) 
        clm_name.append(geomfld['geom_fld'] )


        for fld in filtered_fields:
            clm_name.append(fld['iqg_fld'])
        # for col_name in df.columns:
        #     clm_name.append( col_name)  
        conn = None
        conn = sqlite3.connect(db_name)
        mapping_data_to_insert_in_db=[]
        
        rec_processed=0

        for index,row in gdf.iterrows():
            
            in_str_id,in_str_geom=find_ref_structure(reference_table,row[in_st_fld],conn)
            out_str_id,out_str_geom=find_ref_structure(reference_table,row[out_st_fld],conn)
            # parent_geom=find_parent_geom(gdb_path,src_table,src_geom_fld_name,row[in_st_fld] )
            # roads_layer = gdb_reader.read_layer(src_table,filter_query="uuid = '"+row[in_st_fld]+"'",columns=["geometry"])
            
            csv_row=[]
            # iqgeo_ref_id_val=uq_id_prefix +'/'+str(index)
            iqgeo_ref_id_val=row["OBJ_ID"]  

            uq_fld_val=row[src_uq_fld]
            org_line_geom=row[src_geom_fld_name]
            merged_line = linemerge(org_line_geom)
            
            # new_geom=replace_line_vertices(line_geom,in_str_geom,out_str_geom,None)
            # in_pt_ar=in_str_geom.split(',')
            # out_pt_ar=out_str_geom.split(',')
            
            # pt1={"x":in_pt_ar[0],"y":in_pt_ar[1]}
            # pt2={"x":out_pt_ar[0],"y":out_pt_ar[1]}
            new_geom=change_multilinestring_endpoints(merged_line,in_str_geom,out_str_geom)

            geom_wkb=getEWKB(new_geom,src_crs,tgt_crs)
            # geom_wkb=getEWKB(merged_line,src_crs,tgt_crs)
            

            csv_row.append(iqgeo_ref_id_val)
            csv_row.append(in_str_id)
            csv_row.append(out_str_id)
            csv_row.append(geom_wkb)
            
            for fld in filtered_fields:
                fld_nm=fld['src']
                fld_type=fld['type']
                
                if len(fld_nm)>0:
                    fld_value = row[fld_nm]    
                else:
                    if fld_type=="double" or fld_type=="integer"  or fld_type=="double"  or fld_type=="double"  or fld_type=="double" :
                        fld_value=0
                    else:
                        if fld_type=="date"  :
                            fld_value=""
                        else:
                            fld_value="-"

                csv_row.append(fld_value)

                # csv_row.append(row[fld['src']])
            # add_attribute=pd.Series([iqgeo_ref_id_val,geom_wkb])   
            # attributes=pd.concat([add_attribute,row.drop(src_geom_fld_name)],ignore_index=True)
            # gdf.loc[index, iqgeo_ref_id ] = iqgeo_ref_id
            # "iqgeo_field_map":{"uq_fld_name":"uuid","iqgeo_ref_id":"iqgeo_ref_id"},
            #.combine(add_attribute)
            # csv_data.append(attributes)
            csv_data.append(csv_row)
            mapping_data_to_insert_in_db.append([src_lyr,clm_value, uq_fld_val,iqgeo_ref_id_val,in_str_id,out_str_id])
            rec_processed=rec_processed+1
            if merged_line!=new_geom:
                org_geom_wkb=getEWKB(merged_line,src_crs,tgt_crs)
                
                logging.warning(str(datetime.now())+" | "+"UG_ROUTE GEOM_UPDATE FOR | "+str(iqgeo_ref_id_val) + " | " + org_geom_wkb + " TO |" + geom_wkb )
        
        insert_data_into_sqlite1(conn,'route_id_mapping','src_table','tgt_layer',src_uq_fld,iqgeo_ref_id, mapping_data_to_insert_in_db,"in_structure_id","out_structure_id")

        with open(file_name,'w',newline='') as csvfile:
            writer=csv.writer(csvfile)
            writer.writerow(clm_name)        
            writer.writerows(csv_data)
            print("Field Metadata written sucessfully for " + src_lyr)   
            logging.info(str(datetime.now())+" | " + "UG_ROUTE CSV completed with records - "+ str(rec_processed) +" records | "+ file_name   )

        if conn:
            conn.close()
    except Exception as e:
        print("Field metadata file could not be written. Error occured : {str(e)}")
        logging.error(str(datetime.now())+" | "+"Error occured in UG_ROUTE : {str(e)} | " + file_name)

def create_csv_fiber_nap(gdb_path,src_lyr, clm_value,geom_clm,folder_name, db_name):
    # declaration local arrays
    create_folder_for_cdif(folder_name)
    # layers = list_layers(gdb_path)
    foler_nm=os.getcwd() +"\\output\\"+folder_name+"\\" 
    file_name=foler_nm+ "\\"+clm_value+".csv"
    logging.info(str(datetime.now())+" | "+" creating CSV for ugroute in | "+ file_name )
    try:
        gdf=gpd.read_file(gdb_path,layer=src_lyr)
        df =pd.DataFrame(gdf.drop(columns=geom_clm))
        tgt_lyr_json=eval(clm_value)
        mf = tgt_lyr_json.get("mapped_fields")
        filtered_fields = [flds for flds in mf if len(flds["src"]) > 0]
        uqfld=tgt_lyr_json.get("iqg_uq_field_ref")
    

        geomfld=tgt_lyr_json.get("geom")
        housing_info =tgt_lyr_json.get("housing_info")   
        
        reference_table=housing_info['reference_table']
        iqg_root_housing_fld = housing_info['iqg_root_housing_fld']
        iqg_housing_fld = housing_info['iqg_housing_fld']
        ref_str_fld= housing_info['ref_str_fld']

        # ":{"in_str_fld":"from_structure","out_str_fld":"to_structure"},

        iqgeo_field_map=tgt_lyr_json.get("iqgeo_field_map")
        uq_id_prefix=uqfld['uq_id_prefix']
        src_geom_fld_name=geomfld['src_geom_fld_name']
        iqgeo_ref_id=iqgeo_field_map['iqgeo_ref_id']
        src_uq_fld=iqgeo_field_map['src_uq_fld']

        csv_data=[]
        clm_name=[]
        src_crs=gdf.crs
        tgt_crs="EPSG:4326"
        clm_name.append(uqfld['uq_fld_name'] )
        clm_name.append(iqg_root_housing_fld )
        clm_name.append(iqg_housing_fld ) 
        clm_name.append(geomfld['geom_fld'] )


        for fld in filtered_fields:
            clm_name.append(fld['iqg_fld'])
        # for col_name in df.columns:
        #     clm_name.append( col_name)  
        conn = None
        conn = sqlite3.connect(db_name)
        mapping_data_to_insert_in_db=[]
        
        rec_processed=0
        for index,row in gdf.iterrows():
            ref_str_id,parent_str_geom=find_ref_structure(reference_table,row[ref_str_fld],conn)
            pt1=parent_str_geom[0].split(',')
            point1 = Point(pt1[0], pt1[1]) 
            csv_row=[]
            # iqgeo_ref_id_val=uq_id_prefix +'/'+str(index)
            iqgeo_ref_id_val=row["OBJ_ID"]  

            uq_fld_val=row[src_uq_fld]
            geom_wkb=getEWKB(row[src_geom_fld_name],src_crs,tgt_crs)
            geom_wkb_parent=getEWKB(point1,src_crs,tgt_crs)
            
            csv_row.append(iqgeo_ref_id_val)
            csv_row.append(ref_str_id)      #root housing
            csv_row.append(ref_str_id)      # housing
            csv_row.append(geom_wkb_parent)
            
            for fld in filtered_fields:
                # csv_row.append(row[fld['src']])
                fld_nm=fld['src']
                fld_type=fld['type']
                if len(fld_nm)>0:
                    fld_value = row[fld_nm]    
                else:
                    if fld_type=="double" or fld_type=="integer"  or fld_type=="double"  or fld_type=="double"  or fld_type=="double" :
                        fld_value=0
                    else:
                        if fld_type=="date"  :
                            fld_value=""
                        else:
                            fld_value="-"

                csv_row.append(fld_value)
            
            csv_data.append(csv_row)
            rec_processed=rec_processed+1

            if geom_wkb!=geom_wkb_parent:
                logging.warning(str(datetime.now())+" | "+"FIBER_NAP GEOM_UPDATE FOR | "+iqgeo_ref_id_val + " | " + geom_wkb + " TO |" + geom_wkb_parent )
            # mapping_data_to_insert_in_db.append([src_lyr,clm_value, iqgeo_ref_id_val,uq_fld_val])       
            mapping_data_to_insert_in_db.append([src_lyr,clm_value, uq_fld_val,iqgeo_ref_id_val,str(point1.x) +","+ str(point1.y)])

        # insert_data_into_sqlite2(conn,'equipment_id_mapping','src_table','tgt_layer',src_uq_fld,iqgeo_ref_id, mapping_data_to_insert_in_db,geom_wkb_parent)
        
        insert_data_into_sqlite2(conn,'equipment_id_mapping','src_table','tgt_layer',src_uq_fld,iqgeo_ref_id, mapping_data_to_insert_in_db,'ref_feature_geom')
        with open(file_name,'w',newline='') as csvfile:
            writer=csv.writer(csvfile)
            writer.writerow(clm_name)        
            writer.writerows(csv_data)
            print("Field Metadata written sucessfully for " + src_lyr)   
            logging.info(str(datetime.now())+" | " + " FIBER NAP CSV completed with records - "+ str(rec_processed) +" records | "+ file_name  )

        if conn:
            conn.close()
    except Exception as e:
        logging.error(str(datetime.now())+" | "+"Error occured in create Fiber Nap : {str(e)} | " + file_name)

def create_csv_conduit(gdb_path,src_lyr,clm_names, clm_value,geom_clm,folder_name, db_name):
    # declaration local arrays
    foler_nm=os.getcwd() +"\\output\\"+folder_name+"\\" 
    file_name=foler_nm+ "\\"+clm_value+".csv"
    try:
        create_folder_for_cdif(folder_name)
        # layers = list_layers(gdb_path)
        gdf=gpd.read_file(gdb_path,layer=src_lyr)
        
        tgt_lyr_json=eval(clm_value)
        mf = tgt_lyr_json.get("mapped_fields")
        filtered_fields = [flds for flds in mf if len(flds["src"]) > 0]
        uqfld=tgt_lyr_json.get("iqg_uq_field_ref")
        geomfld=tgt_lyr_json.get("geom")
        link_structure_def =tgt_lyr_json.get("link_structure")
        in_st_fld=link_structure_def['in_str_fld']
        out_st_fld=link_structure_def['out_str_fld']
        reference_table=link_structure_def['reference_table']
        iqg_in_structure = link_structure_def['iqg_in_structure']
        iqg_out_structure = link_structure_def['iqg_out_structure']
        
        housing_info =tgt_lyr_json.get("housing_info")   
        
        housing_reference_table=housing_info['reference_table']
        iqg_root_housing_fld = housing_info['iqg_root_housing_fld']
        iqg_housing_fld = housing_info['iqg_housing_fld']
        ref_str_fld= housing_info['ref_str_fld']

        # ":{"in_str_fld":"from_structure","out_str_fld":"to_structure"},

        iqgeo_field_map=tgt_lyr_json.get("iqgeo_field_map")
        uq_id_prefix=uqfld['uq_id_prefix']
        src_geom_fld_name=geomfld['src_geom_fld_name']
        iqgeo_ref_id=iqgeo_field_map['iqgeo_ref_id']
        src_uq_fld=iqgeo_field_map['src_uq_fld']

        csv_data=[]
        clm_name=[]
        src_crs=gdf.crs
        tgt_crs="EPSG:4326"
        clm_name.append(uqfld['uq_fld_name'] )
        clm_name.append(iqg_in_structure )
        clm_name.append(iqg_out_structure ) 

        clm_name.append(iqg_root_housing_fld )
        clm_name.append(iqg_housing_fld ) 

        clm_name.append(geomfld['geom_fld'] )

        for fld in filtered_fields:
            clm_name.append(fld['iqg_fld'])
        # for col_name in df.columns:
        #     clm_name.append( col_name)  
        conn = None
        conn = sqlite3.connect(db_name)
        mapping_data_to_insert_in_db=[]
        rec_processed=0
        for index,row in gdf.iterrows():
            
            in_str_id,in_str_geom=find_ref_structure(reference_table,row[in_st_fld],conn)
            out_str_id,out_str_geom=find_ref_structure(reference_table,row[out_st_fld],conn)
            
            housing_ref_id=find_ref_housing(housing_reference_table,row[src_uq_fld] , in_str_id,conn)


            

            csv_row=[]
            # iqgeo_ref_id_val=uq_id_prefix +'/'+str(index)
            iqgeo_ref_id_val=row["OBJ_ID"]  

            uq_fld_val=row[src_uq_fld]

            org_line_geom=row[src_geom_fld_name]
            merged_line = linemerge(org_line_geom)
                      
            new_geom=change_multilinestring_endpoints(merged_line,in_str_geom,out_str_geom)

            geom_wkb=getEWKB(new_geom,src_crs,tgt_crs)
            csv_row.append(iqgeo_ref_id_val)
            csv_row.append(in_str_id)
            csv_row.append(out_str_id)
            csv_row.append(housing_ref_id)
            csv_row.append(housing_ref_id)
            
            csv_row.append(geom_wkb)
            
            for fld in filtered_fields:
                # csv_row.append(row[fld['src']])
                fld_nm=fld['src']
                fld_type=fld['type']
                
                if len(fld_nm)>0:
                    fld_value = row[fld_nm]    
                else:
                    if fld_type=="double" or fld_type=="integer"  or fld_type=="double"  or fld_type=="double"  or fld_type=="double" :
                        fld_value=0
                    else:
                        if fld_type=="date"  :
                            fld_value=""
                        else:
                            fld_value="-"
                csv_row.append(fld_value)
    

            csv_data.append(csv_row)
            rec_processed=rec_processed+1
            
            if merged_line!=new_geom:
                org_geom_wkb=getEWKB(merged_line,src_crs,tgt_crs)
                logging.warning(str(datetime.now())+" | "+"CONDUIT GEOM_UPDATE FOR | "+str(iqgeo_ref_id_val) + " | " + org_geom_wkb + " TO |" + geom_wkb )
        
            
            mapping_data_to_insert_in_db.append([src_lyr,clm_value, uq_fld_val,iqgeo_ref_id_val])
        

        # insert_data_into_sqlite(conn,'STRUCTURE_id_mapping','src_table','tgt_layer',src_uq_fld,iqgeo_ref_id, mapping_data_to_insert_in_db)
        
        with open(file_name,'w',newline='') as csvfile:
            writer=csv.writer(csvfile)
            writer.writerow(clm_name)        
            writer.writerows(csv_data)
            print("Field Metadata written sucessfully for " + src_lyr)   
            logging.info(str(datetime.now())+" | " + " CONDUIT CSV completed with records - "+str(rec_processed) +" records | "+ file_name  )

        if conn:
            conn.close()
    except Exception as e:
        # print("Field metadata file could not be written. Error occured : {str(e)}")
        logging.error(str(datetime.now())+" | "+"Error occured in CONDUIT : {str(e)} | " + file_name)

def find_ref_structure(ref_table, str_id,conn):
    cursor = conn.cursor()
    query = f"SELECT iqgeo_ref_id,ref_feature_geom FROM {ref_table}  WHERE uuid=?"

    cursor.execute(query,(str_id,) )
    rows = cursor.fetchall()
    if len(rows)==1:
        # return rows['iqgeo_ref_id']
        id_val=[row[0] for row in rows]
        geom_val=[row[1] for row in rows]

        return id_val[0] ,geom_val 
    else:
        return "",""

def find_ref_housing(ref_table, str_id,instr_id, conn):
    cursor = conn.cursor()
    query = f"SELECT iqgeo_ref_id FROM {ref_table}  WHERE uuid=? and in_structure_id=?"

    cursor.execute(query,(str_id,instr_id,) )
    rows = cursor.fetchall()
    if len(rows)==1:
        # return rows['iqgeo_ref_id']
        id_val=[row[0] for row in rows]
        return id_val[0]  
    else:
        return ""
    
def find_parent_geom(gdb_path, ref_layer, ref_column,ref_value):
    ref_gdf=gpd.read_file(gdb_path,layer=ref_layer)
    matches=ref_gdf[ref_gdf[ref_column]==ref_value]
    if len(matches)==0:
        return None
    else:
        return matches
    
def getEWKB(tempGeo, srcCRS, tgtCRS):


    # Reprojection of data if original data is in other then GCS - WGS84 
    transformer = Transformer.from_crs(srcCRS,tgtCRS,always_xy=True)
    trangeom=transform(transformer.transform,tempGeo)
    shaply_geom=shape(trangeom)
    wkb_data=shaply_geom.wkb_hex
    return wkb_data

def change_multilinestring_endpoints(multilinestring, new_first_point, new_last_point):
    """
    Changes the first and last vertex of a MultiLineString geometry.

    Args:
        multilinestring (shapely.geometry.MultiLineString): The input MultiLineString.
        new_first_point (shapely.geometry.Point): The new point for the first vertex.
        new_last_point (shapely.geometry.Point): The new point for the last vertex.

    Returns:
        shapely.geometry.MultiLineString: The MultiLineString with modified endpoints.
    """
    if not isinstance(multilinestring, LineString):
        raise TypeError("Input must be a shapely  LineString.")
    
    pt1=new_first_point[0].split(',')
    pt2=new_last_point[0].split(',')

    modified_linestrings = []
    # for i, linestring in enumerate(multilinestring.geoms):
    coords = list(multilinestring.coords)

    new_1st_vertex = (float(pt1[0]), float(pt1[1]))
    new_last_vertex=(float(pt2[0]), float(pt2[1]))
    coords[0] = new_1st_vertex
    coords[-1] = new_last_vertex 

        
        # modified_linestrings.append(LineString(coords))
    # modified_linestrings.append((coords))
    ret_geom=LineString(coords)
    return ret_geom

def replace_line_vertices(gdf, 
                         new_first_vertex, new_last_vertex,
                         vertex_index=None, line_field='geometry'):
   
    # Make a copy to avoid modifying original
    # modified_gdf = gdf.copy()
    modified_gdf = gdf
    for idx, row in modified_gdf.iterrows():
        geom = row[line_field]
        
        # Only process LineString geometries
        if geom.geom_type != 'LineString':
            continue
            
        # Get all coordinates from the LineString
        coords = list(geom.coords)
        
        # Determine replacement vertices
        # if vertex_index is not None:
        #     # Use specified vertex for both ends
        #     if 0 <= vertex_index < len(coords):
        #         new_first = coords[vertex_index]
        #         new_last = coords[vertex_index]
        #     else:
        #         print(f"Invalid vertex index {vertex_index} for feature {idx}")
        #         continue
        # else:
            # Use provided coordinates or keep original
            # new_first = new_first_vertex if new_first_vertex else coords[0]
            # new_last = new_last_vertex if new_last_vertex else coords[-1]
        
        # Replace first and last vertices
        if len(coords) > 1:
            coords[0] = new_first_vertex
            coords[-1] = new_last_vertex
        else:
            # For single-vertex lines, just update the point
            coords[0] = new_last_vertex
        
        # Create new LineString with updated coordinates
        modified_gdf.at[idx, line_field] = LineString(coords)
    
    return modified_gdf
class FileGDBReader:
    def __init__(self, gdb_path: str):
        """
        Initialize the File Geodatabase reader with the path to the .gdb directory
        
        Args:
            gdb_path: Path to the Esri File Geodatabase (.gdb directory)
        """
        self.gdb_path = gdb_path
        self.available_layers = None
        self.open_gdb()
    
    def open_gdb(self) -> bool:
        """
        Open the File Geodatabase and get list of available layers
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.available_layers = gpd.list_layers(self.gdb_path)
            print(f"Successfully opened GDB at: {self.gdb_path}")
            print(f"Available layers: {self.available_layers}")
            return True
        except Exception as e:
            print(f"Error opening GDB: {str(e)}")
            self.available_layers = None
            return False
    
    def read_layer(
        self,
        layer_name: str,
        filter_query: Optional[str] = None,
        columns: Optional[list] = None
    ) -> Union[gpd.GeoDataFrame, None]:
        """
        Read a specific layer from the opened File Geodatabase
        
        Args:
            layer_name: Name of the layer to read
            filter_query: Optional SQL WHERE clause to filter features
            columns: Optional list of columns to read (None for all columns)
            
        Returns:
            GeoDataFrame if successful, None if error occurs
        """
        # if not self.available_layers:
        #     print("GDB not properly opened. Call open_gdb() first.")
        #     return None
            
        # if layer_name not in self.available_layers:
        #     print(f"Layer '{layer_name}' not found in GDB. Available layers: {self.available_layers}")
        #     return None
            
        try:
            print(f"Reading layer '{layer_name}'...")
            read_params = {
                'filename': self.gdb_path,
                'layer': layer_name
            }
            
            if filter_query:
                read_params['where'] = filter_query
            if columns:
                read_params['columns'] = columns
                
            gdf = gpd.read_file(**read_params)
            print(f"Successfully read {len(gdf)} features from '{layer_name}'")
            return gdf
            
        except Exception as e:
            print(f"Error reading layer '{layer_name}': {str(e)}")
            return None
        
if __name__ == "__main__":
    print("Task started...")
    log_file =  current_dir=os.getcwd() +"\\output\\CDIF_CREATION_LOG_"+     datetime.now().strftime("%Y%m%d_%H%M%S_%f")+".txt"

    logging.basicConfig(
    filename=log_file,  # Name of the log file
    level=logging.INFO,         # Minimum level of messages to log (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s', # Format of log messages
    filemode='a'                # 'a' for append, 'w' for overwrite
    )
    # 
    # create_fields_file(r"D:\Projects\Sasktel\R_E\sample\NESample.gdb","structures","Structure","manhole")
    # create_csv_manhole(r"D:\Projects\Sasktel\R_E\sample\NESample.gdb","Structure","type_name",'manhole','geometry',"structures")
    # create_field_mapping_file ("structures","manhole")

    # tgt_lyr_json=eval("manhole")
    # mf = tgt_lyr_json.get("mapped_fields")
    # filtered_data = [flds for flds in mf if len(flds["src"]) > 0] 
    # for nm in mf:
    #     print(nm['src'])
        
    # read_objectids(r"D:\Projects\Sasktel\R_E\sample\NESample.gdb","Structure")
    logging.info(str(datetime.now())+" | " + " ********** CDIF CREATION TASK STARTED ********** " )
    # create_design_metadata(r"D:\Projects\Sasktel\R_E\sample\NESample.gdb")
    create_field_mapping_file ("structures","manhole")
    create_csv_manhole_adv(r"D:\Projects\Sasktel\R_E\sample\NESample.gdb","Structure","type_name",'manhole','geometry',"structures",r"D:\Projects\Sasktel\R_E\sample\sasktel_Sqlite1.sqlite")
    
    
    create_field_mapping_file("routes","ug_route")   
    create_csv_ugroute(r"D:\Projects\Sasktel\R_E\sample\NESample.gdb","Span","type_name",'ug_route','geometry',"routes",r"D:\Projects\Sasktel\R_E\sample\sasktel_Sqlite1.sqlite")
    
    create_field_mapping_file("equipment","fiber_nap")
    create_csv_fiber_nap(r"D:\Projects\Sasktel\R_E\sample\NESample.gdb","Equipment", 'fiber_nap','geometry',"equipment",r"D:\Projects\Sasktel\R_E\sample\sasktel_Sqlite1.sqlite")

    # create_field_mapping_file("conduits","mywcom_conduit_run")
    # create_csv_conduit(r"D:\Projects\Sasktel\R_E\sample\NESample.gdb","Span","type_name",'mywcom_conduit_run','geometry',"conduits",r"D:\Projects\Sasktel\R_E\sample\sasktel_Sqlite1.sqlite")

    create_field_mapping_file("conduits","conduit")
    create_csv_conduit(r"D:\Projects\Sasktel\R_E\sample\NESample.gdb","Span","type_name",'conduit','geometry',"conduits",r"D:\Projects\Sasktel\R_E\sample\sasktel_Sqlite1.sqlite")
    logging.info(str(datetime.now())+" | " + " ********** CDIF CREATION TASK FINISHED ********** " )
    

    # ar=[]
    # ar.insert(0,"hi")
    # ar.insert(2,"hi2")
    # ar.insert(1,"hi1")


    
    # ar1=[]
    # ar1.append("hi")
    # ar1.append("hi2")
    # ar1.append("hi1")

    
    

    # print(ar)

    # print(ar1)

    print("Task completed...")
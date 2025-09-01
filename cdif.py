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

from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment,PatternFill
from collections import defaultdict
from time import strftime
from time import gmtime
from datetime import datetime
import sqlite3

class IQGeoCDIF:
    def __init__(self, output_folder_dir, folder_name,  config_json_file_path,input_gdb , extent="0"):
        self.Initialized=False
        self.DataMigrationStatus=0
        self.folder_name=folder_name.lower()
        self.rootDirectory = output_folder_dir
        self.folder_path=os.path.join(output_folder_dir,folder_name)
         
        self.config_json_file_path = config_json_file_path
        self.input_gdb = input_gdb 

        if extent=="0":
            # use Saskatchewan (Canada) default extent if no value passed
            self.extent= "01030000000100000005000000624817016e815bc0e82d078e939f4b407a6431c4c3835bc0d8f547621b7c484076a008e6bf5659c008db8af2698248400e846c5e387e59c0d0b5d49167a64b40624817016e815bc0e82d078e939f4b40"
        else:
            self.extent = extent
            
        self._create_folder_for_cdif()
        self._create_design_metadata()

    def _create_folder_for_cdif(self):
         
        logging.info(f"Creating folder for CDIF | '{self.folder_path}'")
        try:
            if not os.path.exists(self.folder_path):
                os.makedirs(self.folder_path ) 
        except:
            logging.error(str(datetime.now())+" | "+"ERROR IN Creating folder | "+self.folder_path)
        return
        
    def _create_design_metadata(self):

        self.packagemetadata_file_name=self.rootDirectory +"\\package.metadata"
        logging.info(f"Creating Package metadata file | '{self.packagemetadata_file_name}'")
        
        data=[
            ["property","value"],
            ["format","cdif"],
            ["coord_system","4326"],
            ["boundary",self.extent]
        ]
        try:
            with open(self.packagemetadata_file_name,'w',newline='') as csvfile:
                writer=csv.writer(csvfile)
                writer.writerows(data)
            print(f"Package Metadata written sucessfully.")
            logging.info(f"Package metadata written sucessfully.'{self.packagemetadata_file_name}'")
        except Exception as e:
            print(f"Package metadata file could not be written. Error occured : '{str(e)}'")
            logging.error(f"Package metadata file '{self.packagemetadata_file_name}' could not be written. Error occured : '{str(e)}' ")

    def _create_field_mapping_file( self ):

        self.field_file_name= self.folder_path+"\\"+self.target_object.lower()+".fields"
        logging.info(f"Creating field mapping file  '{self.field_file_name}' for object {self.target_object} ")

        print(f"Creating field mapping file  '{self.field_file_name}' for object '{self.target_object}'")

        try:
            logging.info(f"Loading configuration JSON file  '{self.config_json_file_path}' ")

            # with open(self.config_json_file_path, 'r') as file:
            # # Load the JSON data from the file
            #     object_config_json = json.load(file)
           
            fields=[]
            
            hdr_info=[["name","type","unit"]]
            fields.append(hdr_info)        
            
            # mf = object_config_json.get("Attribute_Finalised")

            # filtered_fields = [flds for flds in mf if (flds["FieldSource"]) =="NE"]
            # geo_fields = [flds for flds in mf if (flds["Field_Type"]) =="Geometry"]
            # if len(self.geo_fields)>0:
                
            # geomfld=self.geo_fields[0]["Field_Name"]
            # geomtype= self.object_config_json.get("Geometry_Type")

            hdr_info.append(["id","id",""]) #ID field column information 
            hdr_info.append([self.geomfld,self.geomtype,""])  

            for fld in self.reference_fields:
                hdr_info.append([fld['Field_Name'].lower(),fld['Field_Type'],])
                
            for fld in self.filtered_fields:
                hdr_info.append([fld['Field_Name'].lower(),fld['Field_Type'],])

                    # fields_issues.append([fld['Field_Name'],0,0,0,fld['Mandatory']])

            with open(self.field_file_name,'w',newline='') as csvfile:
                writer=csv.writer(csvfile)
                writer.writerows(hdr_info)
            
            print("Field Metadata written sucessfully for " + self.target_object)
            logging.info( f"Creating field mapping file completed for '{self.target_object}'")
            # else:
            #     print("ERROR: Geometry field not found in the config." )
            #     logging.error( f"ERROR:Geometry field not found in the config '{self.object_config_json}'. ")

        except Exception as e:
            print(f'Field metadata file could not be written. Error occured : {str(e)}')
            logging.error( f"Error occured in create field mapping file '{self.field_file_name}'. Error is {str(e)}  ")

    def InitiateProcess(self ):
        self.start_time = time.time()
        with open(self.config_json_file_path, 'r') as file:
            self.config_json = json.load(file)

        self.records_skipped_due_to_issue=0
        self.records_skipped_due_to_parent_data_mismatch_issue=0
        self.number_of_records_truncated=0
        self.number_of_values_truncated=0

        in_structure_fc= ""
        in_structure_right_clm=""
        in_structure_left_clm=""
        
        out_structure_fc= ""
        out_structure_clm= ""
        out_structure_left_clm=""

        structure_fc= ""
        structure_clm= ""
        structure_left_clm=""        
        structure_right_clm=""

        self.target_object=self.config_json.get("Name").lower()
        self.src_lyr=self.config_json.get("NE_Table")
        self.ref_structure_lyr=self.config_json.get("NE_Structure_Layer")
        self.filter_column=self.config_json.get("Filter")
        
        self.mf = self.config_json.get("Attribute_Finalised")
        self.reference_fields = [flds for flds in self.mf if flds["FieldSource"].upper()=="IQGEO" and  flds["Field_Type"].lower()=="reference"  and flds["Join"] !=""]  #
        for flds in self.reference_fields:
                left_join_cond=flds['Join'].split('=')[0]
                right_join_cond=flds['Join'].split('=')[1]
                left_table=left_join_cond.split('.')[0]
                if left_table!=self.src_lyr:
                    print(f"Warning!! Joining expression {flds['Join']} in referenced column referring to other then {self.src_lyr} layer. ")

                left_col=left_join_cond.split('.')[1]
                right_table=right_join_cond.split('.')[0]
                right_col=right_join_cond.split('.')[1]

                if flds['Field_Name']=="in_structure":      # To handle ROUTE and STRUCTURE Referencing 
                    in_structure_fc= right_table.upper()
                    self.in_structure_fc=right_table.upper()
                    in_structure_right_clm= right_col.upper() #
                    in_structure_left_clm=left_col.upper()
                    self.in_structure_left_clm=in_structure_left_clm
                if flds['Field_Name']=="out_structure":  # To handle ROUTE and STRUCTURE Referencing 
                    out_structure_fc= right_table.upper()
                    self.out_structure_fc=right_table.upper()
                    out_structure_right_clm= right_col.upper()
                    out_structure_left_clm=left_col.upper()
                    self.out_structure_left_clm=out_structure_left_clm
                    #out_structure_gdf=gpd.read_file(self.input_gdb,layer=right_table,  columns=['object_id', right_col])
                
                if flds['Field_Name']=="structure_name":  # To handle Attachment and STRUCTURE Referencing for Pole Anchor 
                    structure_fc= right_table.upper()
                    self.structure_fc=right_table.upper()
                    structure_right_clm= right_col.upper()
                    structure_left_clm=left_col.upper()
                    self.structure_left_clm=structure_left_clm

        self.filtered_fields = [flds for flds in self.mf if flds["FieldSource"]=="NE"]
        self.geo_fields = [flds for flds in self.mf if (flds["Field_Type"]) =="Geometry"]
        NE_Fields_Name=[]

        for flds in self.filtered_fields:
                if flds['Source']!="":
                    NE_Fields_Name.append(flds['Field_Name'])
                else:
                    NE_Fields_Name.append(flds['Source'])

        if len(self.geo_fields)>0:    
            self.geomfld=self.geo_fields[0]["Field_Name"]
            self.geomtype= self.config_json.get("Geometry_Type")
        else:
            print("ERROR: Geometry field not found in the config." )
            logging.error( f"ERROR:Geometry field not found in the config '{self.config_json}'. ")
            return
        
        self._create_field_mapping_file()
        layers = list_layers(self.input_gdb)
        if self.src_lyr in layers:
            print(f"GDB Open Start at {time.time()}")
            self.org_gdf=gpd.read_file(self.input_gdb,layer=self.src_lyr )

            # self.org_gdf=gpd.read_file(self.input_gdb,layer=self.src_lyr,columns=NE_Fields_Name)

            print(f"GDB read completed at {time.time()}")
            
            print("Filtering for  " + self.filter_column) 
            mergedgdf=UTILServices.apply_sql_like_filter(self.org_gdf,self.filter_column) 

            if in_structure_fc!="": #In structure joining needs to be done
                instr_gdf=gpd.read_file(self.input_gdb,layer=right_table,  columns=['object_id', in_structure_right_clm,'TYPE_NAME'])
                instr_gdf= instr_gdf.rename(columns={'object_id': 'instr_object_id', in_structure_right_clm: 'INSTR_'+in_structure_right_clm,'TYPE_NAME': 'INSTR_TYPE_NAME'})   

                self.in_structure_right_clm='INSTR_'+in_structure_right_clm

                instr_gdf_atr=instr_gdf.drop(columns='geometry')
                instr_gdf_geom=instr_gdf[[self.in_structure_right_clm, 'geometry']].rename(columns={"geometry":"InStrGeom"}) 
                mergedgdf=mergedgdf.merge(instr_gdf_atr,  left_on=in_structure_left_clm, right_on=self.in_structure_right_clm, how='left' ).merge(instr_gdf_geom, left_on=in_structure_left_clm, right_on=self.in_structure_right_clm, how='left')
                
            if out_structure_fc!="": #Out structure joining needs to be done
                outstr_gdf=gpd.read_file(self.input_gdb,layer=right_table,  columns=['object_id', out_structure_right_clm,'TYPE_NAME'])
                outstr_gdf= outstr_gdf.rename(columns={'object_id': 'outstr_object_id', out_structure_right_clm: 'OUTSTR_'+out_structure_right_clm,'TYPE_NAME': 'OUTSTR_TYPE_NAME'})
                self.out_structure_right_clm='OUTSTR_'+out_structure_right_clm
                outstr_gdf_atr=outstr_gdf.drop(columns='geometry')
                outstr_gdf_geom=outstr_gdf[[self.out_structure_right_clm, 'geometry']].rename(columns={"geometry":"OutStrGeom"}) 
                mergedgdf=mergedgdf.merge(outstr_gdf_atr,  left_on=out_structure_left_clm, right_on=self.out_structure_right_clm, how='left' ).merge(outstr_gdf_geom, left_on=out_structure_left_clm, right_on=self.out_structure_right_clm, how='left')    
            
            if structure_fc!="": # Joinig to get Pole Anchor Structure reference
                str_gdf=gpd.read_file(self.input_gdb,layer=right_table,  columns=['object_id',structure_right_clm,'TYPE_NAME'])
                str_gdf= str_gdf.rename(columns={'object_id': 'str_object_id', structure_right_clm: 'STR_'+structure_right_clm,'TYPE_NAME': 'STR_TYPE_NAME'})
                self.structure_right_clm='STR_'+structure_right_clm
                str_gdf_atr=str_gdf.drop(columns='geometry')
                str_gdf_geom=str_gdf[[self.structure_right_clm, 'geometry']].rename(columns={"geometry":"StrGeom"}) 
                mergedgdf=mergedgdf.merge(str_gdf_atr,  left_on=structure_left_clm, right_on=self.structure_right_clm, how='left' )
                                #    .merge(str_gdf_geom, left_on=structure_left_clm, right_on=self.structure_right_clm, how='left')    
            self.gdf=mergedgdf
            self.total_records=len(self.gdf)
            if self.total_records>0:
                self.Initialized=True
            else:
                print("No data found to be processed. Terminating the job.")
        else:
            print(f"Source  layer {self.src_lyr} is missing in FileGDB."  ) 

    def ProcessRecords(self):
        if self.Initialized==True:
            print("Starting data migration...")
            self.DataMigrationStatus=1
            rec_processed=0
            csv_data=[]
            # string_truncate_object=[]
            # duplicate_geom=[]
            # summary_rpt=[]
            # bypassed_data=[]
            # fields_issues=[]
            # type_mismatch_data=[]
            mandatory_objects_missing=[]

            self.string_truncate_object=[]
            self.bypassed_data=[]
            self.fields_issues= []
            self.type_mismatch_data= []
            self.parent_missing=[]
            self.topology_issues=[]
            self.skipped_conduit=[]
            self.core_hole_merged=[]
            
            clm_name=[]
            clm_name.append("id") #ID field column information 
            clm_name.append(self.geomfld)  
            
            for fld in self.reference_fields:
                self.fields_issues.append([fld['Field_Name'],0,0,0,fld['Mandatory'],0])
                clm_name.append(fld['Field_Name'].lower())

            for fld in self.filtered_fields:
                self.fields_issues.append([fld['Field_Name'],0,0,0,fld['Mandatory'],0])
                clm_name.append(fld['Field_Name'].lower())

            print("Processing data...  " ,end="")

            if self.folder_name=="structures": 
                csv_data,rec_processed=self.ProcessStructure(clm_name)
            if self.folder_name=="route": 
                csv_data,rec_processed=self.ProcessRoute(clm_name)

            print( str(rec_processed) + " rows processed." )
            flindx=-1
            for cl in clm_name:
                flindx+=1
                if cl.lower()=="name":
                    break             
            if flindx==-1:
                flindx=2
            number_of_geometry_duplicate,duplicate_geom=UTILServices.find_duplicates(csv_data,flindx)
            self.number_of_geometry_duplicate=number_of_geometry_duplicate
            self.duplicate_geom = duplicate_geom
            # self.string_truncate_object=string_truncate_object
            # self.bypassed_data=bypassed_data
            # self.fields_issues=fields_issues
            # self.type_mismatch_data=type_mismatch_data
            self.total_rec_processed = rec_processed
            self.csv_file_name=self.folder_path+ "\\"+self.target_object+".csv"
          
            self._WriteCSVFile(self.csv_file_name ,clm_name,csv_data)        
           
            self.DataMigrationStatus=2

        else:
            print("Proces is not initlizaed properly, either Initilization could not be performed OR some issue may occured during initialization.")

        return
    def ProcessStructure(self,clm_name):
        csv_data=[]
        rec_processed=0
        total_records= len(self.gdf)
        src_crs=self.gdf.crs
        tgt_crs="EPSG:4326"
        obj_id_pre_fix=self.src_lyr.replace(" ", "_")
        uqfld=self.config_json.get("Source_ID")  
        for index,row in self.gdf.iterrows():
            csv_row=[]
            trunc_record=False
            db_type_issue=False
            
            idval=re.sub(r'[^0-9a-zA-Z]', '', row[uqfld])
            # if str(idval)=="22937":
            #     idval=row[uqfld]
            # iqgeo_ref_id_val= obj_id_pre_fix +'/'+ str( idval)  
            # iqgeo_ref_id_val= obj_id_pre_fix +'/'+  idval
            iqgeo_ref_id_val= obj_id_pre_fix +  idval

            # uq_fld_val=row[src_uq_fld]
            str_geom=row["geometry"]  #geomfld

            csv_row.append(iqgeo_ref_id_val)
            # csv_row.append(geom_wkb)
            
            is_any_val_truncated=False
               
            geom_wkb=UTILServices.getEWKB(str_geom,src_crs,tgt_crs)
            csv_row.append(geom_wkb)
            fld_indx=0

            for fld in self.reference_fields:
       
                fld_val =""
                # if fld['Field_Name']=="structure_name":
                    # fld_val=row["str_object_id"]
                    # # in_str_geom=row["InStrGeom"]
                    # validated_obj=UTILServices.check_and_convert_value(fld_val,"str")
                    # if validated_obj['is_null']==True or validated_obj['is_nan']  ==True:
                    #     fld_val=""
                    #     self.parent_missing.append([idval,"in_structure", row[self.structure_left_clm]])
                    # else:
                    #     fld_val =self.structure_fc.upper()+"/"+str((fld_val))


                if fld['Field_Name']=="structure_name":
                    if pd.isnull(row["str_object_id"]):
                        fld_val="" 
                        self.parent_missing.append([row[uqfld],"ref_structure", row[self.in_structure_right_clm+'_x'] ,  ''])
                    else:
                        fld_val=re.sub(r'[^0-9a-zA-Z]', '', row["str_object_id"])  

                        # in_str_geom=row["InStrGeom"]
                        validated_obj=UTILServices.check_and_convert_value(fld_val,"str")
                        if validated_obj['is_null']==True or validated_obj['is_nan']  ==True:
                            fld_val=""
                            self.parent_missing.append([row[uqfld],"ref_structure", row[self.in_structure_right_clm+'_x'] , ''])
                        else:
                            fld_val =self.structure_fc.upper()+str((fld_val))



                csv_row.append( fld_val)
                fld_indx+=1

            for fld in self.filtered_fields:
                fld_val=self._GetFieldValue(fld,fld_indx,row,idval)
                csv_row.append( fld_val)
                fld_indx+=1
                        
            percent =int(100* (rec_processed / total_records))
            print (f"{rec_processed} of {total_records} - {percent} %",end="\r")

            self.records_skipped_due_to_issue=0
            
            if trunc_record==True :
                self.number_of_records_truncated+=1
            if db_type_issue==True :
                self.records_skipped_due_to_issue+=1
            csv_data.append(csv_row)
            rec_processed+=1
        return csv_data,rec_processed
    
    def ProcessRoute(self, clm_name):
        sqlite_path = self.rootDirectory +"\\"+UTILServices.generate_random_string(10)
         
        conn = sqlite3.connect(sqlite_path)
        cur = conn.cursor()
        create_sql = f"CREATE TABLE IF NOT EXISTS route_geom (str_hash TEXT, geom TEXT, lngth REAL , no_vertex INTEGER , obj_id TEXT, from_str_id TEXt, to_str_id TEXT, from_str_type TEXt, to_str_type TEXT, span_type TEXT,in_str_name TEXT,out_str_name TEXT);"
        cur.execute(create_sql)
        create_sql = f"CREATE INDEX idx_str_hash ON route_geom (str_hash);"
        cur.execute(create_sql)

        csv_data=[]
        conduit_data=[]
        corehole_data=[]
        
        rec_processed=0
        total_records= len(self.gdf)
        src_crs=self.gdf.crs
        tgt_crs="EPSG:4326"
        obj_id_pre_fix=self.src_lyr.replace(" ", "_")
        uqfld=self.config_json.get("Source_ID")  
        frm_str_fld_indx=-1
        to_str_fld_indx=-1
       
        self.gdf.sort_values(by=['CALCULATED_LENGTH','Shape_Length'],  inplace=True)

        for index,row in self.gdf.iterrows():
            csv_row=[]
            
            trunc_record=False
            db_type_issue=False
            frm_str_obj_id=""
            to_str_obj_id=""
            
             
            idval=re.sub(r'[^0-9a-zA-Z]', '', row[uqfld])
            if str(row[uqfld])=="{F7881B93-DA6D-44D7-A9C3-D99E4312CFDF}":
                idval=row[uqfld]
                idval=re.sub(r'[^0-9a-zA-Z]', '', row[uqfld])

            # iqgeo_ref_id_val= obj_id_pre_fix +'/'+ str( idval)  
            iqgeo_ref_id_val= obj_id_pre_fix + idval

            # uq_fld_val=row[src_uq_fld]
            str_geom=row["geometry"]  #geomfld
  
            csv_row.append(iqgeo_ref_id_val)
            # csv_row.append(geom_wkb)
            
            is_any_val_truncated=False
            fld_indx=0
            in_str_geom=None
            out_str_geom=None
            for fld in self.reference_fields:
                fld_val =""
                if fld['Field_Name']=="in_structure":
                    if pd.isnull(row["instr_object_id"]):
                        frm_str_obj_id="" 
                        self.parent_missing.append([row[uqfld],"in_structure", row[self.in_structure_right_clm+'_x'] , row[self.out_structure_right_clm +'_x']])
                    else:
                        frm_str_obj_id=re.sub(r'[^0-9a-zA-Z]', '', row["instr_object_id"])  

                        in_str_geom=row["InStrGeom"]
                        validated_obj=UTILServices.check_and_convert_value(fld_val,"str")
                        if validated_obj['is_null']==True or validated_obj['is_nan']  ==True:
                            frm_str_obj_id=""
                            self.parent_missing.append([row[uqfld],"in_structure", row[self.in_structure_right_clm+'_x'] , row[self.out_structure_right_clm +'_x']])
                        else:
                            frm_str_obj_id =self.in_structure_fc.upper()+str((frm_str_obj_id))
                    fld_val=frm_str_obj_id

                if fld['Field_Name']=="out_structure":
                    if pd.isnull(row["outstr_object_id"]):
                        to_str_obj_id="" 
                        self.parent_missing.append([row[uqfld],"out_structure",  row[self.in_structure_right_clm+'_x'] , row[self.out_structure_right_clm +'_x']])
                    else:
                        to_str_obj_id=re.sub(r'[^0-9a-zA-Z]', '', row["outstr_object_id"])   
                        out_str_geom=row["OutStrGeom"]

                        validated_obj=UTILServices.check_and_convert_value(fld_val,"str")
                        if validated_obj['is_null']==True or validated_obj['is_nan']  ==True:
                            to_str_obj_id=""
                            self.parent_missing.append([row[uqfld],"out_structure",  row[self.in_structure_right_clm+'_x'] , row[self.out_structure_right_clm +'_x']])
                        else:
                            to_str_obj_id =self.in_structure_fc.upper()+str((to_str_obj_id))
                    fld_val=to_str_obj_id

                csv_row.append( fld_val)
                fld_indx+=1

            if in_str_geom !=None:
                if out_str_geom !=None:
                    in_str_type = row['TYPE_NAME']
                    str_geom,d1,d2= UTILServices.change_path_start_endpoints(str_geom,in_str_geom, out_str_geom)
                    if d1>10 or d2>10:
                        self.topology_issues.append([idval,d1,d2])
            geom_wkb=UTILServices.getEWKB(str_geom,src_crs,tgt_crs)
            csv_row.insert(1,geom_wkb)
           # fld_indx+=1

            for fld in self.filtered_fields:
                if fld["Field_Name"].upper()=="FROM_STRUCTURE_NAME" : frm_str_fld_indx=fld_indx+2
                if fld["Field_Name"].upper()=="TO_STRUCTURE_NAME": to_str_fld_indx=fld_indx+2

                fld_val=self._GetFieldValue(fld,fld_indx,row,idval)
                csv_row.append( fld_val)
                fld_indx+=1
 
            self.records_skipped_due_to_issue=0
            
            if trunc_record==True :
                self.number_of_records_truncated+=1
            if db_type_issue==True :
                self.records_skipped_due_to_issue+=1
            		
            
            if row["TYPE_NAME"] in  ['BURIED', 'FLOOR SPAN', 'FOREIGN BURIED','FORMATION','RISER','TROUGH','TUNNEL']:
                csv_data.append(csv_row)
                FROM_STRUCTURE_NAME=row["FROM_STRUCTURE_NAME"]
                TO_STRUCTURE_NAME=row["TO_STRUCTURE_NAME"]

                   

                if frm_str_obj_id>to_str_obj_id:
                    str_key=frm_str_obj_id+'|'+to_str_obj_id
                else:
                    str_key=to_str_obj_id +'|'+frm_str_obj_id
                
                lengths = str_geom.length
                v_n=  len(str_geom.geoms[0].coords)
                # cur.execute("INSERT INTO route_geom (str_hash , geom , lngth , no_vertex , obj_id , from_str_id , to_str_id , from_str_type , to_str_type , span_type ,in_str_name ,out_str_name  ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(str_key,geom_wkb,lengths ,v_n ,iqgeo_ref_id_val, row['instr_object_id'],row['outstr_object_id'], row['INSTR_TYPE_NAME'],row['OUTSTR_TYPE_NAME'],row["TYPE_NAME"],FROM_STRUCTURE_NAME,TO_STRUCTURE_NAME ))
                cur.execute("INSERT INTO route_geom (str_hash , geom , lngth , no_vertex , obj_id , from_str_id , to_str_id , from_str_type , to_str_type , span_type ,in_str_name ,out_str_name  ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(str_key,geom_wkb,lengths ,v_n ,iqgeo_ref_id_val, frm_str_obj_id,to_str_obj_id, row['INSTR_TYPE_NAME'],row['OUTSTR_TYPE_NAME'],row["TYPE_NAME"],FROM_STRUCTURE_NAME,TO_STRUCTURE_NAME ))

                
                
            if row["TYPE_NAME"] == 'MESSENGER' :
                FROM_STRUCTURE_NAME=row["FROM_STRUCTURE_NAME"]
                TO_STRUCTURE_NAME=row["TO_STRUCTURE_NAME"]
                # frm_str_obj_id = row['instr_object_id']
                # to_str_obj_id = row['outstr_object_id']
                if frm_str_obj_id>to_str_obj_id:
                    str_key=frm_str_obj_id+'|'+to_str_obj_id
                else:
                    str_key=to_str_obj_id +'|'+frm_str_obj_id
                
                query = f"select obj_id, from_str_id, to_str_id , str_hash,geom from route_geom rg  where str_hash= '{str_key}'"
                cur.execute(query )
                msngr_results = cur.fetchall()
                if msngr_results:
                     self.bypassed_data.append([iqgeo_ref_id_val,'Messenger Route already created',FROM_STRUCTURE_NAME + ' TO ' + TO_STRUCTURE_NAME])
                else:                    
                    lengths = str_geom.length
                    v_n=  len(str_geom.geoms[0].coords)
                    cur.execute("INSERT INTO route_geom (str_hash , geom , lngth , no_vertex , obj_id , from_str_id , to_str_id , from_str_type , to_str_type , span_type ,in_str_name ,out_str_name  ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(str_key,geom_wkb,lengths ,v_n ,iqgeo_ref_id_val, frm_str_obj_id,to_str_obj_id, row['INSTR_TYPE_NAME'],row['OUTSTR_TYPE_NAME'],row["TYPE_NAME"],FROM_STRUCTURE_NAME,TO_STRUCTURE_NAME ))
                    csv_data.append(csv_row)
                
            if row["TYPE_NAME"] =='CONDUIT':
                conduit_data.append(csv_row)
                # print('bypassing conduit for time being')
            if row["TYPE_NAME"] == 'CORE HOLE':
                corehole_data.append(csv_row)
            # if row["TYPE_NAME"] == 'MESSENGER':
                

            rec_processed+=1
            percent =int(100* (rec_processed / total_records))
            print (f"{rec_processed} of {total_records} - {percent} %",end="\r")
        conn.commit()
# Checking Messenger data and modifying geom to shortest path if found
        

        clidx=0
        nm_idx=-1
        if frm_str_fld_indx== -1 or to_str_fld_indx==-1 :
            for cl in clm_name:
                if cl=='in_structure':frm_str_fld_indx= clidx
                if cl=='out_structure':to_str_fld_indx= clidx
                if cl=='name':
                    nm_idx=clidx
                clidx+=1


        if len(conduit_data)>0:
            print('Conduit data processing')

            for conduit_rw in conduit_data:
                FROM_STRUCTURE_NAME=conduit_rw[frm_str_fld_indx]
                TO_STRUCTURE_NAME=conduit_rw[to_str_fld_indx]
                id_val=conduit_rw[0]
                if FROM_STRUCTURE_NAME>TO_STRUCTURE_NAME:
                    str_key=FROM_STRUCTURE_NAME+'|'+TO_STRUCTURE_NAME
                else:
                    str_key=TO_STRUCTURE_NAME +'|'+FROM_STRUCTURE_NAME
                
                query = f"SELECT str_hash , obj_id FROM  route_geom WHERE str_hash = '{str_key}' "
            #     if conduit_rw[0]=='SPAN_REG16/376953':
            #         print (query)
            # # Execute the query with the search value as a parameter
                cur.execute(query )

            # Fetch all matching rows
                results = cur.fetchall()
                if results:
                    print(f"Found route for '{str_key}' so skippling the counduit.")
                    # for crw in results:
                    if nm_idx==-1:
                        self.skipped_conduit.append([FROM_STRUCTURE_NAME, TO_STRUCTURE_NAME, str_key,id_val])
                    else:
                        self.skipped_conduit.append([FROM_STRUCTURE_NAME, TO_STRUCTURE_NAME, str_key,conduit_rw[nm_idx]])

                    # for row in found_data:
                    #     print(row)
                else:
                    cur.execute("INSERT INTO route_geom (str_hash, geom, lngth , no_vertex , obj_id) VALUES (?,?,?,?,?)",(str_key,'',0 ,0 ,iqgeo_ref_id_val))
                    conn.commit()
                    csv_data.append(conduit_rw)     
        if len(corehole_data)>0:
            print('Core Hole data processing')
            for corehole_rw in  corehole_data:
                # print(f'Processsing core hole {corehole_rw}')
                FROM_STRUCTURE_NAME=corehole_rw[frm_str_fld_indx]
                TO_STRUCTURE_NAME=corehole_rw[to_str_fld_indx]
                if FROM_STRUCTURE_NAME>TO_STRUCTURE_NAME:
                    str_key=FROM_STRUCTURE_NAME+'|'+TO_STRUCTURE_NAME
                else:
                    str_key=TO_STRUCTURE_NAME +'|'+FROM_STRUCTURE_NAME

                query = f"SELECT str_hash , obj_id, from_str_id, to_str_id FROM  route_geom WHERE (from_str_id = '{FROM_STRUCTURE_NAME}' or to_str_id = '{TO_STRUCTURE_NAME}' or to_str_id  = '{FROM_STRUCTURE_NAME}' or from_str_id = '{TO_STRUCTURE_NAME}' ) AND (span_type = 'BURIED' or span_type ='FOREIGN BURIED' )AND ( from_str_type  ='SPAN JUNCTION' OR to_str_type ='SPAN JUNCTION') "
              
                cur.execute(query )
                results = cur.fetchall()
                if results:
                    for crw in results:
                        # self.core_hole_merged.append(crw['obj_id'],)
                        buried_span_id_to_update_geom=crw[1]
                        buried_span_id_from_structure=crw[2]
                        buried_span_id_to_structure=crw[3]
                        ch_span_geom=corehole_rw[1]

                        insert_vertices_at=None
                        if FROM_STRUCTURE_NAME == buried_span_id_from_structure:
                            insert_vertices_at=0
                        elif FROM_STRUCTURE_NAME == buried_span_id_to_structure:
                            insert_vertices_at=-1
                        elif TO_STRUCTURE_NAME == buried_span_id_from_structure:
                            insert_vertices_at=0
                        elif TO_STRUCTURE_NAME == buried_span_id_to_structure:
                            insert_vertices_at=-1
                        
                        if insert_vertices_at== 0 or insert_vertices_at==-1:
                            csv_data=self._UpdateBuriedSpanGeomByMergeCoreHole(csv_data,insert_vertices_at,ch_span_geom , buried_span_id_to_update_geom,corehole_rw[0],FROM_STRUCTURE_NAME,TO_STRUCTURE_NAME)
                            print('bypass')

                        # print (buried_span_id_to_update_geom)
                else:
                    self.core_hole_merged.append(['CORE HOLE IGNORED',corehole_rw[0], FROM_STRUCTURE_NAME,TO_STRUCTURE_NAME,''])
    
        conn.commit()
        conn.close()
        try:
            os.remove(sqlite_path)
            print('Removing db file')
        except Exception as ex:
            print(f"Unable to delete temp db  file {sqlite_path}")
            
        return csv_data,rec_processed
    
    def FinalizeCDIF(self):
        print(f"Finalizing CDIF by compressing and putting all files in a zip file  .")
        logging.info(f"Finalizing CDIF by compressing and putting all files in a zip file.")
        
        self.output_zip_file_name=""
        # self._WriteZipFile([self.packagemetadata_file_name.replace(self.rootDirectory+"\\",""), self.csv_file_name.replace(self.rootDirectory,""),  self.field_file_name.replace(self.rootDirectory,"")])
        
        self._WriteSummaryReport()

        
         
        logging.info( f" completed with  - "+ str(self.total_rec_processed) +" records | "+ self.output_zip_file_name   )

    def _GetReferenceFieldValue(self,fld,fld_indx,row,idval):

        return

    def _GetFieldValue(self,fld,fld_indx,row,idval):

        fld_nm=fld['Field_Name'].upper()
        src_nm=fld['Source'].upper()
        if src_nm!="":
            fld_nm=src_nm
        if len(fld_nm)==0:
            print(f"Invalid field name '{fld_nm}'. Terminatig the process." )
            return
        fld_value = row[fld_nm] 
        fld_type=fld['Field_Type'].lower()
        fld_mandatory=fld['Mandatory'].lower()
        domain_val=fld['DomainValue'].lower()
        row_fld_val=row[fld_nm]
        if fld['Field_Name']=="st_rmks":
            aa=0
        validated_obj=UTILServices.check_and_convert_value(row_fld_val, fld_type)
          
        if validated_obj['is_null']==True or validated_obj['is_nan']  ==True:
            self.fields_issues[fld_indx][1]=self.fields_issues[fld_indx][1]+1

            fld_value=""
        else:
            if validated_obj['type_match']==True:
                fld_value=  validated_obj['converted_value']
                if fld['ReplaceValue']!="":
                    fld_value = UTILServices.get_mapped_value( fld['ReplaceValue']  ,fld_value)

                if domain_val !="":
                    if UTILServices.check_domain_value(domain_val,fld_value.lower())==False:
                        self.fields_issues[fld_indx][2]=self.fields_issues[fld_indx][2]+1
                            # if value_is_as_per_type==False:
                        self.bypassed_data.append([idval,fld_nm,fld_value ])
                
                if fld_type.startswith("string"):
                    match=re.search(r'string\((\d+)\)',fld_type)
                    max_len=int(match.group(1))
                    # modified_value = str(fld_value)   
                    strlen= len(fld_value)                             
                    if max_len<strlen:
                        fld_value = fld_value[:max_len]
                        self.string_truncate_object.append([idval,fld_nm, row_fld_val,fld_value])
                        self.fields_issues[fld_indx][3]=self.fields_issues[fld_indx][3]+1
                        trunc_record=True    
            else:
                self.fields_issues[fld_indx][5]=self.fields_issues[fld_indx][5]+1
                self.type_mismatch_data.append([idval,fld_nm,fld_type,fld_value])
                fld_value=""  # Changing value to NULL to avoid import issue in IQQGeo 
                db_type_issue=True
        if fld_value=="":
            if fld["defaultvalue"]!="":
                fld_value= fld["defaultvalue"]

        return fld_value 
    
    def _WriteZipFile(self,selected_files):
        self.output_zip_file_name = self.rootDirectory +"\\" + self.target_object.upper() +'_cdif'+ datetime.now().strftime("%Y%m%d_%H%M%S")+'.zip'

        with zipfile.ZipFile(self.output_zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_name in selected_files:
                file_path = os.path.join(self.rootDirectory, file_name)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    zipf.write(file_path, arcname=file_name) # arcname ensures only the filename is used in the zip
                else:
                    print(f"Warning: File '{file_name}' not found in '{self.folder_path}' and could not be added to the zip.")
                    logging.warning(f"Warning: File '{file_name}' not found in '{self.folder_path}' and could not be added to the zip.")

    def _WriteCSVFile(self,file_name,clm_name, csvdata):
        if len(csvdata)>0:
            with open(file_name,'w',newline='',encoding='utf-8') as csvfile:
                    writer=csv.writer(csvfile)
                    # for csvdata in csvdata_list:
                    writer.writerow( clm_name)        
                    writer.writerows( csvdata)        
        else:
            print("No data processed to write the CSV file.")                    
    def _WriteSummaryReport(self ):
        
        df_xl1 = pd.DataFrame(self.string_truncate_object, columns=['Object ID','Field Name', 'Original String', 'Truncated String'])
        df_xl2 = pd.DataFrame(self.duplicate_geom, columns=['Object ID','Name','Geom'])
        df_xl3 = pd.DataFrame(self.bypassed_data, columns=['Object ID','Bypassed for Field','Field Value'])
        df_xl4 = pd.DataFrame(self.type_mismatch_data, columns=['Object ID','Field Name','Field Type','Field Value'])
        df_xl5 = pd.DataFrame(self.topology_issues, columns=['Object ID','Start Point Distance','End Point Distance'])
        
        if len(self.skipped_conduit)>0:
            df_xl6 = pd.DataFrame(self.skipped_conduit, columns=['FROM_STRUCTURE_NAME', 'TO_STRUCTURE_NAME', 'STRUCTURE_HASH','OBJ_ID'])
        if len(self.core_hole_merged)>0:
            df_xl7 = pd.DataFrame(self.core_hole_merged, columns=['ACTION_TAKEN','CORE HOLE ID','FROM_STRUCTURE_NAME', 'TO_STRUCTURE_NAME', 'SPAN ID GEOMETRY UPDATED'])
        if len(self.parent_missing)>0:
            df_xl8 = pd.DataFrame(self.parent_missing, columns=['Object ID','Type','From Structure','To Structure'])
        

        excel_file_path = self.rootDirectory  + '\\SummaryReport_'+ self.target_object.upper() +"_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".xlsx"
        # df_xl.to_excel(excel_file_path, index=False, sheet_name='TruncatedValues')

        with pd.ExcelWriter(excel_file_path, engine='xlsxwriter') as writer:
            df_xl1.to_excel(writer, sheet_name='TruncatedValues', index=False)
            df_xl2.to_excel(writer, sheet_name='DuplicateGeom', index=False)
            df_xl3.to_excel(writer, sheet_name='OutsideDomain_Bypassed', index=False)
            df_xl4.to_excel(writer, sheet_name='Missing_Mismatch', index=False)
            df_xl5.to_excel(writer, sheet_name='TopologyIssue', index=False)

            if len(self.skipped_conduit)>0:
                df_xl6.to_excel(writer, sheet_name='SkippedConduit', index=False)
            if len(self.core_hole_merged)>0:
                df_xl7.to_excel(writer, sheet_name='CoreHole', index=False)
            if len(self.parent_missing)>0:
                df_xl8.to_excel(writer, sheet_name='MissingObjects', index=False)

        end_time = time.time()
        elapsed_seconds = end_time - self.start_time

        wb = load_workbook(excel_file_path)
        # Create a new sheet
        ws_openpyxl = wb.create_sheet('Summary',0)

        # Add data to the new sheet using openpyxl
        ws_openpyxl['A1'] = 'NE to IQGeo Object Migration Summary Report : ' + self.target_object.upper()
        ws_openpyxl.merge_cells('A1:D1')
        ws_openpyxl['A1'].font = Font(name='Arial', size=14, bold=True, color="FF0000") 
        ws_openpyxl['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws_openpyxl['A2'] = 'Start Time'
        ws_openpyxl['A3'] = "End Time"
        ws_openpyxl['A4'] = "Total Time Taken (min:sec)"
        ws_openpyxl['A5'] = "NE Source FileGDB"
        ws_openpyxl['A6'] = "NE Source Feature Layer"
        ws_openpyxl['A7'] = "Total Records in NE Source Feature Layer"
        ws_openpyxl['A8'] = "Generated CDIF File"
        ws_openpyxl['A9'] = "IQGeo Object Name"
    
        ws_openpyxl['A10'] = "Condition Used to Select NE Data"
        ws_openpyxl['A11'] = "Total Records selected as per Condition"
        ws_openpyxl['A12'] = "Total Records Processed"
        ws_openpyxl['A13'] ="Records Skipped due to value / data type issue"
        ws_openpyxl['A14'] ="Records Skipped due to reference /parent data missing reason"
        ws_openpyxl['A15'] ="Number of Records where data trucated due to shorter length"
        ws_openpyxl['A16'] ="Number of values where data trucated due to shorter length"
        ws_openpyxl['A17'] ="Number of Duplicate Geometires"
        
        m, s = divmod(end_time-self.start_time, 60)

        ws_openpyxl['B2'] = datetime.fromtimestamp(self.start_time).strftime("%d-%b-%Y %H:%M:%S")
        ws_openpyxl['B3'] = datetime.fromtimestamp(end_time).strftime("%d-%b-%Y %H:%M:%S")
        ws_openpyxl['B4'] = str(int(m)) + ":" + str(int(s))
        ws_openpyxl['B5'] = self.input_gdb
        ws_openpyxl['B6'] =  self.src_lyr
        ws_openpyxl['B7'] = len(self.org_gdf)
        ws_openpyxl['B8'] = self.output_zip_file_name

        ws_openpyxl['B9'] = self.target_object
        ws_openpyxl['B10'] = self.filter_column
        ws_openpyxl['B11'] = self.total_records
        ws_openpyxl['B12'] = self.total_rec_processed
        ws_openpyxl['B13'] = self.records_skipped_due_to_issue
        ws_openpyxl['B14'] = self.records_skipped_due_to_parent_data_mismatch_issue
        ws_openpyxl['B15'] = self.number_of_records_truncated
        ws_openpyxl['B16'] =len(self.string_truncate_object)
        ws_openpyxl['B17'] =self.number_of_geometry_duplicate

        

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
        ws_openpyxl['C19'] = 'NULL Values Found'
        ws_openpyxl['D20'] = 'Migrated with Issues'
    
        ws_openpyxl['D20'] = 'Outside Domain/Pick List'
        ws_openpyxl['E20'] = 'Data Truncated'
        ws_openpyxl['F19'] = 'Migrated without Issue'
        ws_openpyxl['G19'] = 'Type Mismatch-Not Migrated'
        
        ws_openpyxl.merge_cells('A19:A20')
        ws_openpyxl.merge_cells('B19:B20')
        ws_openpyxl.merge_cells('C19:C20')
        ws_openpyxl.merge_cells('D19:E19')
        ws_openpyxl.merge_cells('F19:F20')
        ws_openpyxl.merge_cells('G19:G20')





        ws_openpyxl.column_dimensions['A'].width = 60
        ws_openpyxl.column_dimensions['B'].width = 20
        ws_openpyxl.column_dimensions['C'].width = 30
        ws_openpyxl.column_dimensions['D'].width = 20
        ws_openpyxl.column_dimensions['E'].width = 20
        ws_openpyxl.column_dimensions['E'].width = 20
        ws_openpyxl.column_dimensions['E'].width = 20
        
        rwno=21
        for fld in self.fields_issues:
            ws_openpyxl['A'+str(rwno)] = fld[0]
            ws_openpyxl['B'+str(rwno)] = fld[4]
            ws_openpyxl['C'+str(rwno)] = fld[1]
            ws_openpyxl['D'+str(rwno)] = fld[2]
            ws_openpyxl['E'+str(rwno)] = fld[3]
            ws_openpyxl['F'+str(rwno)] = self.total_rec_processed-fld[1]
            ws_openpyxl['G'+str(rwno)] = fld[5]

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
     
    def _UpdateMessengerGeom(self,multiple_msngr, csv_data):
        print("Updating MESSANGER Geometry")
        # query = f"select obj_id, from_str_id, to_str_id , str_hash,geom from route_geom rg  where str_hash in (select  str_hash from route_geom rg  where span_type like 'MESS%'  group by str_hash having count(1)>1) order by str_hash, no_vertex "
        shortest_geom_obj_id=''
        shortest_geom= ''
        last_str_hash=''
        for crw in multiple_msngr:
            cur_str_hash=crw[3]
            if last_str_hash!=cur_str_hash:
                #bypassing 1st row of group which has lowest vertices / length
                # shortest_geom_obj_id=crw[0]
                shortest_geom=crw[4]
            else:
                for row in csv_data:
                    if row[0] == crw[0]  :
                        row[1]=shortest_geom
                        break
            
            last_str_hash=cur_str_hash
        
        return csv_data
            
    def _UpdateBuriedSpanGeomByMergeCoreHole(self,csv_data,insert_vertices_at,ch_span_geom , buried_span_id_to_update_geom,ch_span_id ,FROM_STRUCTURE_NAME,TO_STRUCTURE_NAME):
        
        geom_updated=False
        for row in csv_data:
            if row[0] == buried_span_id_to_update_geom:  
                buried_span_geom= row[1]
                print(f"Merging CoreHole Geometry for- {buried_span_id_to_update_geom} from geom {ch_span_geom} to geom {buried_span_geom} ")

                # updated_geom = UTILServices.insert_geometry(buried_span_geom,ch_span_geom,insert_vertices_at)
                updated_geom = UTILServices.merge_multilines_wkb(buried_span_geom,ch_span_geom)
                updated_geom= updated_geom.upper()
                row[1] = updated_geom
                self.core_hole_merged.append(['CORE HOLE GEOM MERGED',ch_span_id,FROM_STRUCTURE_NAME,TO_STRUCTURE_NAME , buried_span_id_to_update_geom])
                geom_updated=True
                break
            
        if geom_updated==False:
            self.core_hole_merged.append(['CORE HOLE GEOM COULD NOT MERGED',ch_span_id,FROM_STRUCTURE_NAME,TO_STRUCTURE_NAME , buried_span_id_to_update_geom])
            
        return csv_data
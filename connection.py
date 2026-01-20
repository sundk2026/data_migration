import sqlite3, os, oracledb, csv, zipfile
import pandas as pd
from  util_services import UTILServices 
import find_nearby_segment, pdf_generator


class Connection():
    def __init__(self):
        self.input_gdb = r"C:\Kishore\SaskTel_Bisen\kranthi\gdb\SIMPLE_TELCO_Jan07exchange.gdb"
        self.region="Swift Current"
        self.iqgeo_csv = r"C:\Kishore\SaskTel_Bisen\output\connection_data_swift.csv"
        self.source_csv_path =  r"C:\Kishore\SaskTel_Bisen\output"
        # self.segment_data_csv = r"C:\Kishore\SaskTel_Bisen\output\connection_csv_06.csv"
        self.iqgeo_csv_df = pd.read_csv(self.iqgeo_csv)
        # self.segment_data_df = pd.read_csv(self.segment_data_csv)
        self.ref_columns = ['in_object_name', 'out_object_name','in_object_classname','out_object_classname','connector_classname','connector_name']
        self.filtered_fields = ['myw_delta','id', 'in_object', 'out_object',
                                     'in_side', 'in_low',
                                    'in_high', 'out_side', 'out_low', 'out_high', 'splice',
                                    'root_housing', 'housing', 'location', 'myw_change_type',
                                    'comsof_auto', 'design_id', 
                                    'class_name', 'in_object_name','out_object_name',
                                    'in_object_classname', 'in_object_name','out_object_classname',
                                    'out_object_name','connector_classname','connector_name'
                                    ]
        self.set_sqlite()

    def set_sqlite(self):
        if self.input_gdb.endswith(".gdb"):
            sqlite_db = self.input_gdb.replace(".gdb", ".sqlite")
            self.sqlite_db=sqlite_db
            if os.path.exists(sqlite_db):
                print(f'SQL DB {sqlite_db} already exists, bypassing.')
            else:
                print('Exporing selected layers in sqlite db')
                # UTILServices.export_gdb_to_sqlite(self.input_gdb,sqlite_db,['SPAN','SPAN_UNIT','SPAN_SPAN_UNIT','TRANSMEDIA','TRANS_SPAN_ASSOCIATION','transmedia_name'])
                UTILServices.export_gdb_to_sqlite(self.input_gdb,sqlite_db,['STRUCTURE_UNIT', 'STRUCTURE', 'SPLICE_CLOSURE', 'ATTACHMENT', 'CHASSIS', 'SLOT', 'PLUGIN', 'PORT', 'SLOT_PLUGIN', 'EQUIPMENT', 'TRANS_SPAN_ASSOCIATION', 'TRANSMEDIA_UNIT', 'TRANSMEDIA', 'SPAN_SPAN_UNIT', 'SPAN_UNIT', 'SPAN'])
        else:
            raise ValueError("GDB File is missing")
    def get_table_data(self, sql):
        try:
            conn=sqlite3.connect(self.sqlite_db)
            cur = conn.cursor()
            cur.execute(sql)
            df_data = pd.read_sql(sql, conn)

            cur.close()
            conn.close()
            return df_data
        except Exception as e:
            print(str(e),"--error in Getting from GDB")

    def get_NE_table_data(self, sql, type):
        try:
            file_path = "%s\\%s%s"%(self.source_csv_path, type.lower(), ".csv")
            if  os.path.exists(file_path):
                df_data = pd.read_csv(file_path)
            else:
                conn = oracledb.connect(user="SundK2", password="Sundk22$",
                                dsn="sop-oradb-021.stholdco.com:1527/DBP463.STHOLDCO.COM")
                cur = conn.cursor()
                cur.execute(sql)
                df_data = pd.read_sql(sql, conn)
                df_data.to_csv(file_path)

                cur.close()
                conn.close()
            return df_data
        except Exception as e:
            print(str(e),"--error in Getting data from NE DB")

    def get_class_name(self, class_id):
        if class_id == 366:
            return "Transmedia"
        if class_id == 367:
            return "Splice Closure"
        if class_id == 370:
            return "Equipment"
        
    def set_cable_segment_name(self, cable, segment_id):
        if "fiber_cable" in cable:
            seg_name = "mywcom_fiber_segment/"
        elif "copper_cable" in cable:
            seg_name = "mywcom_copper_segment/"
        elif "coax_cable" in cable:
            seg_name = "mywcom_coax_segment/"
        
        return "%s%s"%(seg_name, segment_id)

        
    # def get_segment_data(self, cable_name):
    #     segment_data = list(self.segment_data_df[self.segment_data_df['cable']==cable_name]['id'])
    #     return self.set_cable_segment_name(cable_name, segment_data[0]) if segment_data else 'NA'

    def set_attr_val(self, row):
            cable_row_data_ = {}

            if row['FROM_CLASSID'] == 366:
                in_object_data = self.NE_transmedia_df[self.NE_transmedia_df['OBJECTID'] == row['FROM_OBJECTID']]
                in_object_calssname = "Transmedia"
                in_object_data = in_object_data['TRANSMEDIA_NAME'].iloc[0]
            if row['FROM_CLASSID'] == 367:
                in_object_data = self.NE_splice_closure_df[self.NE_splice_closure_df['OBJECTID'] == row['FROM_OBJECTID']]
                in_object_calssname = "Splice Closure"
                in_object_data = in_object_data['SPLICE_CLOSURE_NAME'].iloc[0]
            if row['FROM_CLASSID'] == 370:
                in_object_data = self.NE_equipment_df[self.NE_equipment_df['OBJECTID'] == row['FROM_OBJECTID']]
                in_object_calssname = "Equipment"
                in_object_data = in_object_data['EQUIPMENT_NAME'].iloc[0]

            
            if row['TO_CLASSID'] == 366:
                out_object_data = self.NE_transmedia_df[self.NE_transmedia_df['OBJECTID'] == row['TO_OBJECTID']]
                out_object_calssname = "Transmedia"
                if out_object_data.empty:
                    out_object_data = 'NA'
                else:
                    out_object_data = out_object_data['TRANSMEDIA_NAME'].iloc[0]
            if row['TO_CLASSID'] == 367:
                out_object_data = self.NE_splice_closure_df[self.NE_splice_closure_df['OBJECTID'] == row['TO_OBJECTID']]
                out_object_calssname = "Splice Closure"
                out_object_data = out_object_data['SPLICE_CLOSURE_NAME'].iloc[0]
            if row['TO_CLASSID'] == 370:
                out_object_data = self.NE_equipment_df[self.NE_equipment_df['OBJECTID'] == row['TO_OBJECTID']]
                out_object_calssname = "Equipment"
                out_object_data = out_object_data['EQUIPMENT_NAME'].iloc[0]




            if row['CONNECTOR_CLASSID'] == 366:
                conn_object_data = self.NE_transmedia_df[self.NE_transmedia_df['OBJECTID'] == row['CONNECTOR_OBJECTID']]
                conn_object_data = conn_object_data['TRANSMEDIA_NAME'].iloc[0]

            if row['CONNECTOR_CLASSID'] == 367:
                conn_object_data = self.NE_splice_closure_df[self.NE_splice_closure_df['OBJECTID'] == row['CONNECTOR_OBJECTID']]
                conn_object_data = conn_object_data['SPLICE_CLOSURE_NAME'].iloc[0]

            if row['CONNECTOR_CLASSID'] == 370:
                conn_object_data = self.NE_equipment_df[self.NE_equipment_df['OBJECTID'] == row['CONNECTOR_OBJECTID']]
                conn_object_data = conn_object_data['EQUIPMENT_NAME'].iloc[0]

            #connection data
            conn_object_df_row = self.iqgeo_csv_df[self.iqgeo_csv_df['name']==conn_object_data]

            housing = conn_object_df_row['concat'].iloc[0] if not conn_object_df_row.empty else 'NA'
            root_housing = conn_object_df_row['root_housing'].iloc[0] if not conn_object_df_row.empty else 'NA'
            location = conn_object_df_row['location'].iloc[0] if not conn_object_df_row.empty else 'NA'
            splice_status = 'true' if "splice_closure" in housing else 'false'
            
            #in_object data
            in_object_df_row = self.iqgeo_csv_df[self.iqgeo_csv_df['name']==in_object_data]
            in_object_id = in_object_df_row['concat'].iloc[0] if not in_object_df_row.empty else 'NA'
            if len(in_object_df_row) > 1 and 'NA' != location and 'NA' not in list(in_object_df_row['location']):
                in_object_id = find_nearby_segment.get_nearby_segment(location, in_object_df_row)
            # if any(n in in_object_id for n in ['fiber_cable', 'copper_cable', 'coax_cable']):
            #     in_object_id = self.get_segment_data(in_object_df_row['concat'].iloc[0]) if not in_object_df_row.empty else 'NA'

            #out_object data
            out_object_df_row = self.iqgeo_csv_df[self.iqgeo_csv_df['name']==out_object_data]
            out_object_id = out_object_df_row['concat'].iloc[0] if not out_object_df_row.empty else 'NA'
            if len(out_object_df_row) > 1 and 'NA' != location and 'NA' not in list(out_object_df_row['location']):
                out_object_id = find_nearby_segment.get_nearby_segment(location, out_object_df_row)
            # if any(n in out_object_id for n in ['fiber_cable', 'copper_cable', 'coax_cable']):
            #     out_object_id = self.get_segment_data(out_object_df_row['concat'].iloc[0]) if not out_object_df_row.empty else 'NA'

            

            out_high = int(row['TO_FIRSTUNIT'])+int(row['NUMBER_OF_UNITS'])
            out_high = out_high - 1 if out_high > 0 else 0
            try:
                for keys in self.filtered_fields:
                    # if keys == 'myw_delta': cable_row_data_.update({'myw_delta':''})
                    # if keys == 'id': cable_row_data_.update({'id':''})
                    if keys == 'in_object': cable_row_data_.update({'in_object':in_object_id})
                    if keys == 'out_object': cable_row_data_.update({'out_object':out_object_id})
                    if keys == 'in_side': cable_row_data_.update({'in_side':'out'})
                    if keys == 'in_low': cable_row_data_.update({'in_low':row['FROM_FIRSTUNIT']})
                    if keys == 'in_high': cable_row_data_.update({'in_high':row['NUMBER_OF_UNITS']})
                    if keys == 'out_side': cable_row_data_.update({'out_side':'in'})
                    if keys == 'out_low': cable_row_data_.update({'out_low':row['TO_FIRSTUNIT']})
                    if keys == 'out_high': cable_row_data_.update({'out_high': out_high})
                    if keys == 'splice': cable_row_data_.update({'splice':splice_status})
                    if keys == 'root_housing': cable_row_data_.update({'root_housing':root_housing})
                    if keys == 'housing': cable_row_data_.update({'housing':housing})
                    if keys == 'location': cable_row_data_.update({'location':location})
                    # if keys == 'myw_change_type': cable_row_data_.update({'myw_change_type':''})
                    # if keys == 'comsof_auto': cable_row_data_.update({'comsof_auto':''})
                    # if keys == 'design_id': cable_row_data_.update({'design_id':row['WORK_ORDER_NAME']})
                    if keys == 'in_object_classname': cable_row_data_.update({'in_object_classname':in_object_calssname})
                    if keys == 'in_object_name': cable_row_data_.update({'in_object_name':in_object_data})
                    if keys == 'out_object_classname': cable_row_data_.update({'out_object_classname':out_object_calssname})
                    if keys == 'out_object_name': cable_row_data_.update({'out_object_name':out_object_data})
                    if keys == 'connector_classname': cable_row_data_.update({'connector_classname':self.get_class_name(row['CONNECTOR_CLASSID'])})
                    if keys == 'connector_name': cable_row_data_.update({'connector_name':conn_object_data})

            except Exception as e:
                print({"error": str(e)})
            
            if in_object_id != 'NA' and housing != 'NA' and out_object_id != 'NA':
                return cable_row_data_, True
            else:
                return cable_row_data_, False
    
    def _WriteCSVFile(self,file_name, csvdata):
        if len(csvdata)>0:
            keys = csvdata[0].keys()
            with open(file_name, 'w', newline='') as output_file:
                dict_writer = csv.DictWriter(output_file, keys)
                dict_writer.writeheader()
                dict_writer.writerows(csvdata)    
            print(f"CSV completed kindly check in this path {file_name}")
        else:
            print("No data processed to write the CSV file.")
            
    def missing_report(self, region_data, ne_data, type):
        missing_data = []
        missing_data_ = {}
        diff_data = [x for x in region_data if x not in ne_data]
        for i in diff_data:
            missing_data.append({'name': i, 'type': type})
        return missing_data
    
    def remove_tag(self, cable_data):
        keys_to_remove = ["class_name","in_object_classname", "in_object_name", 'out_object_classname',
                          'out_object_name', 'connector_classname', 'connector_name']
        # Method 1: Loop and pop
        for d in cable_data:
            for key in keys_to_remove:
                d.pop(key, None)  # None avoids KeyError if key doesn't exist
        return cable_data
    
    def zip_files(self, csv_file_name):
        zip_file_name = os.path.basename(csv_file_name)
        with zipfile.ZipFile('archive.zip', 'w') as zipf:
            for file in self.files_to_zip:
                zipf.write(file)

    def segregate_types_of_cable(self, cable_data_df, type):
        dup_file_name = "%s%s"%(type.split('_')[1], '_duplicate.csv')
        fiber_filter_in_object = cable_data_df[cable_data_df['in_object'].str.contains(type, case=False, na=False)]
        fiber_filter_out_object = cable_data_df[cable_data_df['out_object'].str.contains(type, case=False, na=False)]
        fiber_filter_data = pd.concat([fiber_filter_in_object, fiber_filter_out_object], ignore_index=True)
        fiber_filter_data = fiber_filter_data.drop_duplicates()
        # dupe_mask = fiber_filter_data.duplicated(subset=['in_object', 'out_object'], keep='first')
        # kept_only_duplicates = fiber_filter_data[dupe_mask]
        # if len(kept_only_duplicates) > 0:
        #     kept_only_duplicates.to_csv(os.path.join(self.csv_path_, dup_file_name), index=False)
        # fiber_filter_data = fiber_filter_data.drop_duplicates(subset=['in_object', 'out_object'], keep='first')
        return fiber_filter_data

    def ProcessCable(self):
        report_data = {}
        report_data.update({'region': self.region})
        cable_data = []
        cable_missing_data = []
        sql_get_equipment_name = f"SELECT EQUIPMENT_NAME FROM EQUIPMENT"
        sql_get_splice_closure_name = f"SELECT SPLICE_CLOSURE_NAME FROM SPLICE_CLOSURE"
        region_equipment_name = self.get_table_data(sql_get_equipment_name)
        region_splice_closure_name = self.get_table_data(sql_get_splice_closure_name)

        region_equipment_name = list(region_equipment_name['EQUIPMENT_NAME'])
        region_splice_closure_name = list(region_splice_closure_name['SPLICE_CLOSURE_NAME'])

        report_data.update({"region_equipment_name": len(region_equipment_name)})
        report_data.update({"region_splice_closure_name": len(region_splice_closure_name)})
        
        #200 - point
        self.NE_equipment_df = self.get_NE_table_data(f"SELECT * FROM Ne.EQUIPMENT", "EQUIPMENT_DATA")
        self.NE_splice_closure_df = self.get_NE_table_data(f"SELECT * FROM Ne.SPLICE_CLOSURE", "SPLICE_CLOSURE_DATA")
        self.NE_connection_df = self.get_NE_table_data(f"SELECT * FROM Ne.CONNECTION", "CONNECTION_DATA")
        self.NE_transmedia_df = self.get_NE_table_data(f"SELECT * FROM Ne.TRANSMEDIA", "TRANSMEDIA_DATA")


        equipment_obj_id = self.NE_equipment_df[self.NE_equipment_df['EQUIPMENT_NAME'].isin(region_equipment_name)]
        equipment_name_in_NE = list(equipment_obj_id['EQUIPMENT_NAME'])
        equipment_obj_id = list(equipment_obj_id['OBJECTID'])

        splice_obj_id = self.NE_splice_closure_df[self.NE_splice_closure_df['SPLICE_CLOSURE_NAME'].isin(region_splice_closure_name)]
        splice_name_in_NE = list(splice_obj_id['SPLICE_CLOSURE_NAME'])
        splice_obj_id = list(splice_obj_id['OBJECTID'])

        report_data.update({"NE_equipment_name": len(equipment_obj_id)})
        report_data.update({"NE_splice_name": len(splice_obj_id)})

        equipment_missing_region_element = self.missing_report(region_equipment_name, equipment_name_in_NE, 'EQUIPMENT')
        splice_missing_region_element = self.missing_report(region_splice_closure_name, splice_name_in_NE, 'SPLICE')
        
        report_data.update({"missing_region_equipment_name": len(equipment_missing_region_element)})
        report_data.update({"missing_region_splice_name": len(splice_missing_region_element)})

        missing_elements = equipment_missing_region_element+splice_missing_region_element

        equipment_df = self.NE_connection_df[(self.NE_connection_df['CONNECTOR_CLASSID'] == 370) & 
                                       (self.NE_connection_df['CONNECTOR_OBJECTID'].isin(equipment_obj_id))]
        
        splice_df = self.NE_connection_df[(self.NE_connection_df['CONNECTOR_CLASSID'] == 367) & 
                                       (self.NE_connection_df['CONNECTOR_OBJECTID'] .isin(splice_obj_id))]
        
        report_data.update({"equipment_connection_tbl_row": len(equipment_df)})
        report_data.update({"splice_connection_tbl_row": len(splice_df)})
        
        df_combined = pd.concat([equipment_df, splice_df], ignore_index=True)
        for index,  row in df_combined.iterrows():
            cable_row_data, status = self.set_attr_val(row)
            if status:
                cable_data.append(cable_row_data)
            else:
                cable_missing_data.append(cable_row_data)
            
        report_data.update({"total_count": len(cable_data)})
        report_data.update({"missing_count": len(cable_missing_data)})

        csv_file_name = r"C:\Kishore\SaskTel_Bisen\Swift"
        self.csv_path_ = r"C:\Kishore\SaskTel_Bisen\output"

        cable_data_df = pd.DataFrame(cable_data)
        cable_missing_data_df = pd.DataFrame(cable_missing_data)

        cable_data_df = cable_data_df.replace(r' fsc', '', regex=True)

        if len(cable_data_df) != 0:

            fiber_filter_data = self.segregate_types_of_cable(cable_data_df, 'mywcom_fiber_segment')
            fiber_filter_data = fiber_filter_data.drop(columns=self.ref_columns)
            fiber_filter_data.to_csv(os.path.join(csv_file_name, "mywcom_fiber_connection.csv"), index=False)
            report_data.update({"fiber_count": len(fiber_filter_data)})
            
            copper_filter_data = self.segregate_types_of_cable(cable_data_df, 'mywcom_copper_segment')
            copper_filter_data = copper_filter_data.drop(columns=self.ref_columns) 
            copper_filter_data.to_csv(os.path.join(csv_file_name, "mywcom_copper_connection.csv"), index=False)
            report_data.update({"copper_count": len(copper_filter_data)})

            coax_filter_data = self.segregate_types_of_cable(cable_data_df, 'mywcom_coax_segment')
            coax_filter_data = coax_filter_data.drop(columns=self.ref_columns) 
            coax_filter_data.to_csv(os.path.join(csv_file_name, "mywcom_coax_connection.csv"), index=False)
            report_data.update({"coax_count": len(coax_filter_data)})


        cable_missing_data_df.to_csv(os.path.join(csv_file_name, "missing_report.csv"), index=False)

        
        self._WriteCSVFile(os.path.join(csv_file_name, "ref_connection.csv"), cable_data)
        self._WriteCSVFile(os.path.join(csv_file_name, "missing_elements.csv"), missing_elements)
        pdf_path = os.path.join(csv_file_name, "Regina_summary.pdf")
        pdf_generator.make_summary_pdf(report_data, pdf_path)
        # # self._WriteCSVFile(missing_report_csv_file_name, missing_elements)
        # self._WriteCSVFile(missing_report_csv_file_name, cable_missing_data)
        # data_ = self.remove_tag(cable_data)
        # data_df = pd.DataFrame(data_)

        # data_df.to_csv(csv_file_name, index=False)
        
        # self._WriteCSVFile(csv_file_name, data_)
        return True
    
    
if __name__ == "__main__":
    connection_data = Connection()
    connection_data.ProcessCable()
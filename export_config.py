import pandas as pd
import json
import os
import logging
from datetime import datetime
import sys


def generate_config(excel_path, output_path):
    xls = pd.ExcelFile(excel_path)

    # Rename attribute keys 
    header_mapping = {
        "field name": "Field_Name",
        "display": "Display",
        "type": "Type",
        "field type":"Field_Type",
        "field length":"Field_Length",
        "ne/iqgeo field": "FieldSource",
        "replaced value":"ReplaceValue",
        "mandatory (yes/no)":"Mandatory",
        "default value":"defaultvalue",
        "domain value":"DomainValue",
        "source":"Source",
        "reference join":"Join"
    }

    # For renaming metadata keys (above "Attribute Finalised")
    metadata_mapping = {
        "Geometry Type": "Geometry_Type",
        "Display Name":"Display_Name",
        "Short Description":"Short_Description",
        "Track Changes":"Track_Changes",
        "Attribute Finalised":"Attribute_Finalised",
        "NE Table":"NE_Table",
        "Source ID":"Source_ID",
        "Filter Value":"Filter_Value"
    }

    for sheet_name in xls.sheet_names:
       
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        
        metadata = {}
        attr_header_row_index = None

        #  Extract metadata
        for i in range(len(df)):
            key = df.iloc[i, 0]
            val = df.iloc[i, 1]

            if isinstance(key, str) and key.strip().lower() == "attribute finalised":
                attr_header_row_index = i
                break

            if pd.notna(key):
                key_str = str(key).strip()
                val_str = str(val).strip() if pd.notna(val) else ""
                metadata[metadata_mapping.get(key_str, key_str)] = val_str

        if attr_header_row_index is None:
            print(f" 'Attribute Finalised' section not found in sheet: {sheet_name}")
            continue

        #  Read attribute headers 
        headers = df.iloc[attr_header_row_index, 1:].tolist()
        headers = [str(h).strip().lower() if pd.notna(h) else "" for h in headers]

        #  Parse attribute rows after header
        expected_keys = ["field name", "display", "type","field type" ,"field length","ne/iqgeo field","replaced value","mandatory (yes/no)","default value","domain value" ,"source","reference join"]

        

        attributes = []

        for i in range(attr_header_row_index + 1, len(df)):
            row = df.iloc[i, 1:len(headers) + 1]

            if row.isnull().all():
                continue

            attr_dict = {}
            for key in expected_keys:
                json_key = header_mapping.get(key, key)
                if key in headers:
                    idx = headers.index(key)
                    val = row.iloc[idx] if idx < len(row) else ""
                    val_str = str(val).strip() if pd.notna(val) else ""
                    attr_dict[json_key] = val_str
                else:
                    attr_dict[json_key] = ""

            attributes.append(attr_dict)

        #  Combine metadata and attributes
        final_json = metadata
        final_json["Attribute_Finalised"] = attributes

        #  Save to JSON
        output_filename = output_path + "\\"+metadata.get("Name", sheet_name).replace(" ", "_") + ".json"
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(final_json, f, indent=4)

        print(f" Saved JSON file: {output_filename}")
    return

if __name__ == "__main__":
    print("Task started...")


    if len(sys.argv) > 2:
        # sys.argv[0] is the script name, so we need at least 3 elements for 2 arguments
        xlsfilename = sys.argv[1]
        folder_path = sys.argv[2]
        print ("Input File - "+ xlsfilename)
        print ("Output folder path   "+ folder_path)
    else:
        # xlsfilename = r"C:\SaskTel_Bisen\Development\Data_Migration\config\Action Item-Structure ToBe Model.xlsx"
        xlsfilename = r"C:\SaskTel_Bisen\Development\Data_Migration\config\2.Route.xlsx"
        folder_path = r'C:\\SaskTel_Bisen\\Development\\Data_Migration\\config\\'

    if not os.path.exists(folder_path):
        os.makedirs(folder_path ) 
    try:
        print ("Input File - "+ xlsfilename)
            
        current_dir=os.getcwd()   
        log_folder_path = os.path.join(current_dir,"log")
        if not os.path.exists(log_folder_path):
            os.makedirs(log_folder_path ) 
        
        log_file =  log_folder_path +"\\CONFIG_CREATION_LOG_"+     datetime.now().strftime("%Y%m%d_%H%M%S_%f")+".txt"

        logging.basicConfig(
        filename=log_file,  # Name of the log file
        level=logging.INFO,         # Minimum level of messages to log (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format='%(asctime)s - %(levelname)s - %(message)s', # Format of log messages
        filemode='a'                # 'a' for append, 'w' for overwrite
        )
        logging.info(str(datetime.now())+" | " + " ********** CONFIG CREATION TASK STARTED ********** " )
        generate_config (xlsfilename,folder_path )
        
        logging.info(str(datetime.now())+" | " + " ********** CONFIG CREATION TASK FINISHED ********** " )
    
    except Exception as e:
        print(str(datetime.now())+" | "+"ERROR IN Creating folder | "+log_folder_path + " error "+ e)

    # else:
    #     # xlsfilename = r"C:\SaskTel_Bisen\Development\Data_Migration\Action Item-Structure ToBe Model.xlsx"
    #     # folder_path =r"C:\SaskTel_Bisen\Development\Data_Migration\config"
    #     print ("Required arguments not provided.  python.exe  export_config  'excel file name'  'output folder path'")
    


    #python export_config.py "C:\SaskTel_Bisen\Development\Data_Migration\config\2.Route (2).xlsx", "C:\SaskTel_Bisen\Development\Data_Migration\config\"                    
        

         

     
        
         
        



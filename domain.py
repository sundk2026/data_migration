import arcpy
import os
 
import json
from datetime import datetime

# Set your geodatabase workspace path
 

 

try:
    # List all domains in the workspace
    # domains = arcpy.da.ListDomains(workspace_path)
    domains =	arcpy.da.ListDomains("C:/Users/BiseI1/AppData/Roaming/ESRI/Desktop10.8/ArcCatalog/GNRMP_DIRECT_CONNECTION.sde")
    # Prepare domain data structure
     
    domains_data = []
    # Iterate through each domain
    for domain in domains:
        domain_info = {
            "name": domain.name,
            "description": domain.description or "",
           
        }
        
        # Add values based on domain type
        if domain.domainType == "CodedValue":
            domain_info["values"] = [
                {"value": code, "display_value": desc} 
                for code, desc in domain.codedValues.items()
            ]
        elif domain.domainType == "Range":
            min_val, max_val = domain.range
            domain_info["range"] = {
                "min_value": min_val,
                "max_value": max_val
            }
        flname=domain.name.lower()
	flname=flname.replace(" ", "_")
	flname= r"C:\\Users\\BiseI1\\Documents\\ArcGIS\\mywcm_"+flname+".enum"
	output_json = r"C:\\Users\\BiseI1\\Documents\\ArcGIS\\"+ domain.name +".enum"

        with open(flname, 'w') as json_file:
            json.dump(domain_info, json_file, indent=4)
        # json.dump(domain_info, json_file, indent=4)
    

    #domains_data.append(domain_info)

     
    print("Completed")
    # Write to JSON file
    # with open(output_json, 'w') as json_file:
        # json.dump(domains_data, json_file, indent=4)
        # json.dump(domain_info, json_file, indent=4)
    # print(output_json)

except Exception as e:
    print(e)
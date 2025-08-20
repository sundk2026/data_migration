import shapely
import csv
from shapely.geometry import Polygon
import fiona
from shapely.geometry import shape, LineString, Point,MultiLineString
from shapely.ops import transform
from pyproj import Transformer
from collections import defaultdict
import math
import re
from datetime import datetime, timedelta
import geopandas as gpd
import pandas as pd
import numpy as np
from geopy.distance import geodesic
from pyproj import Geod
from pyogrio import list_layers
import sqlite3
from shapely import wkb

# pip install geopy 
class UTILServices:
    # def __init__(self):

    def getEWKB(tempGeo, srcCRS, tgtCRS):
        # Reprojection of data if original data is in other then GCS - WGS84 
        transformer = Transformer.from_crs(srcCRS,tgtCRS,always_xy=True)
        trangeom=transform(transformer.transform,tempGeo)
        shaply_geom=shape(trangeom)
        wkb_data=shaply_geom.wkb_hex
        return wkb_data
    
    
    def check_domain_value(domain_csv, fld_val):
        try:
            values=[v.strip() for v in domain_csv.split(",")]
            return fld_val.strip() in values
        except Exception as e:
            print(f"Error occured during domain value check '{str(e)}' for domain '{domain_csv}' and value is '{fld_val}'")
         
    def find_duplicates(csv_row, name_fld_idx=2):
        clm_index=1
        value_map=defaultdict(list)
        for rw in csv_row:
            key=rw[clm_index]
            value_map[key].append(rw)
        duplicate_rows=[]
        duplicates={k:v for k, v in value_map.items() if len(v)>1}
        
        
        for val , rows in duplicates.items():
                for rw in rows:
                    csv_string=rw
                    
                    obj_id = csv_string[0]
                    geom = csv_string[1]
                    nm = csv_string[name_fld_idx]

                    duplicate_rows.append([obj_id,nm,geom])

        return len(duplicate_rows)        , duplicate_rows

    def check_field_type_and_value(field_value, field_type):
        # , obj_id,fld_nm,fld_indx,domain_val
        value_is_as_per_type = False
        modified_value = None
        if field_value !=None :
            if isinstance(field_value, str) and field_value.strip().lower() in ["nan", ""]:
                # fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1                
                return True, modified_value
            try:
                if field_type in ["integer", "bigint"]:
                    try:
                        modified_value = int(field_value)
                        if  math.isnan(field_value):
                            modified_value = None
                            # fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1
                        value_is_as_per_type = True          
                    except Exception as e:
                        # fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                        print(f"Error: failed to parse numric '{field_value}':{e}")
                elif field_type in ["double", "float","float64"]:
                    try:
                        modified_value = float(field_value)
                        if  math.isnan(field_value):
                            modified_value = None
                            # fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1
                        value_is_as_per_type = True
                    except Exception as e:
                            # fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                            print(f"Error: failed to parse numric '{field_value}':{e}")
                elif field_type.startswith("numeric"):
                    try:
                        modified_value = float(field_value)
                        if  math.isnan(field_value):
                            modified_value = None
                            # fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1
                        value_is_as_per_type = True
                    except Exception as e:
                            # fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
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
                        # else:
                            # fields_issues[fld_indx][1]=fields_issues[fld_indx][1]+1
                    except Exception as e:
                            # fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
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
                            # string_truncate_object.append([obj_id,fld_nm, field_value,modified_value])
                            # fields_issues[fld_indx][3]=fields_issues[fld_indx][3]+1
                    except Exception as e:
                            # fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                            print(f"Error: failed to parse string '{field_value}':{e}")
                elif field_type == "date":
                    try:
                        date_val = datetime.strptime(str(field_value), "%Y-%m-%d").date()
                        modified_value = str(date_val)
                        value_is_as_per_type = True
                    except Exception as e:
                        # fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                        print(f"Error: failed to parse date '{field_value}':{e}")

                elif field_type == "timestamp":
                    try:
                        # if len(str(field_value))<7:
                        #     field_value = datetime(int(field_value), 1, 1, 0, 0, 0)
                        #     # Convert the datetime object to a Unix timestamp
                        #     # field_value = date_object.timestamp()
                            
                        timestamp_val = datetime.strptime(str(field_value), "%Y-%m-%d %H:%M:%S")
                        modified_value = str(timestamp_val)
                        value_is_as_per_type = True
                    except Exception as e:
                        # fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                        print(f"Error: failed to parse timestamp '{field_value}':{e}")
                elif field_type == "Foreign Key":
                    try:
                        modified_value =  field_value
                        value_is_as_per_type = True
                    except Exception as e:
                        # fields_issues[fld_indx][2]=fields_issues[fld_indx][2]+1
                        print(f"Error: failed to parse timestamp '{field_value}':{e}")
                else:
                    value_is_as_per_type = False
                    modified_value = field_value
            except Exception as e:
                print(f"Error: failed to parse timestamp '{field_value}':{e}")
        else:
            value_is_as_per_type =True

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
    

    def apply_sql_like_filter(gdf: gpd.GeoDataFrame, condition: str) -> gpd.GeoDataFrame:


            

            # Step 1: Normalize SQL syntax to Python
            expr = condition
            expr = re.sub(r'\bAND\b', '&', expr, flags=re.IGNORECASE)
            expr = re.sub(r'\bOR\b', '|', expr, flags=re.IGNORECASE)
            expr = expr.replace('<>', '!=')

            # --- IN / NOT IN ---
            # Handle NOT IN first (avoid conflict with IN)
            # in_pattern = re.compile(r'\b(\w+)\s+NOT\s+IN\s*\(([^)]+)\)', flags=re.IGNORECASE)
            
            # expr = in_pattern.sub(lambda m: f'~gdf["{m.group(1)}"].isin([{UTILServices._convert_in_list(m.group(2))}])', expr)

            expr = re.sub( r'\b(\w+)\s+NOT\s+IN\s*\(([^)]+)\)', lambda m: f'~gdf["{m.group(1)}"].isin([{_convert_in_list(m.group(2))}])', expr, flags=re.IGNORECASE)
            expr = re.sub( r'\b(\w+)\s+IN\s*\(([^)]+)\)', lambda m: f'gdf["{m.group(1)}"].isin([{UTILServices._convert_in_list(m.group(2))}])',expr, flags=re.IGNORECASE )
           
            # Step 2: Replace column names with gdf["col"]
            for col in gdf.columns:
                # expr = re.sub(rf'\b{re.escape(col)}\b', f'gdf["{col}"]', expr)
                expr = re.sub(rf'\b{re.escape(col)}\b(?!"])',f'gdf["{col}"]',expr)
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
            
    def _convert_in_list(in_list_str: str) -> str:
        """Converts SQL IN list 'A','B',1 into Python list syntax with correct quoting."""
        items = []
        for item in in_list_str.split(','):
            item = item.strip()
            if re.match(r"^'.*'$", item): # quoted string
                items.append(item) # keep as is
            else: # number
                items.append(item)
        return ", ".join(items)
    
    def check_and_convert_value(value, expected_type):
         

        # Handle NULL / NaT
        is_null = pd.isnull(value)

        # Handle NaN (only for numeric)
        is_nan = False
        if isinstance(value, (int, float, np.number)) or pd.api.types.is_numeric_dtype(type(value)):
            try:
                is_nan = np.isnan(value)
            except:
                is_nan = False

        # Normalise expected type
        if isinstance(expected_type, str):
            et = expected_type.lower()
        else:
            et = expected_type.__name__.lower()

        converted_value = value
        conversion_success = False
        type_match = False

        try:
            if et in ("int","integer","bigint", "int64"):
                if isinstance(value, (int, np.integer)) and not is_null:
                    converted_value = int(value)
                    type_match = True
                    conversion_success = True
                else:
                    converted_value = int(value)
                    type_match = True
                    conversion_success = True

            elif et in ("float","double", "numeric","float64") or et.startswith("numeric"):
                if isinstance(value, (float, np.floating)) and not is_null:
                    type_match = True
                    conversion_success = True
                else:
                    converted_value = float(value)
                    type_match = True
                    conversion_success = True

            elif et in ("str", "string", "object") or et.startswith("string"):
                if isinstance(value, str) and not is_null:
                    type_match = True
                    conversion_success = True
                else:
                    converted_value = str(value) if not is_null else value
                    type_match = True
                    conversion_success = True

            elif et in ("datetime", "timestamp", "date"):
                if isinstance(value, pd.Timestamp) and not is_null:
                    value = value - timedelta(hours=5.5)
                    converted_value = value.strftime('%Y-%m-%dT%H:%M:%S') 

                    type_match = True
                    conversion_success = True
                else:
                    converted_value = pd.to_datetime(value, errors="raise")
                    converted_value = converted_value - timedelta(hours=6)
                    converted_value = converted_value.strftime('%Y-%m-%dT%H:%M:%S') 
                    type_match = True
                    conversion_success = True

            else:
                # Fallback generic type check
                expected_cls = eval(expected_type) if isinstance(expected_type, str) else expected_type
                if isinstance(value, expected_cls) and not is_null:
                    type_match = True
                    conversion_success = True
                else:
                    converted_value = expected_cls(value)
                    type_match = True
                    conversion_success = True

        except Exception:
            # Conversion failed, leave value as-is
            type_match = False
            conversion_success = False

        return {
            "is_null": bool(is_null),
            "is_nan": bool(is_nan),
            "type_match": bool(type_match),
            "converted_value": converted_value,
            "conversion_success": bool(conversion_success),
            "actual_type": type(value).__name__
        }

    def change_path_start_endpoints(multilinestring, new_first_point, new_last_point):
        """
        Changes the first and last vertex of a MultiLineString geometry.

        Args:
            multilinestring (shapely.geometry.MultiLineString): The input MultiLineString.
            new_first_point (shapely.geometry.Point): The new point for the first vertex.
            new_last_point (shapely.geometry.Point): The new point for the last vertex.

        Returns:
            shapely.geometry.MultiLineString: The MultiLineString with modified endpoints.
        """
        if not isinstance(multilinestring, MultiLineString ):
            raise TypeError("Input must be a   LineString.")
        
         
        # for i, linestring in enumerate(multilinestring.geoms):
        # print(multilinestring)
        # print(new_first_point)
        # print(new_last_point)
        
        lines = list(multilinestring.geoms)
        first_line_segment= list(lines[0].coords)
        last_line_segment= list(lines[-1].coords)

        
        # firstpnt= (first_cords[0][0],first_cords[0][1] )
        # str1pnt= (new_first_point.x, new_first_point.y)

        # dist1 = geodesic(str1pnt, firstpnt).meters
         
 
        dist1= UTILServices.distance_wgs84(first_line_segment[0][1] ,first_line_segment[0][0],new_first_point.y,new_first_point.x)
        dist2= UTILServices.distance_wgs84(last_line_segment[-1][1] ,last_line_segment[-1][0],new_last_point.y,new_last_point.x)
        

        if len(lines)>1:
            #If multiline have multiple segments then change 1st coordinate of 1st segment and last coordinate of last segement
            first_line_segment[0] = new_first_point
            lines[0]=LineString(first_line_segment)

            last_line_segment[-1] = new_last_point
            lines[-1]=LineString(last_line_segment)
        else:
            #If multiline have only one segments then change 1st coordinate of 1st segment and last coordinate of 1st segement
            first_line_segment[0] = new_first_point
            first_line_segment[-1] = new_last_point
            lines[0]=LineString(first_line_segment)

            




        # new_1st_vertex = (float(pt1[0]), float(pt1[1]))
        # new_last_vertex=(float(pt2[0]), float(pt2[1]))
        # coords[0] =new_first_point # new_1st_vertex
        # coords[-1] = new_last_point #new_last_vertex 

            
            # modified_linestrings.append(LineString(coords))
        # modified_linestrings.append((coords))
        ret_geom=MultiLineString(lines)
        return ret_geom, dist1,dist2
    
    def distance_math(lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius in kilometers

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad

        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance
    
    def distance_wgs84(lat1,lon1, lat2, lon2):
        geod = Geod(ellps='WGS84')

        # Define points (longitude, latitude)
        # lon1, lat1 = 21.0122287, 52.2296756
        # lon2, lat2 = 16.9251681, 52.406374

        # Calculate distance
        azimuth1, azimuth2, distance_meters = geod.inv(lon1, lat1, lon2, lat2)
        
        return distance_meters
        # print(f"Distance (pyproj): {distance_km:.2f} km")
    
    def gdb_to_sqlite(gdb_path, sqlite_path):
        
        try:
            layers = list_layers(gdb_path)
            
            for layer_name in layers:
                # Read the GDB layer
                lyr_nm=layer_name[0]
                gdf = gpd.read_file(gdb_path, layer=lyr_nm)

                # Add WKT and WKB columns
                gdf["geom_wkt"] = gdf.geometry.apply(lambda g: g.wkt if g else None)
                gdf["geom_wkb"] = gdf.geometry.apply(lambda g: g.wkb if g else None)

                # Drop original geometry column (optional if you don't want st_geometry)
                gdf = gdf.drop(columns="geometry")

                # Connect to SQLite
                conn = sqlite3.connect(sqlite_path)
                cur = conn.cursor()

                # Create table (dynamically from dataframe columns)
                cols = []
                for col, dtype in zip(gdf.columns, gdf.dtypes):
                    if col == "geom_wkb":
                        cols.append(f"{col} BLOB")  # store binary as BLOB
                    else:
                        if "int" in str(dtype):
                            cols.append(f"{col} INTEGER")
                        elif "float" in str(dtype):
                            cols.append(f"{col} REAL")
                        else:
                            cols.append(f"{col} TEXT")
                create_sql = f"CREATE TABLE IF NOT EXISTS {lyr_nm} ({', '.join(cols)});"
                cur.execute(create_sql)

                    # Insert rows
                placeholders = ", ".join(["?"] * len(gdf.columns))
                insert_sql = f"INSERT INTO {lyr_nm} VALUES ({placeholders})"
                conn.executemany(insert_sql, gdf.values.tolist())

                conn.commit()
                print(f"✅ Exported {len(gdf)} features from {lyr_nm} into {sqlite_path} ")

            conn.close()

        except Exception as ex:
            raise ValueError(f"Error in sqlite db migration: {ex}")



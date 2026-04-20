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
import random
import string
from typing import Literal, Union
import zipfile
import os, glob

from shapely.ops import linemerge, unary_union
from shapely.wkb import loads as load_wkb, dumps as dump_wkb
import binascii
import json



WKBLike = Union[str, bytes, bytearray]

# pip install geopy 
class UTILServices:
    # def __init__(self):

    def findStructureID(structure_folder: str, structure_name: str):
        # cached all data 
        if not hasattr(UTILServices, "_STRUCT_CACHE_SIMPLE"):
            UTILServices._STRUCT_CACHE_SIMPLE = {}

        abs_folder = os.path.abspath(structure_folder)
        if not structure_name:
            return None

        # Build cache for folder
        if abs_folder not in UTILServices._STRUCT_CACHE_SIMPLE:
            catalog = {}  
            all_files = glob.glob(os.path.join(abs_folder, "*"))
            all_csv_files = []
            
            for p in all_files:
                if os.path.isdir(p):
                    csv_files = glob.glob(f"{p}/*.csv")
                    all_csv_files.extend(csv_files)

            for p in all_csv_files:
                if p.lower().endswith(".fields"):
                    continue
                if not os.path.isfile(p):
                    continue
                try:
                    df = pd.read_csv(p, on_bad_lines='skip')
                except Exception:
                    continue
                if df.empty:
                    continue

                # detect name column
                lc = {c.lower(): c for c in df.columns}
                name_col = next((lc[c] for c in ["name"] if c in lc), None)
                if not name_col:
                    continue

                df["__name_norm__"] = df[name_col].astype(str).str.strip().str.upper()

                # store FULL row as dict
                for _, row in df.drop_duplicates("__name_norm__").iterrows():
                    nm = row["__name_norm__"]
                    if nm and nm not in catalog:
                    
                        row_dict = row.to_dict()
                        row_dict.pop("__name_norm__", None)
                        catalog[nm] = row_dict

            UTILServices._STRUCT_CACHE_SIMPLE[abs_folder] = catalog

        # lookup
        catalog = UTILServices._STRUCT_CACHE_SIMPLE[abs_folder]
        key = str(structure_name).strip().upper()

        return catalog.get(key, None)

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
         
    def find_duplicates(csv_row, name_fld_idx=2,clm_index=1, include_geom=True):
        
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
                    nm = csv_string[name_fld_idx]
                    if include_geom==True:
                        geom = csv_string[1]
                        duplicate_rows.append([obj_id,nm,geom])
                    else:
                        duplicate_rows.append([obj_id,nm,""])
                        

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

            expr = re.sub( r'\b(\w+)\s+NOT\s+IN\s*\(([^)]+)\)', lambda m: f'~gdf["{m.group(1)}"].isin([{UTILServices._convert_in_list(m.group(2))}])', expr, flags=re.IGNORECASE)
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
            expr
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


    def generate_random_string(length): 
        """Generates a pseudo-random string."""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for i in range(length))


    def insert_geometry(
        base_wkb: WKBLike,
        add_wkb: WKBLike,
        # where: Literal["start", "end", "auto"] = "auto",
        insert_at
        # tolerance: float = 1e-8
         
    ) -> Union[str, bytes]:
 
        g1 = UTILServices._ensure_mls(UTILServices._load_wkb(base_wkb))
        g2 = UTILServices._ensure_mls(UTILServices._load_wkb(add_wkb))
 
 
        if insert_at == 0:
        # We want g2.end to meet g1.start. Flip g2 if its start is closer instead.
            if UTILServices._start_point(g2).distance(UTILServices._start_point(g1)) < UTILServices._end_point(g2).distance(UTILServices._start_point(g1)):
                g2 = UTILServices._reverse_mls(g2)
                new_parts = list(g2.geoms) + list(g1.geoms)
                join_gap = UTILServices._end_point(g2).distance(UTILServices._start_point(g1))
        elif insert_at == -1:
        # We want g2.start to meet g1.end. Flip g2 if its end is closer instead.
            if UTILServices._end_point(g2).distance(UTILServices._end_point(g1)) < UTILServices._start_point(g2).distance(UTILServices._end_point(g1)):
                g2 = UTILServices._reverse_mls(g2)
                new_parts = list(g1.geoms) + list(g2.geoms)
                join_gap = UTILServices._end_point(g1).distance(UTILServices._start_point(g2))
            else:
                raise ValueError("where must be 'start', 'end', or 'auto'")
        # Build result
        result = MultiLineString(new_parts)
  
        out = wkb.dumps(result)
        return out.hex()  



    def _load_wkb(g: WKBLike):
        """Load WKB from hex string or bytes into a Shapely geometry."""
        if isinstance(g, (bytes, bytearray)):
            return wkb.loads(g)
        if isinstance(g, str):
        # assume hex; if not, this will raise ValueError
            return wkb.loads(bytes.fromhex(g))
        
        raise TypeError("WKB must be hex string or bytes/bytearray")

    def _ensure_mls(geom):
        if geom.geom_type == "LineString":
            return MultiLineString([geom])
        if geom.geom_type == "MultiLineString":
            return geom
        raise TypeError(f"Expected (Multi)LineString, got {geom.geom_type}")
    def _start_point(mls: MultiLineString) -> Point:
        ls0 = mls.geoms[0]
        return Point(ls0.coords[0])

    def _end_point(mls: MultiLineString) -> Point:
        lsN = mls.geoms[-1]
        return Point(lsN.coords[-1])

    def _reverse_linestring(ls: LineString) -> LineString:
        return LineString(list(ls.coords)[::-1])

    def _reverse_mls(mls: MultiLineString) -> MultiLineString:
        # reverse order of parts and flip each part’s direction
        rev_parts = [UTILServices._reverse_linestring(ls) for ls in mls.geoms[::-1]]
        return MultiLineString(rev_parts)

    def update_column(data, key_value, col_index, new_value):
        for row in data:
            if row[0] == key_value:  
                row[col_index] = new_value
        
        return data
    
    def merge_geom(geom_ary):
        shapleygeom=[load_wkb(bytes.fromhex(g)) for g in  geom_ary]
        merged = unary_union (shapleygeom)
        lm=linemerge(merged) 
        return dump_wkb(lm).hex().upper()

    def merge_multilines_wkb(a_wkb: WKBLike, b_wkb: WKBLike, return_hex: bool = True) -> Union[str, bytes]:
     
        def _load(g: WKBLike):
            if isinstance(g, (bytes, bytearray)):
                return wkb.loads(g)
            if isinstance(g, str):
                return wkb.loads(bytes.fromhex(g))
            raise TypeError("WKB must be hex string or bytes/bytearray")
        def _as_mls(geom):
            if geom.geom_type == "LineString":
                return MultiLineString([geom])
            if geom.geom_type == "MultiLineString":
                return geom
            raise TypeError(f"Expected (Multi)LineString, got {geom.geom_type}")
        def _start_pt(mls: MultiLineString) -> Point:
            ls0 = mls.geoms[0]
            return Point(ls0.coords[0])
        def _end_pt(mls: MultiLineString) -> Point:
            lsn = mls.geoms[len(mls.geoms)-1]
            return Point(lsn.coords[len(lsn.coords)-1])
        def _rev_ls(ls: LineString) -> LineString:
            return LineString(list(ls.coords)[::-1])
        def _rev_mls(mls: MultiLineString) -> MultiLineString:
            # reverse order and direction of parts (Shapely 2 safe)
            parts = [mls.geoms[i] for i in range(len(mls.geoms)-1, -1, -1)]
            return MultiLineString([_rev_ls(ls) for ls in parts])
        A = _as_mls(_load(a_wkb))
        B = _as_mls(_load(b_wkb))
        # Decide side automatically: B.end→A.start  vs  B.start→A.end
        d_start_side = _end_pt(B).distance(_start_pt(A))
        d_end_side = _start_pt(B).distance(_end_pt(A))
        attach = "start" if d_start_side <= d_end_side else "end"
        if attach == "start":
            # We want B.end ≈ A.start; flip B if its start is closer to A.start
            if _start_pt(B).distance(_start_pt(A)) < _end_pt(B).distance(_start_pt(A)):
                B = _rev_mls(B)
            
            new_parts = list(B.geoms) + list(A.geoms)
        else:
                # We want B.start ≈ A.end; flip B if its end is closer to A.end
            if _end_pt(B).distance(_end_pt(A)) < _start_pt(B).distance(_end_pt(A)):
                B = _rev_mls(B)
            new_parts = list(A.geoms) + list(B.geoms)
            
        merged = MultiLineString(new_parts)

        merged_geometry = linemerge(merged)

        # If you ever want to collapse into a single LineString when parts touch, uncomment:
        # merged = linemerge(merged)
        out = wkb.dumps(merged_geometry)
        return out.hex() if return_hex else out
    
    def merge_corehole_geom (buried_geom, ch_geom, inserte_at):

        return
    
    def get_char_after(text_to_check,char_to_find):
        result=""         
        index = text_to_check.rfind(char_to_find)
        if index != -1: 
            result = text_to_check[index + 1:]

        return result

    def remove_duplicates (csv_data_list):
        """
        Removes duplicate rows from a list of CSV data, preserving order.
        Assumes each row in csv_data_list is a list of strings (or other hashable types).
        """
        print(f'Removing duplicates...rows before {len(csv_data_list)}')
        seen = set()
        unique_rows = []
        for row in csv_data_list:
            # Convert row to tuple for hashability
            row_tuple = tuple(row)
            if row_tuple not in seen:
                unique_rows.append(row)
                seen.add(row_tuple)
        print(f'Rows after duplicate removal {len(unique_rows)}')
        
        return unique_rows

    def remove_duplicates_from_csv(input_csv_path, output_csv_path=None, subset=None, keep='first'):
        """
        Removes duplicate rows from a CSV file.

         
        """
        try:
            # Read the CSV file into a pandas DataFrame
            df = pd.read_csv(input_csv_path)

            # Remove duplicate rows
            # 'inplace=True' modifies the DataFrame directly
            df.drop_duplicates(subset=subset, keep=keep, inplace=True)

            # Determine the output path
            if output_csv_path is None:
                output_csv_path = input_csv_path

            # Save the DataFrame to a new CSV file (or overwrite the original)
            # 'index=False' prevents pandas from writing the DataFrame index as a column
            df.to_csv(output_csv_path, index=False)
           

        except FileNotFoundError:
            print(f"Error: The file '{input_csv_path}' was not found.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def WriteCSVFile(file_name,clm_name, csvdata, remove_duplicate=True):
        if len(csvdata)>0:
            if remove_duplicate == True:
                print(f'Removing duplicates...',end="\r")
                csvdata= UTILServices.remove_duplicates(csvdata)
                print(f'Total record after duplicate {len(csvdata)}')

            with open(file_name,'w',newline='',encoding='utf-8') as csvfile:
                    writer=csv.writer(csvfile)
                    # for csvdata in csvdata_list:
                    writer.writerow( clm_name)        
                    writer.writerows( csvdata)
                
             
        else:
            print("No data processed to write the CSV file.")        
    
    def WriteZipFile(self,selected_files,rootDirectory,target_object,output_zip_file_name):
        self.output_zip_file_name = rootDirectory +"\\" + target_object.upper() +'_cdif'+ datetime.now().strftime("%Y%m%d_%H%M%S")+'.zip'

        with zipfile.ZipFile(output_zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_name in selected_files:
                file_path = os.path.join(rootDirectory, file_name)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    zipf.write(file_path, arcname=file_name) # arcname ensures only the filename is used in the zip
                else:
                    print(f"Warning: File '{file_name}' not found in '{self.folder_path}' and could not be added to the zip.")
                    # logging.warning(f"Warning: File '{file_name}' not found in '{self.folder_path}' and could not be added to the zip.")
    
    def GetColumnIndex(clm_names,clm):
        idx=0
          
        for cl in clm_names:
            if cl==clm:
                return idx
            idx+=1
        
        return -1
    
    def angle_deg(p0, p1):
        """Planar angle (azimuth) in degrees, 0° = east, 90° = north, [-180, 180)."""
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        ang = math.degrees(math.atan2(dy, dx))  # atan2(y, x)
        return ang
    
    def offset_geometry_latest(geom: LineString, distance: float, side: str = "left"):
        """
        Offset a LineString using Shapely's parallel_offset and replace endpoints with originals.
        Returns a LineString or None if not possible.
        """
        if not isinstance(geom, LineString):
            raise TypeError("Only LineString geometries are supported.")

        # Guard against degenerate lines
        if geom.is_empty or geom.length == 0:
            return None

        # Compute offset; join_style=2 (mitre). Adjust mitre_limit if needed.
        offset = geom.parallel_offset(distance, side=side, join_style=2, mitre_limit=5.0)

        if offset.is_empty:
            return None

        # Normalize to a single LineString
        if isinstance(offset, MultiLineString):
            parts = list(offset.geoms)
            if not parts:
                return None
            offset_ls = max(parts, key=lambda g: g.length)
        elif isinstance(offset, LineString):
            offset_ls = offset
        else:
            merged = linemerge(offset)
            if merged.is_empty:
                return None
            if isinstance(merged, MultiLineString):
                parts = list(merged.geoms)
                if not parts:
                    return None
                offset_ls = max(parts, key=lambda g: g.length)
            elif isinstance(merged, LineString):
                offset_ls = merged
            else:
                return None

        coords = list(offset_ls.coords)
        if len(coords) < 2:
            return None

        # Replace endpoints (do not insert; preserve order)
        coords[0]  = geom.coords[0]
        coords[-1] = geom.coords[-1]

        return LineString(coords)
    
    def offset_geometry(geom, distance, side="left"):
        """
            Offsets a LineString geometry while keeping the first and last vertices fixed.

            Parameters:
            geom (LineString): Input LineString geometry.
            distance (float): Offset distance (positive = outward, negative = inward).
            side (str): "left" or "right" offset direction.

    Returns:
    LineString: Offset geometry with fixed endpoints.
    """
        if not isinstance(geom, LineString):
            raise TypeError("Only LineString geometries are supported.")

    # Create offset line using shapely
        offset_geom = geom.parallel_offset(distance, side, join_style=2)
    # parallel_offset may return MultiLineString
        if offset_geom.geom_type == "MultiLineString":
        # pick the longest one (most likely the intended offset)
            try:
                offset_geom = max(offset_geom, key=lambda l: l.length)
            except Exception as e:
                offset_geom = max(offset_geom.geoms, key=lambda l: l.length)

        if offset_geom:
            # Extract coords and replace first & last with original
            coords = list(offset_geom.coords)
            #adding first and last vertex by taking from source geom
            # coords.insert(0,geom.coords[0])
            # coords.insert(0,geom.coords[-1])

            coords[0]  = geom.coords[0]
            coords[-1] = geom.coords[-1]


        
            return LineString(coords)
        return offset_geom


    def offset_line(line, distance, side='left', join_style=2):
        # Generate offset line using Shapely’s built-in function
        offset = line.parallel_offset(distance, side, join_style=join_style)

        # Handle MultiLineString (take the longest piece)
        if offset.geom_type == 'MultiLineString':
            offset = max(offset.geoms, key=lambda g: g.length)

            # Extract coordinates and fix start/end points
        coords = list(offset.coords)
        coords[0] = line.coords[0]
        coords[-1] = line.coords[-1]

        return LineString(coords)
    def get_db_con():
    
        try:    
            with open('config\dbcon.json', 'r') as f:
                settings = json.load(f)
        except:
             settings=""

        return settings
    def export_gdb_to_sqlite(gdb_path, sqlite_db_path,layers):
        
        # Create a SQLite connection
        conn = sqlite3.connect(sqlite_db_path)

        for layer_name in layers:
            print(f"Exporting feature class: {layer_name}")
            try:
                # Read the feature class into a GeoDataFrame
                gdf = gpd.read_file(gdb_path, layer=layer_name,ignore_geometry=True)

                # Export the GeoDataFrame to a table in the SQLite database
                # 'if_exists="replace"' will overwrite the table if it already exists
                # 'index=False' prevents writing the GeoDataFrame index as a column
                gdf.to_sql(name=layer_name, con=conn, if_exists='replace', index=False)
                print(f"Successfully exported {layer_name} to SQLite.")
            except Exception as e:
                print(f"Error exporting {layer_name}: {e}")

        # Close the SQLite connection
        conn.close()
        print(f"Export process complete. Data saved to {sqlite_db_path}")

    # Example usage:
    # Specify the path to your .gdb and the desired output .sqlite file
        # file_gdb_path = "path/to/your/your_geodatabase.gdb"
        # output_sqlite_path = "path/to/your/output_database.sqlite"

        # # Ensure the output directory exists
        # output_dir = os.path.dirname(output_sqlite_path)
        # if not os.path.exists(output_dir):
        #     os.makedirs(output_dir)

        # export_gdb_to_sqlite(file_gdb_path, output_sqlite_path)
        
    def ConvertMultiLineToLine(geom):

        converted_line = None
        if geom is None:
            return converted_line
        
        if isinstance(geom, LineString):
            converted_line = geom
            
        elif isinstance(geom, MultiLineString):
            coords = []
            for line in geom.geoms:
                coords.extend(line.coords)
            converted_line = LineString(coords)
        return converted_line
    

    def get_csv_path(csv_data_path, folder_name):
        if folder_name == 'cables':
            return glob.glob(os.path.join(os.path.join(csv_data_path, folder_name), "**", "*_cable*.csv"), recursive=True)
        if folder_name == 'routes':
            return [f for f in glob.glob(os.path.join(csv_data_path, folder_name, "**", "*.csv"), recursive=True)
            if os.path.basename(f) in ['formation_ug_route.csv','oh_route.csv','ug_route.csv']]
        if folder_name == 'segment':
            return glob.glob(os.path.join(os.path.join(csv_data_path, folder_name), "**", "*_segment*.csv"), recursive=True)
        return glob.glob(os.path.join(os.path.join(csv_data_path, folder_name), "**", "*.csv"), recursive=True)


    def get_data_of_item(csv_data_path, folder_name):
        csv_paths = UTILServices.get_csv_path(csv_data_path, folder_name)
        df_list = [pd.read_csv(file) for file in csv_paths]
        data = pd.concat(df_list, ignore_index=True)
        return  data
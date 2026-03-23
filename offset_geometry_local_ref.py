import sqlite3, os, oracledb, csv, zipfile
import pandas as pd
from  util_services import UTILServices 
from shapely import wkb, wkt
from shapely.geometry import LineString,MultiLineString, Point
from shapely.ops import transform, substring
from pyproj import Transformer
import binascii, struct
import math, os
from tqdm import tqdm
# from get_offset_geometry import get_geometry
# from shapely.wkb import dumps
import pyproj
import numpy as np

 

class offset_geometry():
    def __init__(self):
        self.csv_path = r"C:\Kishore\Test\cable_kranthi\regina_localreftest\reg_test"
        # self.cable_df = pd.read_csv(os.path.join(self.csv_path, "swc_cable_offset.csv"))
        # self.segment_df = pd.read_csv(os.path.join(self.csv_path, "swc_segment_offset.csv"))
        self.route_data_df = UTILServices.get_data_of_item(self.csv_path, 'route')
        # self.route_data_df = self.route_data_df[self.route_data_df['id'].str.contains('oh_route') | self.route_data_df['id'].str.contains('ug_route')]
        self.route_data_df = self.route_data_df[['id', 'name', 'path']]
        self.cable_df = UTILServices.get_data_of_item(self.csv_path, 'cable')
        self.segment_df = UTILServices.get_data_of_item(self.csv_path, 'segment')

        self.fiber_cable_data = pd.read_csv(os.path.join(self.csv_path, "cable", "fiber_cable.csv")
                                            , dtype={"st_vntge_yr": "Int64",
                                                     "sap_pm_order": "Int64"})
        self.copper_cable_data = pd.read_csv(os.path.join(self.csv_path, "cable", "copper_cable.csv"),
                                             dtype={"st_vntge_yr": "Int64",
                                                     "sap_pm_order": "Int64"})
        self.coax_cable_data = pd.read_csv(os.path.join(self.csv_path, "cable", "coax_cable.csv"),
                                           dtype={"st_vntge_yr": "Int64",
                                                     "sap_pm_order": "Int64"})
        
        self.ref_columns = ['route_name','path', 'count', 'side', 'wkb_hex','placement','distance', 'length']
        
        # self.oh_route = pd.read_csv(os.path.join(self.csv_path, "oh_route_regina.csv"))
        # self.ug_route = pd.read_csv(os.path.join(self.csv_path, "ug_route_regina.csv"))
        # self.structure = pd.read_csv(os.path.join(self.csv_path, "structure_data.csv"))
        self.cable_df['path'] = self.cable_df['path'].apply(lambda x: self.ewkb_to_linestring_wkts(x))
        # self.oh_route['path'] = self.oh_route['path'].apply(lambda x: self.ewkb_to_linestring_wkts(x))
        # self.ug_route['path'] = self.ug_route['path'].apply(lambda x: self.ewkb_to_linestring_wkts(x))
        self.route_data_df['path'] = self.route_data_df['path'].apply(lambda x: self.ewkb_to_linestring_wkts(x))
        self.cable_df['length'] = self.cable_df['path'].apply(lambda x: self.calculate_distance(x))
        self.cable_df["length"] = self.cable_df["length"].astype(float)
        self.cable_df['cable_id'] = self.cable_df['id']
        self.route_dict = {}


        # self.oh_route = self.oh_route[['id', 'name', 'path']]
        # self.ug_route = self.ug_route[['id', 'name', 'path']]
        # self.structure = self.structure[['id', 'name', 'path']]

        # self.route_data_df = pd.concat([self.oh_route, self.ug_route], ignore_index=True)

    def angle_deg(self, p0, p1):
        """Planar angle (azimuth) in degrees, 0° = east, 90° = north, [-180, 180)."""
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        ang = math.degrees(math.atan2(dy, dx))  # atan2(y, x)
        return ang
    
    def almost_equal_xy(self, a, b, tol=1e-12):
        return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol

    def merge_original_endpoints_with_target(self, original_wkt: str, target_wkt: str, tol=1e-12) -> str:
        """
        Build a new LineString: [original_start] + target_coords + [original_end],
        with duplicate suppression at the junctions within the given tolerance.
        """
        orig = wkt.loads(original_wkt)
        targ = wkt.loads(target_wkt)

        if orig.geom_type != "LineString" or targ.geom_type != "LineString":
            raise ValueError("Both inputs must be LINESTRING WKTs")

        orig_coords = list(orig.coords)
        targ_coords = list(targ.coords)

        if len(orig_coords) < 2 or len(targ_coords) < 2:
            raise ValueError("Each LineString must have at least 2 coordinates")

        order_status, nearest_coords = self.closer_point_geodesic(targ_coords[0], orig_coords[0], orig_coords[-1])

        if order_status:
            start_orig = orig_coords[0]
            end_orig   = orig_coords[-1]
        else:
            start_orig = orig_coords[-1]
            end_orig   = orig_coords[0]

        out_coords = []

        # Always start with original start
        out_coords.append(start_orig)

        # Append target coords, but skip if its first is same as original start
        if self.almost_equal_xy(targ_coords[0], start_orig, tol):
            out_coords.extend(targ_coords[1:])
        else:
            out_coords.extend(targ_coords)

        # Finally append original end, but avoid duplicating if target last equals end
        if not self.almost_equal_xy(out_coords[-1], end_orig, tol):
            out_coords.append(end_orig)

        # Build LineString and return WKT
        return LineString(out_coords).wkt
    
    def _read_uint32(self, data, offset, endian):
        return struct.unpack_from(endian+'I', data, offset)[0], offset+4

    def _read_double_pair(self, data, offset, endian):
        x = struct.unpack_from(endian+'d', data, offset)[0]
        y = struct.unpack_from(endian+'d', data, offset+8)[0]
        return (x, y), offset+16

    def ewkb_to_linestring_wkts(self, hexstr):
        """
        Parse EWKB hex:
        - If LINESTRING -> returns [ 'SRID=...;LINESTRING (...)' ]
        - If MULTILINESTRING -> returns [ 'SRID=...;LINESTRING (...)', ... ] (one per part)
        Supports 2D EWKB with optional SRID. (No Z/M.)
        """
        s = hexstr.strip()
        if s.startswith(('0x','0X')): s = s[2:]
        if s.startswith('\\x'): s = s[2:]
        data = binascii.unhexlify(s)

        # Header
        byte_order = data[0]
        endian = '<' if byte_order == 1 else '>'
        gtype_flags, off = struct.unpack_from(endian+'I', data, 1)[0], 5

        has_srid = (gtype_flags & 0x20000000) != 0  # EWKB SRID flag
        base_type = gtype_flags & 0xFF              # 2=LineString, 5=MultiLineString
        srid = None
        if has_srid:
            srid, off = self._read_uint32(data, off, endian)

        def wkt_prefix():
            return f"SRID={srid};" if srid is not None else ""

        if base_type == 2:  # LineString
            npts, off = self._read_uint32(data, off, endian)
            coords = []
            for _ in range(npts):
                (x, y), off = self._read_double_pair(data, off, endian)
                coords.append((x, y))
            wkt = "LINESTRING (" + ", ".join(f"{x:.17g} {y:.17g}" for x, y in coords) + ")"
            return wkt

        elif base_type == 5:  # MultiLineString
            ngeoms, off = self._read_uint32(data, off, endian)
            results = []
            for _ in range(ngeoms):
                # sub-geometry header
                bo = data[off]
                sub_endian = '<' if bo == 1 else '>'
                gtf, off2 = struct.unpack_from(sub_endian+'I', data, off+1)[0], off+5
                has_srid_sub = (gtf & 0x20000000) != 0
                base_sub = gtf & 0xFF
                if has_srid_sub:
                    # Children in EWKB typically do NOT carry SRID; handle if present anyway
                    _, off2 = self._read_uint32(data, off2, sub_endian)
                if base_sub != 2:
                    raise ValueError("Sub-geometry is not a LineString")

                npts, off2 = self._read_uint32(data, off2, sub_endian)
                coords = []
                for __ in range(npts):
                    (x, y), off2 = self._read_double_pair(data, off2, sub_endian)
                    coords.append((x, y))
                wkt = "LINESTRING (" + ", ".join(f"{x:.17g} {y:.17g}" for x, y in coords) + ")"
                results = ''
                off = off2

            return results

        else:
            raise ValueError(f"Unsupported geometry type (base_type={base_type}). 2=LineString, 5=MultiLineString")
        

    def get_offset_geometry(self, wkt_line, s, side):
        try:
            geom = wkt.loads(wkt_line)
            i = list(geom.coords)
            # i = [(-104.67516891069731, 50.49845604825566), (-104.6748792321237, 50.49919992401905), (-104.67333427973112, 50.49907708295743), (-104.67204681940397, 50.49857889093238)]
            multi_line=LineString(i)
            to_meters=Transformer.from_crs("EPSG:4326","EPSG:3857",always_xy=True).transform
            to_latlon=Transformer.from_crs("EPSG:3857","EPSG:4326",always_xy=True).transform
            multi_line_m=transform(to_meters,multi_line)
            offset_line_m=multi_line_m.parallel_offset(s,side=side,join_style=2)
            offset_line_ll=transform(to_latlon,offset_line_m)


            line = LineString(offset_line_ll)
            project_to_m = pyproj.Transformer.from_crs("EPSG:4326","EPSG:3857", always_xy=True).transform
            line_m = transform(project_to_m, line)
            start_trim = 10
            end_trim = 10
            length = line_m.length
            trimmed_m = substring(line_m, start_trim, length-end_trim)
            project_to_ll = pyproj.Transformer.from_crs("EPSG:3857","EPSG:4326",always_xy=True).transform
            trimmed_ll = transform(project_to_ll, trimmed_m)
            merged_wkt = self.merge_original_endpoints_with_target(wkt_line, str(trimmed_ll))
            return True, merged_wkt
        except Exception as e:
            return False, None
       
    def calculate_distance(self, wkt_str):
        if wkt_str:
            geom = wkt.loads(wkt_str)
            project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32613", always_xy=True).transform
            geom_m = transform(project, geom)
            length_m = geom_m.length
            return length_m
        return 0

    def OffsetGeometry(self):
        fiber_cable_off_set_geometry = []
        copper_cable_off_set_geometry = []
        coax_cable_off_set_geometry = []

        
        self.route_data  = (
                    self.segment_df.groupby('root_housing')
                    .agg(
                        count=('cable', 'size'),      # or use 'size' on any column
                        cables=('cable', list)        # all cable values (includes duplicates/NaNs)
                    )
                    .reset_index()
                )

        
        for row_index, row in tqdm(self.route_data.iterrows(), total=len(self.route_data), desc="Processing route"):
            if 'ug_route' not in row['root_housing'] and 'oh_route' not in row['root_housing']:
                continue
            
            if not self.route_data_df.loc[(self.route_data_df['id'] == row['root_housing'])].empty:
                route_row_data = self.route_data_df.loc[(self.route_data_df['id'] == row['root_housing'])]
                route_row_data = route_row_data['path'].iloc[0]
                route_line = wkt.loads(route_row_data)
                start_point = Point(route_line.coords[0])
            else:
                continue
            filter_cable = self.cable_df[self.cable_df['cable_id'].isin(row['cables'])].reset_index(drop=True)
            if not filter_cable.empty:
                filter_cable = filter_cable.sort_values(by="length", ascending=True)
                index_count = 1
                right_side_count = 0
                left_side_count = 0
                for index, row_data in filter_cable.iterrows():
                    if row_data['path'] == '': continue
                    geom = wkt.loads(row_data['path'])
                    if geom.geom_type == 'MultiLineString': continue
                    other_start = Point(geom.coords[0])
                    coords = list(geom.coords)
                    if not start_point.equals(other_start):continue

                    self.route_dict[row['root_housing']] = self.route_dict.get(row['root_housing'], 0)+1
                    side = 'left' if index_count%2 == 0 else 'right'
                    if side == 'right':
                        right_side_count += 1
                        distance = right_side_count*2
                    if side == 'left':
                        left_side_count += 1
                        distance = left_side_count*2
                    try:
                        status, wkt_line = self.get_offset_geometry(row_data['path'], distance, side)
                        off_set_geom = wkt.loads(wkt_line)
                    except Exception as e:
                        print(str(e))
                    if off_set_geom: off_set_geom = off_set_geom.wkb_hex 
                    if "fiber_cable" in row_data['cable_id']:
                        self.fiber_cable_data.loc[
                            self.fiber_cable_data['name'] == row_data['name'],
                            'offset_geom'
                        ] = off_set_geom
                        fiber_cable_off_set_geometry.append({"id": row_data['cable_id'].split('/')[1],
                                                    "offset_geom": off_set_geom,
                                                    "name": row_data['name'],
                                                    "route_name": row['root_housing'],
                                                    "path":row_data['path'],
                                                    "wkb_hex":wkt_line,
                                                    "count": len(filter_cable),
                                                    "placement": index_count,
                                                    "distance":distance,
                                                    "side": side,
                                                    "length": row_data['length']})
                    if "copper_cable" in row_data['cable_id']:
                        self.copper_cable_data.loc[
                            self.copper_cable_data['name'] == row_data['name'],
                            'offset_geom'
                        ] = off_set_geom
                        copper_cable_off_set_geometry.append({"id": row_data['cable_id'].split('/')[1],
                                                    "offset_geom": off_set_geom,
                                                    "name": row_data['name'],
                                                    "route_name": row['root_housing'],
                                                    "path":row_data['path'],
                                                    "wkb_hex":wkt_line,
                                                    "count": len(filter_cable),
                                                    "placement": index_count,
                                                    "distance":distance,
                                                    "side": side,
                                                    "length": row_data['length']})
                    if "coax_cable" in row_data['cable_id']:
                        self.coax_cable_data.loc[
                            self.coax_cable_data['name'] == row_data['name'],
                            'offset_geom'
                        ] = off_set_geom
                        coax_cable_off_set_geometry.append({"id": row_data['cable_id'].split('/')[1],
                                                    "offset_geom": off_set_geom,
                                                    "name": row_data['name'],
                                                    "route_name": row['root_housing'],
                                                    "path":row_data['path'],
                                                    "wkb_hex":wkt_line,
                                                    "count": len(filter_cable),
                                                    "placement": index_count,
                                                    "distance":distance,
                                                    "side": side,
                                                    "length": row_data['length']})
                    index_count += 1
        fiber_offset_df = pd.DataFrame(fiber_cable_off_set_geometry)
        if not fiber_offset_df.empty: fiber_offset_df = fiber_offset_df.dropna(subset=["offset_geom"]).reset_index(drop=True)
        
        copper_offset_df = pd.DataFrame(copper_cable_off_set_geometry)
        if not copper_offset_df.empty: copper_offset_df = copper_offset_df.dropna(subset=["offset_geom"]).reset_index(drop=True)
        
        coax_offset_df = pd.DataFrame(coax_cable_off_set_geometry)
        if not coax_offset_df.empty: coax_offset_df = coax_offset_df.dropna(subset=["offset_geom"]).reset_index(drop=True)

        df_combined = pd.concat([fiber_offset_df, copper_offset_df, coax_offset_df], ignore_index=False)

        if not df_combined.empty: df_combined.to_csv(os.path.join(self.csv_path, "ref_data.csv"), index=False)

        if not fiber_offset_df.empty: fiber_offset_df = fiber_offset_df.drop(columns=self.ref_columns)
        if not copper_offset_df.empty: copper_offset_df = copper_offset_df.drop(columns=self.ref_columns)
        if not coax_offset_df.empty:   coax_offset_df = coax_offset_df.drop(columns=self.ref_columns)

        # if not fiber_offset_df.empty: fiber_offset_df.to_csv(os.path.join(self.csv_path, "fiber_cable.csv"), index=False)
        # if not copper_offset_df.empty: copper_offset_df.to_csv(os.path.join(self.csv_path, "copper_cable.csv"), index=False) 
        # if not coax_offset_df.empty: coax_offset_df.to_csv(os.path.join(self.csv_path, "coax_cable.csv"), index=False)
        
        if not fiber_offset_df.empty: self.fiber_cable_data.to_csv(os.path.join(self.csv_path, "cable", "fiber_cable.csv"), index=False)
        if not copper_offset_df.empty: self.copper_cable_data.to_csv(os.path.join(self.csv_path,  "cable", "copper_cable.csv"), index=False)
        if not coax_offset_df.empty: self.coax_cable_data.to_csv(os.path.join(self.csv_path,  "cable", "coax_cable.csv"), index=False)

        return self.csv_path, True
    
    def closer_point_geodesic(self, target, p1, p2):
        """
        Returns ('p1' or 'p2', distance_to_winner_in_meters)
        target, p1, p2 are (lon, lat) tuples.
        """
        # WGS84 ellipsoid
        geod = pyproj.Geod(ellps="WGS84")

        def geodesic_dist_m(a, b):
            # geodesic distance in meters
            _, _, dist_m = geod.inv(a[0], a[1], b[0], b[1])
            return dist_m

        d1 = geodesic_dist_m(target, p1)
        d2 = geodesic_dist_m(target, p2)

        if not (math.isfinite(d1) and math.isfinite(d2)):
            raise ValueError("Non-finite distance computed. Check inputs.")

        return (True, d1) if d1 <= d2 else (False, d2)
    
if __name__ == "__main__":
    try:
        connection_data = offset_geometry()
        path, status = connection_data.OffsetGeometry()
        if status: print(f"CSV generated and check in path: {path}")
    except Exception as e:
        raise Exception(f"Error : {str(e)}")
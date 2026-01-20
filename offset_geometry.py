import sqlite3, os, oracledb, csv, zipfile
import pandas as pd
from  util_services import UTILServices 
from shapely import wkb, wkt
from shapely.geometry import LineString
import binascii
import math, os
from tqdm import tqdm


class offset_geometry():
    def __init__(self):
        self.csv_path = r"C:\Kishore\Offset_Geometry"
        self.cable_df = pd.read_csv(os.path.join(self.csv_path, "cable_data.csv"))
        self.segment_df = pd.read_csv(os.path.join(self.csv_path, "segment_data.csv"))
        self.ref_columns = ['route_name','path', 'count', 'overall_angle', 'side']

    def angle_deg(self, p0, p1):
        """Planar angle (azimuth) in degrees, 0° = east, 90° = north, [-180, 180)."""
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        ang = math.degrees(math.atan2(dy, dx))  # atan2(y, x)
        return ang
       

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

        
        for index, row in tqdm(self.route_data.iterrows(), total=len(self.route_data), desc="Processing route"):
            filter_cable = self.cable_df[self.cable_df['cable_id'].isin(row['cables'])].reset_index(drop=True)
            if not filter_cable.empty:
                for index, row_data in filter_cable.iterrows():
                    geom = wkt.loads(row_data['path'])
                    coords = list(geom.coords)
                    overall_angle = self.angle_deg(coords[0], coords[-1])
                    side = "left" if overall_angle <= 0 else "top" if overall_angle == 30 else "right" if 0 < overall_angle < 30 else "bottom" if 30 < overall_angle < 90 else "bottom"
                    off_set_geom = UTILServices.offset_geometry(geom, distance=0.0000107*index+1, side=side)
                    # off_set_geom = UTILServices.offset_geometry_latest(geom, distance=0.0000107*index+1, side=side)
                    off_set_geom = off_set_geom.wkb_hex
                    # off_set_geom = off_set_geom.wkb_hex if off_set_geom else ''
                    if "fiber_cable" in row_data['cable_id']:
                        fiber_cable_off_set_geometry.append({"id": row_data['cable_id'],
                                                    "offset_geom": off_set_geom,
                                                    "name": row_data['name'],
                                                    "route_name": row['root_housing'],
                                                    "path":row_data['path'],
                                                    "count": len(filter_cable),
                                                    "overall_angle": overall_angle,
                                                    "side": side})
                    if "copper_cable" in row_data['cable_id']:
                        copper_cable_off_set_geometry.append({"id": row_data['cable_id'],
                                                    "offset_geom": off_set_geom,
                                                    "name": row_data['name'],
                                                    "route_name": row['root_housing'],
                                                    "path":row_data['path'],
                                                    "count": len(filter_cable),
                                                    "overall_angle": overall_angle,
                                                    "side": side})
                    if "coax_cable" in row_data['cable_id']:
                        coax_cable_off_set_geometry.append({"id": row_data['cable_id'],
                                                    "offset_geom": off_set_geom,
                                                    "name": row_data['name'],
                                                    "route_name": row['root_housing'],
                                                    "path":row_data['path'],
                                                    "count": len(filter_cable),
                                                    "overall_angle": overall_angle,
                                                    "side": side})
        fiber_offset_df = pd.DataFrame(fiber_cable_off_set_geometry)
        copper_offset_df = pd.DataFrame(copper_cable_off_set_geometry)
        coax_offset_df = pd.DataFrame(coax_cable_off_set_geometry)

        df_combined = pd.concat([fiber_offset_df, copper_offset_df, coax_offset_df], ignore_index=False)

        if not df_combined.empty: df_combined.to_csv(os.path.join(self.csv_path, "ref_data.csv"), index=False)

        fiber_offset_df = fiber_offset_df.drop(columns=self.ref_columns)
        copper_offset_df = copper_offset_df.drop(columns=self.ref_columns)
        coax_offset_df = coax_offset_df.drop(columns=self.ref_columns)

        if not fiber_offset_df.empty: fiber_offset_df.to_csv(os.path.join(self.csv_path, "fiber_cable.csv"), index=False)
        if not copper_offset_df.empty: copper_offset_df.to_csv(os.path.join(self.csv_path, "copper_cable.csv"), index=False) 
        if not coax_offset_df.empty: coax_offset_df.to_csv(os.path.join(self.csv_path, "coax_cable.csv"), index=False)
if __name__ == "__main__":
    connection_data = offset_geometry()
    connection_data.OffsetGeometry()
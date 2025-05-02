#!/usr/bin/env python

import os
import xarray as xr
import sqlite3
from glob import glob
import numpy as np
import argparse
import sys
import traceback
import geopandas as gpd
import rioxarray


def main():
    try:
        print("dem_to_db.py")
        # work_dir = os.getcwd()
        work_dir = '/package'
        inter = '/inter'
        data_dir = '/inputData'        
        parser = argparse.ArgumentParser(description='load soil data into database')
        parser.add_argument('-i', '--index', help="Specify the index of the sub virtual experience")
        parser.add_argument('-b', '--extract', help="Specify if we need to extract")
        parser.add_argument("--bnd", nargs="+", type=float, help="area bound") 
        parser.add_argument('--cropmask', help="if crop mask is used")
        parser.add_argument('--shp', help="if shapefile is used")


        args = parser.parse_args()
        i = args.index
        b = int(args.extract)
        cropmask = int(args.cropmask)
        bound = args.bnd
        print(bound[0], bound[1], bound[2], bound[3])
        print(b)
        shp = int(args.shp)

        EXPS_DIR = os.path.join(inter, 'EXPS')
        EXP_DIR = os.path.join(EXPS_DIR, 'exp_' + str(i))
        DB_MI = os.path.join(EXP_DIR, 'MasterInput.db')

        ds_mask = xr.open_dataset(glob(os.path.join(data_dir,'land', '*.nc'))[0])
        ds_mask = ds_mask.rio.write_crs("EPSG:4326", inplace=True) 

        if shp == 1:
            shapefile_path = glob(os.path.join(work_dir,'data','shapefile', '*.shp'))[0]
            gdf = gpd.read_file(shapefile_path)
            ds_mask = ds_mask.rio.write_crs("EPSG:4326")
            ds_mask = ds_mask.rio.clip(gdf.geometry, gdf.crs, drop=True)

        else: ds_mask = ds_mask.sel(lat=slice(bound[1],bound[3]), lon=slice(bound[0], bound[2]))
        if cropmask==0: ds_mask['mask'] = xr.full_like(ds_mask['mask'], fill_value=1)

        ds_mask = ds_mask.reindex({'lat': sorted(ds_mask.lat)})
        df_mask = ds_mask.to_dataframe().dropna(axis=0, how="any")
        df_mask = df_mask.reorder_levels(['lat', 'lon'])
        df_mask = df_mask.sort_index(level='lat')

        df_mask = df_mask.reset_index()
        df_mask = df_mask.astype(np.float64).round(4)
        df_mask = df_mask.drop(columns=['spatial_ref'])
        df_mask.columns = ['lat', 'lon', 'mask']
        df_mask = df_mask.set_index(['lat', 'lon'])

        ds_dem = xr.open_dataset(glob(os.path.join(data_dir,'dem', '*.nc'))[0])
        if shp == 1: 
            ds_dem = ds_dem.rio.write_crs("EPSG:4326")
            ds_dem = ds_dem.rio.clip(gdf.geometry, gdf.crs, drop=True)
        else: ds_dem = ds_dem.sel(lat=slice(bound[1],bound[3]), lon=slice(bound[0], bound[2]))
        print(ds_dem)
        ds_dem = ds_dem.reindex({'lat': sorted(ds_dem.lat)})
        ds_dem.coords['mask'] = (('lat', 'lon'), ds_mask.mask.to_masked_array(copy=True))
        print(ds_dem)
        ds_dem = ds_dem.drop_vars(["crs"], errors='ignore')
        df = ds_dem.to_dataframe().dropna(axis=0, how="any")
        df = df.reset_index()
        df.drop(['mask'], axis=1, inplace=True)
        print(df.head(5))
        df = df.rename(columns={'Band1':'dem_average'})
        df = df.astype(np.float64).round(4)

        with sqlite3.connect(DB_MI) as conn:
            df.to_sql('DemTemp', conn, if_exists='replace', index=False)

        sql_as_string = ''
        with open(os.path.join(work_dir, 'scripts', 'db', 'init_coordinates.sql')) as f:
            sql_as_string = f.read()

        with sqlite3.connect(DB_MI) as conn:
            cur = conn.cursor()
            cur.executescript(sql_as_string)
            conn.commit()
            cur.executescript("DROP TABLE DemTemp;")
            conn.commit()
    except:
        print("Unexpected error have been catched:", sys.exc_info()[0])
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
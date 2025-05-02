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



def createsoiltext(row):
    textclass = {1: "clay",
                 2: "silty clay" ,
                 3: "sandy clay",
                 4: "clay loam",
                 5: "silty clay loam",
                 6: "sandy clay loam",
                 7: "loam",
                 8: "silty loam",
                 9: "sandy loam",
                 10: "silt",
                 11: "loamy sand",
                 12: "sand"}

    return textclass[int(row["Band1"])]

def main():
    try:
        print("soil_to_db.py")
        # work_dir = os.getcwd()
        work_dir = '/package'
        inter = '/inter'
        data_dir = '/inputData'

        #--extract "$doExtract" --bnd "$bound";
        parser = argparse.ArgumentParser(description='load soil data into database')
        parser.add_argument('-i', '--index', help="Specify the index of the sub virtual experience")
        parser.add_argument('-b', '--extract', help="Specify if we need to extract")
        parser.add_argument("--bnd", nargs="+", type=float, help="aera bound") 
        parser.add_argument('--soilTexture', help="soil texture")
        parser.add_argument('--cropmask', help="if crop mask is used")
        parser.add_argument('--textclass', help="if soil texture is spatialized")
        parser.add_argument('--shp', help="if shapefile is used")
        
        args = parser.parse_args()
        i = args.index
        soilTexture = args.soilTexture
        b = int(args.extract)
        bound = args.bnd
        cropmask = int(args.cropmask)
        textclass = int(args.textclass)
        print(bound[0], bound[1], bound[2], bound[3])
        print(b)
        shp = int(args.shp)
        
        EXPS_DIR = os.path.join(inter, 'EXPS')
        EXP_DIR = os.path.join(EXPS_DIR, 'exp_' + str(i))
        DB_MI = os.path.join(EXP_DIR, 'MasterInput.db')

        ds_mask = xr.open_dataset(glob(os.path.join(data_dir, 'land', '*.nc'))[0])
        if shp == 1:
            shapefile_path = glob(os.path.join(work_dir,'data', 'shapefile', '*.shp'))[0]
            gdf = gpd.read_file(shapefile_path)
            ds_mask = ds_mask.rio.write_crs("EPSG:4326")
            ds_mask = ds_mask.rio.clip(gdf.geometry, gdf.crs, drop=True)
        else: ds_mask = ds_mask.sel(lat=slice(bound[1],bound[3]), lon=slice(bound[0], bound[2]))
        if cropmask==0: ds_mask['mask'] = xr.full_like(ds_mask['mask'], fill_value=1)
        print(ds_mask)
        print("number of crop pixels", ds_mask["mask"].to_series().dropna().count())

        ds_mask = ds_mask.reindex({'lat': sorted(ds_mask.lat)})
        df_mask = ds_mask.to_dataframe().dropna(axis=0, how="any")
        df_mask = df_mask.reorder_levels(['lat', 'lon'])
        df_mask = df_mask.sort_index(level='lat')
        df_mask = df_mask.reset_index()
        df_mask = df_mask.astype(np.float64).round(4)
        if shp == 1: df_mask = df_mask.drop(columns=['spatial_ref'])
        df_mask.columns = ['lat', 'lon', 'mask']
        df_mask = df_mask.set_index(['lat', 'lon'])
        print(df_mask.head(10))
        SOIL_DIR = os.path.join(data_dir, 'soil')
        ncs = glob(os.path.join(SOIL_DIR, '*.nc'))
        ds = xr.open_mfdataset(ncs, cache=False)
        if shp == 1:
            ds = ds.rio.write_crs("EPSG:4326")
            ds = ds.rio.write_crs("EPSG:4326")
            ds = ds.rio.clip(gdf.geometry, gdf.crs, drop=True)

        else: ds = ds.sel(lat=slice(bound[1],bound[3]), lon=slice(bound[0], bound[2]))
        print(ds)
        ds = ds.reindex({'lat': sorted(ds.lat)})
        ds.coords['mask'] = (('lat', 'lon'), ds_mask.mask.to_masked_array(copy=True))
        # ds = ds.where(ds.mask == 1)
        df = ds.to_dataframe().dropna(axis=0, how="any")
        print(df.head(5))
        print(len(df))
        df = df.reset_index()
        # lon, lat columns at 4 digits
        df["lon"] = df["lon"].round(4)
        df["lat"] = df["lat"].round(4)
        # create IdSoil column as a concatenation of lat and lon separated by "_"
        df["IdSoil"] = df["lat"].astype(str) + "_" + df["lon"].astype(str)
        # change name of column silt, sand, clay to Silt, Sand, Clay
        #df = df.rename(columns={"silt": "Silt", "sand": "Sand", "clay": "Clay"})
        # round values of columns SoilTotalDepth, SoilRDepth, Wwp, Wfc, bd, OrganicNStock, pH, OrganicC, cf, extp, totp, Sand, Clay, Silt with 1 digit
        df[["SoilTotalDepth", "SoilRDepth", "Wwp", "Wfc", "bd", "OrganicNStock", "pH", "OrganicC", "cf", "extp", "totp", "sand", "clay", "silt"]] = df[["SoilTotalDepth", "SoilRDepth", "Wwp", "Wfc", "bd", "OrganicNStock", "pH", "OrganicC", "cf", "extp", "totp", "sand", "clay", "silt"]].astype(np.float64).round(3)
        # remove columns mask, lat, lon, Band1, mask
        df["totp"] = -99
      
        if textclass == 0:
            # replace SoilTextureType by soilTexture
            df["SoilTextureType"] = soilTexture
        else:
            # create SoilTextureType column
            df["SoilTextureType"] = df.apply(createsoiltext, axis=1)
        
        df = df.drop(columns=["mask", "lat", "lon", "Band1"])
        # SoilOption is always simple
        df["SoilOption"] = "simple"
        # Slope is always null
        df["Slope"] = None
        # RunoffType is always 1
        df["RunoffType"] = 1
        # albedo is always 0.3
        df["albedo"] = 0.3
        print(df.head(5))
        with sqlite3.connect(DB_MI) as conn:
            df.to_sql('Soil', conn, if_exists='replace', index=False)
    except:
        print("Unexpected error have been catched:", sys.exc_info()[0])
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python

import os
import xarray as xr
from glob import glob
import sys
import traceback
from joblib import Parallel, delayed
import argparse
import numpy as np
import geopandas as gpd
import rioxarray
import dask

def main():
    inter = '/inter'
    data_dir = '/inputData'
    work_dir = '/package'
    parser = argparse.ArgumentParser(description='load soil data into database')
    parser.add_argument("--bnd", nargs="+", type=float, help="area bound")
    parser.add_argument("--models", nargs="+", type=str, help="Specify the models") 
    parser.add_argument("--shp", help="Specify the shapefile")
    args = parser.parse_args()
    bound = args.bnd
    models = args.models
    shp = int(args.shp)
    print("domain is ", bound[0], bound[1], bound[2], bound[3])
    # Load reference grid (ensures all expected pixels are there)
    ref_ds = xr.open_dataset(glob(os.path.join(data_dir, 'meteo', 'Rainfall', '*.nc'))[0])
    # Clip reference dataset to the bounding box
    if shp == 0:
        lon_min, lon_max = bound[0], bound[2]  # Adjust based on your bounding box
        lat_min, lat_max = bound[1], bound[3]
        ref_ds_clipped = ref_ds.sel(lon=slice(lon_min, lon_max), lat=slice(lat_min, lat_max))
    else:
        shapefile_path = glob(os.path.join(work_dir,'data','shapefile', '*.shp'))[0]
        gdf = gpd.read_file(shapefile_path)
        ref_ds = ref_ds.rio.write_crs("EPSG:4326")
        ref_ds_clipped = ref_ds.rio.clip(gdf.geometry, gdf.crs, drop=True)

    ref_ds_clipped['lat'] = np.round(ref_ds_clipped['lat'], 4)
    ref_ds_clipped['lon'] = np.round(ref_ds_clipped['lon'], 4)
    
    EXPS_DIR = os.path.join(inter, 'EXPS')
    
    def merge(m):
        ncs = glob(os.path.join(EXPS_DIR,'exp_*', m+'_yearly_*.nc'))
        v = list(set(["_".join(os.path.basename(u).split("_")[2:-1]) for u in ncs]))
        print(v)
        if len(ncs) == 0:
            return
        for n in v:
            subdomain_files = glob(os.path.join(EXPS_DIR,'exp_*', m+'_yearly_'+n+'_*.nc'))
            if len(subdomain_files)==0: return
            #Load all subdomain NetCDF files
            subdomain_datasets = [xr.open_dataset(f) for f in subdomain_files]
            # Merge subdomain datasets while preserving spatial structure
            merged_ds = xr.merge(subdomain_datasets)
            # Reindex merged dataset to reference grid
            final_ds = merged_ds.reindex(lat=ref_ds_clipped.lat,lon=ref_ds_clipped.lon, fill_value=np.nan)
            final_ds['lat'] = final_ds['lat'].astype('float32')
            final_ds['lon'] = final_ds['lon'].astype('float32')  
            for var in final_ds.data_vars:
                if np.issubdtype(final_ds[var].dtype, np.floating):
                    final_ds[var] = final_ds[var].astype("float32")          
            # Save merged dataset to NetCDF file
            outdir = os.path.join(inter,"outputs")
            os.makedirs(outdir, exist_ok=True)
            output_file = os.path.join(outdir, m+'_yearly_'+n+'.nc')
            final_ds.to_netcdf(output_file, encoding={var: {"_FillValue": np.nan} for var in final_ds.data_vars})
            print(f"Merged dataset saved as {output_file}")
    try:
        Parallel(n_jobs=-1)(
            delayed(merge)(f) for f in models)
    except:
        print("Unexpected error have been catched:", sys.exc_info()[0])
        traceback.print_exc()
        sys.exit(1)    
        
    print("DONE!")

if __name__ == "__main__":
    main()        


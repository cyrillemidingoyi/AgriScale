#!/usr/bin/env python

import os
import xarray as xr
import sqlite3
from glob import glob
import numpy as np
import argparse
import sys
import pandas as pd
import traceback
#import dask.dataframe as dd
#from dask import delayed
from time import time
from joblib import delayed, Parallel
import re
import tracemalloc
import dask

dask.config.set({"array.slicing.split_large_chunks": False}) 
pd.set_option('display.max_columns', None)


METEO_COLS = ['idPoint', 'w_date', 'year', 'DOY', 'Nmonth', 'NdayM', 'srad', 'tmax', 'tmin', 'tmoy', 'rain',
              'wind', 'rhum', 'Etppm', 'Tdewmin', 'Tdewmax', 'Surfpress']


def format_df_meteo(df):

    df['year'] = df['time'].dt.year
    df['Nmonth'] = df['time'].dt.month
    df['NdayM'] = df['time'].dt.day
    df['DOY'] = df['time'].dt.dayofyear
    df['w_date'] = df['time'].dt.strftime('%Y-%m-%d')
    df['idPoint'] = df['lat'].round(4).astype(str) + '_' + df['lon'].round(4).astype(str)
    df['rhum'] = None
    df['Etppm'] = None

    df = df[METEO_COLS]
    return df



def main():
    #try:
    print("meteo_to_db.py")
    work_dir = '/package'
    inter = '/inter'
    data_dir = '/inputData'
    parser = argparse.ArgumentParser(
            description='load soil data into database')
    parser.add_argument(
            '-i', '--index', help="Specify the index of the sub virtual experience")
    parser.add_argument('-b', '--extract', help="Specify if we need to extract")
    parser.add_argument("--bnd", nargs="+", type=float, help="area bound") 
    parser.add_argument('-m', '--max', help="Specify the max year")
    parser.add_argument('-n', '--min', help="Specify the min year")



    args = parser.parse_args()
    i = args.index
    b = int(args.extract)
    mini = int(args.min)
    maxi = int(args.max)

    n_jobs = int(os.environ.get("SLURM_CPUS_PER_TASK"))
    bound = args.bnd
    print(bound[0], bound[1], bound[2], bound[3])
    print(b)

    EXPS_DIR = os.path.join(inter, 'EXPS')
    EXP_DIR = os.path.join(EXPS_DIR, 'exp_' + str(i))
    DB_MI = os.path.join(EXP_DIR, 'MasterInput.db')

    ds_mask = xr.open_dataset(glob(os.path.join(data_dir,'land', '*.nc'))[0])
    if b==1: ds_mask = ds_mask.sel(lat=slice(bound[1],bound[3]), lon=slice(bound[0], bound[2]))

    ds_mask = ds_mask.reindex({'lat': sorted(ds_mask.lat)})
    df_mask_full = ds_mask.to_dataframe()

    df_mask_full = df_mask_full.reorder_levels(['lat', 'lon'])
    df_mask_full = df_mask_full.sort_index(level='lat')

    df_mask = df_mask_full.dropna(axis=0, how="any")
    df_mask = df_mask.reset_index()

    

    SLURM_ARRAY_TASK_COUNT = int(os.environ.get("SLURM_ARRAY_TASK_COUNT"))
    print(len(df_mask), SLURM_ARRAY_TASK_COUNT, "bbbbbbb")
    i = int(i)
    k, m = divmod(len(df_mask), SLURM_ARRAY_TASK_COUNT)
    STEP_START = i * k + min(i, m)
    STEP_END = (i + 1) * k + min(i + 1, m)

    print("STEP_START : " + str(STEP_START))
    print("STEP_END : " + str(STEP_END))
    print("END - START : " + str(STEP_END - STEP_START))

       
    df_mask.loc[~df_mask.index.isin(range(STEP_START, STEP_END)), 'mask'] = None

    df_mask = df_mask.dropna(axis=0, how="any")
    df_mask = df_mask.set_index(['lat', 'lon'])

    da_mask_full = df_mask_full.where(
            df_mask_full.isin(df_mask)).to_xarray()
    ds_mask = ds_mask.where(da_mask_full.mask == 1)
    
    print(ds_mask)

    METEO_DIR = os.path.join(data_dir, 'meteo')
    
    parameters = ["2m-dewpoint-temperature-max", "2m-dewpoint-temperature-min",\
                     "Rainfall", "Solar-Radiation-Flux", "surface-pressure", "Temperature-Air-2m-Max-24h", \
                     "Temperature-Air-2m-Min-24h", "Wind-Speed-10m-Mean" ] 
    
    include_years = [str(year) for year in range(mini, maxi+1)]
    include_pattern = re.compile('|'.join(include_years))


    years = [str(year) for year in range(1991,2021)]

    # Calculate the chunk size for each process
    print(f"number of processes is {n_jobs}")

    def apply_order(parameter, files_batch):
        print(f"Processing parameter: {parameter}, files: {len(files_batch)}")

        with dask.config.set(**{'array.slicing.split_large_chunks': True}):

            ds = xr.open_mfdataset(files_batch, combine="by_coords", chunks={'time': 1}) #parallel=True, chunks={'time': 1}
            if b==1: ds = ds.sel(lat=slice(bound[1],bound[3]), lon=slice(bound[0], bound[2]))
            if "crs" in ds: ds = ds.drop_vars(["crs"])
            ds = ds.reindex({'lat': sorted(ds.lat)})
            ds = ds.assign_coords(mask=(('lat', 'lon'), ds_mask.mask.values))
            new_ds = ds.where(ds.mask == 1, drop=True)
            return new_ds

    def process_parameters(parameters):
        all_results = []
        years_per_batch=min(5, maxi-mini+1)
        for parameter in parameters:
            # Locate all files for the parameter
            ncpath = os.path.join(METEO_DIR, parameter)
            files = [
                os.path.join(ncpath, filename) 
                for filename in os.listdir(ncpath) 
                if include_pattern.search(filename)
            ]
        
            print(f"Found {len(files)} files for parameter: {parameter}")
        
            # Process years in batches for this parameter
            parameter_result = process_years_in_batches(parameter, files, years_per_batch)
            all_results.append(parameter_result)
    
        # Combine all parameters into a single dataset
        return xr.merge(all_results).compute()

    def process_years_in_batches(parameter, files, years_per_batch):
        # Process files in batches of years_per_batch
        batches = [
            files[i:i + years_per_batch]
            for i in range(0, len(files), years_per_batch)
        ]
    
        # Process batches in parallel
        results = Parallel(n_jobs=n_jobs, prefer="processes")(
        delayed(apply_order)(parameter, batch) for batch in batches
        )

        return xr.concat(results, dim="time")

    # merge the list of datasets in a single dataset
    ds = process_parameters(parameters)
    
    df = ds.to_dataframe().dropna(axis=0, how="any")
    df = df.reset_index()
    df.drop(['mask'], axis=1, inplace=True)
    df['time'] = pd.to_datetime(df.time, format='%Y-%m-%d')
    df = df.rename(columns={"pr":"rain"})
    df['tmoy'] = df[['tmin','tmax']].mean(axis=1)
    df.loc[:,"lat": "lon"] = df.loc[:,"lat": "lon"].apply(lambda x: np.float64(x).round(3))
    df[['srad', 'tmax', 'tmin', 'tmoy', 'rain','wind', 'Tdewmin', 'Tdewmax', 'Surfpress']] = df[['srad', 'tmax', 'tmin', 'tmoy', 'rain','wind', 'Tdewmin', 'Tdewmax', 'Surfpress']].astype(np.float64).round(1)
    df = format_df_meteo(df)
    print(df.head(20))
    with sqlite3.connect(DB_MI) as conn:
        cur = conn.cursor()
        cur.executescript("DROP TABLE RAclimateD;")
        conn.commit()
        df.to_sql('RAclimateD', conn, if_exists='replace', index=False)


if __name__ == "__main__":
    main()

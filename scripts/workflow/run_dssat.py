import sqlite3
import pandas as pd
import os
import shutil
import subprocess
import argparse
from pathlib import Path
import zipfile
from joblib import Parallel, delayed
import multiprocessing
from glob import glob
import numpy as np
import time
from modfilegen.Converter.DssatConverter import dssatconverter
from modfilegen import GlobalVariables
import concurrent.futures


import traceback
import sys
import re
    

def main():


    work_dir = '/package' 
    inter = '/inter'
    parser = argparse.ArgumentParser(description='load etp into database')
    parser.add_argument('-i', '--index', help="Specify the index of the sub virtual experience")
    parser.add_argument('--ncpus', help="number of cpus by task")
    args = parser.parse_args()
    i = args.index
    size = int(args.ncpus)
    EXPS_DIR = os.path.join(inter, 'EXPS')
    EXP_DIR = os.path.join(EXPS_DIR, 'exp_' + str(i))

    DB_MI = os.path.join(EXP_DIR, 'MasterInput.db')
    DB_MD = os.path.join(EXP_DIR, "ModelsDictionaryArise.db")

    directoryPath = os.path.join(EXP_DIR, "output")
    if not os.path.exists(directoryPath):
        Path(directoryPath).mkdir(parents=True, exist_ok=True)

    GlobalVariables["dbModelsDictionary" ] = DB_MD     
    GlobalVariables["dbMasterInput" ] = DB_MI
    GlobalVariables["directorypath"] = directoryPath 
    GlobalVariables["pltfolder"] = os.path.join(work_dir, "data","cultivars","dssat") # path of cultivars
    GlobalVariables["nthreads"] = size
    GlobalVariables["dt"] = 0

    dssatconverter.main()
        
    # read in directorypath all the files end with "dssat.csv" and concatenate them
    files = glob(os.path.join(directoryPath, '*_dssat.csv'))
    if not files: return
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    print(f"Number of effective simulations in this subdomain: {len(df)}")
    #shutil.rmtree(directoryPath)

    v = list(set(["_".join(u.split("_")[3:]) for u in df["Idsim"]]))
    
    df["Planting"]= df["Planting"]%1000
    df["Emergence"]= df["Emergence"]%1000
    df["Ant"]= df["Ant"]%1000
    df["Mat"]= df["Mat"]%1000
    df["Yield"] = df["Yield"].div(1000)
    df["Biom_ma"] = df["Biom_ma"].div(1000)

    df["Planting"] =  df["Planting"].astype(float).astype(int) 
    df["Ant"] = df["Ant"].astype(float).astype(int) 
    df["Mat"] = df["Mat"].astype(float).astype(int)
    df["Emergence"] = df["Emergence"].astype(float).astype(int)

    df.loc[df["Emergence"]>366, "Emergence"] = None  
    df.loc[df["Ant"]>366, "Ant"] = None
    df.loc[df["Mat"]>366, "Mat"] = None
    df.loc[df["Yield"]<0, "Yield"] = None
    df.loc[df["Biom_ma"]<0, "Biom_ma"] = None

    def create_netcdf(id_, df):
        df_2 = df[df["Idsim"].str.endswith(id_)]
        dsfin = df_2[["time","lat","lon","Planting","Emergence","Ant","Mat","Biom_ma","Yield","GNumber","MaxLai","Nleac","SoilN","CroN_ma","CumE","Transp"]]
        dsfin = dsfin.reset_index().set_index(
                        ['time', 'lat', 'lon']).to_xarray()
        o = os.path.join(EXP_DIR, 'dssat' + '_yearly_' + id_ + "_" + str(i) + '.nc')
        dsfin.to_netcdf(o)
    
    njobs = len(v) if len(v) < size else size
    Parallel(n_jobs=njobs)(delayed(create_netcdf)(f, df) for f in v)
    df.reset_index()
    os.remove(DB_MI)
    print("DONE!")
    """df = df[["Model","Idsim","Texte","Planting","Emergence","Ant","Mat","Biom_ma","Yield","GNumber","MaxLai","Nleac","SoilN","CroN_ma","CumE","Transp"]]
        
    with sqlite3.connect(DB_MI, timeout=15) as c:
        cur = c.cursor()
        cur.executescript("DELETE FROM SummaryOutput WHERE Model='Dssat';")
        c.commit()
        df.to_sql('SummaryOutput', c, if_exists='append', index=False)
        c.commit()"""
        
    
if __name__ == "__main__":

    main()

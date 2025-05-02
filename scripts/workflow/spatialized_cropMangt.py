#!/usr/bin/env python

import os
import sqlite3
import argparse
import sys
import traceback
import pandas as pd
import xarray as xr
from glob import glob
import json

#python ${DATAMILL_WORK}/scripts/functions/spatialized_cropMangt.py --index $i --svariety "$s_variety" --sfert "$s_fert" --sirr "$s_irr" --ssowing "$s_sowing" --sdensity "$s_density" --variety_dict "$variety_dict" --sowingDates "${SW[@]}";

def main():
    try:
        print("spatialized_cropMangt.py")
        work_dir = '/package'
        inter = '/inter'
        parser = argparse.ArgumentParser(description='load')
        parser.add_argument('-i', '--index', help="Specify the index of the sub virtual experience")
        parser.add_argument(
        "--variety_dict", 
        type=str, 
        required=True, 
        help="JSON string representing a dictionary of varieties"
        )
        parser.add_argument("--svariety", help="Specify the variety option")
        parser.add_argument("--sfert", help="Specify the fertilization option")
        parser.add_argument("--sirr", help="Specify the irrigation option")
        parser.add_argument("--ssowing", help="Specify the sowing option")
        parser.add_argument("--sdensity", help="Specify the density option")
        parser.add_argument('-d', '--sowingDates',type=int, nargs="+", help="Specify the list of sowing dates")
        parser.add_argument("--bnd", nargs="+", type=float, help="aera bound")
        parser.add_argument('--sowingoption', help="Specify the sowing option")
        parser.add_argument("--cropvariety", nargs="*", help="Crop variety")
        parser.add_argument("--ferti", nargs="*", help="fertilizer option") 

        scratch = 0
        args = parser.parse_args()
        
            # Convert the JSON string to a Python dictionary
        try:
            variety_dict = json.loads(args.variety_dict)
        except json.JSONDecodeError:
            print("Error: Invalid JSON format in --variety_dict")
            return
        
        # Use the dictionary
        print("Parsed variety dictionary:", variety_dict)
        for key, value in variety_dict.items():
            print(f"{key}: {value}")
            print(f"{type(key)}: {type(value)}")
        
        i = int(args.index)
        s_variety = int(args.svariety)
        s_fert = int(args.sfert)
        s_irrig = int(args.sirr)
        s_sowing = int(args.ssowing)
        s_density = int(args.sdensity)

        sd = args.sowingoption
        bound = args.bnd
        print(bound[0], bound[1], bound[2], bound[3])  
        
        variety = args.cropvariety
        fertioption = args.ferti
        
        nc_variety_file = None
        nc_fert_file = None
        nc_irrig_file = None
        nc_sowing_file = None
        nc_density_file = None
        
        sw = args.sowingDates
        print(sw)

        EXPS_DIR = os.path.join(inter, 'EXPS')
        EXP_DIR = os.path.join(EXPS_DIR, 'exp_' + str(i))
        DB_MI = os.path.join(EXP_DIR, 'MasterInput.db')

	    # Reset CropManagement table
        dbori = os.path.join(work_dir, 'db', 'MasterInput.db')

        conn_sq1 = sqlite3.connect(dbori)

        df_mangt= pd.read_sql('SELECT * FROM CropManagement', conn_sq1) 
        conn_sq1.close() 
        
        # Possibility to build the cropmanagement table by scratch:
        if scratch == 1: #TODO
            df_mangt = pd.DataFrame(columns=['idMangt', 'Idcultivar', 'sowingdate', 'sdens', 'OFertiPolicyCode', 'InoFertiPolicyCode', "IrrigationPolicyCode", "SoilTillPolicyCode"])
        
        
        print(df_mangt.head(10))
        spatialized = False
        
        if s_variety == 1:
            # Read the spatialized variety file
            nc_variety_file = glob(os.path.join(work_dir, 'data', 'gridded_data', 'variety', '*.nc'))[0]
        if s_fert == 1:
            # Read the spatialized fertilization file
            nc_fert_file = glob(os.path.join(work_dir, 'data', 'gridded_data', 'fert', '*.nc'))[0]
        if s_irrig == 1:
            # Read the spatialized irrigation file
            nc_irrig_file = glob(os.path.join(work_dir, 'data', 'gridded_data', 'irrig', '*.nc'))[0]
        if s_sowing == 1:
            # Read the spatialized sowing file
            nc_sowing_file = glob(os.path.join(work_dir, 'data', 'gridded_data', 'sowing', '*.nc'))[0]
        if s_density == 1:
            # Read the spatialized density file
            nc_density_file = glob(os.path.join(work_dir, 'data', 'gridded_data', 'density', '*.nc'))[0]
        
        nc_files = [nc_variety_file, nc_fert_file, nc_irrig_file, nc_sowing_file, nc_density_file]
        spatialized_files = []
        if nc_files.count(None) == len(nc_files):
            print("No spatialized file selected")
        else:
            spatialized = True
            print("Selected spatialized files:")
            for nc_file in nc_files:
                if nc_file is not None:
                    print(f"- {nc_file}")
                    spatialized_files.append(nc_file)
        
        # Read the spatialized files
        
        if spatialized_files :
            nc_spacialized = xr.open_mfdataset(spatialized_files)
            print(nc_spacialized)
            
            nc_spacialized = nc_spacialized.sel(lat=slice(bound[1],bound[3]), lon=slice(bound[0], bound[2]))
        
            # Convert the spatialized data to a pandas dataframe
            df_spatialized = nc_spacialized.to_dataframe().dropna(axis=0, how="any")
            print(df_spatialized.head(10))
        
            if s_variety == 1:
                #replace the variety values with the values from the variety dictionary: but convert first df_spatialized['variety'] to string
                df_spatialized['variety'] = df_spatialized['variety'].astype(str)
                df_spatialized['variety'] = df_spatialized['variety'].map(variety_dict)
                # replace colum name "variety" by "Idcultivar"
                df_spatialized = df_spatialized.rename(columns={"variety":"Idcultivar"})
                # reset the index
                
                # create a new column "id"  based on lat and lon columns 4 digits after the decimal point
                
            if s_sowing == 1:
                df_spatialized = df_spatialized.rename(columns={"sowing_date": "sowingdate"})
                df_mangt.drop("sowingdate", axis=1, inplace=True)

            if s_density == 1:
                df_mangt.drop("sdens", axis=1, inplace=True)

            if s_fert == 1:
                df_mangt.drop("InoFertiPolicyCode", axis=1, inplace=True)
            
            df_spatialized = df_spatialized.reset_index()
            df_spatialized["idPoint"] = df_spatialized["lat"].round(4).astype(str) + '_' + df_spatialized["lon"].round(4).astype(str)
        
            if s_variety == 1:
                # keep only the Idcultivar conatined in the variety dictionary
                df_mangt = df_mangt[df_mangt['Idcultivar'].isin(variety_dict.values())]
                # merge the spatialized data with the CropManagement table based on the Idcultivar column
                df_mangt = pd.merge(df_mangt, df_spatialized, on="Idcultivar", how="inner")
            else:
                # cross join the CropManagement table with the spatialized data
                df_mangt["key"] = 0
                df_spatialized["key"] = 0
                df_mangt = df_mangt.merge(df_spatialized, on="key")
                df_mangt.drop("key", axis=1, inplace=True)
                
            
        
            print(df_mangt)
        
           
            # convert sowing_date as int
            df_mangt["sowingdate"] = df_mangt["sowingdate"].astype(int)
            
        
            # replace idMangt column by the concatenation of id and idMangt columns if len(spatialized_files) != 5
            if len(spatialized_files) != 5:
                df_mangt["oldid"] = df_mangt["idMangt"]
                df_mangt["idMangt"] = df_mangt['idPoint'] + "_" + df_mangt["idMangt"]

            
        if int(sd) == 3:
            # use sw the list of sowing dates
            df_mangt.drop("sowingdate", axis=1, inplace=True)
            # Make a cartesian product between the CropManagement table and the list of sowing dates
            df_sowing = pd.DataFrame()
            df_sowing["sowingdate"] = sw
            df_sowing["key"] = 0
            df_mangt["key"] = 0
            df_mangt = df_mangt.merge(df_sowing, on="key")
            df_mangt.drop("key", axis=1, inplace=True)
            df_mangt["sowingdate"] = df_mangt["sowingdate"].astype(int)
            # Change the values of the column idMangt with the values of idMangt + "_" + sowingdate
            df_mangt["idMangt"] = df_mangt["idMangt"] + "_" + df_mangt["sowingdate"].astype(str)
            if spatialized: df_mangt["oldid"] = df_mangt["oldid"] + "_" + df_mangt["sowingdate"].astype(str)
            
        if s_variety == 0:
            # No spatialized variety file. select in cropmanagement the variety in the list cropvariety
            print("variety", variety)
            if len(variety) != 0:
                df_mangt = df_mangt[df_mangt['Idcultivar'].isin(variety)]
        
        if s_fert == 0:
            # No spatialized fertilization file. select in cropmanagement the fertilization in the list ferti
            if len(fertioption) != 0:
                df_mangt = df_mangt[df_mangt['InoFertiPolicyCode'].isin(fertioption)]
               
        with sqlite3.connect(DB_MI) as conn:
            print("test cropmanagement", df_mangt.head(10))
            cur = conn.cursor()
            df_mangt.to_sql("CropManagement", conn, if_exists='replace', index=False)                
            conn.commit()    
    except:
        print("Unexpected error have been catched:", sys.exc_info()[0])
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

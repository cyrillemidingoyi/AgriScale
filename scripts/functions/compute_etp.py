from mpi4py import MPI
import sqlite3
import calculate_etp
from joblib import Parallel, delayed
import argparse
import sys
import traceback
import os
import pandas as pd


comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

print("number of processes", size)



def main():
    try:
        print("compute ETP")
        work_dir = '/package' 
        inter = '/inter'
        parser = argparse.ArgumentParser(description='load etp into database')
        parser.add_argument('-i', '--index', help="Specify the index of the sub virtual experience")
        args = parser.parse_args()
        i = args.index
        EXPS_DIR = os.path.join(inter, 'EXPS')
        EXP_DIR = os.path.join(EXPS_DIR, 'exp_' + str(i))
        DB_MI = os.path.join(EXP_DIR, 'MasterInput.db')
        
        with sqlite3.connect(DB_MI, timeout=15) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM RAclimateD")
            nrows = cur.fetchone()[0]
            #nrows = df_clim.shape[0]
            step = nrows//size
            print("the number of steps is:", step)
            start_idx = rank * step
            end_idx = (rank + 1) * step if rank < size - 1 else nrows
            print(rank, start_idx+1, end_idx)

            if rank == size - 1:
                step = nrows - start_idx
            
            # select the rows for this process based on the rank
            df_clim = pd.read_sql(f'select * from RAclimateD LIMIT {start_idx}, {step}', conn)
            print(df_clim.shape)

            #df_clim = df_clim.iloc[start_idx:end_idx]
            
            if 'altitude' in df_clim.columns:
                df_clim.drop('altitude', axis=1, inplace=True)
            if 'latitude' in df_clim.columns:
                df_clim.drop('latitude', axis=1, inplace=True)
            df_coord = pd.read_sql('select * from Coordinates', conn)
            df = df_clim.merge(df_coord[['idPoint', 'latitudeDD', 'altitude']], how='inner', on='idPoint')
            print(df.shape)
            df = df.rename(columns={"latitudeDD":"latitude"})
            print(df.head(10))

            df["Etppm"] = df.apply(lambda x: calculate_etp.ET0pm_Tdew(x["latitude"], x["altitude"], x["DOY"], x["tmin"], x["tmax"], x["tmoy"], x["Tdewmin"], x["Tdewmax"], x["wind"], x["srad"]), axis=1)
            print(df[["Etppm"]].head(10))
            
            # save the dataframe to a csv file for each process
            repi = os.path.join(EXP_DIR, f"etp_{rank}.csv")
            print(repi, rank)
            df.to_csv(repi, index=False)
                
            # Wait for all processes to finish
            comm.barrier()
    
            # Merge all the dataframes from all processes into one dataframe    
            #df_all = comm.gather(df, root=0)
            
            if rank == 0:
                df_all = pd.DataFrame()
                # Read all the csv files into a list of dataframes
                df_all = pd.concat([pd.read_csv(os.path.join(EXP_DIR, f"etp_{i}.csv")) for i in range(size)], ignore_index=True)                
                print(df_all.shape)
                for i in range(size):
                    os.remove(os.path.join(EXP_DIR, f"etp_{i}.csv")) 
                cur.executescript("DELETE FROM RAclimateD")
                df_all.to_sql('RAclimateD', conn, if_exists='replace', index=False) 
                conn.commit()        
                print("ETP DONE")
    except:
        print("Unexpected error have been catched:", sys.exc_info()[0])
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
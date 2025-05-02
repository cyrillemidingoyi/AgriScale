#!/usr/bin/env python

import os
import argparse
import sys
import traceback
import subprocess
import sqlite3
import pandas as pd


def main():
    try:
        print("reset_cropMangt.py")
        # work_dir = os.getcwd()
        work_dir = '/package'
        inter = '/inter'
        parser = argparse.ArgumentParser(description='Initialize virtual experience directories')
        parser.add_argument('-i', '--index', help="Specify the index of the sub virtual experience")
        args = parser.parse_args()
        i = args.index


        dbori = os.path.join(work_dir, 'db', 'MasterInput.db')
        EXPS_DIR = os.path.join(inter, 'EXPS')
        EXP_DIR = os.path.join(EXPS_DIR, 'exp_' + str(i))
        DB_MI = os.path.join(EXP_DIR, 'MasterInput.db')  

        conn_sq1 = sqlite3.connect(dbori)
        conn_sq2 = sqlite3.connect(DB_MI)

        try:
            df_mangt= pd.read_sql('SELECT * FROM CropManagement', conn_sq1)
            df_mangt.to_sql("CropManagement", conn_sq2, if_exists='replace', index=False)
            conn_sq2.commit()
        except sqlite3.Error as e:
            print(f"Erreur : {e}")
            conn_sq2.rollback()  # En cas d'erreur, annulez la transaction

    except:
        print("Unexpected error have been catched:", sys.exc_info()[0])
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

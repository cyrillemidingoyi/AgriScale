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
        print("reset_celsiusdb.py")
        work_dir = '/package'
        inter = '/inter'
        parser = argparse.ArgumentParser(description='Initialize virtual experience directories')
        parser.add_argument('-i', '--index', help="Specify the index of the sub virtual experience")
        args = parser.parse_args()
        i = args.index

        dbfrom = os.path.join(work_dir, 'db', 'CelsiusV3nov17_dataArise.db')
        EXPS_DIR = os.path.join(inter, 'EXPS')
        EXP_DIR = os.path.join(EXPS_DIR, 'exp_' + str(i))
        dbto  = os.path.join(EXP_DIR, 'CelsiusV3nov17_dataArise.db')  
        res = subprocess.check_call(['cp',  dbfrom, dbto])

    except:
        print("Unexpected error have been catched:", sys.exc_info()[0])
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

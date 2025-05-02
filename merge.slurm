#!/bin/bash

#SBATCH -p sen2agri
#SBATCH -A crpmdl
#SBATCH --job-name=DATAMILL
#SBATCH --output="out/merge_%a.out"
#SBATCH --error="err/merge_%a.err"
#SBATCH --nodes=1
#SBATCH --ntasks=1    # Each task in the array is a separate job
#SBATCH --cpus-per-task=4  # Each task uses 4 CPU cores


export SIMUL_DIR=$SLURM_SUBMIT_DIR

echo "SIMUL_DIR =  ${SIMUL_DIR} "


cd ${SIMUL_DIR}



date


singularity exec --no-home -B  /tank/crop_modelling/lima/CropModellingArise:/package -B /tank/crop_modelling/lima/tmp:$TMPDIR  -B /tank/crop_modelling/lima/result:/inter   datamill.sif python3 /package/scripts/netcdf/merge_yearly.py


date

# sbatch --array=0-0 merge.slurm

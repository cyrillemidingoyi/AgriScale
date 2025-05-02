#!/bin/bash

#SBATCH -p sen2agri
#SBATCH -A crpmdl
#SBATCH --job-name=AGRISCALE
#SBATCH --output="out/agriscale_%a.out"
#SBATCH --error="err/agriscale_%a.err"  # Fixed the error output file name
#SBATCH --nodes=1
#SBATCH --ntasks=1    # Each task in the array is a separate job
#SBATCH --cpus-per-task=4  # Each task uses 4 CPU cores


export SIMUL_DIR=$SLURM_SUBMIT_DIR

echo "SIMUL_DIR =  ${SIMUL_DIR} "


cd ${SIMUL_DIR}

export ncpus=$SLURM_CPUS_PER_TASK
export nchunks=$SLURM_ARRAY_TASK_COUNT
export INDEXES=$SLURM_ARRAY_TASK_ID

echo "number of chunks =  ${nchunks} "
echo "number of tasks =  ${SLURM_ARRAY_TASK_COUNT} "
echo "number of cpus =  ${ncpus} "
echo "INDEXES : $INDEXES"

date

singularity exec --no-home -B /tank/crop_modelling/lima/AgriScale:/package -B /tank/crop_modelling/lima/AgriScale/result_Agriscale:/inter -B /tank/crop_modelling/lima/tmp:$TMPDIR -B  /tank/crop_modelling/lima/merged_data:/inputData datamill.sif /package/scripts/main.sh $INDEXES $ncpus $nchunks

date


# Example on how to submit this jobarray to cloud:
# sbatch --array=0-22 datamill.slurm


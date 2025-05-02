#!/bin/bash
##SBATCH -p agap_short
##SBATCH -p agap_normal
#SBATCH -p agap_long
##SBATCH -p agap_bigmem
#SBATCH -a agap
#SBATCH --job-name=MERGE
#SBATCH --output="out/etp_%a.out"
#SBATCH --error="err/etp_%a.err"
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
##SBATCH --ntasks-per-node=6
#SBATCH --mem=120G
##SBATCH --mem=350G
##SBATCH --mail-type=begin        
##SBATCH --mail-type=end          
##SBATCH --nodelist=smp03



export SIMUL_DIR=$SLURM_SUBMIT_DIR

cd ${SIMUL_DIR}

echo "SIMUL_DIR =  ${SIMUL_DIR} "


module load singularity/3.5 squashfs/4.3 libarchive/3.3.2



date


singularity exec --no-home -B  /lustre/$USER/CropModellingArise:/package -B /storage/replicated/cirad/projects/AIDA/LIMA/merged_data:/inputData -B /storage/replicated/cirad/projects/AIDA/$USER/Atelier_LIMA/work_dir_ao:/output  datamill.sif python3 /package/scripts/functions/etp.py


date

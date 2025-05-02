#!/usr/bin/env bash

set -e

data='/inputData'
DATAMILL_WORK='/package'

export INDEXES=$1
export ncpus=$2
export nchunks=$3



# Source the shared function file
source "${DATAMILL_WORK}/scripts/config_parser.sh"



# Extract all values from the INI file

s_variety=$(get_config_value "s_variety")
echo "🔹 Spatialized Variety: $S_VARIETY"

s_fert=$(get_config_value "s_fert")
s_irr=$(get_config_value "s_irr")
s_sowing=$(get_config_value "s_sowing")
s_density=$(get_config_value "s_density")

variety_dict=$(get_dict_value "variety_dict")
variety=($(get_list_value "variety"))
models=($(get_list_value "models"))
SD=$(get_config_value "SD")
initcond=$(get_config_value "initcond")
soilTextureType=$(get_config_value "soilTextureType")
textclass=$(get_config_value "textclass")
simoption=($(get_list_value "simoption"))
fertioption=($(get_list_value "fertioption"))
startd=$(get_config_value "startd")
endd=$(get_config_value "endd")
doExtract=$(get_config_value "doExtract")
export bound=($(get_list_value "bound"))
SW=($(get_list_value "SW"))
start_sowing=$(get_config_value "start_sowing")
end_sowing=$(get_config_value "end_sowing")
mini=$(get_config_value "mini")
maxi=$(get_config_value "maxi")
cropmask=$(get_config_value "cropmask")
testoption=$(get_config_value "testoption")
shapefile=$(get_config_value "shapefile")

#####################################

echo "INDEXES : $INDEXES"
i=$INDEXES;

DIR_EXP=${DATAMILL_WORK}/EXPS/exp_$i
DB_MI=$DIR_EXP/MasterInput.db
DB_CEL=$DIR_EXP/CelsiusV3nov17_dataArise.db
DB_MD=${DATAMILL_WORK}/db/ModelsDictionaryArise.db
echo "DIR_EXP : $DIR_EXP"
echo "DB_MI : $DB_MI"
echo "DB_MD : $DB_MD"
echo "INDEXES  : $INDEXES "
echo "n_jobs : $n_jobs"

################################################# Start EXP generation ####################


# can be commented from here

python3 ${DATAMILL_WORK}/scripts/workflow/init_dirs.py --index $i;
wait


python3 ${DATAMILL_WORK}/scripts/netcdf/soil_to_db.py --index $i --soilTexture "$soilTextureType" --extract "$doExtract" --bnd "${bound[@]}" --cropmask "$cropmask" --textclass $textclass --shp $shapefile;
wait

# comment from here to know the number of pixels

python3 ${DATAMILL_WORK}/scripts/netcdf/meteo_to_db2.py --index $i --extract "$doExtract" --bnd "${bound[@]}" --min $mini --max $maxi --cropmask "$cropmask" --testoption $testoption --shp $shapefile --ncpus $ncpus --nchunks $nchunks;
wait 

python3 ${DATAMILL_WORK}/scripts/netcdf/dem_to_db.py --index $i --extract "$doExtract" --bnd "${bound[@]}" --cropmask "$cropmask" --shp $shapefile;
wait

date
python3 ${DATAMILL_WORK}/scripts/functions/compute_etp1.py --index $i --ncpus $ncpus;
date
wait

python ${DATAMILL_WORK}/scripts/workflow/spatialized_cropMangt.py --index $i --svariety "$s_variety" --sfert "$s_fert" --sirr "$s_irr" --ssowing "$s_sowing" --sdensity "$s_density" --variety_dict "$variety_dict" --sowingDates "${SW[@]}" --bnd "${bound[@]}" --cropvariety "${variety[@]}" --ferti "${fertioption[@]}" --sowingoption $SD ;
wait

python3 ${DATAMILL_WORK}/scripts/workflow/init_simunitlist.py --index $i --startdate $startd --enddate $endd --option "${simoption[@]}" --sowingoption $SD --deltaStart $start_sowing --deltaEnd $end_sowing;
wait




################################################# End EXP generation ####################


if [[ " ${models[@]} " =~ " celsius " ]]; then
   ${DATAMILL_WORK}/scripts/workflow/celsius.sh
fi
wait


if [ $SD -eq 1 ]
then
python3 ${DATAMILL_WORK}/scripts/workflow/modify_simunilist.py --index $i;
fi 
wait


if [[ " ${models[@]} " =~ " stics " ]]; then
   ${DATAMILL_WORK}/scripts/workflow/stics.sh
fi
wait

if [[ " ${models[@]} " =~ " dssat " ]]; then
   ${DATAMILL_WORK}/scripts/workflow/dssat.sh
fi
wait

## comm2

### first time: run the EXP generation by putting in comment the rest of code below with these balises (:<<comment and comment) and run sbatch --array=0-19%5 datamill.slurm

### Then remove the comment balises and put in comment EXP generation part. And run sbatch --array=0-19 datamill.slurm  (without %5)

:<<comm2
comm2


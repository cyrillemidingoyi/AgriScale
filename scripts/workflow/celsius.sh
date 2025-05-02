#!/usr/bin/env bash

export INDEXES=$INDEXES #($SLURM_ARRAY_TASK_ID)
export ncpus=$ncpus # number of cpus


if [[ -z "$DATAMILL_WORK" ]]; then
  export DATAMILL_WORK='/package'
fi

echo "celsius INDEXES : $INDEXES"
i=$INDEXES;

work_dir='/inter'
DIR_EXP=${work_dir}/EXPS/exp_$i

cd $DIR_EXP

python3 ${DATAMILL_WORK}/scripts/workflow/run_celsius.py --index $i --ncpus $ncpus ;
wait



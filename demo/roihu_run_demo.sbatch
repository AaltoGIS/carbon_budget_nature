#!/bin/bash
# Execute the Helsinki notebooks on the demo data (demo/run_demo.py) and time them.
# CSC Roihu, CPU side. Submit from the repository root:  sbatch demo/roihu_run_demo.sbatch
# Indicative cost: max(0.75*2 cores, 0.375*16 GiB) = 6 BU/h.
#SBATCH --job-name=demo_run
#SBATCH --account=project_2010423
#SBATCH --partition=small
#SBATCH --time=01:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --output=demo/work/slurm_run_%j.out
#SBATCH --error=demo/work/slurm_run_%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$PWD}"
PY=/projappl/project_2010423/HPC-env/env_container/bin/python   # Tykky container of the analysis
export MPLBACKEND=Agg
export XDG_CACHE_HOME="${TMPDIR:-/tmp}/cache"                   # contextily tile cache off Lustre
$PY demo/run_demo.py --save-executed "$@"

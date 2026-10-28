#!/bin/bash
# Cut the demo inputs out of the full intermediates (reads ~5 GB of parquet).
# CSC Roihu, CPU side. Submit from the repository root:  sbatch demo/roihu_extract.sbatch
# Indicative cost: max(0.75*4 cores, 0.375*24 GiB) = 9 BU/h, i.e. a few BU.
#SBATCH --job-name=demo_extract
#SBATCH --account=project_2010423
#SBATCH --partition=small
#SBATCH --time=00:40:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --output=demo/work/slurm_extract_%j.out
#SBATCH --error=demo/work/slurm_extract_%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$PWD}"
PY=/projappl/project_2010423/HPC-env/env_container/bin/python   # Tykky container of the analysis
mkdir -p demo/work
$PY demo/extract_demo_inputs.py \
    --candidates demo/work/candidates.parquet \
    --src-scratch /scratch/project_2010423 \
    --src-data /projappl/project_2010423/carbon_budgets_paper/data \
    --dst demo --n-per-area 50

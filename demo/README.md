# Demo: stages 04 and 05 on a small dataset

The mobile phone data behind the paper (Locomizer) cannot be redistributed and the full CO₂e
origin–destination tables are too large for a repository. This folder lets anyone run the
mobile-phone part of the pipeline (stages 04 and 05, Helsinki, three modes) on a small dataset,
with the notebooks exactly as used for the paper.

## Dataset

| Path | Content |
|---|---|
| `scratch/data/users_and_stays_3months.parquet` | 100 simulated users, 50 with a home in Kallio (inner city) and 50 in Espoonlahti (suburb); one home row, one work row and about ten stays per user, in the schema produced by `04_mobile_phone_stays/01_stays_helsinki.ipynb` |
| `scratch/{pt,car,bike}_co2_*.parquet` | CO₂e per origin–destination pair for the three modes, cut from the routing outputs of `02_routing_and_emissions/` (about 150,000 pairs each) |
| `data/pois_per_hex_new_class.parquet` | POIs per H3 hexagon and decent-mobility category (`01_points_of_interest/`) |
| `data/job_distribution_from_census.parquet` | Jobs per hexagon (`01_points_of_interest/`) |
| `data/postal_code/`, `data/helsinki_filter_map.geojson` | Postal code areas and city extent for the maps |
| `expected_output/` | Results the run must reproduce |

The users are simulated with `make_demo_users.py` from open data only (POIs and jobs per hexagon),
with a fixed seed. They follow the behaviour of the real sample: workplaces are drawn from the job
distribution with a distance decay, stays from the POI distribution with a distance decay plus a share
of places without POIs, and the number of places and visit frequencies per user match the aggregate
statistics reported in the paper. `extract_demo_inputs.py` keeps the users for whom every leg has a
routed CO₂e value in all three modes and cuts the matching rows out of the full origin–destination tables.

## Run

From the repository root, with the conda environment of `environment.yml` activated (Java must be
present because the notebooks import r5py):

```bash
python demo/run_demo.py                  # the seven Helsinki notebooks of stages 04 and 05
python demo/run_demo.py --save-executed  # also keep the executed notebooks in demo/output/executed/
```

The notebooks are executed unchanged with `demo/` as working directory, so their relative paths
(`data/`, `scratch/`, `output/`) resolve inside this folder. They can also be opened in Jupyter and
run by hand after starting Jupyter from `demo/`.

1. `04_mobile_phone_stays/user_pois_{pt,car,bike}_helsinki.ipynb` → `data/user_pois_{pt,car,bike}_1.parquet`, `data/users_and_works.parquet`
2. `05_carbon_cost_of_decent_mobility/exposure_curves/exposure_{pt,car,bike}_helsinki.ipynb` → `scratch/{pt,car,bike}_typ_cat.parquet`, `output/{PT,car,bike}_expenditure_weekly_typical.parquet`
3. `05_carbon_cost_of_decent_mobility/tours/decent_mobility_tours_helsinki.ipynb` → `output/tour_{pt,car,bike}_helsinki_decent_per_user.parquet` (weekly decent-mobility CO₂e per user, the input to Figs. 2–4)

A report with the time of each notebook and any failing cell is written to `output/run_report.md`.

## Expected output and run time

About 1 minute for the seven notebooks on one core of a CSC Roihu node (AMD Zen 5), under 4 GB of
memory, plus a few minutes for the first import of the geolibraries and Java on a fresh installation.
Expect about 5 minutes on a normal desktop computer. The run is deterministic: with the same package
versions it reproduces the per-user files in `expected_output/` exactly. `expected_output/run_report_roihu.md`
is the report of that run.

| Mode | Users | Median weekly CO₂e (kg) | Within 7 kg | Median Kallio / Espoonlahti (kg) |
|---|---|---|---|---|
| Public transport | 100 | 5.4 | 59 % | 1.9 / 8.9 |
| Car | 100 | 18.1 | 2 % | 11.2 / 25.9 |
| Cycling | 100 | 1.8 | 100 % | 0.8 / 2.7 |

The values show that the pipeline behaves as in the paper (inner city below suburb, cycling below public
transport below car); the simulated users are not a sample of the population.

Notes:

- The exposure notebooks end with an exploratory block on neighbourhood-level population weighting
  that is not used in the paper. Its cells are tagged `skip-execution` and skipped by `run_demo.py`.
  When running by hand, stop at that heading.
- Map cells fetch CARTO basemap tiles through `basemaps.py`. Without internet access they fail, but
  nothing downstream depends on them.

## Rebuilding the demo data (maintainers)

Requires the full intermediates of the analysis, which are not in the repository:

```bash
python demo/make_demo_users.py --pois data/pois_per_hex_new_class.parquet \
    --jobs data/job_distribution_from_census.parquet --out demo/work/candidates.parquet
sbatch demo/roihu_extract.sbatch       # or: python demo/extract_demo_inputs.py --src-scratch ... --src-data ...
sbatch demo/roihu_run_demo.sbatch      # or: python demo/run_demo.py --save-executed
```

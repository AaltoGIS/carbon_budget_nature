# Demo: synthetic users for the Helsinki pipeline

The mobile phone data behind the paper (Locomizer) cannot be redistributed, and the full
CO₂e origin–destination tables are too large for a repository. This folder lets anyone run the
mobile-phone part of the pipeline (stages 04 and 05, Helsinki, three modes) end to end on a
small **synthetic** dataset, with the notebooks exactly as they were used for the paper.

**Nothing in this folder is derived from a real user.** The 100 users are generated from open
data only (`make_demo_users.py`); the CO₂e tables are subsets of the routing results, which are
themselves derived from open data (GTFS, Digiroad, OpenStreetMap, the national elevation model).

## Contents

| Path | What it is | Origin |
|---|---|---|
| `scratch/data/users_and_stays_3months.parquet` | 100 synthetic users (50 with a home around Kallio, inner city; 50 around Espoonlahti, suburb), 1,174 rows: one home row, one work row and on average ten stays per user, with the schema produced by `04_mobile_phone_stays/01_stays_helsinki.ipynb` | `make_demo_users.py`, seed 20240415 |
| `scratch/pt_co2_3000.parquet`, `scratch/pt_co2_3000_1.parquet` | Public transport CO₂e per OD pair (`from_id`, `to_id`, `pt_co2_total`, g CO₂e), 154,496 pairs | subset of the r5r/GTFS routing output of `02_routing_and_emissions/public_transport/` |
| `scratch/car_co2_6000.parquet` | Car CO₂e per OD pair (`Origin_Hexagon_ID`, `Destination_Hexagon_ID`, `car_co2`), 154,396 pairs | subset of the Digiroad routing output of `02_routing_and_emissions/car/` |
| `scratch/bike_co2_3000.parquet` | Cycling CO₂e per OD pair (`from_id`, `to_id`, `co2_emissions_g`), 154,744 pairs | subset of the OSMnx routing output of `02_routing_and_emissions/cycling/` |
| `data/pois_per_hex_new_class.parquet` | POIs per H3 level-9 hexagon and decent-mobility category, Helsinki region | `01_points_of_interest/` (Overture Maps) |
| `data/job_distribution_from_census.parquet` | Jobs per hexagon | `01_points_of_interest/` (Statistics Finland) |
| `data/postal_code/` | Postal code areas of the Helsinki region (used to name the neighbourhood of each home) | HSY / Statistics Finland open data |
| `data/helsinki_filter_map.geojson` | City extent used by the map notebooks | own drawing |
| `expected_output/` | The per-user results the run must reproduce (see below) | this demo |

The OD subsets contain every pair whose origin or destination is a home or work hexagon of a
demo user and whose other end is a hexagon that a demo user visits, in both directions. That is
all the pipeline reads: home→stay for the exposure curves, and home→work, work→stay and
stay→home for the weekly tours.

## How the synthetic users are made

`make_demo_users.py` builds each user from open data only (POIs per hexagon from Overture Maps,
jobs per hexagon from the census), with a fixed random seed:

- **Home**: a random hexagon within two rings of the area centre (Kallio or Espoonlahti), on urban land.
- **Work**: drawn from the job hexagons, with probability proportional to the number of jobs and
  decaying with distance from home (8 km scale, at most 25 km). Big job centres attract more workers,
  most commutes are short, a few are long.
- **Stays**: the number of visited places follows a log-normal with median 9 and 90th percentile 24,
  as in the real sample. Three quarters of them are POI hexagons, drawn with a weight that grows with
  the number of POIs and decays with distance from home (4 km scale, at most 15 km). The remaining
  quarter are hexagons without POIs, because about 28 % of real stays fall in such places. Every user
  has at least four stays in each of the three categories the tour builder needs.
- **Visit frequencies**: a skewed distribution (most places visited once or twice, a few up to 15
  times); home and work get their own distributions.

The output has the schema of the real stays table, so the notebooks read it unchanged.
`extract_demo_inputs.py` then keeps the users for whom every leg (home-work, home-stay, work-stay,
stay-home) has a routed CO₂e value in all three modes, and cuts the matching rows out of the full
origin-destination tables. Distances, the pull of jobs and amenities, and the stay and frequency
distributions are therefore realistic; the individual users are not, and nothing about them
describes a real person.

## Running the demo

From the repository root, with the conda environment of `environment.yml` activated (the
notebooks import r5py, so a Java runtime must be present even though no routing is done here):

```bash
python demo/run_demo.py                  # seven Helsinki notebooks of stages 04 and 05
python demo/run_demo.py --save-executed  # also keep the executed notebooks in demo/output/executed/
```

The script executes the **unchanged** notebooks with `demo/` as the working directory, so their
relative paths (`data/`, `scratch/`, `output/`) resolve inside this folder. Any notebook of the
Helsinki chain can also be opened in Jupyter and run by hand after starting Jupyter from `demo/`.

Order and outputs:

1. `04_mobile_phone_stays/user_pois_{pt,car,bike}_helsinki.ipynb` → `demo/data/user_pois_{pt,car,bike}_1.parquet`, `demo/data/users_and_works.parquet`
2. `05_carbon_cost_of_decent_mobility/exposure_curves/exposure_{pt,car,bike}_helsinki.ipynb` → `demo/scratch/{pt,car,bike}_typ_cat.parquet`, `demo/output/{PT,car,bike}_expenditure_weekly_typical.parquet`
3. `05_carbon_cost_of_decent_mobility/tours/decent_mobility_tours_helsinki.ipynb` → `demo/output/tour_{pt,car,bike}_helsinki_decent_per_user.parquet` (weekly decent-mobility CO₂e per user, the input to Figs. 2-4), and `..._typical_per_user.parquet`

A report with the wall time of every notebook and any failing cell is written to
`demo/output/run_report.md`.

### Expected output and run time

Measured on one CPU core of a CSC Roihu compute node (AMD Zen 5) inside the container of
`environment-tested.txt`: **1.0 min wall time** for the seven notebooks (5 to 25 s each), under 4 GB of
memory. The first import of the geolibraries and the Java runtime can add a few minutes on a cold node or a
fresh installation. A laptop should take a few minutes. The notebooks contain no random step, so a run with the same
package versions reproduces the values in `expected_output/` exactly.

| Mode | Users | Median weekly CO₂e (kg) | Within 7 kg | Median Kallio / Espoonlahti (kg) |
|---|---|---|---|---|
| Public transport | 100 | 5.4 | 59 % | 1.9 / 8.9 |
| Car | 100 | 18.1 | 2 % | 11.2 / 25.9 |
| Cycling | 100 | 1.8 | 100 % | 0.8 / 2.7 |

The synthetic users are not a sample of the real population; the table only shows that the pipeline
behaves as described in the paper (inner city below suburb, cycling below public transport below car).

`expected_output/run_report_roihu.md` is the report of this run: all seven notebooks execute without a
failing cell and `run_demo.py` exits with status 0.

The three exposure notebooks end with a block of exploratory cells on neighbourhood-level population
weighting (kept for transparency, marked by a heading cell "Exploratory: ... not used in the paper"). They need
a file that is not among the pipeline inputs and do not run top to bottom; nothing downstream depends on them.
Their code cells carry the `skip-execution` tag, which `run_demo.py` honours, so they are not executed by the
demo. When running a notebook by hand in Jupyter, stop at that heading.

Basemap tiles: map cells call CARTO through `basemaps.py`. Without a `CARTO_KEY` the tiles are
fetched anonymously and carry a watermark; without internet access those cells fail but nothing
downstream depends on them.

## Rebuilding the demo data (maintainers)

Requires the full intermediates of the analysis (not in the repository):

```bash
python demo/make_demo_users.py --pois data/pois_per_hex_new_class.parquet \
    --jobs data/job_distribution_from_census.parquet --out demo/work/candidates.parquet
sbatch demo/roihu_extract.sbatch       # or: python demo/extract_demo_inputs.py --src-scratch ... --src-data ...
sbatch demo/roihu_run_demo.sbatch      # or: python demo/run_demo.py --save-executed
```

The two `.sbatch` files are the Slurm scripts used on CSC Roihu; on a workstation run the Python
commands directly.

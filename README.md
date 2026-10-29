# Electrification fails to reconcile urban transport with 2030 climate targets

Analysis code for the paper

> *Electrification fails to reconcile urban transport with 2030 climate targets*
> César Marín-Flores, Subhrasankha Dey, Xiuning Zhang, Elsa Arcaute, Henrikki Tenkanen
> Department of Built Environment, Aalto University; Centre for Advanced Spatial Analysis, University College London

The study tests whether minimum ("decent") mobility needs can be met within 2030 Paris-compatible
carbon budgets in Finland's four largest urban regions (Helsinki, Turku, Tampere and Oulu), by
transport mode (cycling, public transport and private car). It combines multimodal routing,
life-cycle emission factors and anonymised mobile phone location data from Locomizer
(April to June 2024).

## Repository structure

The notebooks are numbered in the order in which they are run. Each stage is repeated for the
four study regions, with one notebook per region (the Helsinki notebook is the reference
implementation; the other regions follow the same steps with region-specific inputs).

| Folder | Content | Paper section |
|---|---|---|
| `01_points_of_interest/` | Download of points of interest (POIs) from Overture Maps, aggregation to the H3 level-9 grid, re-classification into the decent-mobility categories, and census job distribution | Methods: Points of interest data |
| `02_routing_and_emissions/` | Door-to-door routing and CO₂e estimation per origin–destination pair for public transport (r5r/GTFS), private car (Digiroad, Dijkstra) and cycling (OSMnx with slope penalty) | Methods: Multimodal routing; Estimation of travel-related CO₂ emissions |
| `03_accessibility_within_budget/` | Share of POIs reachable from each hexagon within a 1 kg CO₂e round trip, by mode | Fig. 1 |
| `04_mobile_phone_stays/` | Processing of stay locations, inference of home and work locations, spatial filters, and matching of stays to POI categories per user and mode | Methods: Mobility data and stay locations |
| `05_carbon_cost_of_decent_mobility/` | Exposure-weighted cumulative CO₂e curves per user and POI category (`exposure_curves/`), and construction of the weekly decent-mobility tours (`tours/`) | Methods: Carbon cost from mobility data; Trip chains for decent mobility; Supplementary Fig. S11 |
| `06_figures/` | Main-text figures: weekly expenditure and compliance (Fig. 2a,b), compliance maps by city and mode (Fig. 2c), income inequality (Fig. 3), BEV vs ICE electrification scenario (Fig. 4) | Results |
| `07_supplementary/` | Sensitivity to the carbon budget threshold (A), representativeness and home/work inference (B), observed commuting patterns (C), sensitivity to the POI exposure level and nearest-POI comparison (D) | Supplementary Material A to D |
| `basemaps.py` | Helper for keyed CARTO basemap tiles in contextily (reads the key from the `CARTO_KEY` environment variable) | |
| `data/` | Small configuration files: POI category list, category mapping and the classification used in the paper. See `data/README.md` for the full list of inputs | |
| `output/` | Aggregated, non-personal tables behind the figures (see `output/README.md`) | Figs. 1-4, Supplementary |
| `tools/` | Script that derives the shared aggregates from the per-user results | |
| `demo/` | Small demo dataset and runner for the mobile-phone stages (see `demo/README.md`) | |
| `environment-tested.txt` | Package versions the analysis was run with | |

## Data

The mobile phone data used in this study were provided by Locomizer under a licence agreement and
cannot be shared. Every notebook that reads them documents the expected schema in its first cells.
All other inputs are open data:

- Points of interest: Overture Maps Foundation (`overturemaps` Python package)
- Street and cycling networks: OpenStreetMap (OSMnx)
- Public transport schedules: national GTFS feeds; routing with r5r/r5py
- Road network for cars: Digiroad, Finnish Transport Infrastructure Agency
- Elevation: National Land Survey of Finland 2 m DEM
- Population and income: Statistics Finland grid database (250 m and 1 km)
- Region boundaries and postal code areas: Statistics Finland

Large inputs and per-user intermediate results are not versioned. They are expected under
`data/`, `scratch/` (large intermediates) and `output/` (per-user results and figures), relative
to the repository root. Notebooks are run from the repository root as the working directory.

`output/` contains the aggregated tables behind every figure (distributions, summary statistics,
hexagon-level means with a minimum of five users, income-decile tables, hourly home/work presence).
They are described in `output/README.md` and were produced with `tools/make_shared_outputs.py`.
The figures can be re-plotted from them without access to the restricted data.

## System requirements

- Python 3.10 and the packages in `environment.yml`. The exact versions used for the paper are in
  `environment-tested.txt` (pandas 2.3.3, geopandas 1.1.4, shapely 2.1.2, pyarrow 23.0.1, h3 3.7.7,
  osmnx 1.6.0, r5py 1.1.7, matplotlib 3.10.9). The notebooks use the h3-py version 3 API.
- Java 21 or later (r5py).
- Tested on Red Hat Enterprise Linux 9.8, x86_64 (CSC Roihu supercomputer). Pure Python; Linux and
  macOS with the same conda environment should work but were not re-tested.
- Hardware: the demo runs on a laptop (one core, under 4 GB of memory). The full pipeline keeps
  origin–destination tables of 29 to 69 million pairs per mode in memory (about 30 GB) and the routing
  stages take hours per region; they were run on CSC Roihu.

## Installation

```bash
conda env create -f environment.yml
conda activate decent-mobility
conda install -c conda-forge openjdk=21   # or any system JDK 21+
```

About 10–20 minutes on a normal desktop computer.

## Demo

`demo/` runs stages 04 and 05 for Helsinki on a small dataset: 100 simulated users and the open-data
inputs they need (about 6 MB). No real mobile phone record is included. From the repository root:

```bash
python demo/run_demo.py
```

The script runs the seven Helsinki notebooks unchanged, with `demo/` as working directory. Output:
weekly decent-mobility CO₂e per user and mode in `demo/output/tour_{pt,car,bike}_helsinki_decent_per_user.parquet`,
and a run report with the time of each notebook. The expected results are in `demo/expected_output/`;
the run is deterministic and reproduces them exactly with the same package versions.

Run time: about 1 minute on one core of a CSC Roihu node, plus a few minutes for the first import of the
geolibraries and Java. Expect about 5 minutes on a normal desktop computer. See `demo/README.md`.

## Instructions for use

To run the pipeline on your own mobility data, provide one stays table per region at
`scratch/data/users_and_stays_3months{_city}.parquet` with the schema produced by
`04_mobile_phone_stays/01_stays_helsinki.ipynb`:

| Column | Type | Meaning |
|---|---|---|
| `user_id` | string | pseudonymous user identifier |
| `stay_gid9` | string | H3 level-9 hexagon of a stay location |
| `frequency_period` | int | number of visits to that hexagon in the study period |
| `home_gid9`, `work_gid9` | string | inferred home and work hexagons of the user |
| `is_home`, `is_work` | int (0/1) | whether the stay is the home or the work location |

Place the open-data inputs listed in `data/README.md` and run the notebooks from the repository root in
folder order (01 → 07), one notebook per region and mode. `tools/make_shared_outputs.py` rebuilds the
aggregated tables in `output/` from the per-user results.

## Reproduction

The full results cannot be reproduced without the Locomizer data. What can be reproduced:

1. Stages 01 to 03 (POIs and jobs per hexagon, routed CO₂e per origin–destination pair, accessibility
   within budget, Fig. 1) from the open inputs in `data/README.md`. Tens of GB of memory and hours per region.
2. Stages 04 and 05 on the demo dataset, or on your own stays table as described above.
3. The numbers behind Figs. 1 to 4 and the Supplementary figures, from the tables in `output/`.

## Citation

See `CITATION.cff`. A DOI will be added upon publication.

## Licence

The code is released under the MIT Licence (see `LICENSE`).

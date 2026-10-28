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
| `demo/` | Runnable demo of the mobile-phone stages on 100 **synthetic** users and small open-data subsets (see `demo/README.md`) | |
| `environment-tested.txt` | Exact package versions of the environment the analysis was run in | |

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

`output/` does contain the **aggregated tables behind every figure** (distributions, summary
statistics, hexagon-level means with a minimum of five users, income-decile tables, hourly
home/work presence). They are described in `output/README.md` and were produced with
`tools/make_shared_outputs.py`. They are the data behind every figure and allow the results to be
re-plotted and checked without access to the restricted data; the figure notebooks themselves read the
per-user results, which are not shared.

## Environment

The analysis was run with Python 3.10 in a conda environment; the packages are listed in
`environment.yml`:

```bash
conda env create -f environment.yml
conda activate decent-mobility
```

The exact versions the analysis was run with are listed in `environment-tested.txt` (Python 3.10.20 in a
Tykky/Apptainer container on CSC Roihu, Red Hat Enterprise Linux 9.8, x86_64; key packages: pandas 2.3.3,
geopandas 1.1.4, shapely 2.1.2, pyarrow 23.0.1, h3 3.7.7, osmnx 1.6.0, r5py 1.1.7, matplotlib 3.10.9).
The notebooks use the h3-py **version 3** API (`h3.geo_to_h3`, `h3.k_ring`); `tools/make_shared_outputs.py`
works with both API versions.

Public transport routing (r5py) requires Java 21. Most routing and exposure-curve steps
were executed on the CSC Roihu supercomputer because of the size of the origin–destination
matrices (tens of millions of pairs per region).

## System requirements, installation, demo and instructions for use

### System requirements

- **Operating system.** Tested on Red Hat Enterprise Linux 9.8 (x86_64, CSC Roihu) inside the container
  described by `environment.yml`. The code is pure Python and is expected to run on Linux and macOS with
  the same conda environment; this was not re-tested.
- **Software.** Python 3.10 and the packages in `environment.yml` (exact versions in
  `environment-tested.txt`); a Java runtime (OpenJDK 21 or later) for r5py, which every notebook imports.
- **Hardware.** The demo runs on an ordinary laptop (one core, under 4 GB of memory). The full pipeline
  holds origin-destination tables of 29 to 69 million pairs per mode in memory (about 30 GB) and the
  routing stages take hours per region; they were run on CSC Roihu.

### Installation guide

```bash
conda env create -f environment.yml      # typical time 10-20 minutes on a broadband connection
conda activate decent-mobility
```

Java: `conda install -c conda-forge openjdk=21` inside the environment, or any system JDK 21+.

### Demo

`demo/` contains 100 synthetic users for two Helsinki-region areas (Kallio and Espoonlahti) and the
subsets of the open-data intermediates they need (POIs and jobs per hexagon, CO₂e per origin-destination
pair for the three modes, postal code areas), about 6 MB in total. No real mobile phone record is
included. From the repository root:

```bash
python demo/run_demo.py
```

This executes the seven unchanged Helsinki notebooks of stages 04 and 05 with `demo/` as working
directory and writes the per-user weekly decent-mobility CO₂e to
`demo/output/tour_{pt,car,bike}_helsinki_decent_per_user.parquet`, plus a run report with the wall time of
every notebook. Expected per-user results are in `demo/expected_output/`; the run is deterministic, so they
are reproduced exactly with the same package versions. Measured run time: 1.0 min on one core of a CSC Roihu
node (under 4 GB of memory), plus up to a few minutes for the first import of the geolibraries and the Java
runtime; expect about 5 minutes on a normal desktop computer.
See `demo/README.md` for the list of outputs, the expected values and how the synthetic users are made.

### Instructions for use

To run the pipeline on your own mobility data, provide one table per region with the schema produced by
`04_mobile_phone_stays/01_stays_helsinki.ipynb`, at `scratch/data/users_and_stays_3months{_city}.parquet`:

| Column | Type | Meaning |
|---|---|---|
| `user_id` | string | pseudonymous user identifier |
| `stay_gid9` | string | H3 level-9 hexagon of a stay location |
| `frequency_period` | int | number of visits to that hexagon in the study period |
| `home_gid9`, `work_gid9` | string | inferred home and work hexagons of the user |
| `is_home`, `is_work` | int (0/1) | whether the stay is the home or the work location |

Then place the open-data inputs listed in `data/README.md` and run the notebooks from the repository
root in the order of the folder numbers (01 → 07), one notebook per region and mode. The aggregated,
non-personal tables in `output/` are rebuilt from the per-user results with `tools/make_shared_outputs.py`.

### Reproduction instructions

The full results of the paper cannot be reproduced without the Locomizer data. What can be reproduced:

1. **Open-data stages (01 to 03)** from the inputs listed in `data/README.md`: POIs and jobs per hexagon,
   the routed CO₂e per origin-destination pair for the three modes, and the accessibility-within-budget maps
   (Fig. 1). The routing stages need tens of GB of memory and hours per region.
2. **Mobile-phone stages (04 and 05)** on the synthetic users of `demo/`, or on your own stays table as
   described above. The demo reproduces `demo/expected_output/` exactly.
3. **The numbers behind Figs. 1 to 4 and the Supplementary figures** from the aggregated tables in
   `output/`, described in `output/README.md`.

## Citation

See `CITATION.cff`. A DOI will be added upon publication.

## Licence

The code is released under the MIT Licence (see `LICENSE`).

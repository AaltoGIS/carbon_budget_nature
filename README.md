# Carbon budget compliance and decent mobility in Finnish urban regions

Analysis code for the paper

> **Beyond electrification: Meeting minimum mobility needs within carbon budgets**
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
`tools/make_shared_outputs.py`, so the figures can be reproduced without access to the
restricted data.

## Environment

The analysis was run with Python 3.10 in a conda environment; the packages are listed in
`environment.yml`:

```bash
conda env create -f environment.yml
conda activate decent-mobility
```

Public transport routing (r5py) requires Java 21. Most routing and exposure-curve steps
were executed on the CSC Roihu supercomputer because of the size of the origin–destination
matrices (tens of millions of pairs per region).

## Citation

See `CITATION.cff`. A DOI will be added upon publication.

## Licence

The code is released under the MIT Licence (see `LICENSE`).

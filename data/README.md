# Data

This folder holds the small configuration files that are versioned with the code:

| File | Description |
|---|---|
| `category_list.csv` | List of Overture Maps primary categories present in the study areas |
| `category_mapping.json` | Mapping from Overture primary categories to aggregated POI categories |
| `classification_paper.txt` | Final classification of primary categories into the decent-mobility purposes used in the paper (Education; Healthcare and Health; Recreational, Outdoors; Shopping, Errands; Social, Cultural) |

The remaining inputs are not versioned because of their size or licence. The notebooks
expect them at the following locations (relative to the repository root):

| Path | Source | Notes |
|---|---|---|
| `data/*_region_boundary.geojson`, `data/*_filter_map.geojson`, `data/filter_hex_*.parquet` | Statistics Finland / own processing | Study area boundaries and hexagon filters |
| `data/grid_data/rttk250m_tilv2019.shp` | Statistics Finland grid database, 250 m | Median income |
| `data/1km_data/vaki2024_1km.shp` | Statistics Finland, 1 km population grid | Representativeness check |
| `data/postal_code/`, `data/postal_code_finland/` | Statistics Finland (Paavo) | Postal code areas |
| `data/pois_per_hex*.parquet`, `data/job_distribution_from_census*.parquet` | Produced by `01_points_of_interest/` | POIs and jobs per H3 hexagon |
| `data/travel_time_matrix_bicycle*.csv`, `data/OD_cycling_33M_snap*.parquet` | Produced by `02_routing_and_emissions/cycling/` | Cycling travel times and snapped OD pairs |
| `scratch/pt_co2_3000*.parquet`, `scratch/car_co2_6000*.parquet`, `scratch/bike_co2_3000*.parquet` | Produced by `02_routing_and_emissions/` | CO₂e per OD pair and mode |
| `scratch/data/ucl_stays/`, `scratch/data/stays_sufficient_users.parquet`, `scratch/data/user_home+work.parquet`, `scratch/data/users_and_stays_3months*.parquet` | Locomizer mobile phone data (restricted) | Stay locations and inferred home/work |
| `data/user_pois_{mode}_1*.parquet`, `data/users_and_works*.parquet` | Produced by `04_mobile_phone_stays/` | Stays matched to POI categories per user |
| `scratch/{mode}_typ_cat*.parquet`, `output/{mode}_expenditure_weekly_typical*.parquet` | Produced by `05_carbon_cost_of_decent_mobility/exposure_curves/` | Exposure-based carbon cost per user and category |
| `output/tour_{mode}_{city}_decent_per_user.parquet` | Produced by `05_carbon_cost_of_decent_mobility/tours/` | Weekly decent-mobility CO₂e per user (input to all figures) |

# Demo run report

Total wall time: 5.4 min (Python 3.10.20)

| Notebook | Code cells | Seconds | Failing cells |
|---|---|---|---|
| 04_mobile_phone_stays/user_pois_pt_helsinki.ipynb | 50 | 253.5 | none |
| 04_mobile_phone_stays/user_pois_car_helsinki.ipynb | 42 | 8.5 | none |
| 04_mobile_phone_stays/user_pois_bike_helsinki.ipynb | 43 | 8.5 | none |
| 05_carbon_cost_of_decent_mobility/exposure_curves/exposure_pt_helsinki.ipynb | 133 | 9.2 | none |
| 05_carbon_cost_of_decent_mobility/exposure_curves/exposure_car_helsinki.ipynb | 132 | 9.3 | none |
| 05_carbon_cost_of_decent_mobility/exposure_curves/exposure_bike_helsinki.ipynb | 123 | 9.4 | none |
| 05_carbon_cost_of_decent_mobility/tours/decent_mobility_tours_helsinki.ipynb | 205 | 25.6 | none |

The first notebook spends about four minutes in its import cell (first load of the geolibraries and the Java runtime on a freshly allocated node); on a warm node it takes about 10 s and the whole demo 1.0 min.

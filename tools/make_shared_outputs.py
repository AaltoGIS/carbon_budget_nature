"""
Build the aggregated, non-personal data files in ``output/`` from the per-user
results of the analysis pipeline.

The mobile phone data (Locomizer) and every per-user intermediate derived from
it cannot be shared. This script reduces them to the aggregates that the paper's
figures are drawn from:

* distributions (histogram counts) and summary statistics of weekly CO2e per
  city and mode, including the BEV scenario;
* hexagon-level means with a minimum number of users per hexagon (``K_MIN``);
* compliance and mean CO2e by income decile;
* hourly home/work presence probabilities and 1 km grid user counts without
  grid identifiers.

Stages:
    light  - inputs are small per-user tables; runs in seconds.
    heavy  - joins the 250 m income grid and the raw stay table; run as a batch job.

Usage:
    python tools/make_shared_outputs.py --stage light|heavy|all \
        --src /path/to/working/folder --scratch /path/to/scratch --dst output/
"""
import argparse
import json
import shutil
from pathlib import Path

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from shapely.geometry import Point, Polygon

CITIES = ["helsinki", "turku", "tampere", "oulu"]
CITY_LABEL = {"helsinki": "Helsinki", "turku": "Turku", "tampere": "Tampere", "oulu": "Oulu"}
MODES = ["bike", "pt", "car"]
MODE_LABEL = {"bike": "Cycling", "pt": "Public transport", "car": "Car", "car_bev": "Car (BEV)"}

K_MIN = 5                      # minimum users per hexagon / cell for spatial aggregates
BUDGET_THRESHOLDS_KG = [3.8, 5.6, 7.0, 8.4]
BEV_SCALE = 70 / 162           # g CO2e/km BEV over ICE (see Methods, Table 1)
DIST_BIN_KG = 0.1
DIST_MAX_KG = 60.0
COMMUTE_BIN_KG = 0.05
COMMUTE_MAX_KG = 15.0
COMMUTE_MIN_G = {"pt": 15, "car": 35, "bike": 10}   # cleaning rule of the commuting figure


def suffix(city):
    return "" if city == "helsinki" else f"_{city}"


def hex_polygon(h):
    return Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(h)])


def hex_point(h):
    lat, lng = h3.cell_to_latlng(h)
    return Point(lng, lat)


def summary_stats(values):
    v = np.clip(np.asarray(values, dtype=float), 0, None)
    v = v[~np.isnan(v)]
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    iqr = q3 - q1
    lo = v[v >= q1 - 1.5 * iqr].min()
    hi = v[v <= q3 + 1.5 * iqr].max()
    row = {
        "n_users": int(len(v)), "mean_kg": v.mean(), "sd_kg": v.std(ddof=1),
        "p5_kg": np.percentile(v, 5), "p10_kg": np.percentile(v, 10), "p25_kg": q1,
        "median_kg": med, "p75_kg": q3, "p90_kg": np.percentile(v, 90), "p95_kg": np.percentile(v, 95),
        "whisker_low_kg": lo, "whisker_high_kg": hi,
    }
    for t in BUDGET_THRESHOLDS_KG:
        row[f"pct_within_{t}kg"] = 100 * (v <= t).mean()
    return row


def histogram(values, bin_kg, max_kg):
    v = np.clip(np.asarray(values, dtype=float), 0, None)
    edges = np.round(np.arange(0, max_kg + bin_kg / 2, bin_kg), 6)
    counts, _ = np.histogram(v[v < max_kg], bins=edges)
    rows = [{"bin_lower_kg": edges[i], "bin_upper_kg": edges[i + 1], "n_users": int(c)}
            for i, c in enumerate(counts) if c > 0]
    n_over = int((v >= max_kg).sum())
    if n_over:
        rows.append({"bin_lower_kg": max_kg, "bin_upper_kg": np.inf, "n_users": n_over})
    return rows


def read_filter_polygon(src, city, crs):
    """City extent used to clip the hexagon maps (same file as in the figure notebooks)."""
    path = src / "data" / f"{city}_filter_map.geojson"
    if not path.exists():
        path = src / "data" / f"filter_hex_{city}.geojson"
    return gpd.read_file(path).to_crs(crs).union_all()


# ----------------------------------------------------------------------------- light stage
def stage_light(src, scratch, dst):
    # --- Fig. 1: share of POIs reachable within 1 kg CO2e (routing-based, no personal data)
    n = 0
    for mode in MODES:
        for city in CITIES:
            f = src / "output" / f"{mode}_map_data_overall{suffix(city)}.parquet"
            shutil.copy(f, dst / f.name)
            n += 1
    print(f"Fig. 1: copied {n} hexagon accessibility tables")

    # --- weekly decent-mobility CO2e per user (Fig. 2a-b, Fig. 4, Supplementary A)
    per_user = {}
    for city in CITIES:
        for mode in MODES:
            df = pd.read_parquet(src / "output" / f"tour_{mode}_{city}_decent_per_user.parquet")
            per_user[(city, mode)] = df
            if mode == "car":
                bev = df.copy()
                bev["decent_mobility_co2"] = bev["decent_mobility_co2"] * BEV_SCALE
                per_user[(city, "car_bev")] = bev

    dist_rows, summ_rows = [], []
    for mode in MODES + ["car_bev"]:
        pooled = []
        for city in CITIES:
            kg = per_user[(city, mode)]["decent_mobility_co2"].dropna().values / 1000
            pooled.append(kg)
            for r in histogram(kg, DIST_BIN_KG, DIST_MAX_KG):
                dist_rows.append({"city": CITY_LABEL[city], "mode": mode, **r})
            summ_rows.append({"city": CITY_LABEL[city], "mode": mode, **summary_stats(kg)})
        allv = np.concatenate(pooled)
        for r in histogram(allv, DIST_BIN_KG, DIST_MAX_KG):
            dist_rows.append({"city": "Overall", "mode": mode, **r})
        summ_rows.append({"city": "Overall", "mode": mode, **summary_stats(allv)})
    pd.DataFrame(dist_rows).to_csv(dst / "decent_mobility_weekly_co2_distribution.csv", index=False)
    pd.DataFrame(summ_rows).to_csv(dst / "decent_mobility_weekly_co2_summary.csv", index=False)
    print("Fig. 2/4, Suppl. A: distributions and summary statistics written")

    # --- hexagon-level mean weekly CO2e per home hexagon (Fig. 2c, Supplementary A maps)
    hex_rows = []
    for city in CITIES:
        clip = read_filter_polygon(src, city, "EPSG:3857")
        for mode in MODES + ["car_bev"]:
            base_mode = "car" if mode == "car_bev" else mode
            typical = pd.read_parquet(src / "output" / f"tour_{base_mode}_{city}_typical_per_user.parquet",
                                      columns=["user_id", "home_gid9"]).drop_duplicates("user_id")
            df = per_user[(city, mode)].merge(typical, on="user_id", how="left")
            df = df[df["home_gid9"].notna() & (df["home_gid9"].astype(str) != "1")]
            df["co2_kg"] = df["decent_mobility_co2"] / 1000
            agg = (df.groupby("home_gid9")
                     .agg(n_users=("user_id", "nunique"), mean_co2_kg=("co2_kg", "mean"),
                          median_co2_kg=("co2_kg", "median"))
                     .reset_index())
            agg = agg[agg["n_users"] >= K_MIN].copy()
            geom = gpd.GeoSeries([hex_polygon(h) for h in agg["home_gid9"]], crs="EPSG:4326").to_crs("EPSG:3857")
            agg["in_city_filter"] = geom.within(clip).values
            agg.insert(0, "mode", mode)
            agg.insert(0, "city", CITY_LABEL[city])
            hex_rows.append(agg)
    hexes = pd.concat(hex_rows, ignore_index=True)
    hexes.to_parquet(dst / "decent_mobility_home_hexagons.parquet", index=False)
    print(f"Fig. 2c / Suppl. A: {len(hexes)} city-mode-hexagon rows (>= {K_MIN} users each)")

    # --- Supplementary C: commuting CO2e per user (jobs tour) and home/work hexagon counts
    c_dist, c_summ = [], []
    for city in CITIES:
        for mode in MODES:
            df = pd.read_parquet(scratch / f"{mode}_typ_cat{suffix(city)}.parquet",
                                 columns=["user_id", "poi_type", "typical_trip_co2"])
            s = df.loc[df["poi_type"] == "jobs", "typical_trip_co2"].dropna()
            s = s[s >= COMMUTE_MIN_G[mode]] / 1000
            for r in histogram(s.values, COMMUTE_BIN_KG, COMMUTE_MAX_KG):
                c_dist.append({"city": CITY_LABEL[city], "mode": mode, **r})
            c_summ.append({"city": CITY_LABEL[city], "mode": mode, **summary_stats(s.values)})
    pd.DataFrame(c_dist).to_csv(dst / "commuting_co2_distribution.csv", index=False)
    pd.DataFrame(c_summ).to_csv(dst / "commuting_co2_summary.csv", index=False)

    hw_rows = []
    for city in CITIES:
        users = pd.read_parquet(src / "data" / f"user_pois_pt_1{suffix(city)}.parquet",
                                columns=["user_id", "home_gid9", "work_gid9", "is_home", "is_work"])
        for kind, flag, col in [("home", "is_home", "home_gid9"), ("work", "is_work", "work_gid9")]:
            u = users[users[flag] == 1].drop_duplicates("user_id")
            cnt = u.groupby(col).size().rename("n_users").reset_index().rename(columns={col: "gid9"})
            cnt = cnt[(cnt["n_users"] >= K_MIN) & (cnt["gid9"].astype(str) != "1")]
            cnt.insert(0, "location", kind)
            cnt.insert(0, "city", CITY_LABEL[city])
            hw_rows.append(cnt)
    pd.concat(hw_rows, ignore_index=True).to_parquet(dst / "commuting_home_work_hexagons.parquet", index=False)
    print("Suppl. C: commuting distributions and home/work hexagon counts written")

    # --- Supplementary D: sensitivity of the carbon cost to the POI exposure level
    for city in ["oulu", "turku"]:
        df = pd.read_csv(src / "output" / f"sensitivity_summary_{city}.csv")
        df = df.rename(columns={"threshold": "exposure_level"})
        df.insert(0, "city", CITY_LABEL[city])
        df.to_csv(dst / f"exposure_level_sensitivity_{city}.csv", index=False)
    print("Suppl. D: exposure-level sensitivity tables copied")


# ----------------------------------------------------------------------------- heavy stage
def stage_heavy(src, scratch, dst):
    # --- Fig. 3: income deciles and bivariate income x PT CO2e hexagons
    frames = []
    for city in CITIES:
        u = pd.read_parquet(src / "data" / f"user_pois_pt_1{suffix(city)}.parquet",
                            columns=["user_id", "home_gid9", "is_home"])
        u = u[u["is_home"] == 1].drop_duplicates("user_id")[["user_id", "home_gid9"]]
        u["city"] = city
        frames.append(u)
    homes = pd.concat(frames, ignore_index=True)
    homes = homes[homes["home_gid9"].astype(str) != "1"]
    homes = gpd.GeoDataFrame(homes, geometry=[hex_point(h) for h in homes["home_gid9"]],
                             crs="EPSG:4326").to_crs("EPSG:3067")

    income = gpd.read_file(src / "data" / "grid_data" / "rttk250m_tilv2019.shp",
                           columns=["grid_id", "hr_mtu"], engine="pyogrio").to_crs("EPSG:3067")
    joined = gpd.sjoin(homes, income[["grid_id", "hr_mtu", "geometry"]], how="left", predicate="within")
    matched = joined[joined["hr_mtu"].notna()]
    unmatched = joined[joined["hr_mtu"].isna()][homes.columns]
    recovered = gpd.sjoin_nearest(unmatched, income[["grid_id", "hr_mtu", "geometry"]], how="left",
                                  max_distance=50)
    recovered = recovered[recovered["hr_mtu"].notna()]
    hi = pd.concat([matched, recovered], ignore_index=True)
    hi = hi[hi["hr_mtu"] >= 0].drop_duplicates("user_id")
    hi["income_decile"] = hi.groupby("city")["hr_mtu"].transform(
        lambda x: pd.qcut(x, 10, labels=False, duplicates="drop") + 1)
    print(f"Fig. 3: {len(hi)} of {len(homes)} home locations matched to an income cell")

    rows = []
    for city in CITIES:
        for mode in MODES:
            co2 = pd.read_parquet(src / "output" / f"tour_{mode}_{city}_decent_per_user.parquet")
            co2["co2_kg"] = co2["decent_mobility_co2"] / 1000
            df = co2.merge(hi.loc[hi["city"] == city, ["user_id", "income_decile", "hr_mtu"]],
                           on="user_id", how="inner")
            df["compliant"] = df["co2_kg"] <= 7
            g = (df.groupby("income_decile")
                   .agg(n_users=("user_id", "count"), compliance_rate=("compliant", "mean"),
                        avg_co2_kg=("co2_kg", "mean"), median_co2_kg=("co2_kg", "median"),
                        income_min_eur=("hr_mtu", "min"), income_max_eur=("hr_mtu", "max"))
                   .reset_index())
            g.insert(0, "mode", mode)
            g.insert(0, "city", CITY_LABEL[city])
            rows.append(g)
    pd.concat(rows, ignore_index=True).to_csv(dst / "fig3_compliance_by_income_decile.csv", index=False)

    biv = []
    for city in CITIES:
        clip = read_filter_polygon(src, city, "EPSG:3067")
        sub = hi[hi["city"] == city]
        sub = sub[sub.geometry.within(clip)]
        pt = pd.read_parquet(src / "output" / f"tour_pt_{city}_decent_per_user.parquet")
        pt["co2_kg"] = pt["decent_mobility_co2"] / 1000
        m = sub.merge(pt[["user_id", "co2_kg"]], on="user_id", how="inner").dropna(subset=["co2_kg", "hr_mtu"])
        agg = (m.groupby("home_gid9")
                 .agg(n_users=("user_id", "count"), mean_income_eur=("hr_mtu", "mean"),
                      mean_pt_co2_kg=("co2_kg", "mean"))
                 .reset_index())
        # terciles are defined over all hexagons (as in the figure), then small hexagons are withheld
        agg = agg.dropna(subset=["mean_income_eur", "mean_pt_co2_kg"])
        # rank first so that tied hexagon means do not produce duplicate bin edges
        agg["income_tercile"] = pd.qcut(agg["mean_income_eur"].rank(method="first"), 3, labels=[1, 2, 3]).astype(int)
        agg["co2_tercile"] = pd.qcut(agg["mean_pt_co2_kg"].rank(method="first"), 3, labels=[1, 2, 3]).astype(int)
        agg = agg[agg["n_users"] >= K_MIN]
        agg.insert(0, "city", CITY_LABEL[city])
        biv.append(agg)
    pd.concat(biv, ignore_index=True).to_parquet(dst / "fig3_income_pt_co2_hexagons.parquet", index=False)
    print("Fig. 3: decile table and bivariate hexagons written")

    # --- Supplementary B: home/work presence by hour and sample representativeness
    users = pd.read_parquet(scratch / "data" / "user_home+work.parquet",
                            columns=["user_id", "YY", "MM", "home_gid9", "work_gid9"])
    users = users[users["home_gid9"].notna() & (users["home_gid9"].astype(str) != "None")]
    boundaries = {
        "helsinki": src / "data" / "Boundary_Helsinki.gpkg",
        "turku": src / "data" / "Turku_region_boundary.geojson",
        "tampere": src / "data" / "Tampere_region_boundary.geojson",
        "oulu": src / "data" / "oulu_region_boundary.geojson",
    }
    study_area = gpd.GeoSeries(
        [gpd.read_file(p).to_crs("EPSG:4326").union_all() for p in boundaries.values()],
        crs="EPSG:4326").union_all()
    hexes = pd.Series(users["home_gid9"].unique())
    pts = gpd.GeoSeries([hex_point(h) for h in hexes], crs="EPSG:4326")
    in_area = set(hexes[pts.within(study_area).values])
    users = users[users["home_gid9"].isin(in_area)].copy()
    user_ids = set(users["user_id"].unique())
    print(f"Suppl. B: {len(user_ids)} users with a home location in the four study areas")

    users["YY"] = pd.to_numeric(users["YY"], errors="coerce")
    users["MM"] = pd.to_numeric(users["MM"], errors="coerce")
    counts = {}
    pf = pq.ParquetFile(scratch / "data" / "stays_sufficient_users.parquet")
    id_array = pd.Series(sorted(user_ids)).values
    for batch in pf.iter_batches(batch_size=4_000_000,
                                 columns=["user_id", "YY", "MM", "DD", "HH", "stay_gid9"]):
        mask = pc.is_in(batch.column("user_id"), value_set=pa.array(id_array, type=batch.column("user_id").type))
        b = batch.filter(mask).to_pandas()
        if b.empty:
            continue
        for c in ["YY", "MM", "DD", "HH"]:
            b[c] = pd.to_numeric(b[c], errors="coerce")
        b = b.merge(users, on=["user_id", "YY", "MM"], how="left")
        date = pd.to_datetime({"year": b["YY"], "month": b["MM"], "day": b["DD"]}, errors="coerce")
        b["day_type"] = np.where(date.dt.dayofweek < 5, "work_day", "non_work_day")
        b["place_type"] = np.select([b["stay_gid9"] == b["home_gid9"], b["stay_gid9"] == b["work_gid9"]],
                                    ["home", "work"], default="other")
        g = b.dropna(subset=["HH"]).groupby(["day_type", "HH", "place_type"]).size()
        for k, v in g.items():
            counts[k] = counts.get(k, 0) + int(v)
    tbl = pd.Series(counts).rename("n_stays").reset_index()
    tbl.columns = ["day_type", "hour", "place_type", "n_stays"]
    tbl["hour"] = tbl["hour"].astype(int)
    wide = tbl.pivot_table(index=["day_type", "hour"], columns="place_type", values="n_stays",
                           fill_value=0).reset_index()
    total = wide[["home", "work", "other"]].sum(axis=1)
    for p in ["home", "work", "other"]:
        wide[f"p_{p}"] = wide[p] / total
    wide = wide.rename(columns={"home": "n_home", "work": "n_work", "other": "n_other"})
    wide.sort_values(["day_type", "hour"]).to_csv(dst / "home_work_hourly_presence.csv", index=False)

    first = users.sort_values(["YY", "MM"]).drop_duplicates("user_id", keep="first")
    home_counts = first.groupby("home_gid9").size().rename("user_count").reset_index()
    hc = gpd.GeoDataFrame(home_counts, geometry=[hex_point(h) for h in home_counts["home_gid9"]],
                          crs="EPSG:4326").to_crs("EPSG:3067")
    grid = gpd.read_file(src / "data" / "1km_data" / "vaki2024_1km.shp", columns=["grd_id", "vaesto"],
                         engine="pyogrio").to_crs("EPSG:3067")
    j = gpd.sjoin(hc, grid[["grd_id", "vaesto", "geometry"]], how="inner", predicate="within")
    cells = (j.groupby("grd_id").agg(users_home_count=("user_count", "sum"), population=("vaesto", "first"))
               .reset_index(drop=True))
    cells = cells[(cells["population"] > 0)].sample(frac=1, random_state=0).reset_index(drop=True)
    cells.to_csv(dst / "population_vs_users_1km.csv", index=False)
    totals = {"census_population_total": int(grid["vaesto"].clip(lower=0).sum()),
              "sample_users_total": int(home_counts["user_count"].sum()),
              "grid_cells_with_users": int(len(cells)), "grid_cells_total": int(len(grid))}
    json.dump(totals, open(dst / "population_vs_users_1km_totals.json", "w"), indent=1)
    print("Suppl. B: hourly presence table and 1 km grid comparison written")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["light", "heavy", "all"], default="all")
    ap.add_argument("--src", required=True, help="working folder with data/ and output/ of the pipeline")
    ap.add_argument("--scratch", required=True, help="folder with the large intermediates")
    ap.add_argument("--dst", default="output", help="destination folder for the shared aggregates")
    a = ap.parse_args()
    src, scratch, dst = Path(a.src), Path(a.scratch), Path(a.dst)
    dst.mkdir(parents=True, exist_ok=True)
    if a.stage in ("light", "all"):
        stage_light(src, scratch, dst)
    if a.stage in ("heavy", "all"):
        stage_heavy(src, scratch, dst)

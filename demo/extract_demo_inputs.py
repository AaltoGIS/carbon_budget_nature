"""
Cut the demo inputs out of the full intermediates of the analysis.

The full CO2e origin-destination tables (tens of millions of pairs per mode,
derived from open routing data) are too large for the repository. The demo
only needs the pairs that the synthetic users travel, so this script:

1. reads the candidate users written by demo/make_demo_users.py;
2. scans the three full OD tables once and keeps the rows whose origin or
   destination is a home or work hexagon of a candidate and whose other end is
   any hexagon a candidate visits;
3. keeps the users for which every leg the pipeline needs
   (home->work, home->stay, work->stay, stay->home) has a routed CO2e value in
   all three modes, and at least MIN_TOURS stays per decent-mobility category;
   the first --n-per-area such users per area form the demo sample;
4. writes the final users table, the OD subsets (same file names and column
   names the notebooks read) and copies the small open-data files
   (POIs and jobs per hexagon, postal code areas) into the demo folder.

Reads ~5 GB of parquet: run it as a batch job (see demo/roihu_extract.sbatch),
never on a login node. Memory stays low because the tables are streamed in
row batches.
"""
import argparse
import json
import shutil
import time
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

TABLES = {
    "pt": dict(src="pt_co2_3000_1.parquet", cols=("from_id", "to_id", "pt_co2_total"),
               out=["pt_co2_3000.parquet", "pt_co2_3000_1.parquet"]),   # notebooks use both names
    "car": dict(src="car_co2_6000.parquet", cols=("Origin_Hexagon_ID", "Destination_Hexagon_ID", "car_co2"),
                out=["car_co2_6000.parquet"]),
    "bike": dict(src="bike_co2_3000.parquet", cols=("from_id", "to_id", "co2_emissions_g"),
                 out=["bike_co2_3000.parquet"]),
}
OPEN_DATA = [
    "pois_per_hex_new_class.parquet",
    "job_distribution_from_census.parquet",
    "helsinki_filter_map.geojson",
    "postal_code/Postinumeroalueet_2024.shp",
    "postal_code/Postinumeroalueet_2024.shx",
    "postal_code/Postinumeroalueet_2024.dbf",
    "postal_code/Postinumeroalueet_2024.prj",
    "postal_code/Postinumeroalueet_2024.cpg",
]
REQUIRED = ["Social, Cultural", "Shopping, Errands", "Recreational, Outdoors"]
MIN_TOURS = 3


def scan(path, cols, anchors, allhex):
    """Stream one OD table and keep rows (from in anchors & to in allhex) | (from in allhex & to in anchors)."""
    pf = pq.ParquetFile(path)
    parts = []
    t0 = time.time()
    for batch in pf.iter_batches(batch_size=2_000_000, columns=list(cols)):
        f, t = batch.column(0), batch.column(1)
        a = pa.array(sorted(anchors), type=f.type)
        h = pa.array(sorted(allhex), type=f.type)
        mask = pc.or_(pc.and_(pc.is_in(f, value_set=a), pc.is_in(t, value_set=h)),
                      pc.and_(pc.is_in(f, value_set=h), pc.is_in(t, value_set=a)))
        sel = batch.filter(mask)
        if sel.num_rows:
            parts.append(sel)
    df = pa.Table.from_batches(parts).to_pandas() if parts else pd.DataFrame(columns=list(cols))
    n_before = len(df)
    df = df.drop_duplicates(subset=list(cols[:2]), keep="first").reset_index(drop=True)
    print(f"  {Path(path).name}: {pf.metadata.num_rows:,} rows scanned in {time.time() - t0:,.0f} s -> "
          f"{len(df):,} kept ({n_before - len(df):,} duplicate pairs dropped)", flush=True)
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidates", default="demo/work/candidates.parquet")
    ap.add_argument("--src-scratch", required=True, help="folder with the full pt_co2_3000_1 / car_co2_6000 / bike_co2_3000 tables")
    ap.add_argument("--src-data", required=True, help="folder with pois_per_hex_new_class, job_distribution_from_census, postal_code/")
    ap.add_argument("--dst", default="demo")
    ap.add_argument("--n-per-area", type=int, default=50)
    args = ap.parse_args()

    dst = Path(args.dst)
    cand = pd.read_parquet(args.candidates)
    meta = pd.read_parquet(Path(args.candidates).with_name(Path(args.candidates).stem + "_meta.parquet"))
    anchors = set(cand["home_gid9"]) | set(cand["work_gid9"])
    allhex = anchors | set(cand["stay_gid9"])
    print(f"candidates: {cand.user_id.nunique()} users, {len(anchors)} home/work hexagons, {len(allhex)} hexagons in total")

    # ---- 1. scan the full tables once
    od = {}
    for mode, spec in TABLES.items():
        od[mode] = scan(Path(args.src_scratch) / spec["src"], spec["cols"], anchors, allhex)
    pairs = {mode: set(zip(df.iloc[:, 0], df.iloc[:, 1])) for mode, df in od.items()}

    def routed(a, b):
        return all((a, b) in p for p in pairs.values())

    # ---- 2. validate users and stays
    pois = pd.read_parquet(Path(args.src_data) / "pois_per_hex_new_class.parquet")
    poi_wide = pois.pivot_table(index="h3_id", columns="category", values="count", aggfunc="sum", fill_value=0)

    keep_rows, chosen, rejected = [], {a: [] for a in meta.area.unique()}, {"no_home_work_leg": 0, "too_few_tours": 0}
    for uid, g in cand.groupby("user_id", sort=False):
        area = meta.loc[meta.user_id == uid, "area"].iloc[0]
        if len(chosen[area]) >= args.n_per_area:
            continue
        home, work = g["home_gid9"].iloc[0], g["work_gid9"].iloc[0]
        if not routed(home, work):
            rejected["no_home_work_leg"] += 1
            continue
        stays = g[(g.is_home == 0) & (g.is_work == 0)]
        valid = stays[[routed(home, s) and routed(work, s) and routed(s, home) for s in stays["stay_gid9"]]]
        cats = poi_wide.reindex(valid["stay_gid9"]).fillna(0)
        if any((cats[c] > 0).sum() < MIN_TOURS for c in REQUIRED):
            rejected["too_few_tours"] += 1
            continue
        chosen[area].append(uid)
        keep_rows.append(pd.concat([g[(g.is_home == 1) | (g.is_work == 1)], valid]))

    users = pd.concat(keep_rows, ignore_index=True)
    short = {a: len(v) for a, v in chosen.items() if len(v) < args.n_per_area}
    print(f"selected: {', '.join(f'{a}: {len(v)}' for a, v in chosen.items())} users; rejected {rejected}")
    if short:
        print(f"WARNING: fewer users than requested in {short}; raise --oversample in make_demo_users.py")

    # ---- 3. restrict the OD subsets to the selected users' hexagons and write
    anchors = set(users["home_gid9"]) | set(users["work_gid9"])
    allhex = anchors | set(users["stay_gid9"])
    (dst / "scratch" / "data").mkdir(parents=True, exist_ok=True)
    (dst / "data" / "postal_code").mkdir(parents=True, exist_ok=True)
    users.to_parquet(dst / "scratch" / "data" / "users_and_stays_3months.parquet", index=False)

    summary = {"n_users": int(users.user_id.nunique()), "n_rows": int(len(users)),
               "n_stays": int(((users.is_home == 0) & (users.is_work == 0)).sum()),
               "users_per_area": {a: len(v) for a, v in chosen.items()}, "rejected": rejected, "od_tables": {}}
    for mode, spec in TABLES.items():
        df = od[mode]
        f, t = df.iloc[:, 0], df.iloc[:, 1]
        sub = df[(f.isin(anchors) & t.isin(allhex)) | (f.isin(allhex) & t.isin(anchors))].reset_index(drop=True)
        for name in spec["out"]:
            sub.to_parquet(dst / "scratch" / name, index=False, compression="zstd")
        size_mb = (dst / "scratch" / spec["out"][0]).stat().st_size / 1e6
        summary["od_tables"][mode] = {"rows": int(len(sub)), "file_mb": round(size_mb, 2),
                                      "median_g_co2e_per_pair": round(float(sub.iloc[:, 2].median()), 1)}
        print(f"  {mode}: {len(sub):,} pairs written, {size_mb:.2f} MB each file")

    # ---- 4. open-data files the notebooks read
    for rel in OPEN_DATA:
        src = Path(args.src_data) / rel
        if src.exists():
            shutil.copy2(src, dst / "data" / rel)
        else:
            print(f"  WARNING: {src} not found, not copied")

    (dst / "work").mkdir(exist_ok=True)
    (dst / "work" / "extract_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

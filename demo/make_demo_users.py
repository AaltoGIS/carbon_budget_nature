"""
Generate SYNTHETIC mobile phone users for the demo.

No Locomizer record is used. Users are drawn from open data only:

* homes   - H3 level-9 hexagons around two Helsinki-region centres
            (Kallio, inner city; Espoonlahti, suburb);
* works   - sampled from the census job distribution per hexagon
            (Statistics Finland, produced by 01_points_of_interest/), with a
            distance-decay from home;
* stays   - sampled from hexagons with points of interest (Overture Maps,
            produced by 01_points_of_interest/), with a distance-decay from
            home, plus a share of stays in hexagons without POIs.

The marginal distributions (stays per user, visit frequencies, home-to-stay
distances) are set to resemble the aggregate statistics of the real sample
reported in the paper; individual rows are random.

Output has exactly the schema produced by 04_mobile_phone_stays/01_stays_*.ipynb
and read by every downstream notebook:

    user_id, stay_gid9, frequency_period, home_gid9, work_gid9, is_home, is_work

Usage (from the repository root; seconds on a laptop):
    python demo/make_demo_users.py --n-per-area 50 --oversample 1.6 \
        --pois data/pois_per_hex_new_class.parquet \
        --jobs data/job_distribution_from_census.parquet \
        --out demo/work/candidates.parquet

The output is a *candidate* set (oversampled). demo/extract_demo_inputs.py keeps
the users whose home-work-stay legs all have a routed CO2e value in the three
modes, and writes the final users table.
"""
import argparse
import uuid
from pathlib import Path

import h3  # h3-py 3.x API (as used in the notebooks)
import numpy as np
import pandas as pd

AREAS = {
    # name: (lat, lon) of the centre; homes are drawn from k_ring(centre, HOME_RING)
    "kallio": (60.1841, 24.9503),
    "espoonlahti": (60.1480, 24.6550),
}
HOME_RING = 2
REQUIRED = ["Social, Cultural", "Shopping, Errands", "Recreational, Outdoors"]
MIN_STAYS_PER_REQUIRED = 4     # tours need >= 3 valid tours per category; keep a margin
MAX_STAY_KM = 15.0
STAY_DECAY_KM = 4.0
WORK_DECAY_KM = 8.0
MAX_WORK_KM = 25.0
SHARE_NON_POI_STAYS = 0.25     # real sample: ~28 % of non-home/work stays are in hexagons without POIs

STAY_FREQ = ([1, 2, 3, 4, 6, 10, 15], [0.55, 0.20, 0.10, 0.06, 0.05, 0.03, 0.01])
WORK_FREQ = ([1, 2, 3, 4, 5, 7, 10], [0.20, 0.18, 0.18, 0.14, 0.12, 0.10, 0.08])


def km(h1, h2):
    return h3.point_dist(h3.h3_to_geo(h1), h3.h3_to_geo(h2), unit="km")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-per-area", type=int, default=50)
    ap.add_argument("--oversample", type=float, default=1.6, help="candidates = n_per_area * oversample")
    ap.add_argument("--seed", type=int, default=20240415)
    ap.add_argument("--pois", default="data/pois_per_hex_new_class.parquet")
    ap.add_argument("--jobs", default="data/job_distribution_from_census.parquet")
    ap.add_argument("--out", default="demo/work/candidates.parquet")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)

    pois = pd.read_parquet(args.pois)
    poi_wide = pois.pivot_table(index="h3_id", columns="category", values="count", aggfunc="sum", fill_value=0)
    poi_wide["total"] = poi_wide.sum(axis=1)
    poi_hexes = poi_wide.index.to_numpy()

    jobs = pd.read_parquet(args.jobs)
    if "ID" not in jobs.columns:
        jobs = jobs.reset_index()
    jobs = jobs[["ID", "weighted_tyo"]].dropna()
    jobs = jobs[jobs["weighted_tyo"] > 0]
    job_hexes = jobs["ID"].to_numpy()
    job_w = jobs["weighted_tyo"].to_numpy()
    job_set = set(job_hexes)

    n_cand = int(np.ceil(args.n_per_area * args.oversample))
    rows, meta = [], []

    for area, (lat, lon) in AREAS.items():
        centre = h3.geo_to_h3(lat, lon, 9)
        ring = sorted(h for h in h3.k_ring(centre, HOME_RING) if h in job_set)
        if not ring:
            raise SystemExit(f"no urban hexagons around {area}")
        # precompute distances from the area centre once; per-user distances use the home hexagon
        for _ in range(n_cand):
            user_id = str(uuid.UUID(int=int(rng.integers(0, 2**63)) << 64 | int(rng.integers(0, 2**63)), version=4))
            home = ring[rng.integers(len(ring))]

            # ---- work: job-weighted, distance-decayed, not home, 0.3-25 km
            d_jobs = np.array([km(home, h) for h in job_hexes])
            ok = (d_jobs > 0.3) & (d_jobs <= MAX_WORK_KM)
            p = job_w * np.exp(-d_jobs / WORK_DECAY_KM) * ok
            work = str(rng.choice(job_hexes, p=p / p.sum()))

            # ---- number of stays: lognormal with median 9, p90 ~24 (real sample), clipped
            n_stays = int(np.clip(np.round(np.exp(rng.normal(np.log(9), 0.765))), 6, 40))
            n_non_poi = int(np.round(n_stays * SHARE_NON_POI_STAYS))
            n_poi = n_stays - n_non_poi

            # ---- POI stays: weight ~ sqrt(1 + n_pois) * exp(-d / 4 km), within 15 km, unique
            d_poi = np.array([km(home, h) for h in poi_hexes])
            ok = (d_poi <= MAX_STAY_KM) & (poi_hexes != home) & (poi_hexes != work)
            w = np.sqrt(1 + poi_wide["total"].to_numpy()) * np.exp(-d_poi / STAY_DECAY_KM) * ok
            chosen = list(rng.choice(poi_hexes, size=min(n_poi, int(ok.sum())), replace=False, p=w / w.sum()))

            # make sure every required category is visited often enough for the tour builder
            for cat in REQUIRED:
                have = int((poi_wide.loc[chosen, cat] > 0).sum()) if chosen else 0
                need = MIN_STAYS_PER_REQUIRED - have
                if need > 0:
                    cand_ok = ok & (poi_wide[cat].to_numpy() > 0) & ~np.isin(poi_hexes, chosen)
                    wc = w * cand_ok
                    extra = rng.choice(poi_hexes, size=min(need, int(cand_ok.sum())), replace=False, p=wc / wc.sum())
                    chosen.extend(extra.tolist())

            # ---- non-POI stays: job hexagons without POIs, distance-decayed
            ok_np = (~np.isin(job_hexes, poi_hexes)) & (d_jobs <= MAX_STAY_KM) & (job_hexes != home) & (job_hexes != work)
            wn = np.exp(-d_jobs / STAY_DECAY_KM) * ok_np
            non_poi = rng.choice(job_hexes, size=min(n_non_poi, int(ok_np.sum())), replace=False, p=wn / wn.sum())

            stays = [str(h) for h in chosen] + [str(h) for h in non_poi]
            freq = rng.choice(STAY_FREQ[0], size=len(stays), p=STAY_FREQ[1])

            rows.append((user_id, home, int(np.clip(np.round(rng.normal(11, 6)), 2, 40)), home, work, 1, 0))
            rows.append((user_id, work, int(rng.choice(WORK_FREQ[0], p=WORK_FREQ[1])), home, work, 0, 1))
            rows.extend((user_id, s, int(f), home, work, 0, 0) for s, f in zip(stays, freq))
            meta.append((user_id, area))

    users = pd.DataFrame(rows, columns=["user_id", "stay_gid9", "frequency_period", "home_gid9", "work_gid9", "is_home", "is_work"])
    users = users.astype({"frequency_period": "int64", "is_home": "int64", "is_work": "int64"})
    meta = pd.DataFrame(meta, columns=["user_id", "area"])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    users.to_parquet(out, index=False)
    meta.to_parquet(out.with_name(out.stem + "_meta.parquet"), index=False)

    g = users.groupby("user_id").size()
    print(f"candidates: {len(meta)} users ({', '.join(f'{a}: {n}' for a, n in meta.area.value_counts().items())}), "
          f"{len(users)} rows; stays/user median {g.median():.0f}, p90 {g.quantile(.9):.0f}")
    print(f"written: {out} and {out.with_name(out.stem + '_meta.parquet')}")


if __name__ == "__main__":
    main()

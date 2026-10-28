"""
Execute the Helsinki notebooks on the demo data, without modifying them.

Every notebook addresses its inputs and outputs with paths relative to the
working directory (data/, scratch/, output/). Running the unchanged notebooks
with demo/ as the working directory therefore makes them read the synthetic
users and the open-data subsets in demo/ and write their results to
demo/data, demo/scratch and demo/output.

Usage (from the repository root):
    python demo/run_demo.py                 # the seven Helsinki notebooks of stages 04-05
    python demo/run_demo.py --save-executed # also keep the executed notebooks (with outputs)
    python demo/run_demo.py NOTEBOOK ...    # a subset, paths relative to the repository root

Cells that raise are recorded, not fatal: the run continues and a report with
per-notebook wall time and the list of failing cells is written to
demo/output/run_report.md (and .json). The exit code is 1 if any cell failed.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

DEFAULT_NOTEBOOKS = [
    "04_mobile_phone_stays/user_pois_pt_helsinki.ipynb",
    "04_mobile_phone_stays/user_pois_car_helsinki.ipynb",
    "04_mobile_phone_stays/user_pois_bike_helsinki.ipynb",
    "05_carbon_cost_of_decent_mobility/exposure_curves/exposure_pt_helsinki.ipynb",
    "05_carbon_cost_of_decent_mobility/exposure_curves/exposure_car_helsinki.ipynb",
    "05_carbon_cost_of_decent_mobility/exposure_curves/exposure_bike_helsinki.ipynb",
    "05_carbon_cost_of_decent_mobility/tours/decent_mobility_tours_helsinki.ipynb",
]


def run_one(nb_path, cwd, kernel, timeout, save_dir, label=None):
    nb = nbformat.read(nb_path, as_version=4)
    client = NotebookClient(nb, timeout=timeout, kernel_name=kernel, allow_errors=True,
                            resources={"metadata": {"path": str(cwd)}})
    t0 = time.time()
    client.execute()
    elapsed = time.time() - t0

    errors = []
    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    for i, cell in enumerate(code_cells):
        for out in cell.get("outputs", []):
            if out.get("output_type") == "error":
                first = next((l.strip() for l in cell.source.splitlines() if l.strip() and not l.strip().startswith("#")), "")
                errors.append({"cell": i, "ename": out.get("ename"), "evalue": str(out.get("evalue"))[:200], "code": first[:100]})
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        nbformat.write(nb, save_dir / Path(nb_path).name)
    return {"notebook": label or str(nb_path), "seconds": round(elapsed, 1), "n_code_cells": len(code_cells), "errors": errors}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notebooks", nargs="*", default=DEFAULT_NOTEBOOKS)
    ap.add_argument("--repo-root", default=Path(__file__).resolve().parents[1])
    ap.add_argument("--cwd", default=None, help="working directory for the kernels (default: the demo folder)")
    ap.add_argument("--kernel", default="python3")
    ap.add_argument("--timeout", type=int, default=1800, help="per-cell timeout in seconds")
    ap.add_argument("--save-executed", action="store_true", help="write executed notebooks to <cwd>/output/executed/")
    args = ap.parse_args()

    root = Path(args.repo_root).resolve()
    cwd = Path(args.cwd).resolve() if args.cwd else Path(__file__).resolve().parent
    (cwd / "output").mkdir(exist_ok=True)
    (cwd / "scratch").mkdir(exist_ok=True)

    # the kernels inherit this environment
    os.environ.setdefault("MPLBACKEND", "Agg")                     # no display needed
    os.environ["PYTHONPATH"] = f"{root}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"  # `import basemaps`

    results = []
    t_all = time.time()
    for nb in args.notebooks:
        nb_path = (root / nb) if not Path(nb).is_absolute() else Path(nb)
        print(f"-> {nb}", flush=True)
        res = run_one(nb_path, cwd, args.kernel, args.timeout,
                      (cwd / "output" / "executed") if args.save_executed else None, label=str(nb))
        status = "ok" if not res["errors"] else f"{len(res['errors'])} failing cell(s)"
        print(f"   {res['seconds']:7.1f} s  {status}", flush=True)
        for e in res["errors"]:
            print(f"     cell {e['cell']:3d}: {e['ename']}: {e['evalue'][:90]}  <- {e['code']}", flush=True)
        results.append(res)
    total = time.time() - t_all

    report = {"total_seconds": round(total, 1), "python": sys.version.split()[0], "notebooks": results}
    (cwd / "output" / "run_report.json").write_text(json.dumps(report, indent=2))
    lines = [f"# Demo run report\n", f"Total wall time: {total / 60:.1f} min (Python {report['python']})\n",
             "| Notebook | Code cells | Seconds | Failing cells |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['notebook']} | {r['n_code_cells']} | {r['seconds']} | "
                     + ("none" if not r["errors"] else "; ".join(f"{e['cell']} ({e['ename']})" for e in r["errors"])) + " |")
    (cwd / "output" / "run_report.md").write_text("\n".join(lines) + "\n")
    print(f"\ntotal {total / 60:.1f} min; report: {cwd / 'output' / 'run_report.md'}")
    sys.exit(1 if any(r["errors"] for r in results) else 0)


if __name__ == "__main__":
    main()

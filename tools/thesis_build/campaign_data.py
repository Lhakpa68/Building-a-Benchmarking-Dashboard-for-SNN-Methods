"""Read the single measurement campaign out of the results database.

One machine, one campaign. Every figure and table in Chapter 4 is generated
from this module so that the document and the released dashboard cannot report
different numbers for the same condition.
"""
from __future__ import annotations

import sqlite3
import sys

import os
os.environ.setdefault("SNN_RESULTS_DIR", "/root/work/cpu/final/results")
sys.path.insert(0, "/root/work/cpu/final/dashboard")
import dashboard_config as C          # noqa: E402
import dashboard_data as dd           # noqa: E402

LABEL = {"brian2": "Brian2", "nest": "NEST", "snntorch": "snnTorch",
         "spikingjelly": "SpikingJelly", "nengo": "Nengo",
         "reference": "NumPy control"}
BACKEND = {"cpp_standalone": "C++ standalone", "cython": "Cython",
           "numpy": "NumPy", "threads1": "1 thread", "threads2": "2 threads", "threads4": "4 threads",
           "reference": "reference", "cpu": "CPU", "scalar": "scalar",
           "vectorised": "vectorised"}


def name(fw, bk):
    return f"{LABEL.get(fw, fw)} / {BACKEND.get(bk, bk)}"


def _db():
    db = sqlite3.connect(str(C.DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def campaign_machine(db):
    return db.execute("SELECT machine_id FROM conditions GROUP BY machine_id "
                      "ORDER BY COUNT(*) DESC LIMIT 1").fetchone()[0]


def conditions():
    """The canonical condition record per key - exactly the rows the dashboard
    serves (dashboard_data._LATEST: CPU-corrected session for inference and
    scalability, the two training campaigns for training) - each carrying the
    individual runs behind it."""
    db = _db()
    rows = db.execute(f"SELECT * FROM ({dd._LATEST})").fetchall()
    out = []
    for c in rows:
        rs = db.execute(
            "SELECT runtime_s, peak_rss_mb, cpu_pct, energy_j FROM runs "
            "WHERE run_group=? AND framework=? AND backend=? AND task=? "
            "AND network_size=? AND phase=? ORDER BY run_index",
            (c["run_group"], c["framework"], c["backend"], c["task"],
             c["network_size"], c["phase"])).fetchall()
        d = dict(c)
        d["runs"] = [r["runtime_s"] for r in rs]
        out.append(d)
    return out


# ── the statistics Chapter 4 quotes ───────────────────────────────────────
def kruskal_wallis(groups):
    """H, N, k. Ties get mid-ranks; no correction is applied and none is
    needed here, because the measured values are continuous and distinct."""
    flat = sorted((v, gi) for gi, g in enumerate(groups) for v in g)
    ranks, i = {}, 0
    while i < len(flat):
        j = i
        while j + 1 < len(flat) and flat[j + 1][0] == flat[i][0]:
            j += 1
        mid = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = mid
        i = j + 1
    n = len(flat)
    h = 0.0
    for gi, g in enumerate(groups):
        rs = [ranks[k] for k, (_v, gg) in enumerate(flat) if gg == gi]
        h += len(rs) * ((sum(rs) / len(rs)) - (n + 1) / 2) ** 2
    return 12 / (n * (n + 1)) * h, n, len(groups)


def cliffs_delta(a, b):
    """Non-parametric effect size: the probability that a random draw from a
    exceeds one from b, minus the reverse. Exact at these sample sizes."""
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b))


def inference():
    rows = [c for c in conditions()
            if c["task"] == "inference" and c["phase"] == "simulate"]
    setup = {(c["framework"], c["backend"]): c["runtime_median_s"]
             for c in conditions()
             if c["task"] == "inference" and c["phase"] == "setup"}
    worst = max(c["energy_median_j"] or 0 for c in rows
                if not c["compile_dominated"])
    for c in rows:
        c["setup_s"] = setup.get((c["framework"], c["backend"]))
        c["energy_index"] = (100 * (c["energy_median_j"] or 0) / worst
                             if worst else None)
        c["id"] = name(c["framework"], c["backend"])
    return sorted(rows, key=lambda c: c["runtime_median_s"])


def scalability():
    series = {}
    for c in conditions():
        if c["task"] != "scalability" or c["phase"] != "simulate":
            continue
        key = (c["framework"], c["backend"])
        series.setdefault(key, {})[c["network_size"]] = c
    out = []
    for (fw, bk), by_n in series.items():
        pts = sorted(by_n.items())
        fit = dd.fit_scaling([n for n, _ in pts],
                             [c["runtime_median_s"] for _, c in pts])
        out.append(dict(id=name(fw, bk), framework=fw, backend=bk,
                        points=pts, fit=fit))
    return sorted(out, key=lambda s: -(s["fit"]["k"] if s["fit"] else -9))


def summary():
    meta = dd.get_meta()
    return dict(conditions=meta["counts"]["conditions"],
                runs=meta["counts"]["runs"],
                backends=meta["counts"]["backends"],
                excluded=meta["excluded"],
                machine=meta["machine"],
                sizes=meta["sizes"])


if __name__ == "__main__":
    s = summary()
    print(s["conditions"], "conditions,", s["runs"], "runs,",
          s["backends"], "backends;", s["excluded"], "excluded")
    inf = inference()
    h, n, k = kruskal_wallis([c["runs"] for c in inf])
    print(f"Kruskal-Wallis H={h:.1f}, N={n}, k={k}, df={k - 1}")
    for c in inf:
        print(f"  {c['id']:28} {c['runtime_median_s'] * 1000:9.3f} ms  "
              f"n={len(c['runs'])}  cv={c['cv_pct']:.2f}")

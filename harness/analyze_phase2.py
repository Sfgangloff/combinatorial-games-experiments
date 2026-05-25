"""Phase-2 analysis: search-complexity × toolset cost-ratio surface + G-CD checks.

Loads solved trials for the three anchor puzzles, ordered by formal search
complexity (search_nodes from `core.generator.grade`):

  - puzzle_001    (5×5)  search_nodes ≈ 96
  - puzzle_002    (7×7)  search_nodes ≈ 501
  - gen_7x7_s1_00 (7×7)  search_nodes ≈ 4547

All three are formally tier-3 by the propagation/+1-ply/search grader
(`core.generator.grade`); they differ in search complexity by ≈47× and
function as low/mid/high complexity anchors for the cost-ratio surface.

Produces:
  - per-puzzle summary tables (n, cost μ ± σ, calls μ ± σ)
  - cost ratios vs `none` with 1σ overlap flag
  - G-CD prediction checks (P1', P2', P3', P4 ; plus the pre-committed
    monotone P3 from G-CD-v1 for transparency)
  - optional figures F1 (cost vs log search_nodes) and F2 (calls vs cost)

CLI:
    python -m harness.analyze_phase2                      # tables only
    python -m harness.analyze_phase2 --figures            # + write paper/figures/*.png
    python -m harness.analyze_phase2 --meta off           # meta filter (default off)
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "harness" / "results"
FIGURES = REPO / "paper" / "figures"

TOOLSETS = ["none", "fine", "medium", "coarse"]

# Anchor puzzles for the cost-ratio surface, ordered by search complexity.
# search_nodes values come from `core.generator.grade()` ; the integer index
# `i` is just an ordering used internally for stable dict keys.
ANCHORS = [
    {"i": 1, "puzzle_id": "puzzle_001",    "search_nodes":   96,
     "grid": "5×5", "label": "low (96 nodes)"},
    {"i": 2, "puzzle_id": "puzzle_002",    "search_nodes":  501,
     "grid": "7×7", "label": "mid (501 nodes)"},
    {"i": 3, "puzzle_id": "gen_7x7_s1_00", "search_nodes": 4547,
     "grid": "7×7", "label": "high (4547 nodes)"},
]
# Backwards compatibility: TIERS used to enumerate (i, puzzle_id, label).
TIERS = [(a["i"], a["puzzle_id"], a["label"]) for a in ANCHORS]


def _cost(record: dict) -> float | None:
    for m in record["messages"]:
        if m.get("role") == "result":
            return m.get("total_cost_usd")
    return None


def _load_trials(puzzle_id: str, toolset: str, meta: str) -> list[dict]:
    pattern = f"*_{puzzle_id}_toolset-{toolset}_meta-{meta}.json"
    out: list[dict] = []
    for path in sorted(glob.glob(str(RESULTS / pattern))):
        with open(path) as f:
            r = json.load(f)
        if not r["outcome"]["solved"]:
            continue
        cost = _cost(r)
        if cost is None:
            continue
        out.append({
            "file": os.path.basename(path),
            "calls": r["outcome"]["tool_call_count"],
            "time": r["elapsed_seconds"],
            "cost": cost,
        })
    return out


def _stats(values: list[float]) -> tuple[float, float]:
    if not values:
        return float("nan"), float("nan")
    m = statistics.mean(values)
    s = statistics.stdev(values) if len(values) > 1 else 0.0
    return m, s


def _intervals_overlap(a_mean: float, a_sd: float, b_mean: float, b_sd: float) -> bool:
    lo_a, hi_a = a_mean - a_sd, a_mean + a_sd
    lo_b, hi_b = b_mean - b_sd, b_mean + b_sd
    return not (hi_a < lo_b or hi_b < lo_a)


def collect(meta: str) -> dict[int, dict[str, dict]]:
    """anchor_index -> toolset -> {n, cost_mean, cost_sd, calls_mean, calls_sd, trials}."""
    out: dict[int, dict[str, dict]] = {}
    for a in ANCHORS:
        adata: dict[str, dict] = {}
        for ts in TOOLSETS:
            trials = _load_trials(a["puzzle_id"], ts, meta)
            costs = [t["cost"] for t in trials]
            calls = [t["calls"] for t in trials]
            cm, cs = _stats(costs)
            km, ks = _stats(calls)
            adata[ts] = {
                "n": len(trials),
                "cost_mean": cm, "cost_sd": cs,
                "calls_mean": km, "calls_sd": ks,
                "trials": trials,
            }
        out[a["i"]] = adata
    return out


def print_tables(data: dict[int, dict[str, dict]]) -> None:
    for a in ANCHORS:
        td = data[a["i"]]
        print(f"\n=== {a['puzzle_id']} ({a['grid']}, search_nodes={a['search_nodes']}, {a['label']}) ===\n")
        print(f"{'toolset':<8} {'n':>2}   "
              f"{'cost μ ± σ':<18} {'calls μ ± σ':<16}")
        print("-" * 50)
        for ts in TOOLSETS:
            d = td[ts]
            if d["n"] == 0:
                print(f"{ts:<8} {d['n']:>2}   (no solved trials)")
                continue
            cs = f"${d['cost_mean']:.2f} ± ${d['cost_sd']:.2f}"
            ks = f"{d['calls_mean']:.1f} ± {d['calls_sd']:.1f}"
            print(f"{ts:<8} {d['n']:>2}   {cs:<18} {ks:<16}")
        # ratios + overlap
        ref = td["none"]
        if ref["n"] == 0:
            continue
        print(f"\n  Cost ratios vs none:")
        for ts in TOOLSETS:
            if ts == "none":
                continue
            d = td[ts]
            if d["n"] == 0:
                continue
            r = d["cost_mean"] / ref["cost_mean"] if ref["cost_mean"] else float("nan")
            overlap = _intervals_overlap(
                d["cost_mean"], d["cost_sd"], ref["cost_mean"], ref["cost_sd"]
            )
            tag = "overlaps" if overlap else "SEPARATED"
            print(f"    {ts:<7} {r:.2f}×  ({tag} 1σ)")


def gcd_predictions(data: dict[int, dict[str, dict]]) -> None:
    """G-CD predictions P1'-P4 evaluated against data (low/mid/high search complexity)."""
    print("\n\n=== G-CD prediction checks ===\n")

    def ratio(idx: int, ts_num: str, ts_den: str) -> tuple[float, bool]:
        d_num = data[idx][ts_num]
        d_den = data[idx][ts_den]
        if d_num["n"] == 0 or d_den["n"] == 0:
            return float("nan"), False
        r = d_num["cost_mean"] / d_den["cost_mean"]
        sep = not _intervals_overlap(
            d_num["cost_mean"], d_num["cost_sd"],
            d_den["cost_mean"], d_den["cost_sd"],
        )
        return r, sep

    # P1': low-complexity ratios collapse to ~1 (all 1σ-overlap with none).
    lo = data[1]
    overlaps = []
    for ts in TOOLSETS:
        if ts == "none" or lo[ts]["n"] == 0:
            continue
        overlaps.append(_intervals_overlap(
            lo[ts]["cost_mean"], lo[ts]["cost_sd"],
            lo["none"]["cost_mean"], lo["none"]["cost_sd"],
        ))
    p1_pass = all(overlaps) if overlaps else False
    print(f"P1' (low-complexity ratios collapse to ≈1): "
          f"{'PASS' if p1_pass else 'FAIL'}  "
          f"({sum(overlaps)}/{len(overlaps)} toolsets 1σ-overlap with none)")

    # P2': mid-complexity coarse < none with separated 1σ.
    r2, sep2 = ratio(2, "coarse", "none")
    p2_pass = sep2 and r2 < 1.0
    print(f"P2' (mid-complexity coarse/none < 1, separated): "
          f"{'PASS' if p2_pass else 'FAIL'}  "
          f"(ratio={r2:.2f}×, separated={sep2})")

    # P3 (G-CD-v1, monotone, pre-committed): high-complexity coarse/none
    # ratio ≤ mid-complexity ratio.
    r3, sep3 = ratio(3, "coarse", "none")
    p3_pass = not math.isnan(r2) and not math.isnan(r3) and r3 <= r2 and sep3
    print(f"P3  (G-CD-v1 monotone, hi-cx ratio ≤ mid-cx ratio, separated): "
          f"{'PASS' if p3_pass else 'FAIL'}  "
          f"(mid ratio={r2:.2f}×, hi ratio={r3:.2f}×, "
          f"hi separated={sep3})")
    if not p3_pass and not math.isnan(r3):
        if r3 > r2:
            print(f"    ↳ P3 falsified: hi-complexity ratio LARGER than mid — "
                  f"Goldilocks shape (granularity advantage shrinks at hi-cx).")
        elif not sep3:
            print(f"    ↳ P3 partial: ratio direction OK but hi-cx 1σ CIs overlap — "
                  f"signal collapses at hi-cx without inverting.")

    # P3' (G-CD-v2, Goldilocks): high-complexity ratios collapse back toward 1,
    # mirroring low-complexity (all toolset 1σ CIs overlap with `none`).
    hi = data[3]
    if hi["none"]["n"] > 0:
        hi_overlaps = []
        for ts in TOOLSETS:
            if ts == "none" or hi[ts]["n"] == 0:
                continue
            hi_overlaps.append(_intervals_overlap(
                hi[ts]["cost_mean"], hi[ts]["cost_sd"],
                hi["none"]["cost_mean"], hi["none"]["cost_sd"],
            ))
        p3prime_pass = all(hi_overlaps) if hi_overlaps else False
        print(f"P3' (G-CD-v2, hi-complexity ratios re-collapse to ≈1): "
              f"{'PASS' if p3prime_pass else 'FAIL'}  "
              f"({sum(hi_overlaps)}/{len(hi_overlaps)} toolsets 1σ-overlap with none)")

    # P4: calls/cost decoupling — within mid-complexity, per-call cost varies
    # by >10× across granularities despite cost varying <2×.
    print(f"\nP4 (cost-per-call by toolset, mid-complexity / puzzle_002):")
    mid = data[2]
    for ts in TOOLSETS:
        d = mid[ts]
        if d["n"] == 0 or d["calls_mean"] == 0:
            continue
        cpc = d["cost_mean"] / d["calls_mean"]
        print(f"  {ts:<7}  {d['calls_mean']:>5.1f} calls  "
              f"${d['cost_mean']:.2f}  ⇒ ${cpc:.4f}/call")
    print(f"  ↳ if `fine` cost/call ≪ `none` cost/call, the decoupling holds.")


def write_figures(data: dict[int, dict[str, dict]]) -> None:
    import matplotlib.pyplot as plt

    FIGURES.mkdir(parents=True, exist_ok=True)
    xs_nodes = [a["search_nodes"] for a in ANCHORS]
    xs_labels = [f"{a['puzzle_id']}\n({a['search_nodes']:,} nodes)" for a in ANCHORS]
    idx_for_anchor = {a["i"]: a for a in ANCHORS}
    colors = {"none": "#444", "fine": "#d62728", "medium": "#1f77b4", "coarse": "#2ca02c"}
    markers = {"none": "o", "fine": "s", "medium": "^", "coarse": "D"}

    # F1: cost μ ± σ per toolset, x-axis = log10(search_nodes).
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for ts in TOOLSETS:
        xs, ys, es = [], [], []
        for a in ANCHORS:
            d = data[a["i"]][ts]
            if d["n"] == 0:
                continue
            xs.append(a["search_nodes"])
            ys.append(d["cost_mean"])
            es.append(d["cost_sd"])
        if not xs:
            continue
        ax.errorbar(xs, ys, yerr=es, marker=markers[ts], color=colors[ts],
                    label=ts, capsize=3, linewidth=1.2, markersize=6)
    ax.set_xscale("log")
    ax.set_xticks(xs_nodes)
    ax.set_xticklabels(xs_labels, fontsize=9)
    ax.set_xlabel("Search complexity (search_nodes from formal grader, log scale)")
    ax.set_ylabel("Cost per solved trial (USD)")
    ax.set_title("Cost vs search complexity, by toolset (μ ± 1σ)")
    ax.legend(title="toolset", loc="best")
    ax.grid(True, which="both", alpha=0.3)
    f1 = FIGURES / "f1_cost_by_complexity.png"
    fig.tight_layout()
    fig.savefig(f1, dpi=160)
    plt.close(fig)
    print(f"  wrote {f1.relative_to(REPO)}")

    # F1b: ratio vs `none` per toolset, x-axis = log10(search_nodes).
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for ts in TOOLSETS:
        if ts == "none":
            continue
        xs, ys = [], []
        for a in ANCHORS:
            d = data[a["i"]][ts]
            ref = data[a["i"]]["none"]
            if d["n"] == 0 or ref["n"] == 0 or not ref["cost_mean"]:
                continue
            xs.append(a["search_nodes"])
            ys.append(d["cost_mean"] / ref["cost_mean"])
        if not xs:
            continue
        ax.plot(xs, ys, marker=markers[ts], color=colors[ts],
                label=ts, linewidth=1.4, markersize=7)
    ax.axhline(1.0, color="#888", linestyle="--", linewidth=0.8)
    ax.set_xscale("log")
    ax.set_xticks(xs_nodes)
    ax.set_xticklabels(xs_labels, fontsize=9)
    ax.set_xlabel("Search complexity (search_nodes, log scale)")
    ax.set_ylabel("Cost ratio vs `none` toolset")
    ax.set_title("Cost-ratio surface across search complexity (V-shape)")
    ax.legend(title="toolset", loc="best")
    ax.grid(True, which="both", alpha=0.3)
    f1b = FIGURES / "f1b_cost_ratio_by_complexity.png"
    fig.tight_layout()
    fig.savefig(f1b, dpi=160)
    plt.close(fig)
    print(f"  wrote {f1b.relative_to(REPO)}")

    # F2: calls vs cost scatter — load-bearing P4 figure (unchanged axes).
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for ts in TOOLSETS:
        xs, ys = [], []
        for a in ANCHORS:
            for t in data[a["i"]][ts]["trials"]:
                xs.append(t["calls"])
                ys.append(t["cost"])
        if xs:
            ax.scatter(xs, ys, marker=markers[ts], color=colors[ts],
                       label=ts, s=42, alpha=0.85, edgecolor="white", linewidth=0.6)
    ax.set_xscale("log")
    ax.set_xlabel("Tool calls per solved trial (log scale)")
    ax.set_ylabel("Cost per solved trial (USD)")
    ax.set_title("Calls vs cost: P4 decoupling (all three puzzles pooled)")
    ax.legend(title="toolset", loc="best")
    ax.grid(True, which="both", alpha=0.3)
    f2 = FIGURES / "f2_calls_vs_cost.png"
    fig.tight_layout()
    fig.savefig(f2, dpi=160)
    plt.close(fig)
    print(f"  wrote {f2.relative_to(REPO)}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--meta", choices=["off", "on"], default="off")
    p.add_argument("--figures", action="store_true",
                   help=f"also write figures into {FIGURES.relative_to(REPO)}/")
    args = p.parse_args()

    data = collect(args.meta)
    print_tables(data)
    gcd_predictions(data)

    if args.figures:
        print("\nWriting figures...")
        write_figures(data)


if __name__ == "__main__":
    main()

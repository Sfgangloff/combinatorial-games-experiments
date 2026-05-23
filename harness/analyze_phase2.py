"""Phase-2 analysis: tier × toolset cost-ratio surface + G-CD prediction tests.

Loads solved trials for the three anchor puzzles (tier-1: puzzle_001, tier-2:
puzzle_002, tier-3: gen_7x7_s1_00) and produces:

  - a tier × toolset summary table (n, cost μ ± σ, calls μ ± σ)
  - cost ratios vs `coarse` and vs `none` per tier, with 1σ overlap flag
  - G-CD prediction checks (P1, P2, P3, P4)
  - optional figures F1 (cost-ratio surface) and F2 (calls vs cost scatter)

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

# Anchor puzzles for the cost-ratio surface. (tier, puzzle_id, label).
TIERS = [
    (1, "puzzle_001", "tier-1 / 5×5 easy"),
    (2, "puzzle_002", "tier-2 / 7×7 hard"),
    (3, "gen_7x7_s1_00", "tier-3 / 7×7 generated"),
]


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
    """tier -> toolset -> {n, cost_mean, cost_sd, calls_mean, calls_sd, trials}."""
    out: dict[int, dict[str, dict]] = {}
    for tier, pid, _label in TIERS:
        tdata: dict[str, dict] = {}
        for ts in TOOLSETS:
            trials = _load_trials(pid, ts, meta)
            costs = [t["cost"] for t in trials]
            calls = [t["calls"] for t in trials]
            cm, cs = _stats(costs)
            km, ks = _stats(calls)
            tdata[ts] = {
                "n": len(trials),
                "cost_mean": cm, "cost_sd": cs,
                "calls_mean": km, "calls_sd": ks,
                "trials": trials,
            }
        out[tier] = tdata
    return out


def print_tables(data: dict[int, dict[str, dict]]) -> None:
    for tier, pid, label in TIERS:
        td = data[tier]
        print(f"\n=== Tier {tier}: {pid} ({label}) ===\n")
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
    """G-CD predictions P1-P4 from the design note, evaluated against data."""
    print("\n\n=== G-CD prediction checks ===\n")

    def ratio(tier: int, ts_num: str, ts_den: str) -> tuple[float, bool]:
        d_num = data[tier][ts_num]
        d_den = data[tier][ts_den]
        if d_num["n"] == 0 or d_den["n"] == 0:
            return float("nan"), False
        r = d_num["cost_mean"] / d_den["cost_mean"]
        sep = not _intervals_overlap(
            d_num["cost_mean"], d_num["cost_sd"],
            d_den["cost_mean"], d_den["cost_sd"],
        )
        return r, sep

    # P1: tier-1 ratios collapse to ~1 (all 1σ-overlap with none).
    t1 = data[1]
    overlaps = []
    for ts in TOOLSETS:
        if ts == "none" or t1[ts]["n"] == 0:
            continue
        overlaps.append(_intervals_overlap(
            t1[ts]["cost_mean"], t1[ts]["cost_sd"],
            t1["none"]["cost_mean"], t1["none"]["cost_sd"],
        ))
    p1_pass = all(overlaps) if overlaps else False
    print(f"P1 (tier-1 ratios collapse to ≈1): "
          f"{'PASS' if p1_pass else 'FAIL'}  "
          f"({sum(overlaps)}/{len(overlaps)} toolsets 1σ-overlap with none)")

    # P2: tier-2 coarse < none with separated 1σ, ratio < 1.
    r2, sep2 = ratio(2, "coarse", "none")
    p2_pass = sep2 and r2 < 1.0
    print(f"P2 (tier-2 coarse/none < 1, separated): "
          f"{'PASS' if p2_pass else 'FAIL'}  "
          f"(ratio={r2:.2f}×, separated={sep2})")

    # P3: tier-3 coarse/none ratio ≤ tier-2 coarse/none ratio.
    r3, sep3 = ratio(3, "coarse", "none")
    p3_pass = not math.isnan(r2) and not math.isnan(r3) and r3 <= r2 and sep3
    print(f"P3 (tier-3 coarse/none ≤ tier-2 coarse/none, still separated): "
          f"{'PASS' if p3_pass else 'FAIL'}  "
          f"(tier-2 ratio={r2:.2f}×, tier-3 ratio={r3:.2f}×, "
          f"tier-3 separated={sep3})")
    if not p3_pass and not math.isnan(r3):
        if r3 > r2:
            print(f"    ↳ P3 falsified: tier-3 ratio LARGER than tier-2 — "
                  f"granularity advantage shrinks with difficulty (Goldilocks).")
        elif not sep3:
            print(f"    ↳ P3 partial: ratio direction OK but tier-3 1σ CIs overlap — "
                  f"signal collapses at tier-3 without inverting.")

    # P4: calls/cost decoupling — within a tier, does cost scale sub-linearly
    #     with calls across toolsets? Use the tier-2 numbers (most informative).
    print(f"\nP4 (cost-per-call by toolset, tier-2):")
    t2 = data[2]
    for ts in TOOLSETS:
        d = t2[ts]
        if d["n"] == 0 or d["calls_mean"] == 0:
            continue
        cpc = d["cost_mean"] / d["calls_mean"]
        print(f"  {ts:<7}  {d['calls_mean']:>5.1f} calls  "
              f"${d['cost_mean']:.2f}  ⇒ ${cpc:.4f}/call")
    print(f"  ↳ if `fine` cost/call ≪ `none` cost/call, the decoupling holds.")


def write_figures(data: dict[int, dict[str, dict]]) -> None:
    import matplotlib.pyplot as plt

    FIGURES.mkdir(parents=True, exist_ok=True)
    tiers = [t for t, _, _ in TIERS]
    colors = {"none": "#444", "fine": "#d62728", "medium": "#1f77b4", "coarse": "#2ca02c"}
    markers = {"none": "o", "fine": "s", "medium": "^", "coarse": "D"}

    # F1: cost μ ± σ per toolset, three tiers on x-axis.
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    for ts in TOOLSETS:
        xs, ys, es = [], [], []
        for tier in tiers:
            d = data[tier][ts]
            if d["n"] == 0:
                continue
            xs.append(tier)
            ys.append(d["cost_mean"])
            es.append(d["cost_sd"])
        if not xs:
            continue
        ax.errorbar(xs, ys, yerr=es, marker=markers[ts], color=colors[ts],
                    label=ts, capsize=3, linewidth=1.2, markersize=6)
    ax.set_xticks(tiers)
    ax.set_xticklabels([f"tier-{t}" for t in tiers])
    ax.set_xlabel("Formal difficulty tier")
    ax.set_ylabel("Cost per solved trial (USD)")
    ax.set_title("Cost vs difficulty tier, by toolset (μ ± 1σ)")
    ax.legend(title="toolset", loc="upper left")
    ax.grid(True, alpha=0.3)
    f1 = FIGURES / "f1_cost_by_tier.png"
    fig.tight_layout()
    fig.savefig(f1, dpi=160)
    plt.close(fig)
    print(f"  wrote {f1.relative_to(REPO)}")

    # F1b: ratio vs none per toolset, three tiers on x-axis.
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    for ts in TOOLSETS:
        if ts == "none":
            continue
        xs, ys = [], []
        for tier in tiers:
            d = data[tier][ts]
            ref = data[tier]["none"]
            if d["n"] == 0 or ref["n"] == 0 or not ref["cost_mean"]:
                continue
            xs.append(tier)
            ys.append(d["cost_mean"] / ref["cost_mean"])
        if not xs:
            continue
        ax.plot(xs, ys, marker=markers[ts], color=colors[ts],
                label=ts, linewidth=1.2, markersize=6)
    ax.axhline(1.0, color="#888", linestyle="--", linewidth=0.8)
    ax.set_xticks(tiers)
    ax.set_xticklabels([f"tier-{t}" for t in tiers])
    ax.set_xlabel("Formal difficulty tier")
    ax.set_ylabel("Cost ratio vs `none` toolset")
    ax.set_title("Cost-ratio surface across tiers")
    ax.legend(title="toolset", loc="best")
    ax.grid(True, alpha=0.3)
    f1b = FIGURES / "f1b_cost_ratio_by_tier.png"
    fig.tight_layout()
    fig.savefig(f1b, dpi=160)
    plt.close(fig)
    print(f"  wrote {f1b.relative_to(REPO)}")

    # F2: calls vs cost scatter — load-bearing P4 figure.
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for ts in TOOLSETS:
        xs, ys = [], []
        for tier in tiers:
            for t in data[tier][ts]["trials"]:
                xs.append(t["calls"])
                ys.append(t["cost"])
        if xs:
            ax.scatter(xs, ys, marker=markers[ts], color=colors[ts],
                       label=ts, s=42, alpha=0.85, edgecolor="white", linewidth=0.6)
    ax.set_xscale("log")
    ax.set_xlabel("Tool calls per solved trial (log scale)")
    ax.set_ylabel("Cost per solved trial (USD)")
    ax.set_title("Calls vs cost: P4 decoupling check (all tiers pooled)")
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

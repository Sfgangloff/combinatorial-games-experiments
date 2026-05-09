"""Aggregate per-cell stats across n trials for a given puzzle.

CLI:
    python -m harness.aggregate_phase1 puzzle_001 [--meta off]
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

TOOLSETS = ["none", "fine", "medium", "coarse"]


def _cost(record: dict) -> float | None:
    for m in record["messages"]:
        if m.get("role") == "result":
            return m.get("total_cost_usd")
    return None


def _load_trials(puzzle_id: str, toolset: str, meta: str) -> list[dict]:
    pattern = f"*_{puzzle_id}_toolset-{toolset}_meta-{meta}.json"
    out = []
    for path in sorted(glob.glob(str(RESULTS / pattern))):
        with open(path) as f:
            r = json.load(f)
        if not r["outcome"]["solved"]:
            continue
        cost = _cost(r)
        out.append({
            "file": os.path.basename(path),
            "calls": r["outcome"]["tool_call_count"],
            "time": r["elapsed_seconds"],
            "cost": cost,
        })
    return out


def _stats(values: list[float]) -> tuple[float, float, float]:
    """mean, stdev, stderr"""
    m = statistics.mean(values)
    s = statistics.stdev(values) if len(values) > 1 else 0.0
    se = s / math.sqrt(len(values)) if len(values) > 1 else 0.0
    return m, s, se


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("puzzle_id")
    p.add_argument("--meta", choices=["off", "on"], default="off")
    args = p.parse_args()

    print(f"\n=== {args.puzzle_id}, meta={args.meta} ===\n")
    print(f"{'toolset':<8} {'n':>2}   "
          f"{'cost μ ± σ':<18} {'calls μ ± σ':<16} {'time μ ± σ (s)':<18}")
    print("-" * 70)

    cost_means: dict[str, tuple[float, float, int]] = {}
    for ts in TOOLSETS:
        trials = _load_trials(args.puzzle_id, ts, args.meta)
        n = len(trials)
        if n == 0:
            print(f"{ts:<8} {n:>2}   (no solved trials)")
            continue
        costs = [t["cost"] for t in trials if t["cost"] is not None]
        calls = [t["calls"] for t in trials]
        times = [t["time"] for t in trials]
        cm, cs, _ = _stats(costs) if costs else (0.0, 0.0, 0.0)
        km, ks, _ = _stats(calls)
        tm, ts_, _ = _stats(times)
        cost_means[ts] = (cm, cs, n)
        cost_str = f"${cm:.2f} ± ${cs:.2f}"
        calls_str = f"{km:.1f} ± {ks:.1f}"
        time_str = f"{tm:.1f} ± {ts_:.1f}"
        print(f"{ts:<8} {n:>2}   {cost_str:<18} {calls_str:<16} {time_str:<18}")

    # ratios vs coarse with rough overlap test (mean ± 1σ)
    if "coarse" in cost_means:
        cm_c, cs_c, n_c = cost_means["coarse"]
        print(f"\nCost ratios vs coarse (μ ± σ basis):")
        for ts in TOOLSETS:
            if ts == "coarse" or ts not in cost_means:
                continue
            cm, cs, n = cost_means[ts]
            ratio = cm / cm_c if cm_c else float("nan")
            # overlap of [μ-σ, μ+σ] intervals
            lo_a, hi_a = cm - cs, cm + cs
            lo_c, hi_c = cm_c - cs_c, cm_c + cs_c
            overlap = not (hi_a < lo_c or hi_c < lo_a)
            tag = "OVERLAPS coarse" if overlap else "separated from coarse"
            print(f"  {ts:<7} {ratio:.2f}×   ({tag})")


if __name__ == "__main__":
    main()

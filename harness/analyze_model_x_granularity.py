"""
Analyze the model x granularity sweep — does the Goldilocks zone shift with
model capability?

Groups solved trials by (model, puzzle, toolset), computes per-cell cost
mu +/- sigma, and for each (model, difficulty rung) the granularity benefit:
the cheapest toolset's cost relative to `none` (the no-tools baseline). The
capability-relative Goldilocks hypothesis predicts that the difficulty rung
where the benefit PEAKS rises with model capability — a weaker model gets its
help on an easier puzzle.

Reads the same harness/results/*.json the other aggregators use; model comes
from each record's "model" field (None = SDK default = Opus 4.7).

CLI:
    python -m harness.analyze_model_x_granularity
    python -m harness.analyze_model_x_granularity \
        --puzzles gen_7x7_s14_00 gen_7x7_s27_00 gen_7x7_s1_00 puzzle_002 \
        --models claude-haiku-4-5 claude-sonnet-4-6 claude-opus-4-7
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import statistics
from pathlib import Path

from harness.run_model_grid import model_label

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "harness" / "results"
MANIFEST = REPO / "puzzles" / "manifest.json"

TOOLSETS = ["none", "fine", "medium", "coarse"]

# Capability rank (higher = stronger). Used to test the shift direction.
_CAPABILITY_RANK = {
    "claude-haiku-4-5": 0,
    "claude-sonnet-4-6": 1,
    "claude-opus-4-7": 2,
    "claude-opus-4-8": 3,
}

# Difficulty proxy for puzzles not carrying search_nodes in the manifest
# (the hand-transcribed corpus). From the Phase-2 anchors in
# notes/2026-05-21_phase2_design.md.
_FALLBACK_NODES = {"puzzle_001": 96, "puzzle_002": 501, "puzzle_004": 10**9}


def _cost(record: dict) -> float | None:
    for m in record["messages"]:
        if m.get("role") == "result":
            return m.get("total_cost_usd")
    return None


def _difficulty(puzzle_id: str, manifest: dict) -> float:
    for e in manifest.get("puzzles", []):
        if e["id"] == puzzle_id and e.get("search_nodes") is not None:
            return float(e["search_nodes"])
    return float(_FALLBACK_NODES.get(puzzle_id, 0))


def _load(manifest: dict) -> dict[tuple[str, str, str], list[dict]]:
    """(model_label, puzzle, toolset) -> list of solved trial dicts."""
    cells: dict[tuple[str, str, str], list[dict]] = {}
    for path in sorted(glob.glob(str(RESULTS / "*.json"))):
        if Path(path).name.startswith("._"):
            continue  # exFAT AppleDouble junk; not real results
        try:
            r = json.loads(Path(path).read_text())
        except (ValueError, OSError):  # ValueError covers JSON + Unicode decode
            continue
        cond = r.get("condition") or {}
        if "toolset" not in cond or bool(cond.get("meta")):
            continue
        if not (r.get("outcome") or {}).get("solved"):
            continue
        key = (model_label(r.get("model")), r.get("puzzle_id"), cond["toolset"])
        cells.setdefault(key, []).append(
            {"cost": _cost(r), "calls": r["outcome"]["tool_call_count"]}
        )
    return cells


def _stats(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    m = statistics.mean(values)
    s = statistics.stdev(values) if len(values) > 1 else 0.0
    return m, s


def _benefit_for(cells, model: str, puzzle: str) -> dict | None:
    """Best-toolset cost saving vs `none` at this (model, puzzle), with a
    1-sigma separation test. Returns None if `none` or all tool cells are
    missing."""
    none_costs = [t["cost"] for t in cells.get((model, puzzle, "none"), []) if t["cost"] is not None]
    if not none_costs:
        return None
    nm, ns = _stats(none_costs)
    best = None  # (toolset, mean, sigma, ratio)
    for ts in TOOLSETS:
        if ts == "none":
            continue
        costs = [t["cost"] for t in cells.get((model, puzzle, ts), []) if t["cost"] is not None]
        if not costs:
            continue
        m, s = _stats(costs)
        ratio = m / nm if nm else float("nan")
        if best is None or ratio < best[3]:
            best = (ts, m, s, ratio)
    if best is None:
        return None
    ts, bm, bs, ratio = best
    # 1-sigma separation: best band sits clearly below none's band
    separated = (bm + bs) < (nm - ns)
    return {
        "none_mean": nm, "none_sigma": ns,
        "best_toolset": ts, "best_mean": bm, "best_sigma": bs,
        "ratio": ratio, "benefit": 1.0 - ratio, "separated": separated,
        "n_none": len(none_costs),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzles", nargs="+", default=None,
                    help="difficulty ladder, easiest-first (default: all seen, sorted by search_nodes)")
    ap.add_argument("--models", nargs="+", default=None,
                    help="models weakest-first (default: all seen, by capability rank)")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"puzzles": []}
    cells = _load(manifest)
    if not cells:
        print("No solved trials found in harness/results/. Run the sweep first "
              "(python -m harness.run_model_grid --dry-run).")
        return

    seen_models = sorted({k[0] for k in cells})
    seen_puzzles = {k[1] for k in cells}
    models = args.models or sorted(
        seen_models, key=lambda m: _CAPABILITY_RANK.get(m, 99))
    puzzles = args.puzzles or sorted(seen_puzzles, key=lambda p: _difficulty(p, manifest))

    print("\n=== Model x granularity: does the Goldilocks zone shift? ===")
    print("benefit = 1 - (cheapest toolset cost / none cost); '*' = best band "
          "separated from none at 1 sigma.\n")
    header = f"{'model':<20} " + "".join(
        f"{p[:12]:>14}" for p in puzzles)
    print(header)
    print(f"{'difficulty ->':<20} " + "".join(
        f"{int(_difficulty(p, manifest)):>14}" for p in puzzles))
    print("-" * len(header))

    peak_difficulty: dict[str, float] = {}
    for model in models:
        row = f"{model:<20} "
        best_benefit = None
        for p in puzzles:
            b = _benefit_for(cells, model, p)
            if b is None:
                row += f"{'--':>14}"
                continue
            star = "*" if b["separated"] else " "
            cell = f"{b['benefit']*100:>5.0f}%{star}{b['best_toolset'][:5]:>6}"
            row += f"{cell:>14}"
            if b["separated"] and (best_benefit is None or b["benefit"] > best_benefit[1]):
                best_benefit = (p, b["benefit"])
        if best_benefit is not None:
            peak_difficulty[model] = _difficulty(best_benefit[0], manifest)
            row += f"   peak@{best_benefit[0][:14]}"
        print(row)

    # Hypothesis test: peak-benefit difficulty should be non-decreasing with
    # capability rank (weaker model peaks on an easier puzzle).
    print("\n--- Capability-relative Goldilocks check ---")
    ranked = [m for m in models if m in peak_difficulty]
    ranked.sort(key=lambda m: _CAPABILITY_RANK.get(m, 99))
    if len(ranked) < 2:
        print("Need a separated peak for >=2 models to test the shift; "
              "collect more trials.")
        return
    diffs = [(m, peak_difficulty[m]) for m in ranked]
    print("peak-benefit difficulty by capability (weakest -> strongest):")
    for m, d in diffs:
        print(f"  {m:<20} peak difficulty ~ {int(d)} search_nodes")
    monotone = all(diffs[i][1] <= diffs[i + 1][1] for i in range(len(diffs) - 1))
    strict = any(diffs[i][1] < diffs[i + 1][1] for i in range(len(diffs) - 1))
    if monotone and strict:
        print("\nVERDICT: peak-benefit difficulty RISES with capability — "
              "consistent with the capability-relative Goldilocks hypothesis.")
    elif monotone:
        print("\nVERDICT: peak-benefit difficulty is flat across models — "
              "no shift detected (or ladder too coarse).")
    else:
        print("\nVERDICT: peak-benefit difficulty is NON-monotone in capability "
              "— the simple shift hypothesis is not supported as stated.")


if __name__ == "__main__":
    main()

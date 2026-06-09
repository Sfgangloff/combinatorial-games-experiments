"""
Model x granularity sweep — resumable, window-budget-capped, model-aware.

Motivation (see notes/2026-06-09_model_x_granularity.md): every experiment so
far ran on a single model (Opus 4.7, the SDK default). The capability-relative
Goldilocks hypothesis says the difficulty band where granularity *helps* should
shift with model capability — coarse tools should help a weaker model on an
EASIER puzzle than they help Opus. Testing it means running the SAME
puzzle x toolset grid across several models.

`run_plan` can't drive this directly: its resume counter keys trials by
(puzzle, toolset, meta) and ignores the model, so a Sonnet cell would be
"satisfied" by Opus trials. This runner keys everything by
(puzzle, toolset, model) instead. It otherwise mirrors run_plan: round-robin
the still-missing trials, predict spend to stay under --window-budget, abort
the whole batch on a rate-limit/fatal error (resume is idempotent), and treat
--dry-run as always-free.

Budget safety: the repo's bash hook only gates `harness.run_plan`. This runner
ALSO spends real subscription compute, so it refuses to launch live unless
BUDGET_AUTHORIZED=1 is set in the session env (same contract as run_plan).
--dry-run never needs it. (Recommended: also add this module to
.claude/hooks/check_bash.sh for defense in depth — see the design note.)

CLI:
    python -m harness.run_model_grid --dry-run
    python -m harness.run_model_grid \
        --models claude-sonnet-4-6 claude-haiku-4-5 --include-default \
        --puzzles gen_7x7_s1_00 puzzle_002 --toolsets none coarse \
        --n 3 --window-budget 8 --max-turns 200
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from harness.conditions import Condition
from harness.run import run_one
from harness.run_plan import _classify, _record_cost, _predicted_cost

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO / "harness" / "results"

# The SDK default model in this repo is Opus 4.7 (see the result records, which
# show "claude-opus-4-7[1m]" even when "model": null was requested). Treat a
# None-model cell as the Opus anchor so existing baseline trials count.
DEFAULT_MODEL_LABEL = "claude-opus-4-7"

# Rough per-model cost multipliers vs the Opus baseline, for window budgeting
# only (actual spend is read back from each record). Input/output $/1M:
# Opus 4.7/4.8 5/25, Sonnet 4.6 3/15, Haiku 4.5 1/5. Token counts also shift
# per model, so these are deliberately conservative priors, not exact.
_MODEL_COST_MULT: dict[str, float] = {
    DEFAULT_MODEL_LABEL: 1.0,
    "claude-opus-4-8": 1.0,
    "claude-opus-4-7": 1.0,
    "claude-sonnet-4-6": 0.6,
    "claude-haiku-4-5": 0.25,
}
_DEFAULT_MODEL_MULT = 0.6


def model_label(model: str | None) -> str:
    """Canonical label for grouping/keys. None -> the SDK default (Opus 4.7)."""
    return DEFAULT_MODEL_LABEL if model is None else model


def _model_mult(model: str | None) -> float:
    return _MODEL_COST_MULT.get(model_label(model), _DEFAULT_MODEL_MULT)


def _predicted(puzzle_id: str, toolset: str, model: str | None) -> float:
    return _predicted_cost(puzzle_id, toolset) * _model_mult(model)


# A plan cell is (puzzle_id, toolset, model, n). model is str | None.
Cell = tuple[str, str, "str | None", int]


def _good_trial_counts() -> dict[tuple[str, str, str], int]:
    """Count 'good' trials per (puzzle_id, toolset, model_label) from results/."""
    counts: dict[tuple[str, str, str], int] = {}
    if not RESULTS_DIR.exists():
        return counts
    for f in RESULTS_DIR.glob("*.json"):
        if f.name.startswith("._"):
            continue  # exFAT AppleDouble junk; not real results
        try:
            rec = json.loads(f.read_text())
        except (ValueError, OSError):  # ValueError covers JSON + Unicode decode
            continue
        cond = rec.get("condition") or {}
        if "toolset" not in cond:
            continue
        # meta is held off for this sweep; skip meta-on trials so they don't
        # contaminate the model x granularity cells.
        if bool(cond.get("meta")):
            continue
        if _classify(rec) != "good":
            continue
        key = (rec.get("puzzle_id"), cond["toolset"], model_label(rec.get("model")))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _build_remaining(plan: list[Cell]) -> list[tuple[str, str, "str | None"]]:
    """Round-robin still-missing trials; cheapest cell first within each round."""
    have = _good_trial_counts()
    max_n = max((n for *_, n in plan), default=0)
    remaining: list[tuple[str, str, "str | None"]] = []
    for r in range(max_n):
        round_cells = []
        for puzzle_id, toolset, model, n in plan:
            need = n - have.get((puzzle_id, toolset, model_label(model)), 0)
            if need > r:
                round_cells.append((puzzle_id, toolset, model))
        round_cells.sort(key=lambda c: _predicted(c[0], c[1], c[2]))
        remaining.extend(round_cells)
    return remaining


def _print_plan(plan: list[Cell], window_budget: float) -> None:
    have = _good_trial_counts()
    print("MODEL x GRANULARITY PLAN (target n per cell):")
    print(f"  {'model':<20} {'puzzle':<14} {'toolset':<9} have/target")
    for puzzle_id, toolset, model, n in plan:
        h = have.get((puzzle_id, toolset, model_label(model)), 0)
        flag = "" if h >= n else "  <-- remaining"
        print(f"  {model_label(model):<20} {puzzle_id:<14} {toolset:<9} "
              f"{h}/{n}{flag}")
    remaining = _build_remaining(plan)
    total_cost = sum(_predicted(p, t, m) for p, t, m in remaining)
    n_windows = max(1, -(-int(total_cost) // int(window_budget))) if remaining else 0
    print(f"\n  remaining trials : {len(remaining)}")
    print(f"  predicted spend  : ${total_cost:.2f}  (rough per-model priors)")
    print(f"  window budget    : ${window_budget:.2f}")
    print(f"  est. windows     : ~{n_windows}")
    if remaining:
        print("\n  next window order (cheapest-first within each round):")
        spent = 0.0
        for p, t, m in remaining:
            c = _predicted(p, t, m)
            if spent + c > window_budget:
                print("    -- window budget reached, rest resumes next run --")
                break
            spent += c
            print(f"    {model_label(m):<20} {p} {t}  (~${c:.2f})")


async def _run(plan: list[Cell], window_budget: float, max_turns: int) -> None:
    remaining = _build_remaining(plan)
    if not remaining:
        print("Nothing to do: plan already satisfied.")
        return
    print(f"{len(remaining)} trial(s) remaining; window budget "
          f"${window_budget:.2f}.\n")
    spent = 0.0
    started = time.time()
    for puzzle_id, toolset, model in remaining:
        pred = _predicted(puzzle_id, toolset, model)
        if spent + pred > window_budget:
            print(f"\nWindow budget would be exceeded "
                  f"(${spent:.2f} + ~${pred:.2f} > ${window_budget:.2f}). "
                  f"Stopping cleanly; re-run to resume next window.")
            break
        cond = Condition(toolset=toolset, meta=False)
        print(f"[{model_label(model)} | {puzzle_id} | {cond.name}] starting "
              f"(pred ~${pred:.2f}, spent ${spent:.2f})...")
        record = await run_one(puzzle_id, cond, max_turns=max_turns,
                               model=model, log=False)
        klass = _classify(record)
        actual = _record_cost(record)
        if actual is not None:
            spent += actual
        if klass == "rate_limited":
            print(f"  ABORT: fatal run error (likely rate-limit/window "
                  f"closed): {record.get('error')!r}. Stopping the batch so "
                  f"the rest of the plan is not burned into a closed window. "
                  f"Re-run the same command after the limit resets — resume "
                  f"is idempotent (this run was not counted).")
            break
        o = record["outcome"]
        print(f"  done: class={klass} solved={o['solved']} "
              f"calls={o['tool_call_count']} "
              f"cost={'$%.2f' % actual if actual is not None else '-'} "
              f"spent=${spent:.2f}")
    print(f"\nWall time: {(time.time() - started) / 60:.1f} min. "
          f"Window spend: ${spent:.2f}.")
    leftover = _build_remaining(plan)
    print(f"Trials still remaining after this window: {len(leftover)}")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", default=["claude-sonnet-4-6", "claude-haiku-4-5"],
                   help="model ids to sweep (capability ladder below Opus)")
    p.add_argument("--include-default", action="store_true",
                   help="also include a None-model (SDK default = Opus 4.7) "
                        "cell as the strong anchor; reuses existing baseline trials")
    p.add_argument("--puzzles", nargs="+",
                   default=["puzzle_001", "puzzle_002", "gen_7x7_s3_00", "gen_7x7_s1_00"],
                   help="difficulty ladder, easiest-first (prefer fixed-size puzzles)")
    p.add_argument("--toolsets", nargs="+",
                   default=["none", "fine", "medium", "coarse"],
                   choices=["none", "fine", "medium", "coarse", "scratchpad"])
    p.add_argument("--n", type=int, default=3, help="target trials per cell")
    p.add_argument("--window-budget", type=float, default=8.0)
    p.add_argument("--max-turns", type=int, default=200)
    p.add_argument("--dry-run", action="store_true",
                   help="print plan + predicted spend, run nothing (always free)")
    return p.parse_args()


def main() -> None:
    a = _parse_args()
    models: list[str | None] = list(a.models)
    if a.include_default:
        models = [None] + models
    plan: list[Cell] = [
        (puzzle, toolset, model, a.n)
        for model in models
        for puzzle in a.puzzles
        for toolset in a.toolsets
    ]
    if a.dry_run:
        _print_plan(plan, a.window_budget)
        return
    # Live-spend gate (the bash hook only knows about run_plan).
    if os.environ.get("BUDGET_AUTHORIZED") != "1":
        print("Blocked: a live model x granularity sweep burns subscription "
              "compute. Re-run with --dry-run to plan for free, or set "
              "BUDGET_AUTHORIZED=1 in this session to authorize a window.")
        raise SystemExit(2)
    asyncio.run(_run(plan, a.window_budget, a.max_turns))


if __name__ == "__main__":
    main()

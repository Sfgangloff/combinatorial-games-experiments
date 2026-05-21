"""
Resumable, window-budget-capped batch runner for the 5h-rate-limit regime.

Motivation (see notes/2026-05-18_aaai_plan_and_meta_confound.md): under
subscription-only compute the 5h window is the schedule atom. `run_subset`
has no repeat-n and no resume — a rate-limit hit mid-batch wastes the rest
of the window (the puzzle_002 note describes 6 cells aborting in ~3s once
the overage cap fires). This runner:

  * defines a *plan* of (puzzle, toolset, meta, n) cells,
  * counts already-good trials by scanning harness/results/ (so it RESUMES
    across windows instead of re-running),
  * round-robins remaining trials (one per cell per round) so a truncated
    window still leaves n balanced across toolsets,
  * stops launching before predicted spend exceeds --window-budget,
  * ABORTS the whole batch the moment a run looks rate-limited / conn-reset
    instead of firing the remaining plan into rejected stubs,
  * --dry-run prints the plan + predicted spend + #windows and touches no
    budget.

Default plan = the Phase-1 gate (puzzle_002 x {none,fine,medium,coarse} x
meta-off x n=3). So `python -m harness.run_plan --dry-run` shows exactly
what closing the gate still costs.

CLI:
    python -m harness.run_plan --dry-run
    python -m harness.run_plan --puzzle puzzle_002 \
        --toolsets none fine medium coarse --n 3 --window-budget 8
    python -m harness.run_plan --dry-run \
        --meta-probe scratchpad@puzzle_001       # add 1 meta-on probe cell
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from harness.conditions import Condition
from harness.run import run_one

REPO = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO / "harness" / "results"

# Predicted per-trial cost (USD), from the aggregates in notes/. Used only
# to decide whether the NEXT run fits the window budget; actual cost is read
# back from each record and is what's accumulated. Unknown (puzzle,toolset)
# falls back to _DEFAULT_COST.
_COST_TABLE: dict[tuple[str, str], float] = {
    ("puzzle_001", "none"): 1.15, ("puzzle_001", "fine"): 1.71,
    ("puzzle_001", "medium"): 1.18, ("puzzle_001", "coarse"): 0.82,
    ("puzzle_001", "scratchpad"): 1.30,
    ("puzzle_002", "none"): 5.28, ("puzzle_002", "fine"): 4.99,
    ("puzzle_002", "medium"): 3.61, ("puzzle_002", "coarse"): 2.32,
    ("puzzle_002", "scratchpad"): 2.58,
}
_DEFAULT_COST = 3.00


def _predicted_cost(puzzle_id: str, toolset: str) -> float:
    return _COST_TABLE.get((puzzle_id, toolset), _DEFAULT_COST)


def _record_cost(record: dict) -> float | None:
    for msg in record.get("messages", []):
        if msg.get("role") == "result":
            return msg.get("total_cost_usd")
    return None


def _classify(record: dict) -> str:
    """
    'good'        -> a valid completed trial, counts toward n
    'rate_limited'-> overage / conn-reset / fatal SDK kill: ABORT the batch
    'incomplete'  -> clean model-side non-solve, no process error: don't
                     count, don't abort (a legitimate trial outcome)

    Note: an actual rate-limit kill surfaces as a generic SDK fatal error
    ("Command failed with exit code 1 / Fatal error in message reader"),
    indistinguishable by string from other fatal errors. We deliberately
    treat ANY record-level error as 'rate_limited' (= abort the batch):
    continuing past a fatal SDK error rarely helps and risks burning the
    window, while stopping is always safe because resume is idempotent.
    """
    err = record.get("error") or ""
    blob = err.lower()
    if any(k in blob for k in (
        "econnreset", "overage", "rejected", "rate limit", "ratelimit",
        "529", "overloaded", "org_level_disabled",
        "exit code", "fatal error", "check stderr",
    )):
        return "rate_limited"
    elapsed = record.get("elapsed_seconds") or 0.0
    calls = (record.get("outcome") or {}).get("tool_call_count", 0)
    if elapsed < 15 and calls == 0:
        return "rate_limited"  # the ~3s rejected-stub signature
    if err:
        return "rate_limited"  # any other process-level error: stop safely
    if _record_cost(record) is None:
        return "incomplete"
    return "good"


def _good_trial_counts() -> dict[tuple[str, str, bool], int]:
    """Count 'good' trials per (puzzle_id, toolset, meta) from results/."""
    counts: dict[tuple[str, str, bool], int] = {}
    if not RESULTS_DIR.exists():
        return counts
    for f in RESULTS_DIR.glob("*.json"):
        try:
            rec = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        cond = rec.get("condition") or {}
        if "toolset" not in cond:
            continue
        if _classify(rec) != "good":
            continue
        key = (rec.get("puzzle_id"), cond["toolset"], bool(cond.get("meta")))
        counts[key] = counts.get(key, 0) + 1
    return counts


def _build_remaining(plan: list[tuple[str, str, bool, int]]
                     ) -> list[tuple[str, str, bool]]:
    """
    Round-robin the still-missing trials: round r yields one trial of every
    cell that still needs >= r+1 trials, cheapest cell first within a round.
    A truncated window therefore leaves n balanced across toolsets.
    """
    have = _good_trial_counts()
    max_n = max((n for *_, n in plan), default=0)
    remaining: list[tuple[str, str, bool]] = []
    for r in range(max_n):
        round_cells = []
        for puzzle_id, toolset, meta, n in plan:
            need = n - have.get((puzzle_id, toolset, meta), 0)
            if need > r:
                round_cells.append((puzzle_id, toolset, meta))
        round_cells.sort(key=lambda c: _predicted_cost(c[0], c[1]))
        remaining.extend(round_cells)
    return remaining


def _print_plan(plan, remaining, window_budget) -> None:
    have = _good_trial_counts()
    print("PLAN (target n per cell):")
    for puzzle_id, toolset, meta, n in plan:
        h = have.get((puzzle_id, toolset, meta), 0)
        m = "on" if meta else "off"
        print(f"  {puzzle_id:<11} {toolset:<10} meta-{m:<3} "
              f"have={h} target={n} remaining={max(0, n - h)}")
    total_cost = sum(_predicted_cost(p, t) for p, t, _ in remaining)
    n_windows = max(1, -(-int(total_cost) // int(window_budget))) if remaining else 0
    print(f"\n  remaining trials : {len(remaining)}")
    print(f"  predicted spend  : ${total_cost:.2f}")
    print(f"  window budget    : ${window_budget:.2f}")
    print(f"  est. windows     : ~{n_windows}")
    if remaining:
        print("\n  next window order (cheapest-first within each round):")
        spent = 0.0
        for p, t, mt in remaining:
            c = _predicted_cost(p, t)
            if spent + c > window_budget:
                print(f"    -- window budget reached, rest resumes next run --")
                break
            spent += c
            print(f"    {p} {t} meta-{'on' if mt else 'off'}  (~${c:.2f})")


async def _run(plan, window_budget, max_turns, model) -> None:
    remaining = _build_remaining(plan)
    if not remaining:
        print("Nothing to do: plan already satisfied.")
        return
    print(f"{len(remaining)} trial(s) remaining; window budget "
          f"${window_budget:.2f}.\n")
    spent = 0.0
    started = time.time()
    for puzzle_id, toolset, meta in remaining:
        pred = _predicted_cost(puzzle_id, toolset)
        if spent + pred > window_budget:
            print(f"\nWindow budget would be exceeded "
                  f"(${spent:.2f} + ~${pred:.2f} > ${window_budget:.2f}). "
                  f"Stopping cleanly; re-run to resume next window.")
            break
        cond = Condition(toolset=toolset, meta=meta)
        print(f"[{puzzle_id} | {cond.name}] starting "
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


def _parse_meta_probe(spec: str) -> tuple[str, str, bool, int]:
    """'scratchpad@puzzle_001' -> (puzzle_001, scratchpad, meta=True, n=1)."""
    toolset, _, puzzle_id = spec.partition("@")
    if not puzzle_id:
        raise argparse.ArgumentTypeError("meta-probe must be TOOLSET@PUZZLE")
    return (puzzle_id, toolset, True, 1)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--puzzle", default="puzzle_002")
    p.add_argument("--toolsets", nargs="+",
                   default=["none", "fine", "medium", "coarse"],
                   choices=["none", "fine", "medium", "coarse", "scratchpad"])
    p.add_argument("--n", type=int, default=3, help="target trials per cell")
    p.add_argument("--meta-probe", type=_parse_meta_probe, default=None,
                   help="extra meta-on probe cell, e.g. scratchpad@puzzle_001")
    p.add_argument("--window-budget", type=float, default=8.0)
    p.add_argument("--max-turns", type=int, default=200)
    p.add_argument("--model", default=None)
    p.add_argument("--dry-run", action="store_true",
                   help="print plan + predicted spend, run nothing")
    return p.parse_args()


def main() -> None:
    a = _parse_args()
    plan: list[tuple[str, str, bool, int]] = [
        (a.puzzle, t, False, a.n) for t in a.toolsets
    ]
    if a.meta_probe is not None:
        plan.append(a.meta_probe)
    remaining = _build_remaining(plan)
    if a.dry_run:
        _print_plan(plan, remaining, a.window_budget)
        return
    asyncio.run(_run(plan, a.window_budget, a.max_turns, a.model))


if __name__ == "__main__":
    main()

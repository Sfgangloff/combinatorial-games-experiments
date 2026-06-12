#!/usr/bin/env python3
"""
Failure-mode taxonomy across tool granularity (q-0013).

Question: does tool granularity change the TYPE of agent failure, not just the
rate? On the two puzzles no toolset ever solves (puzzle_003 = 25x30 / ~750
cells, puzzle_004 = 15x15 / ~225 cells), classify every GENUINE failure
(harness error is None, solved is not True) by:

  - submit behaviour:  did the agent ever submit a (wrong) solution?
                       submit_attempts > 0  ->  WRONG-SUBMIT
  - engagement depth:  tool_call_count, vs a low/high threshold
                       <= EARLY_CALLS  ->  EARLY-REFUSE   (declines fast)
                       >  EARLY_CALLS  ->  GRIND-EXHAUST  (burns the budget,
                                                           then declines)

No new compute: pure read over harness/results/*.json. Reproduces the numbers
behind a-<failure-modes> for q-0013.
"""
import json
import glob
import os
from collections import defaultdict

RESULTS = os.path.join(os.path.dirname(__file__), "results", "*.json")
EARLY_CALLS = 5  # <= this many tool calls = principled early refusal


def final_text(d):
    txt = ""
    for m in d.get("messages", []):
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                    txt = b["text"]
    return txt.strip()


def classify(o):
    if (o.get("submit_attempts") or 0) > 0:
        return "wrong-submit"
    if (o.get("tool_call_count") or 0) <= EARLY_CALLS:
        return "early-refuse"
    return "grind-exhaust"


def main():
    fails = []  # (puzzle, toolset, calls, max_turns, submits, mode, final)
    for f in sorted(glob.glob(RESULTS)):
        d = json.load(open(f))
        o = d.get("outcome") or {}
        if d.get("error") is not None:
            continue  # infra failure, not an agent behaviour
        if o.get("solved") is True:
            continue
        fails.append((
            d["puzzle_id"],
            d["condition"].get("toolset"),
            o.get("tool_call_count") or 0,
            d.get("max_turns"),
            o.get("submit_attempts") or 0,
            classify(o),
            final_text(d),
        ))

    print(f"Genuine agent failures (error=None, not solved): {len(fails)}\n")

    # per (puzzle, toolset)
    by_cell = defaultdict(list)
    for pz, ts, calls, mt, sub, mode, _ in fails:
        by_cell[(pz, ts)].append((calls, mode, sub))

    print(f"{'puzzle':<14}{'toolset':<12}{'n':>3}{'calls(mean)':>13}{'mode':>16}{'wrong-submits':>15}")
    print("-" * 73)
    for (pz, ts) in sorted(by_cell):
        rows = by_cell[(pz, ts)]
        n = len(rows)
        mean_calls = sum(r[0] for r in rows) / n
        modes = {r[1] for r in rows}
        mode = next(iter(modes)) if len(modes) == 1 else "MIXED:" + "/".join(sorted(modes))
        subs = sum(1 for r in rows if r[2] > 0)
        print(f"{pz:<14}{ts:<12}{n:>3}{mean_calls:>13.1f}{mode:>16}{subs:>15}")

    # headline aggregates
    print("\n=== Headline aggregates ===")
    total_wrong = sum(1 for r in fails if r[5] == "wrong-submit")
    print(f"WRONG-SUBMIT failures: {total_wrong}/{len(fails)} "
          f"(agent NEVER blind-guesses; always declines honestly)")

    # none vs tools on each puzzle
    for pz in sorted({r[0] for r in fails}):
        none_calls = [r[2] for r in fails if r[0] == pz and r[1] == "none"]
        tool_calls = [r[2] for r in fails if r[0] == pz and r[1] != "none"]
        nm = sum(none_calls) / len(none_calls) if none_calls else float("nan")
        tm = sum(tool_calls) / len(tool_calls) if tool_calls else float("nan")
        print(f"  {pz}: none mean-calls={nm:.1f} (n={len(none_calls)})  "
              f"tools mean-calls={tm:.1f} (n={len(tool_calls)})")


if __name__ == "__main__":
    main()

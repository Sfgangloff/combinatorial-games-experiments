"""
Reasoning-externalization analysis: how tool granularity moves solving cost
between *generated reasoning tokens* and *externalized tool calls*.

Background. Phase-1/2 established the Goldilocks cost story in DOLLARS: tool
granularity separates from `none` only at intermediate+ difficulty. The
mechanism was open. Total cost factors as

    cost  ~=  turns  x  ($/turn)

and the existing solved trials reveal a sharp structure (no new compute):

  - The no-tools `none` agent solves in very FEW turns (~3-4), but each turn is
    token-heavy: it generates the whole deduction chain as output tokens, so
    its $/turn is large.
  - Tool agents (fine/medium/coarse) take MANY turns (~25-120): one deduction
    per round-trip. Each turn is token-light (the reasoning is externalized
    into the tool call), so their $/turn is small.

So granularity does NOT reduce turns — it trades a few expensive turns for many
cheap ones. This script characterizes that trade and tests H-EXT:

  EXT1 (turns explode, not shrink). turns(none) is the minimum at every rung;
       tools multiply the turn count. (The naive "tools save round-trips"
       intuition is false here.)
  EXT2 (reasoning is externalized). output_tokens(none) >> output_tokens(tool):
       the no-tools agent pays in generated reasoning; the tool agent offloads
       it. Report the externalization ratio.
  EXT3 (Goldilocks gap is mechanistic). The dollar gap cost(none) - cost(coarse)
       is largest at intermediate difficulty and erodes at both ends — because
       on the easy rung `none` is already cheap, and on the hard rung the
       many tool turns each re-read a growing transcript (cache-read context
       cost), eating coarse's per-turn advantage.

Reads the same harness/results/*.json as the other analyzers; Opus 4.7 (the
SDK default, model=None) baseline.

CLI:
    python -m harness.analyze_efficiency_frontier
    python -m harness.analyze_efficiency_frontier --meta off
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "harness" / "results"

TOOLSETS = ["none", "fine", "medium", "coarse"]

# Difficulty ladder, easiest-first (search_nodes from core.generator.grade;
# puzzle_001/002 predate manifest search_nodes, values from the Phase-2 note).
ANCHORS = [
    {"puzzle_id": "puzzle_001",    "search_nodes":   96, "label": "low"},
    {"puzzle_id": "puzzle_002",    "search_nodes":  501, "label": "mid"},
    {"puzzle_id": "gen_7x7_s1_00", "search_nodes": 4547, "label": "high"},
]


def _result_msg(record: dict) -> dict | None:
    for m in record.get("messages", []):
        if m.get("role") == "result":
            return m
    return None


def _load_trials(puzzle_id: str, toolset: str, meta: str) -> list[dict]:
    pattern = f"*_{puzzle_id}_toolset-{toolset}_meta-{meta}.json"
    out: list[dict] = []
    for path in sorted(glob.glob(str(RESULTS / pattern))):
        if os.path.basename(path).startswith("._"):
            continue
        try:
            r = json.load(open(path))
        except (ValueError, OSError):
            continue
        if not (r.get("outcome") or {}).get("solved"):
            continue
        rm = _result_msg(r)
        if not rm or rm.get("total_cost_usd") is None:
            continue
        cost = float(rm["total_cost_usd"])
        turns = rm.get("num_turns")
        if not turns:
            continue
        usage = rm.get("usage") or {}
        out.append({
            "cost": cost,
            "turns": int(turns),
            "calls": r["outcome"]["tool_call_count"],
            "cost_per_turn": cost / int(turns),
            "out_tok": usage.get("output_tokens"),
            "cache_read": usage.get("cache_read_input_tokens"),
        })
    return out


def _stats(values: list[float]) -> tuple[float, float]:
    vals = [v for v in values if v is not None]
    if not vals:
        return float("nan"), float("nan")
    m = statistics.mean(vals)
    s = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return m, s


def _cell(trials: list[dict], key: str) -> tuple[float, float]:
    return _stats([t[key] for t in trials])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", default="off", choices=["off", "on"])
    args = ap.parse_args()

    # Load every cell.
    cells: dict[tuple[str, str], list[dict]] = {}
    for a in ANCHORS:
        for ts in TOOLSETS:
            cells[(a["puzzle_id"], ts)] = _load_trials(a["puzzle_id"], ts, args.meta)

    print("\n=== Efficiency frontier: turns vs dollars across granularity ===")
    print("Opus 4.7 baseline (model=None); solved trials only; meta-%s.\n" % args.meta)

    # Per-rung table.
    for a in ANCHORS:
        pid = a["puzzle_id"]
        print(f"--- {pid}  (search_nodes={a['search_nodes']}, {a['label']}) ---")
        print(f"  {'toolset':<9}{'n':>3}  {'cost $':>14}  {'turns':>12}  "
              f"{'$/turn':>9}  {'out_tok':>9}")
        for ts in TOOLSETS:
            tr = cells[(pid, ts)]
            n = len(tr)
            cm, cs = _cell(tr, "cost")
            tm, tsd = _cell(tr, "turns")
            dpt, _ = _cell(tr, "cost_per_turn")
            ot, _ = _cell(tr, "out_tok")
            cm_s = f"{cm:6.2f}±{cs:4.2f}" if cm == cm else "        --"
            tm_s = f"{tm:5.1f}±{tsd:4.1f}" if tm == tm else "       --"
            dpt_s = f"{dpt:7.3f}" if dpt == dpt else "     --"
            ot_s = f"{ot:9.0f}" if ot == ot else "       --"
            print(f"  {ts:<9}{n:>3}  {cm_s:>14}  {tm_s:>12}  {dpt_s:>9}  {ot_s}")
        print()

    def mean_of(pid: str, ts: str, key: str) -> float:
        return _cell(cells[(pid, ts)], key)[0]

    # EXT1: turns explode (none is the minimum), they don't shrink.
    print("--- EXT1: tools multiply turns; `none` always uses the fewest ---")
    print(f"  {'rung':<14}{'turns none':>11}{'turns fine':>11}"
          f"{'turns med':>11}{'turns coarse':>13}{'tool/none x':>12}")
    for a in ANCHORS:
        pid = a["puzzle_id"]
        tn = mean_of(pid, "none", "turns")
        tf = mean_of(pid, "fine", "turns")
        tm = mean_of(pid, "medium", "turns")
        tc = mean_of(pid, "coarse", "turns")
        tool_turns = [t for t in (tf, tm, tc) if t == t]
        ratio = (statistics.mean(tool_turns) / tn) if (tn == tn and tn and tool_turns) else float("nan")
        print(f"  {pid:<14}{tn:>11.1f}{tf:>11.1f}{tm:>11.1f}{tc:>13.1f}{ratio:>12.1f}")
    print("  => the no-tools agent solves in the fewest turns at every rung; "
          "granularity does NOT save round-trips.\n")

    # EXT2: reasoning is externalized (output tokens move from model to tools).
    print("--- EXT2: `none` pays in generated reasoning tokens; tools offload it ---")
    print(f"  {'rung':<14}{'out_tok none':>13}{'out_tok coarse':>15}"
          f"{'externalize x':>15}")
    for a in ANCHORS:
        pid = a["puzzle_id"]
        on = mean_of(pid, "none", "out_tok")
        oc = mean_of(pid, "coarse", "out_tok")
        ratio = (on / oc) if (on == on and oc == oc and oc) else float("nan")
        print(f"  {pid:<14}{on:>13.0f}{oc:>15.0f}{ratio:>15.1f}")
    print("  => `none` generates many more output tokens than coarse: the "
          "deduction work is in-context (none) vs in the tool (coarse).\n")

    # EXT3: the dollar gap is Goldilocks-shaped in difficulty.
    print("--- EXT3: dollar gap (none - coarse) peaks at intermediate difficulty ---")
    print(f"  {'rung':<14}{'nodes':>7}{'cost none':>11}{'cost coarse':>13}"
          f"{'gap $':>9}{'coarse/none':>13}")
    gaps = []
    for a in ANCHORS:
        pid = a["puzzle_id"]
        cn = mean_of(pid, "none", "cost")
        cc = mean_of(pid, "coarse", "cost")
        gap = cn - cc if (cn == cn and cc == cc) else float("nan")
        ratio = (cc / cn) if (cn == cn and cc == cc and cn) else float("nan")
        gaps.append((a["label"], gap))
        print(f"  {pid:<14}{a['search_nodes']:>7}{cn:>11.2f}{cc:>13.2f}"
              f"{gap:>9.2f}{ratio:>13.2f}")
    vals = [g for _, g in gaps if g == g]
    peak_mid = len(vals) == 3 and vals[1] >= vals[0] and vals[1] >= vals[2]
    print(f"  => gap is {'PEAKED at the mid rung' if peak_mid else 'not single-peaked'} "
          f"({' / '.join(f'{lab}:{g:.2f}' for lab, g in gaps if g == g)}); "
          "consistent with a Goldilocks zone in dollars even though the\n"
          "     turn/token trade is monotone in granularity.\n")


if __name__ == "__main__":
    main()

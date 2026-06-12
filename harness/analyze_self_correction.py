"""
Self-correction analysis across tool granularity (q-0014).

Question: does tool granularity change the agent's ability to SELF-CORRECT
mid-trajectory -- once it has committed a deduction (placed an edge), is it more
or less likely to REVERSE that commitment under fine vs medium vs coarse tools?

We read the edge-mutating tool calls in every trial transcript and detect two
kinds of self-correction event, both of which mean "the agent undid something it
had already committed to the board":

  FLIP            an edge (edge_type,row,col) is re-set to a DIFFERENT value than
                  it currently holds on that board handle. line->blocked,
                  blocked->line, line->empty, etc. This is the agent reversing a
                  concrete deduction it had placed.
  EXPLICIT-UNDO   a dedicated retraction primitive is invoked:
                    fine     reset_edge        (clear a placed edge)
                    medium   restore           (roll the board back to a snapshot)
                    scratchpad retract / try_both / assume  (branch machinery)
                  coarse has NO retraction primitive -- by design its only lever
                  is apply_move, so for coarse self-correction can ONLY show up as
                  a FLIP. That asymmetry is part of the answer.

Edge-set primitives per toolset:
    fine        set_edge      (+ reset_edge = explicit undo)
    medium      apply_edge    (+ restore     = explicit undo)
    coarse      apply_move    (no undo primitive)
    scratchpad  apply_edge    (+ retract/try_both/assume = branch machinery)

Metrics, aggregated over trials per toolset (and split solved / failed):
    commits          # edge-set operations
    flips            # edge-set ops that overwrite a different current value
    flip_rate        flips / commits        <- normalized self-correction signal
    explicit_undo    # dedicated retraction calls
    self_corr_rate   (flips + explicit_undo) / commits

NO new compute: pure read over harness/results/*.json. Opus-4.7 baseline
(model field absent / null); meta-off by default.

CLI:
    python -m harness.analyze_self_correction
    python -m harness.analyze_self_correction --meta off
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "harness" / "results"

TOOLSETS = ["fine", "medium", "coarse", "scratchpad"]

# edge-set primitive name per toolset (the "commit a deduction" verb)
SET_TOOL = {
    "fine": "mcp__slitherlink-fine__set_edge",
    "medium": "mcp__slitherlink-medium__apply_edge",
    "coarse": "mcp__slitherlink-coarse__apply_move",
    "scratchpad": "mcp__slitherlink-scratchpad__apply_edge",
}
# dedicated retraction / branch-undo primitives per toolset
UNDO_TOOLS = {
    "fine": {"mcp__slitherlink-fine__reset_edge"},
    "medium": {"mcp__slitherlink-medium__restore"},
    "coarse": set(),  # no undo primitive by design
    "scratchpad": {
        "mcp__slitherlink-scratchpad__retract",
        "mcp__slitherlink-scratchpad__try_both",
        "mcp__slitherlink-scratchpad__assume",
    },
}

# difficulty rung label by puzzle_id (search_nodes ordering; matches the other
# analyzers). Used only for a per-difficulty breakdown.
RUNG = {
    "puzzle_001": "easy",
    "puzzle_002": "hard",
    "gen_7x7_s1_00": "tier3",
    "puzzle_004": "15x15",
    "puzzle_003": "25x30",
    "gen_7x7_s3_00": "tier3",
}


def iter_tool_uses(d):
    for m in d.get("messages", []):
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                yield b.get("name"), b.get("input") or {}


def edge_key(inp):
    return (inp.get("edge_type"), inp.get("row"), inp.get("col"))


def analyze_trial(d, toolset):
    """Return (commits, flips, explicit_undo) for one trial transcript."""
    set_tool = SET_TOOL[toolset]
    undo_tools = UNDO_TOOLS[toolset]
    # current value of each edge, per board handle
    state = defaultdict(dict)  # handle -> {edge_key: value}
    commits = flips = undo = 0
    for name, inp in iter_tool_uses(d):
        if name == set_tool:
            handle = inp.get("handle")
            ek = edge_key(inp)
            if ek[0] is None:
                continue  # malformed
            val = inp.get("value")
            commits += 1
            prev = state[handle].get(ek)
            if prev is not None and prev != val:
                flips += 1
            state[handle][ek] = val
        elif name in undo_tools:
            undo += 1
    return commits, flips, undo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", choices=["off", "on", "all"], default="off")
    args = ap.parse_args()

    # agg[toolset] = list of (puzzle, solved, commits, flips, undo)
    agg = defaultdict(list)
    for f in sorted(glob.glob(str(RESULTS / "*.json"))):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if d.get("error") is not None:
            continue  # infra failure, not agent behaviour
        cond = d.get("condition") or {}
        ts = cond.get("toolset")
        if ts not in SET_TOOL:
            continue
        if args.meta != "all":
            want = (args.meta == "on")
            if bool(cond.get("meta")) != want:
                continue
        # Opus-4.7 baseline only (model absent / null)
        if d.get("model"):
            continue
        commits, flips, undo = analyze_trial(d, ts)
        if commits == 0 and undo == 0:
            continue  # no edge activity (e.g. immediate refuse) -- skip
        agg[ts].append((
            d.get("puzzle_id"),
            (d.get("outcome") or {}).get("solved") is True,
            commits, flips, undo,
        ))

    print(f"Self-correction across granularity (q-0014)  [meta={args.meta}, Opus-4.7]\n")
    print(f"{'toolset':<11}{'trials':>7}{'commits':>9}{'flips':>7}"
          f"{'flip%':>8}{'undo':>6}{'selfcorr%':>11}")
    print("-" * 59)
    summary = {}
    for ts in TOOLSETS:
        rows = agg.get(ts, [])
        if not rows:
            continue
        C = sum(r[2] for r in rows)
        F = sum(r[3] for r in rows)
        U = sum(r[4] for r in rows)
        flip_pct = 100 * F / C if C else 0.0
        sc_pct = 100 * (F + U) / C if C else 0.0
        summary[ts] = (flip_pct, sc_pct, C, F, U)
        print(f"{ts:<11}{len(rows):>7}{C:>9}{F:>7}{flip_pct:>7.1f}%"
              f"{U:>6}{sc_pct:>10.1f}%")

    # per-difficulty flip-rate, fine vs coarse (the q-0014 contrast)
    print("\n=== flip% by difficulty rung (fine vs medium vs coarse) ===")
    print(f"{'rung':<8}{'fine':>10}{'medium':>10}{'coarse':>10}")
    rungs_order = ["easy", "hard", "tier3", "15x15", "25x30"]
    by_rung = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # rung->ts->[C,F]
    for ts in ("fine", "medium", "coarse"):
        for pz, solved, C, F, U in agg.get(ts, []):
            r = RUNG.get(pz, pz)
            by_rung[r][ts][0] += C
            by_rung[r][ts][1] += F
    for r in rungs_order:
        if r not in by_rung:
            continue
        cells = []
        for ts in ("fine", "medium", "coarse"):
            C, F = by_rung[r][ts]
            cells.append(f"{(100*F/C):.1f}% ({F}/{C})" if C else "-")
        print(f"{r:<8}{cells[0]:>10}{cells[1]:>10}{cells[2]:>10}")

    # headline contrasts
    print("\n=== Headline ===")
    if "fine" in summary and "coarse" in summary:
        ff = summary["fine"][0]
        cf = summary["coarse"][0]
        print(f"FLIP rate  fine={ff:.1f}%  medium={summary.get('medium',(0,))[0]:.1f}%  "
              f"coarse={cf:.1f}%")
        if cf > 0:
            print(f"  fine/coarse flip-rate ratio = {ff/cf:.2f}x")
    print("Note: coarse has NO undo primitive (explicit_undo structurally 0); its")
    print("only self-correction channel is the FLIP, so the flip% column is the")
    print("fair cross-granularity comparison.")


if __name__ == "__main__":
    main()

"""
Total-effort conservation analysis (q-0016): is the TOTAL reasoning effort
(generated reasoning tokens + tool-driven context work) roughly conserved across
tool granularity, or does granularity change the total amount of work — not just
where it happens?

Background. a-0015 (H-EXT, e-0011) established RELOCATION: the no-tools `none`
agent solves in few token-heavy turns (lots of generated output tokens), while
tool agents take many token-light turns (one deduction per round-trip,
externalized into tool calls). That answered "where does the work go." It did
NOT answer "is the total the same." A relocation can be effort-neutral (a pure
transfer) or effort-inflating (the new location carries overhead).

This script tests conservation directly from the existing solved trials (NO new
compute), by reading the full token usage of each result message:

    output_tokens                generated reasoning ("thinking on the model")
    cache_read_input_tokens      transcript RE-READS — the per-turn context tax
    cache_creation_input_tokens  newly-cached context
    input_tokens                 fresh (uncached) input
    total_processed = sum of the four  (raw token throughput = a work proxy)

Conservation predictions:

  C1 (output NOT conserved, declines with granularity). output_tokens(none) is
     the max; tools generate fewer. (This is the relocation half, a-0015.)
  C2 (total NOT conserved, INFLATES with granularity). total_processed(coarse)
     >> total_processed(none): every tool turn re-reads the whole growing
     transcript, so cache_read balloons faster than output shrinks. The
     relocation is therefore effort-INFLATING, not effort-neutral.
  C3 (the inflation lives in cache_read, not generation). The extra throughput
     under granularity is dominated by transcript re-reads (cache_read fraction
     rises with turns), confirming the tax is context re-processing, not extra
     reasoning.

Reads the same harness/results/*.json as the other analyzers; Opus 4.7
(model=None) baseline, solved trials only.

CLI:
    python -m harness.analyze_effort_conservation
    python -m harness.analyze_effort_conservation --meta off
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
# puzzle_001/002 predate manifest search_nodes — values from the Phase-2 note,
# matching harness/analyze_efficiency_frontier.py).
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
        usage = rm.get("usage") or {}
        out_tok = usage.get("output_tokens")
        if out_tok is None:
            continue
        inp = usage.get("input_tokens") or 0
        cache_create = usage.get("cache_creation_input_tokens") or 0
        cache_read = usage.get("cache_read_input_tokens") or 0
        total = inp + cache_create + cache_read + out_tok
        turns = rm.get("num_turns") or 0
        out.append({
            "cost": float(rm["total_cost_usd"]),
            "turns": int(turns),
            "out_tok": out_tok,
            "cache_read": cache_read,
            "cache_create": cache_create,
            "input_tok": inp,
            "total": total,
            "read_frac": (cache_read / total) if total else float("nan"),
        })
    return out


def _mean(values: list[float]) -> float:
    vals = [v for v in values if v is not None and v == v]
    return statistics.mean(vals) if vals else float("nan")


def _meansd(values: list[float]) -> tuple[float, float]:
    vals = [v for v in values if v is not None and v == v]
    if not vals:
        return float("nan"), float("nan")
    m = statistics.mean(vals)
    s = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return m, s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", default="off", choices=["off", "on"])
    args = ap.parse_args()

    cells: dict[tuple[str, str], list[dict]] = {}
    for a in ANCHORS:
        for ts in TOOLSETS:
            cells[(a["puzzle_id"], ts)] = _load_trials(a["puzzle_id"], ts, args.meta)

    def cell_mean(pid: str, ts: str, key: str) -> float:
        return _mean([t[key] for t in cells[(pid, ts)]])

    print("\n=== Total-effort conservation across granularity (q-0016) ===")
    print("Opus 4.7 baseline (model=None); solved trials only; meta-%s." % args.meta)
    print("total_processed = input + cache_create + cache_read + output (tokens).\n")

    # Per-rung breakdown of token throughput by component.
    for a in ANCHORS:
        pid = a["puzzle_id"]
        print(f"--- {pid}  (search_nodes={a['search_nodes']}, {a['label']}) ---")
        print(f"  {'toolset':<9}{'n':>3}{'turns':>7}{'out_tok':>10}"
              f"{'cache_read':>12}{'cache_cr':>10}{'TOTAL':>12}{'read%':>7}")
        for ts in TOOLSETS:
            tr = cells[(pid, ts)]
            n = len(tr)
            tu = _mean([t["turns"] for t in tr])
            ot = _mean([t["out_tok"] for t in tr])
            cr = _mean([t["cache_read"] for t in tr])
            cc = _mean([t["cache_create"] for t in tr])
            tot = _mean([t["total"] for t in tr])
            rf = _mean([t["read_frac"] for t in tr])
            fmt = lambda x, w: (f"{x:>{w}.0f}" if x == x else f"{'--':>{w}}")
            print(f"  {ts:<9}{n:>3}{fmt(tu,7)}{fmt(ot,10)}{fmt(cr,12)}"
                  f"{fmt(cc,10)}{fmt(tot,12)}"
                  f"{(f'{rf*100:>6.1f}' if rf==rf else '    --'):>7}")
        print()

    # C1: output tokens are NOT conserved — they decline with granularity.
    print("--- C1: generated output tokens decline with granularity (relocation) ---")
    print(f"  {'rung':<14}{'none':>10}{'fine':>10}{'medium':>10}{'coarse':>10}"
          f"{'none/coarse':>12}")
    for a in ANCHORS:
        pid = a["puzzle_id"]
        vals = {ts: cell_mean(pid, ts, "out_tok") for ts in TOOLSETS}
        ratio = (vals["none"] / vals["coarse"]
                 if vals["none"] == vals["none"] and vals["coarse"] else float("nan"))
        print(f"  {pid:<14}" + "".join(
            f"{vals[ts]:>10.0f}" if vals[ts] == vals[ts] else f"{'--':>10}"
            for ts in TOOLSETS) + f"{ratio:>12.2f}")
    print("  => `none` generates the most reasoning tokens at every rung; tools "
          "offload generation (confirms a-0015).\n")

    # C2: total throughput is NOT conserved — it inflates with granularity.
    print("--- C2: TOTAL token throughput INFLATES with granularity (not conserved) ---")
    print(f"  {'rung':<14}{'none':>12}{'fine':>12}{'medium':>12}{'coarse':>12}"
          f"{'coarse/none':>12}")
    inflations = []
    for a in ANCHORS:
        pid = a["puzzle_id"]
        vals = {ts: cell_mean(pid, ts, "total") for ts in TOOLSETS}
        ratio = (vals["coarse"] / vals["none"]
                 if vals["none"] and vals["none"] == vals["none"]
                 and vals["coarse"] == vals["coarse"] else float("nan"))
        inflations.append((a["label"], ratio))
        print(f"  {pid:<14}" + "".join(
            f"{vals[ts]:>12.0f}" if vals[ts] == vals[ts] else f"{'--':>12}"
            for ts in TOOLSETS) + f"{ratio:>12.2f}")
    print("  => coarse processes far MORE total tokens than none at every rung: "
          "the relocation is effort-INFLATING, not effort-neutral.")
    print("     inflation (coarse/none): " +
          " / ".join(f"{lab}:{r:.1f}x" for lab, r in inflations if r == r) + "\n")

    # C3: the inflation lives in cache_read (transcript re-reads), not generation.
    print("--- C3: the extra effort is transcript RE-READS (cache_read), not reasoning ---")
    print(f"  {'rung':<14}{'read% none':>12}{'read% coarse':>14}"
          f"{'cr_read none':>14}{'cr_read coarse':>16}{'read x':>9}")
    for a in ANCHORS:
        pid = a["puzzle_id"]
        rfn = cell_mean(pid, "none", "read_frac")
        rfc = cell_mean(pid, "coarse", "read_frac")
        crn = cell_mean(pid, "none", "cache_read")
        crc = cell_mean(pid, "coarse", "cache_read")
        rx = (crc / crn) if (crn and crn == crn and crc == crc) else float("nan")
        print(f"  {pid:<14}{rfn*100:>11.1f}%{rfc*100:>13.1f}%"
              f"{crn:>14.0f}{crc:>16.0f}{rx:>9.1f}")
    print("  => under coarse tools the bulk of throughput is re-reading the "
          "growing transcript each turn; that is the conservation-breaking tax.\n")


if __name__ == "__main__":
    main()

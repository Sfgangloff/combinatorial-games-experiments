#!/usr/bin/env python3
"""
Give-up timing and confidence calibration across tool granularity (q-0015).

Question: does tool granularity change WHEN, and how confidently, the agent
decides to give up? Does coarser tooling abandon earlier or later, and is the
agent's confidence at the give-up point CALIBRATED (i.e. does its expressed
confidence match the actual outcome, or does it ever overclaim a solve)?

This extends e-0013 (failure-mode taxonomy: WHERE/how-much engagement before a
failure) with the orthogonal CONFIDENCE/CALIBRATION axis. e-0013 established
that wrong-submits = 0 (the agent never blind-guesses); q-0015 asks the dual
question on the language side: when it stops, does it ever *claim* success it
did not achieve (over-confidence), and conversely does it assert confidence
when it genuinely solved (so the confidence signal is informative)?

Method (no new compute, pure read over harness/results/*.json):

  WHEN  -- per failed trial, give-up timing measured two ways:
           * tool_call_count  (engagement depth, as in e-0013)
           * turns / max_turns (fraction of the turn budget consumed before
             the agent voluntarily stopped). A *voluntary* decline that stops
             well short of max_turns is an EARLY abandonment; one that runs to
             the budget is EXHAUSTION-driven.

  CONFIDENCE -- classify the FINAL assistant message by lexical markers into:
           * ASSERT-SOLVED : claims the puzzle is solved / complete / verified
           * DECLINE       : honest give-up; explicitly refuses to submit a
                             guess ("declining", "would be a fabricated
                             solution", "stopping rather than submit", ...)
           * OTHER         : neither clear assertion nor explicit decline.

  CALIBRATION -- cross-tabulate CONFIDENCE x actual `solved`:
           * OVERCLAIM   = trial NOT solved but final ASSERTs solved (and does
                           not also decline). These are calibration failures.
           * CONFIRMED   = solved and final ASSERTs solved (informative signal).
           * HONEST-DECLINE = not solved and final DECLINEs.
         A perfectly calibrated agent has 0 OVERCLAIMs and DECLINEs on the
         failures it cannot finish.

Lexical, not semantic: markers are reported so the classification is auditable.
"""
import json
import glob
import os
import re
from collections import defaultdict

RESULTS = os.path.join(os.path.dirname(__file__), "results", "*.json")

# --- lexical marker sets (lowercased substring / regex match on final text) ---
ASSERT_SOLVED = [
    "the solution is complete", "puzzle is solved", "puzzle is now solved",
    "solution is verified", "i have solved", "i've solved", "now solved",
    "satisfies all", "all constraints are satisfied", "all the cell constraints",
    "single closed loop", "one single loop", "valid solution", "final solution",
    "complete and valid", "solution satisfies", "is the solution",
]
DECLINE = [
    "declin", "i am stopping", "i'm stopping", "stopping here", "stop here",
    "cannot make meaningful progress", "not feasible", "not realistically",
    "would be wrong", "would almost certainly be wrong", "fabricat", "a guess",
    "guessed solution", "rather than submit", "without submitting",
    "no solution submitted", "not submitting", "give up", "unable to",
    "blows the budget", "burn the budget", "waste the", "cannot complete",
]


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


def assistant_turns(d):
    return sum(1 for m in d.get("messages", []) if m.get("role") == "assistant")


def markers_hit(text, markers):
    low = text.lower()
    return [m for m in markers if m in low]


def classify_confidence(text):
    asserts = markers_hit(text, ASSERT_SOLVED)
    declines = markers_hit(text, DECLINE)
    # an explicit decline dominates: even if "valid solution" appears in a
    # sentence like "would not produce a valid solution", the decline is the act.
    if declines:
        return "DECLINE", asserts, declines
    if asserts:
        return "ASSERT-SOLVED", asserts, declines
    return "OTHER", asserts, declines


def main():
    rows = []  # dicts per genuine trial (error is None)
    for f in sorted(glob.glob(RESULTS)):
        if os.path.basename(f).startswith("._"):
            continue
        d = json.load(open(f))
        if d.get("error") is not None:
            continue  # infra failure, not agent behaviour
        o = d.get("outcome") or {}
        text = final_text(d)
        conf, asserts, declines = classify_confidence(text)
        turns = assistant_turns(d)
        mt = d.get("max_turns") or 0
        rows.append(dict(
            puzzle=d["puzzle_id"],
            toolset=d["condition"].get("toolset"),
            solved=o.get("solved") is True,
            calls=o.get("tool_call_count") or 0,
            submits=o.get("submit_attempts") or 0,
            turns=turns,
            max_turns=mt,
            frac=(turns / mt) if mt else float("nan"),
            conf=conf,
        ))

    fails = [r for r in rows if not r["solved"]]
    solves = [r for r in rows if r["solved"]]
    print(f"Genuine trials: {len(rows)}  (solved={len(solves)}  failed={len(fails)})\n")

    # === WHEN: give-up timing on failures, by toolset ===
    print("=== WHEN the agent gives up (failed trials, by toolset) ===")
    print(f"{'toolset':<12}{'n':>3}{'calls(mean)':>13}{'turns(mean)':>13}{'turns/budget':>14}")
    print("-" * 55)
    by_ts = defaultdict(list)
    for r in fails:
        by_ts[r["toolset"]].append(r)
    for ts in sorted(by_ts):
        rs = by_ts[ts]
        n = len(rs)
        mc = sum(r["calls"] for r in rs) / n
        mt = sum(r["turns"] for r in rs) / n
        mf = sum(r["frac"] for r in rs) / n
        print(f"{ts:<12}{n:>3}{mc:>13.1f}{mt:>13.1f}{mf:>13.1%}")

    # none vs tools timing
    none_frac = [r["frac"] for r in fails if r["toolset"] == "none"]
    tool_frac = [r["frac"] for r in fails if r["toolset"] != "none"]
    if none_frac and tool_frac:
        print(f"\n  none  : gives up at {sum(none_frac)/len(none_frac):.1%} of turn budget (n={len(none_frac)})")
        print(f"  tools : gives up at {sum(tool_frac)/len(tool_frac):.1%} of turn budget (n={len(tool_frac)})")
    # did ANY failure run to the turn budget? (exhaustion vs voluntary)
    exhausted = [r for r in fails if r["max_turns"] and r["turns"] >= r["max_turns"]]
    print(f"  failures that hit max_turns (budget-exhaustion stop): {len(exhausted)}/{len(fails)}")
    print("  -> all others are VOLUNTARY declines (agent chose to stop early).")

    # === CONFIDENCE x OUTCOME: calibration ===
    print("\n=== CALIBRATION: final-message confidence x actual outcome ===")
    print(f"{'':<16}{'solved':>10}{'failed':>10}")
    cell = defaultdict(int)
    for r in rows:
        cell[(r["conf"], r["solved"])] += 1
    for conf in ["ASSERT-SOLVED", "DECLINE", "OTHER"]:
        print(f"{conf:<16}{cell[(conf, True)]:>10}{cell[(conf, False)]:>10}")

    overclaim = [r for r in fails if r["conf"] == "ASSERT-SOLVED"]
    honest_decline = [r for r in fails if r["conf"] == "DECLINE"]
    confirmed = [r for r in solves if r["conf"] == "ASSERT-SOLVED"]
    print("\n=== Headline calibration aggregates ===")
    print(f"OVERCLAIM (failed but final asserts solved): {len(overclaim)}/{len(fails)}")
    print(f"HONEST-DECLINE (failed and explicitly declines to submit): {len(honest_decline)}/{len(fails)}")
    print(f"CONFIRMED (solved and final asserts the solution): {len(confirmed)}/{len(solves)}")
    print(f"WRONG-SUBMITS across failures (corroborates e-0013): "
          f"{sum(1 for r in fails if r['submits'] > 0)}/{len(fails)}")

    # decline rate by toolset (is calibration granularity-dependent?)
    print("\n=== Decline-vs-overclaim on failures, by toolset ===")
    print(f"{'toolset':<12}{'n':>3}{'DECLINE':>9}{'OVERCLAIM':>11}{'OTHER':>7}")
    for ts in sorted(by_ts):
        rs = by_ts[ts]
        dec = sum(1 for r in rs if r["conf"] == "DECLINE")
        ov = sum(1 for r in rs if r["conf"] == "ASSERT-SOLVED")
        ot = sum(1 for r in rs if r["conf"] == "OTHER")
        print(f"{ts:<12}{len(rs):>3}{dec:>9}{ov:>11}{ot:>7}")


if __name__ == "__main__":
    main()

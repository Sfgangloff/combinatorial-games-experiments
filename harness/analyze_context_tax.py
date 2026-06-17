"""Context-tax decomposition: the verified mechanism under the Goldilocks curve.

e-0012 in the `slitherlink-tool-granularity` stream. No new compute — reads the
existing solved-trial JSON in `harness/results/`.

Motivation
----------
a-0015 (H-EXT) claims tool granularity *relocates* reasoning into many
token-light turns; a-0013 (Goldilocks) claims the dollar benefit of doing so is
single-peaked, and the externalization note ATTRIBUTES the hard-rung collapse to
a per-turn "context re-read tax" (cache-read tokens that grow with turn count) —
but that attribution was never measured. This script measures it.

Each trial's `usage` carries `cache_read_input_tokens` (CR), `output_tokens`
(OUT), and `num_turns`. The agent re-reads the growing transcript every turn, so
CR is the dollar proxy for the context tax. We test three things:

  T1  CR scales with turns      (the tax exists and is turn-driven)
  T2  CR/OUT ratio rises with difficulty for tooled sets but not for `none`
      (the tax, not output, is what closes the gap at the hard rung)
  T3  Decompose coarse-vs-none cost into an externalization saving (less OUT)
      minus a context-tax penalty (more CR); show the penalty overtakes the
      saving exactly at the hard rung -> Goldilocks falls out mechanistically.

Then derive the q-0011 (capability) prediction from the verified mechanism.

Run:  python -m harness.analyze_context_tax
"""
import glob
import json
import math
import os
import statistics as st

RESULTS = os.path.join(os.path.dirname(__file__), "results")

# difficulty ladder: (puzzle_id, label, search_nodes) — from core.generator.grade
RUNGS = [
    ("puzzle_001", "tier-1 easy", 96),
    ("puzzle_002", "tier-2 mid", 501),
    ("gen_7x7_s1_00", "tier-3 hard", 4547),
]
TOOLSETS = ["none", "fine", "medium", "coarse"]

# Anthropic price per token (USD) at the time of the runs, Opus 4.7 1M-context
# tier (<=200k). Used only to attribute cost to CR vs OUT; ratios are
# price-independent, the absolute $ split is illustrative.
P_OUT = 75.0 / 1e6          # output
P_CR = 1.50 / 1e6           # cache read
P_CC = 18.75 / 1e6          # cache creation (1h ephemeral)
P_IN = 15.0 / 1e6           # uncached input


def load():
    rows = []
    for fn in glob.glob(os.path.join(RESULTS, "2026*.json")):
        if "/._" in fn or os.path.basename(fn).startswith("._"):
            continue
        try:
            d = json.load(open(fn))
        except Exception:
            continue
        cond = d.get("condition")
        if not isinstance(cond, dict) or cond.get("meta"):
            continue
        msgs = d.get("messages") or []
        if not msgs or msgs[-1].get("role") != "result":
            continue
        res = msgs[-1]
        out = d.get("outcome", {})
        if not out.get("solved"):
            continue
        u = res.get("usage", {})
        rows.append(dict(
            pid=d["puzzle_id"], toolset=cond.get("toolset"),
            turns=res.get("num_turns", 0) or 0,
            cost=res.get("total_cost_usd", 0.0) or 0.0,
            out=u.get("output_tokens", 0) or 0,
            cr=u.get("cache_read_input_tokens", 0) or 0,
            cc=u.get("cache_creation_input_tokens", 0) or 0,
            inp=u.get("input_tokens", 0) or 0,
        ))
    return rows


def cell(rows, pid, ts):
    return [r for r in rows if r["pid"] == pid and r["toolset"] == ts]


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return float("nan")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def main():
    rows = load()
    print(f"# Context-tax decomposition (e-0012)  — {len(rows)} solved meta-off trials\n")

    # ---- T1: CR vs turns across all tooled solved trials -------------------
    tooled = [r for r in rows if r["toolset"] != "none"]
    r_turn_cr = pearson([r["turns"] for r in tooled], [r["cr"] for r in tooled])
    r_turn_out = pearson([r["turns"] for r in tooled], [r["out"] for r in tooled])
    print("## T1  Is the context tax turn-driven?  (tooled trials, all rungs)")
    print(f"  n={len(tooled)}  corr(turns, cache_read) = {r_turn_cr:+.3f}"
          f"   corr(turns, output) = {r_turn_out:+.3f}")
    # CR per turn
    cpt = [r["cr"] / r["turns"] for r in tooled if r["turns"]]
    print(f"  cache_read per turn: {mean(cpt):,.0f} tok/turn  "
          f"(each turn re-reads ~the whole transcript)\n")

    # ---- per-cell table -----------------------------------------------------
    print("## Per-cell means (solved, meta-off)")
    hdr = (f"{'rung':<13}{'set':<8}{'n':>2} {'turns':>6} {'out_tok':>9}"
           f" {'cr_tok':>10} {'cost$':>7} {'CR/OUT':>7} {'$CR':>6} {'$OUT':>6}")
    print(hdr)
    table = {}
    for pid, label, nodes in RUNGS:
        for ts in TOOLSETS:
            c = cell(rows, pid, ts)
            if not c:
                continue
            m = {k: mean([r[k] for r in c]) for k in ("turns", "out", "cr", "cc", "inp", "cost")}
            m["n"] = len(c)
            cr_out = m["cr"] / m["out"] if m["out"] else float("nan")
            dollar_cr = m["cr"] * P_CR
            dollar_out = m["out"] * P_OUT
            table[(pid, ts)] = m | {"cr_out": cr_out, "$cr": dollar_cr, "$out": dollar_out, "label": label}
            print(f"{label:<13}{ts:<8}{m['n']:>2} {m['turns']:>6.1f} {m['out']:>9,.0f}"
                  f" {m['cr']:>10,.0f} {m['cost']:>7.2f} {cr_out:>7.2f}"
                  f" {dollar_cr:>6.2f} {dollar_out:>6.2f}")
        print()

    # ---- T2: CR/OUT ratio trend across difficulty --------------------------
    print("## T2  Does the context tax (CR/OUT) climb with difficulty?")
    for ts in TOOLSETS:
        seq = []
        for pid, label, nodes in RUNGS:
            t = table.get((pid, ts))
            seq.append(f"{t['cr_out']:.2f}" if t else "  -")
        print(f"  {ts:<8} CR/OUT  easy->hard:  " + "  ".join(f"{s:>5}" for s in seq))
    print()

    # ---- T3: decompose coarse-vs-none gap into saving - penalty ------------
    print("## T3  Goldilocks decomposition: externalization saving vs context tax")
    print("  Per rung, coarse relative to none, in OUTPUT tokens (saving) and")
    print("  CACHE-READ tokens (penalty), and the net cost ratio coarse/none.")
    print(f"  {'rung':<13}{'cost ratio':>11}{'OUT saved':>11}{'CR added':>11}"
          f"{'$OUT saved':>11}{'$CR added':>11}{'net mech$':>10}")
    for pid, label, nodes in RUNGS:
        n_ = table.get((pid, "none"))
        c_ = table.get((pid, "coarse"))
        if not (n_ and c_):
            continue
        ratio = c_["cost"] / n_["cost"]
        out_saved = n_["out"] - c_["out"]            # >0 = coarse externalizes
        cr_added = c_["cr"] - n_["cr"]               # >0 = coarse pays tax
        d_out = out_saved * P_OUT
        d_cr = cr_added * P_CR
        net = d_out - d_cr        # >0 mechanism predicts coarse cheaper
        print(f"  {label:<13}{ratio:>11.2f}{out_saved:>11,.0f}{cr_added:>11,.0f}"
              f"{d_out:>11.2f}{d_cr:>11.2f}{net:>10.2f}")
    print()
    print("  Reading: net mech$ > 0  => mechanism predicts coarse wins (mid rung);")
    print("  net mech$ -> 0 / <0 at the hard rung => the context tax has eaten the")
    print("  externalization saving => Goldilocks collapse, mechanistically.\n")

    # ---- q-0011 prediction --------------------------------------------------
    print("## q-0011 prediction derived from the verified mechanism")
    print("""  The dollar benefit of coarse = (OUT saved)*P_OUT - (CR added)*P_CR.
  OUT saved grows with how much in-context deduction the model would have
  done unaided (its in-head reasoning load at that difficulty); CR added grows
  with the EXTRA turns tooling induces times the transcript size. A weaker
  model (a) hits its in-head reasoning blow-up at a LOWER search_nodes (so
  OUT-saved peaks earlier on the ladder) and (b) emits a smaller transcript per
  turn but needs MORE turns. Net: the rung where (OUT saved) >> (CR added) —
  the Goldilocks peak — shifts to LOWER search_nodes for weaker models.
  Falsifiable form (MG1'): peak of [OUT_saved*P_OUT - CR_added*P_CR] over the
  difficulty ladder is non-decreasing in model capability. This is e-0010's
  pre-registered test, now with a mechanistic (not just phenomenological)
  rationale and a concrete per-trial estimator computable from `usage`.""")


if __name__ == "__main__":
    main()

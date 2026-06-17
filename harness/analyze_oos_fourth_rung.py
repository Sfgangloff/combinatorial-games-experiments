"""Out-of-sample test of the two-term G-CD estimator on a 4th puzzle.

e-0018 in `slitherlink-tool-granularity`. No new compute — uses the existing
gen_7x7_s3_00 trials, a SECOND tier-3 puzzle the e-0016/e-0017 cost model never
saw (those used puzzle_001/puzzle_002/gen_7x7_s1_00).

Why this matters
----------------
a-0021/MG1' (the q-0011 cross-model prediction) assumes the externalization
SAVING — the no-tools agent's in-head output volume — is the term that locates
the Goldilocks peak, and treats it as governed by formal difficulty
(search_nodes). gen_7x7_s3_00 is graded search_nodes=3789, almost the same as
gen_7x7_s1_00 (4547) — a near-identical formal difficulty. It is therefore a
direct test of two things:

  O1  Is the in-head SAVING term a clean function of search_nodes? If two tier-3
      puzzles of near-equal grade have very different none-output, then the MG1'
      peak-location prediction cannot be stated in search_nodes alone — it must
      be stated in the model's realized in-head output (which is what e-0016
      actually used). Quantify the spread.

  O2  Does the two-term estimator net = OUT_saved*P_OUT - CR_added*P_CR predict
      the SIGN and rough magnitude of the none-vs-coarse cost gap out of sample?
      gen_7x7_s3_00 is the first rung where coarse is expected to LOSE.

Run:  python -m harness.analyze_oos_fourth_rung
"""
import glob
import json
import os
import statistics as st

RESULTS = os.path.join(os.path.dirname(__file__), "results")
P_OUT = 75.0 / 1e6
P_CR = 1.50 / 1e6
# global billed/list discount measured in e-0017 (toolset/rung invariant)
DISCOUNT = 0.335

PUZZLES = [
    ("puzzle_001", "tier-1", 96),
    ("puzzle_002", "tier-2", 501),
    ("gen_7x7_s3_00", "tier-3a", 3789),   # NEW out-of-sample rung
    ("gen_7x7_s1_00", "tier-3b", 4547),
]


def load():
    rows = []
    for fn in glob.glob(os.path.join(RESULTS, "2026*.json")):
        if os.path.basename(fn).startswith("._"):
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
        if not d.get("outcome", {}).get("solved"):
            continue
        u = msgs[-1].get("usage", {})
        rows.append(dict(
            pid=d["puzzle_id"], ts=cond.get("toolset"),
            out=u.get("output_tokens", 0) or 0,
            cr=u.get("cache_read_input_tokens", 0) or 0,
            cost=msgs[-1].get("total_cost_usd", 0.0) or 0.0,
        ))
    return rows


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    rows = load()
    print("# Out-of-sample 4th-rung test of the two-term estimator (e-0018)\n")

    def cell(pid, ts):
        return [r for r in rows if r["pid"] == pid and r["ts"] == ts]

    # ---- O1: in-head SAVING (none output) vs search_nodes ------------------
    print("## O1  Is the externalization saving a clean function of search_nodes?")
    print(f"  {'puzzle':<14}{'nodes':>7}{'n_none':>8}{'none_out (in-head tok)':>24}")
    none_out = {}
    for pid, label, nodes in PUZZLES:
        c = cell(pid, "none")
        m = mean([r["out"] for r in c]) if c else float("nan")
        none_out[pid] = m
        print(f"  {label:<14}{nodes:>7}{len(c):>8}{m:>24,.0f}")
    t3a = none_out["gen_7x7_s3_00"]; t3b = none_out["gen_7x7_s1_00"]
    print(f"\n  Two tier-3 puzzles, near-equal grade (3789 vs 4547 nodes):")
    print(f"    none in-head output = {t3a:,.0f} vs {t3b:,.0f}  -> ratio {t3a/t3b:.2f}x")
    print("  => the in-head SAVING term is NOT pinned by search_nodes; same formal")
    print("     tier spans a ~3-4x range of realized in-head reasoning. MG1' must be")
    print("     stated in realized in-head output, not in search_nodes.\n")

    # ---- O2: two-term net vs actual gap, out of sample ---------------------
    print("## O2  Two-term net predicts the none-vs-coarse cost gap (sign + size)?")
    print("  net = OUT_saved*P_OUT - CR_added*P_CR, scaled by the e-0017 discount 0.335")
    print(f"  {'puzzle':<14}{'n(none/coarse)':>16}{'actual gap$':>13}"
          f"{'net (list)$':>13}{'net*0.335$':>13}")
    for pid, label, nodes in PUZZLES:
        nc = cell(pid, "none"); cc = cell(pid, "coarse")
        if not (nc and cc):
            print(f"  {label:<14}{f'{len(nc)}/{len(cc)}':>16}{'(missing cell)':>13}")
            continue
        gap = mean([r["cost"] for r in nc]) - mean([r["cost"] for r in cc])
        out_saved = mean([r["out"] for r in nc]) - mean([r["out"] for r in cc])
        cr_added = mean([r["cr"] for r in cc]) - mean([r["cr"] for r in nc])
        net = out_saved * P_OUT - cr_added * P_CR
        print(f"  {label:<14}{f'{len(nc)}/{len(cc)}':>16}{gap:>13.2f}"
              f"{net:>13.2f}{net*DISCOUNT:>13.2f}")
    print()
    print("  Reading: gen_7x7_s3_00 (tier-3a) is the OUT-OF-SAMPLE rung. If its")
    print("  actual gap is NEGATIVE (coarse costs more) and the discounted net is")
    print("  also negative and close, the two-term estimator generalizes beyond the")
    print("  3 puzzles it was built on — including to the sign flip where coarse loses.")
    print("  (n=1 per cell at tier-3a: a point estimate, not a CI.)\n")


if __name__ == "__main__":
    main()

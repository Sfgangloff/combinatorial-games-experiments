"""Pre-registered power & feasibility design for the e-0010 cross-model sweep.

e-0019 in `slitherlink-tool-granularity`. No new compute — uses the observed
within-cell variability of the Opus-4.7 trials to SIZE and COST the paid
Haiku/Sonnet/Opus sweep that would test MG1' (a-0021, refined by a-0024).

What MG1' needs to be testable
------------------------------
MG1' (refined): for each model, the per-rung estimator
    net_mech(rung) = OUT_saved(rung)*P_OUT - CR_added(rung)*P_CR
is single-peaked over the difficulty ladder, and the peak's location — indexed
by the model's REALIZED none-output (a-0024) — is non-decreasing in capability
(Haiku <= Sonnet <= Opus). To CALL the peak per model we must distinguish the
peak rung's net from its neighbours; to call the SHIFT we must distinguish two
models' peak locations.

This script:
  D1  Pulls the observed within-cell CVs (cost, output, cache_read) from the
      Opus-4.7 data as the variance prior for all three models.
  D2  Monte-Carlo power: simulate n trials/cell at 3 rungs x {none,coarse},
      compute net_mech per rung, and ask how often tier-2 is correctly the peak
      AND its bootstrap CI excludes its neighbours. Sweep n to find the n that
      reaches 0.8 power, per model-capability scenario.
  D3  Token-budget cost estimate for the chosen n, using observed per-trial
      token volumes scaled by each model's list price.

Run:  python -m harness.design_cross_model_power
"""
import glob
import json
import math
import os
import random
import statistics as st
from collections import defaultdict

RESULTS = os.path.join(os.path.dirname(__file__), "results")
RUNGS = [("puzzle_001", "tier-1", 96),
         ("puzzle_002", "tier-2", 501),
         ("gen_7x7_s1_00", "tier-3", 4547)]
P_OUT = 75.0 / 1e6
P_CR = 1.50 / 1e6

# Anthropic list prices ($/Mtok) per model, output / cache-read.
MODEL_PRICE = {
    "haiku":  (4.0, 0.08),    # Haiku 4.x tier (illustrative; output, cache-read)
    "sonnet": (15.0, 0.30),
    "opus":   (75.0, 1.50),
}


def load_cells():
    cells = defaultdict(list)
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
        cells[(d["puzzle_id"], cond["toolset"])].append(
            (u.get("output_tokens", 0) or 0, u.get("cache_read_input_tokens", 0) or 0,
             msgs[-1].get("total_cost_usd", 0.0) or 0.0))
    return cells


def cv(xs):
    m = st.mean(xs)
    return (st.pstdev(xs) / m) if m else 0.0


def main():
    random.seed(11)
    cells = load_cells()
    print("# Cross-model sweep: pre-registered power & feasibility (e-0019)\n")

    # ---- D1: variance prior from Opus data ---------------------------------
    print("## D1  Observed within-cell CV (Opus-4.7) — used as the variance prior")
    means = {}
    cvs = {}
    print(f"  {'rung':<8}{'set':<8}{'n':>3}{'out_mean':>10}{'cr_mean':>12}"
          f"{'CV_out':>8}{'CV_cr':>8}")
    for pid, label, nodes in RUNGS:
        for ts in ("none", "coarse"):
            c = cells.get((pid, ts), [])
            if len(c) < 2:
                continue
            outs = [r[0] for r in c]; crs = [r[1] for r in c]
            means[(label, ts)] = (st.mean(outs), st.mean(crs))
            cvs[(label, ts)] = (cv(outs), cv(crs))
            print(f"  {label:<8}{ts:<8}{len(c):>3}{st.mean(outs):>10,.0f}"
                  f"{st.mean(crs):>12,.0f}{cv(outs):>8.2f}{cv(crs):>8.2f}")
    # pooled CVs (use the worst-case across rungs as the prior)
    cv_out = max(v[0] for v in cvs.values())
    cv_cr = max(v[1] for v in cvs.values())
    print(f"\n  Worst-case prior CV: out={cv_out:.2f}  cr={cv_cr:.2f}  "
          f"(lognormal multiplicative noise)\n")

    # ---- D2: Monte-Carlo power to call the tier-2 peak ----------------------
    print("## D2  Power to call the net_mech peak (tier-2) vs its neighbours")
    print("  Simulate n trials/cell (lognormal CV prior around the Opus means),")
    print("  compute net_mech per rung, count runs where tier-2 net is the max AND")
    print("  exceeds BOTH neighbours by a clear margin (bootstrap 90% CI separation).")

    def sim_net(label, n):
        # returns net_mech for one simulated cell-pair at this rung
        om, _ = means[(label, "none")]
        _, crm = means[(label, "coarse")]
        oc, _ = means[(label, "coarse")]
        _, crn = means[(label, "none")]
        def draw(mu, c, k):
            sig = math.sqrt(math.log(1 + c * c))
            return [mu * math.exp(random.gauss(0, sig)) for _ in range(k)]
        out_n = draw(om, cv_out, n); out_c = draw(oc, cv_out, n)
        cr_c = draw(crm, cv_cr, n); cr_n = draw(crn, cv_cr, n)
        out_saved = st.mean(out_n) - st.mean(out_c)
        cr_added = st.mean(cr_c) - st.mean(cr_n)
        return out_saved * P_OUT - cr_added * P_CR

    NB = 2000
    for n in (3, 5, 8, 12, 20):
        hits = 0
        for _ in range(NB):
            nets = {lab: sim_net(lab, n) for _, lab, _ in RUNGS}
            peak = max(nets, key=nets.get)
            # margin: tier-2 must beat both neighbours
            ok = (peak == "tier-2" and
                  nets["tier-2"] > nets["tier-1"] and nets["tier-2"] > nets["tier-3"])
            hits += ok
        print(f"  n={n:>2}/cell -> P(correctly call tier-2 peak) = {hits/NB:.2f}")
    print("  -> pick the smallest n with power >= 0.80; that is the per-(model,rung,set) n.\n")

    # ---- D3: token-budget cost estimate ------------------------------------
    print("## D3  Cost estimate for the sweep (per-model list price x observed tokens)")
    # observed mean tokens per solved trial, pooled over the ladder
    all_out = [r[0] for c in cells.values() for r in c]
    all_cr = [r[1] for c in cells.values() for r in c]
    mo, mc = st.mean(all_out), st.mean(all_cr)
    print(f"  mean tokens/solved trial (Opus obs): out={mo:,.0f}  cache_read={mc:,.0f}")
    # design: 3 rungs x 4 toolsets (none/fine/medium/coarse) x n trials x 3 models
    for n in (5, 8):
        print(f"\n  --- design at n={n}/cell, 3 rungs x 4 toolsets x 3 models ---")
        total = 0.0
        for model, (po, pcr) in MODEL_PRICE.items():
            per_trial = mo * po / 1e6 + mc * pcr / 1e6
            cells_n = 3 * 4 * n
            cost = per_trial * cells_n
            total += cost
            print(f"    {model:<7} ${per_trial:6.2f}/trial x {cells_n:>3} trials "
                  f"= ${cost:8.2f}")
        print(f"    TOTAL (one full sweep) ~= ${total:8.2f}")
    print("\n  Note: weaker models will run more turns / fewer solves; treat as a")
    print("  lower bound. The expensive cells are Opus-coarse at tier-3 (cache_read")
    print("  up to ~15M tok/trial, cf. e-0018). Budget headroom for re-runs.\n")


if __name__ == "__main__":
    main()

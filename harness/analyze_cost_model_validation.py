"""Cost-model validation & trial-level hardening of the G-CD two-term estimator.

e-0017 in the `slitherlink-tool-granularity` stream. No new compute — reads the
existing solved-trial JSON in `harness/results/`.

Motivation
----------
e-0016 (a-0020) reproduces the Goldilocks dollar gap with a two-term token model
  net_mech = (OUT_saved)*P_OUT - (CR_added)*P_CR
and reports corr(net_mech, actual none-coarse gap) = 0.998. But that 0.998 is over
only THREE cell-mean points (one per difficulty rung), and the absolute split was
admitted to over-predict the gap (it ignores cache-creation and uncached-input).
Two unresolved robustness questions:

  V1  Does a FULL four-term list-price reconstruction
        cost_hat = OUT*P_OUT + CR*P_CR + CC*P_CC + IN*P_IN
      actually match the harness-billed `total_cost_usd` per trial? If yes, the
      list-price split is sound and the e-0016 caveat ("over-predicts") was a
      cell-mean artefact, not a pricing error. Quantify the per-trial residual.

  V2  Move the two-term estimator from 3 cell-means to all 42 trials. Regress
      per-trial actual cost on the externalization saving and the context tax
      computed AGAINST EACH RUNG's mean `none` baseline. Report n, R^2, and the
      fitted coefficients (should sit near the list prices P_OUT / P_CR if the
      two terms really are the cost drivers). This replaces a fragile 3-point
      correlation with a 42-point fit.

  V3  Bootstrap the none-coarse gap and the net_mech prediction per rung to put
      a confidence interval on the "single-peaked, peak at tier-2" headline —
      is the peak statistically distinguishable from the easy/hard rungs?

Run:  python -m harness.analyze_cost_model_validation
"""
import glob
import json
import math
import os
import random
import statistics as st

RESULTS = os.path.join(os.path.dirname(__file__), "results")

RUNGS = [
    ("puzzle_001", "tier-1 easy", 96),
    ("puzzle_002", "tier-2 mid", 501),
    ("gen_7x7_s1_00", "tier-3 hard", 4547),
]
TOOLSETS = ["none", "fine", "medium", "coarse"]

# Opus 4.7 list prices (USD/token), <=200k context tier.
P_OUT = 75.0 / 1e6
P_CR = 1.50 / 1e6
P_CC = 18.75 / 1e6     # 1h ephemeral cache write
P_IN = 15.0 / 1e6


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
        if d.get("puzzle_id") not in {r[0] for r in RUNGS}:
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


def ols2(X, y):
    """Two-regressor OLS through the origin: y ~ b1*x1 + b2*x2. Returns (b1,b2,R2).
    Closed form via normal equations on a 2x2 system."""
    s11 = sum(x[0] * x[0] for x in X)
    s12 = sum(x[0] * x[1] for x in X)
    s22 = sum(x[1] * x[1] for x in X)
    s1y = sum(x[0] * yy for x, yy in zip(X, y))
    s2y = sum(x[1] * yy for x, yy in zip(X, y))
    det = s11 * s22 - s12 * s12
    if det == 0:
        return float("nan"), float("nan"), float("nan")
    b1 = (s22 * s1y - s12 * s2y) / det
    b2 = (s11 * s2y - s12 * s1y) / det
    yhat = [b1 * x[0] + b2 * x[1] for x in X]
    sse = sum((yy - yh) ** 2 for yy, yh in zip(y, yhat))
    sst = sum(yy * yy for yy in y)  # through-origin R^2 (uncentered)
    r2 = 1 - sse / sst if sst else float("nan")
    return b1, b2, r2


def main():
    rows = load()
    print(f"# Cost-model validation (e-0017) — {len(rows)} solved meta-off ladder trials\n")

    # ===================================================================== V1
    print("## V1  Four-term list-price reconstruction vs billed total_cost_usd")
    print("  cost_hat = OUT*$75 + CR*$1.50 + CC*$18.75 + IN*$15  (per Mtok)\n")
    errs = []
    rel = []
    for r in rows:
        ch = r["out"] * P_OUT + r["cr"] * P_CR + r["cc"] * P_CC + r["inp"] * P_IN
        e = ch - r["cost"]
        errs.append(e)
        if r["cost"]:
            rel.append(e / r["cost"])
    rcorr = pearson([r["cost"] for r in rows],
                    [r["out"] * P_OUT + r["cr"] * P_CR + r["cc"] * P_CC + r["inp"] * P_IN
                     for r in rows])
    print(f"  corr(cost_hat, billed) = {rcorr:+.4f}   n={len(rows)}")
    print(f"  mean signed residual  = {mean(errs):+.4f} $   "
          f"(>0 = list price over-predicts)")
    print(f"  mean |relative error| = {mean([abs(x) for x in rel])*100:5.1f} %   "
          f"median = {st.median([abs(x) for x in rel])*100:5.1f} %")
    # which term explains the bulk?
    tot = {k: sum(r[k] * p for r in rows)
           for k, p in (("out", P_OUT), ("cr", P_CR), ("cc", P_CC), ("inp", P_IN))}
    tt = sum(tot.values())
    print("  cost share by term (list price, summed): "
          + "  ".join(f"{k}={v/tt*100:4.1f}%" for k, v in tot.items()))
    print("  -> if residual is small, the e-0016 two-term split is exact up to the")
    print("     CC/IN terms; if those terms are tiny, two-term is a faithful model.\n")

    # ===================================================================== V2
    print("## V2  Trial-level two-term estimator (n=42, not 3 cell-means)")
    print("  Per trial, vs its rung's mean `none` baseline:")
    print("    x1 = OUT_saved = out_none_bar - out_i   (externalization saving, tok)")
    print("    x2 = CR_added  = cr_i - cr_none_bar     (context tax, tok)")
    print("  Regress billed (none_bar_cost - cost_i) ~ b1*x1 + b2*x2 through origin.")
    print("  Two-term mechanism predicts b1≈P_OUT=7.5e-5, b2≈P_CR=1.5e-6.\n")
    base = {}
    for pid, label, nodes in RUNGS:
        nc = [r for r in rows if r["pid"] == pid and r["toolset"] == "none"]
        base[pid] = dict(out=mean([r["out"] for r in nc]),
                         cr=mean([r["cr"] for r in nc]),
                         cost=mean([r["cost"] for r in nc]))
    X, y, labels = [], [], []
    for r in rows:
        b = base[r["pid"]]
        x1 = b["out"] - r["out"]
        x2 = r["cr"] - b["cr"]
        ygap = b["cost"] - r["cost"]   # >0 = this trial cheaper than its none baseline
        X.append((x1, x2)); y.append(ygap); labels.append((r["pid"], r["toolset"]))
    b1, b2, r2 = ols2(X, y)
    print(f"  fitted b1 (per OUT-saved tok) = {b1:.3e}   (list P_OUT = {P_OUT:.3e})")
    print(f"  fitted b2 (per CR-added tok)  = {b2:.3e}   (list P_CR  = {P_CR:.3e})")
    print(f"  through-origin R^2 = {r2:.4f}   n={len(X)}")
    # correlation of the pure list-price net_mech with actual gap, trial level
    netmech = [x[0] * P_OUT - x[1] * P_CR for x in X]
    rtl = pearson(netmech, y)
    print(f"  corr(list-price net_mech, billed gap) at TRIAL level = {rtl:+.4f}")
    print("  (e-0016 reported 0.998 over 3 cell-means; this is the n=42 version)\n")

    # ===================================================================== V3
    print("## V3  Bootstrap CI on the none-coarse gap & net_mech peak (10k resamples)")
    random.seed(7)
    NB = 10000
    def cellrows(pid, ts):
        return [r for r in rows if r["pid"] == pid and r["toolset"] == ts]
    print(f"  {'rung':<13}{'billed gap $ (95% CI)':>30}{'net_mech $ (95% CI)':>28}")
    peak_counts = {pid: 0 for pid, *_ in RUNGS}
    boot_gap = {pid: [] for pid, *_ in RUNGS}
    for _ in range(NB):
        rung_gap = {}
        rung_net = {}
        for pid, label, nodes in RUNGS:
            nc = cellrows(pid, "none"); cc = cellrows(pid, "coarse")
            ns = [random.choice(nc) for _ in nc]
            cs = [random.choice(cc) for _ in cc]
            g = mean([r["cost"] for r in ns]) - mean([r["cost"] for r in cs])
            out_saved = mean([r["out"] for r in ns]) - mean([r["out"] for r in cs])
            cr_added = mean([r["cr"] for r in cs]) - mean([r["cr"] for r in ns])
            net = out_saved * P_OUT - cr_added * P_CR
            rung_gap[pid] = g; rung_net[pid] = net
            boot_gap[pid].append(g)
        peak = max(rung_net, key=rung_net.get)
        peak_counts[peak] += 1
    # report per-rung billed gap CI + a fresh net_mech bootstrap CI
    boot_net = {pid: [] for pid, *_ in RUNGS}
    for _ in range(NB):
        for pid, label, nodes in RUNGS:
            nc = cellrows(pid, "none"); cc = cellrows(pid, "coarse")
            ns = [random.choice(nc) for _ in nc]
            cs = [random.choice(cc) for _ in cc]
            out_saved = mean([r["out"] for r in ns]) - mean([r["out"] for r in cs])
            cr_added = mean([r["cr"] for r in cs]) - mean([r["cr"] for r in ns])
            boot_net[pid].append(out_saved * P_OUT - cr_added * P_CR)
    def ci(xs):
        xs = sorted(xs)
        return xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs))]
    for pid, label, nodes in RUNGS:
        glo, ghi = ci(boot_gap[pid]); nlo, nhi = ci(boot_net[pid])
        gm = mean(boot_gap[pid]); nm = mean(boot_net[pid])
        print(f"  {label:<13}{gm:>8.2f} [{glo:>6.2f},{ghi:>6.2f}]      "
              f"{nm:>8.2f} [{nlo:>6.2f},{nhi:>6.2f}]")
    print()
    print("  P(net_mech peak rung) over 10k bootstraps:")
    for pid, label, nodes in RUNGS:
        print(f"    {label:<13} {peak_counts[pid]/NB*100:5.1f}%")
    print("  -> if tier-2 dominates, the single-peaked Goldilocks shape is robust to")
    print("     resampling; if easy/hard CIs include 0 while mid excludes 0, the peak")
    print("     is statistically real, not a 3-point coincidence.\n")


if __name__ == "__main__":
    main()

"""
Paper 3: decision curve analysis and calibration (§10.5), temporal validation 2017-2019.

Decision curves. Net benefit = TP/n - FP/n x pt/(1-pt), over patient-landmarks, for M0+A, M1-D,
treat-all and treat-none, across 1-30% threshold probability. The upper end is well above the
7.5% event rate and covers the top-10% flag's PPV region (~39%) only partly by design: beyond
30% so few landmarks are flagged that net benefit is uninformative. ΔNB (M1-D - M0+A) is given
at 5, 10, 15 and 20% with a patient-level clustered bootstrap CI.

Calibration. Observed against predicted by decile of predicted risk, with Wilson 95% intervals,
and the calibration intercept (offset logistic regression) and slope. Because the event rate
falls from 10.0% to 7.5% between eras (§10.6), over-prediction is expected; the pre-specified
intercept-only recalibration is shown alongside.

Figures are written as PDF (vector, for submission) and PNG (for review).
Palette: categorical slots 1 and 2 of the reference palette, validated; model identity is also
carried by line style and direct labels so the figures survive grayscale printing.
"""
import os as _os
_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # repository root
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import brentq
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression

P3 = _REPO_ROOT + "/08_paper3_multimodal"
FIG = f"{P3}/figures"
SEED = 20260917
REPS = 2000
C_M0, C_M1 = "#2a78d6", "#eb6834"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "pdf.fonttype": 42, "savefig.dpi": 300,
})

v = pd.read_csv(f"{P3}/m1_validation_predictions.csv")
y = v.composite_event.to_numpy()
P = {"M0+A": v["M0+A"].to_numpy(), "M1-D": v["M1-D"].to_numpy()}
stay = v.stay_id.to_numpy()
n = len(y)


def net_benefit(yy, p, pt):
    flag = p >= pt
    tp = (flag & (yy == 1)).sum()
    fp = (flag & (yy == 0)).sum()
    return tp / len(yy) - fp / len(yy) * pt / (1 - pt)


def calib(yy, p):
    z = logit(np.clip(p, 1e-6, 1 - 1e-6))
    icpt = brentq(lambda a: (yy - expit(a + z)).sum(), -10, 10)
    slope = LogisticRegression(max_iter=2000, C=1e6).fit(z.reshape(-1, 1), yy).coef_[0, 0]
    return icpt, slope


def wilson(k, m, zc=1.96):
    ph = k / m
    den = 1 + zc ** 2 / m
    c = (ph + zc ** 2 / (2 * m)) / den
    h = zc * np.sqrt(ph * (1 - ph) / m + zc ** 2 / (4 * m ** 2)) / den
    return c - h, c + h


# ----------------------------------------------------------------------------- decision curve
pts = np.linspace(0.01, 0.30, 59)
nb = {m: np.array([net_benefit(y, p, t) for t in pts]) for m, p in P.items()}
prev = y.mean()
nb_all = prev - (1 - prev) * pts / (1 - pts)

rng = np.random.default_rng(SEED)
patients, inverse = np.unique(stay, return_inverse=True)
members = [np.flatnonzero(inverse == i) for i in range(len(patients))]
at = [0.05, 0.10, 0.15, 0.20]
boot = {t: [] for t in at}
for _ in range(REPS):
    pos = np.concatenate([members[i] for i in rng.integers(0, len(patients), len(patients))])
    for t in at:
        boot[t].append(net_benefit(y[pos], P["M1-D"][pos], t) - net_benefit(y[pos], P["M0+A"][pos], t))

print(f"validation: {n} landmarks, {int(y.sum())} events ({100*prev:.2f}%)")
print("\nΔ net benefit, M1-D - M0+A (per 100 patient-landmarks), patient-level bootstrap")
dnb = []
for t in at:
    obs = net_benefit(y, P["M1-D"], t) - net_benefit(y, P["M0+A"], t)
    lo, hi = np.percentile(boot[t], [2.5, 97.5])
    dnb.append({"threshold": t, "nb_M0A": net_benefit(y, P["M0+A"], t),
                "nb_M1D": net_benefit(y, P["M1-D"], t), "delta": obs, "lo": lo, "hi": hi})
    print(f"  pt {int(100*t):2d}%  NB M0+A {100*net_benefit(y, P['M0+A'], t):.2f}  "
          f"M1-D {100*net_benefit(y, P['M1-D'], t):.2f}  Δ {100*obs:+.2f} [{100*lo:+.2f}, {100*hi:+.2f}]")
pd.DataFrame(dnb).to_csv(f"{P3}/dca_delta_net_benefit.csv", index=False)

fig, ax = plt.subplots(figsize=(4.6, 3.4))
ax.grid(True, color=GRID, linewidth=0.5)
ax.set_axisbelow(True)
ax.axhline(0, color=INK2, linewidth=1.0, linestyle=(0, (1, 1.5)), label="Treat none")
ax.plot(100 * pts, 100 * nb_all, color=INK2, linewidth=1.0, linestyle=(0, (4, 2)), label="Treat all")
ax.plot(100 * pts, 100 * nb["M0+A"], color=C_M0, linewidth=2.0, label="M0+A")
ax.plot(100 * pts, 100 * nb["M1-D"], color=C_M1, linewidth=2.0, linestyle=(0, (6, 2)), label="M1-D")
ax.set_xlim(1, 30)
ax.set_ylim(-1, 100 * prev + 0.8)
ax.set_xlabel("Threshold probability (%)")
ax.set_ylabel("Net benefit (per 100 patient-landmarks)")
ax.legend(frameon=False, loc="upper right", fontsize=8, handlelength=2.6)
ax.text(1.4, 100 * prev + 0.25, f"event rate {100*prev:.1f}%", color=INK2, fontsize=7.5, va="bottom")
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(f"{FIG}/fig_decision_curve.{ext}")
plt.close(fig)

# -------------------------------------------------------------------------------- calibration
print("\ncalibration, temporal validation")
rows = []
fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.5), sharey=True)
LIM = 0.55
for ax, (m, p), col, ls in zip(axes, P.items(), (C_M0, C_M1), ("-", (0, (6, 2)))):
    icpt, slope = calib(y, p)
    recal = expit(logit(np.clip(p, 1e-6, 1 - 1e-6)) + icpt)
    i2, s2 = calib(y, recal)
    rows.append({"model": m, "intercept": icpt, "slope": slope, "mean_pred": p.mean(),
                 "observed": y.mean(), "recal_intercept": i2, "recal_slope": s2})
    print(f"  {m}: intercept {icpt:+.3f}, slope {slope:.3f}, mean predicted {100*p.mean():.2f}% "
          f"vs observed {100*y.mean():.2f}% | after intercept-only recalibration: "
          f"intercept {i2:+.3f}, slope {s2:.3f}")

    bins = pd.qcut(p, 10, labels=False, duplicates="drop")
    g = pd.DataFrame({"p": p, "r": recal, "y": y, "b": bins}).groupby("b")
    mp, mr, ob, k, cnt = g.p.mean(), g.r.mean(), g.y.mean(), g.y.sum(), g.y.size()
    lo, hi = wilson(k.to_numpy(), cnt.to_numpy())

    ax.grid(True, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    diag = np.linspace(0, LIM, 200)
    ax.plot(diag, diag, color=INK2, linewidth=1.0, linestyle=(0, (1, 1.5)))
    ax.vlines(mp, lo, hi, color=col, linewidth=1.2, alpha=0.9)
    ax.plot(mp, ob, color=col, linewidth=2.0, linestyle=ls, marker="o", markersize=5,
            markeredgecolor="white", markeredgewidth=1.2, label="As fitted")
    ax.plot(mr, ob, color=INK2, linewidth=1.0, linestyle=(0, (4, 2)), marker="s", markersize=3.5,
            markerfacecolor="white", markeredgecolor=INK2, label="Intercept recalibrated")
    # square-root scale on both axes: predicted risk is heavily right-skewed, so on a linear axis
    # eight deciles crowd the origin; the identity line stays straight under the same transform
    for setter in (ax.set_xscale, ax.set_yscale):
        setter("function", functions=(np.sqrt, np.square))
    ticks = [0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels([f"{t:g}" for t in ticks])
    ax.set_yticklabels([f"{t:g}" for t in ticks])
    ax.set_xlim(0, LIM)
    ax.set_ylim(0, LIM)
    ax.set_aspect("equal")
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    ax.set_title(m, loc="left", fontsize=10, color=INK, fontweight="bold")
    ax.set_xlabel("Predicted risk, decile mean (√ scale)")
    ax.text(0.02, LIM - 0.02, f"intercept {icpt:+.2f}\nslope {slope:.2f}", color=INK2,
            fontsize=8, va="top", ha="left")
axes[0].set_ylabel("Observed 24-h event rate (√ scale)")
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(f"{FIG}/fig_calibration.{ext}")
plt.close(fig)
pd.DataFrame(rows).to_csv(f"{P3}/calibration_validation.csv", index=False)
print(f"\nSaved figures to {FIG}: fig_decision_curve, fig_calibration (.pdf, .png)")

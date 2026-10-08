"""
Paper 3: Figure 1 (study design) and Figure 4 (post hoc redundancy analysis).

Every number drawn comes from manuscript/numbers.json; nothing is typed. Palette: reference categorical
slots 1–2 (validated with 51); text stays in ink, colour marks only.
Writes figures/fig1_study_design.{pdf,png} and figures/fig4_redundancy.{pdf,png}.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = Path(__file__).parent
N = json.load(open(HERE / "manuscript" / "numbers.json"))
FIG = HERE / "figures"
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID, FILL = "#0b0b0b", "#52514e", "#e4e3df", "#f3f2ee"
plt.rcParams.update({
    "font.family": ["Helvetica", "Arial Unicode MS", "DejaVu Sans"], "font.size": 8.5,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
    "pdf.fonttype": 42, "savefig.dpi": 300,
})


def n(k, d=0):
    v = N[k]
    return f"{v:,.{d}f}"


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)


# =============================================================================== Figure 4
def figure4():
    rows = [("Demographic and clinical\ncharacteristics, imaging availability", "B1"),
            ("+ filtered dynamic state", "B2"),
            ("+ Glasgow Coma Scale\neye and motor scores", "B3"),
            ("+ all physiology and treatment\n(imaging-availability baseline)", "B4")]
    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    ys = list(range(len(rows)))[::-1]
    ax.axvline(0, color=INK2, linewidth=0.9, linestyle=(0, (1, 1.5)), zorder=1)
    for y, (label, b) in zip(ys, rows):
        d, lo, hi = N[f"redund.{b}.d_capture"], N[f"redund.{b}.d_capture_lo"], N[f"redund.{b}.d_capture_hi"]
        ax.plot([lo, hi], [y, y], color=BLUE, linewidth=2.0, solid_capstyle="round", zorder=2)
        ax.plot(d, y, "o", color=BLUE, markersize=7, markeredgecolor="white", markeredgewidth=1.4, zorder=3)
        ax.text(19.6, y, f"{N[f'redund.{b}.capture_base']:.1f} → {N[f'redund.{b}.capture_img']:.1f}",
                ha="left", va="center", color=INK, fontsize=8.5)
        ax.text(27.4, y, f"{d:+.2f} ({lo:.2f} to {hi:.2f})".replace("-", "−"), ha="left", va="center", color=INK, fontsize=8.5)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5, color=INK)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(-7, 19)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xticks([-5, 0, 5, 10, 15])
    ax.set_xticklabels(["−5", "0", "5", "10", "15"])
    ax.grid(axis="x", color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("Change in top-10% event capture from adding imaging phenotypes, percentage points (95% CI)")
    top = len(rows) - 0.4
    ax.text(19.6, top + 0.12, "Capture, %\nbaseline → with imaging", ha="left", va="bottom", color=INK2, fontsize=7.8)
    ax.text(27.4, top + 0.12, "Difference\n(95% CI)", ha="left", va="bottom", color=INK2, fontsize=7.8)
    ax.text(-7, top + 0.55, "Baselines are nested: each row adds to all rows above it (post hoc)",
            ha="left", va="bottom", color=INK2, fontsize=7.8)
    save(fig, "fig4_redundancy")


# =============================================================================== Figure 1
def box(ax, x, y, w, h, text, fc=FILL, ec=INK2, lw=0.8, fs=7.4, weight="normal", color=INK, ha="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.10", fc=fc, ec=ec, lw=lw))
    tx = x + w / 2 if ha == "center" else x + 0.18
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs, color=color, fontweight=weight, linespacing=1.3)


def arrow(ax, x1, y1, x2, y2, color=INK2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=0.8, shrinkA=0, shrinkB=0, mutation_scale=8))


def side_exclusion(ax, x_line, y, x_box, w, text):
    ax.plot([x_line, x_box], [y, y], color=INK2, lw=0.8)
    box(ax, x_box, y - 0.5, w, 1.0, text, fc="white", fs=6.9, ha="left")


def figure1():
    fig = plt.figure(figsize=(7.2, 7.9))
    FLOOR, WIN, HOR, LAST = (int(N["design.report_floor_h"]), N["design.window_h"], N["design.horizon_h"],
                             N["design.last_landmark_h"])

    # ---------------------------------------------------------------- A: participants and reports
    ax = fig.add_axes([0.01, 0.535, 0.98, 0.455])
    ax.set_xlim(0, 20.4); ax.set_ylim(0.6, 13); ax.axis("off")
    ax.text(0.1, 12.9, "A", fontsize=11, fontweight="bold", color=INK, va="top")
    ax.text(0.75, 12.85, "Participants and radiology reports", fontsize=9, color=INK, va="top")

    L, LW = 0.2, 5.7                                   # participants column
    cx = L + LW / 2
    box(ax, L, 10.5, LW, 1.5, f"Adults in intensive care after\nacute stroke, MIMIC-IV\n{n('flow.source_cohort')} patients")
    box(ax, L, 7.9, LW, 1.1, f"Admitted 2008–2019\n{n('flow.note_era_patients')} patients")
    box(ax, L, 5.3, LW, 1.1, f"≥1 eligible landmark\n{n('flow.analysis_patients')} patients · {n('cohort.all.landmarks')} patient-landmarks",
        weight="bold")
    arrow(ax, cx, 10.5, cx, 9.0); arrow(ax, cx, 7.9, cx, 6.4)
    side_exclusion(ax, cx, 9.75, 6.2, 3.7, f"Admitted 2020–2022, no\nradiology reports ({n('flow.excluded_2020_2022')})")
    side_exclusion(ax, cx, 7.15, 6.2, 3.7, f"No eligible landmark\n({n('flow.excluded_no_eligible_landmark')})")
    ax.plot([cx, cx], [5.3, 4.75], color=INK2, lw=0.8)
    ax.plot([2.45, 7.65], [4.75, 4.75], color=INK2, lw=0.8)
    for i, (lab, key, yrs) in enumerate([("Development", "dev", "2008–2016"), ("Temporal validation", "val", "2017–2019")]):
        bx = 0.2 + i * 5.2
        arrow(ax, bx + 2.25, 4.75, bx + 2.25, 4.3)
        box(ax, bx, 1.6, 4.5, 2.7,
            f"{lab}\n{yrs}\n{n(f'cohort.{key}.patients')} patients\n{n(f'cohort.{key}.landmarks')} patient-landmarks\n"
            f"{n(f'cohort.{key}.events')} events ({N[f'cohort.{key}.event_rate_pct']:.1f}%)", fs=7.2)

    R, RW = 10.6, 5.7                                  # reports column
    rx = R + RW / 2
    box(ax, R, 10.5, RW, 1.5, f"Head CT/MRI reports of the\nindex admission, stored by {LAST} h\n{n('reports.analysis_population')} reports")
    box(ax, R, 7.9, RW, 1.1, f"Extracted by a local\nlanguage model: {n('reports.extracted')}")
    box(ax, R, 5.3, RW, 1.1, f"Eligible for use at landmarks\n{n('reports.eligible_after_floor')} reports", weight="bold")
    arrow(ax, rx, 10.5, rx, 9.0); arrow(ax, rx, 7.9, rx, 6.4)
    side_exclusion(ax, rx, 9.75, 16.6, 3.75, f"Could not be\nprocessed ({n('reports.quarantined')})")
    side_exclusion(ax, rx, 7.15, 16.6, 3.75, f"Stored >{FLOOR} h before ICU\nadmission ({n('reports.floor_excluded')})")
    ax.add_patch(FancyBboxPatch((R, 1.6), 9.75, 2.7, boxstyle="round,pad=0,rounding_size=0.10", fc="white",
                                ec=INK2, lw=0.8, linestyle=(0, (3, 2)), zorder=0))
    box(ax, R, 1.6, 9.75, 2.7,
        f"Validation of automated extraction (separate sample)\n"
        f"developed on {n('extraction.dev_reports')} reports; validated on {n('extraction.val_reports')} random reports\n"
        f"against blinded annotation by one trained annotator\n"
        f"entry: κ ≥ {N['extraction.kappa_threshold']:.2f} and ≥{n('extraction.min_positives')} annotator-positive reports\n"
        f"→ {n('extraction.phenotypes_passing')} of {n('extraction.phenotypes_candidate')} phenotypes and "
        f"{n('extraction.locations_passing')} location categories", fs=7.2, fc="none", ec="none")
    ax.text(R, 1.25, "Midline shift, intraventricular haemorrhage, intracranial haemorrhage; intraparenchymal\n"
                     "and subarachnoid compartment; middle cerebral artery territory; cerebellum",
            fontsize=6.8, color=INK2, va="top", linespacing=1.3)

    # ---------------------------------------------------------------- B: landmark timeline
    bx = fig.add_axes([0.08, 0.28, 0.88, 0.175])
    fig.text(0.01, 0.505, "B", fontsize=11, fontweight="bold", color=INK, va="top")
    fig.text(0.045, 0.502, f"Repeated landmarks (the {HOR}-hour landmark as an example)", fontsize=9, color=INK, va="top")
    PRE = HOR / FLOOR                                   # compress the hours before ICU admission

    def X(h):
        return h * PRE if h < 0 else h
    bx.set_xlim(X(-FLOOR) - 2, LAST + HOR + 2); bx.set_ylim(0, 3.6)
    bx.spines["left"].set_visible(False); bx.set_yticks([])
    ticks = [-FLOOR, 0] + list(range(WIN, LAST + 1, WIN)) + [LAST + HOR]
    bx.set_xticks([X(t) for t in ticks])
    bx.set_xticklabels([("−" + str(-t)) if t < 0 else str(t) for t in ticks], fontsize=7.2)
    bx.set_xlabel("Hours from ICU admission (before admission compressed)", fontsize=7.8)
    bx.text(X(-FLOOR / 2), -0.02, "//", transform=bx.get_xaxis_transform(), ha="center", va="center", fontsize=9,
            color=INK2, backgroundcolor="white")
    EX = HOR                                            # the example landmark
    for h in range(WIN, LAST + 1, WIN):
        c = BLUE if h == EX else INK2
        bx.plot([h, h], [0, 0.45], color=c, lw=0.9 if h != EX else 1.3)
        bx.plot(h, 0.45, "v", color=c, markersize=4.5 if h != EX else 6.5)
    bx.text(LAST + 1.5, 0.3, f"landmarks every {WIN} h", fontsize=6.9, color=INK2, va="center")
    bx.add_patch(Rectangle((X(0), 0.8), EX, 0.6, fc=BLUE, alpha=0.18, ec="none"))
    bx.text(EX / 2, 1.55, "predictors", ha="center", va="bottom", fontsize=7.2, color=INK)
    bx.add_patch(Rectangle((EX, 0.8), HOR, 0.6, fc=ORANGE, alpha=0.22, ec="none"))
    bx.text(EX + HOR / 2, 1.55, f"outcome within {HOR} h", ha="center", va="bottom", fontsize=7.2, color=INK)
    bx.plot([EX, EX], [0.45, 3.1], color=BLUE, lw=1.2)
    bx.text(EX + 0.8, 3.1, "prediction boundary", fontsize=7.2, color=INK, va="top")
    bx.add_patch(Rectangle((X(-FLOOR), 2.1), EX - X(-FLOOR), 0.55, fc=FILL, ec=INK2, lw=0.6))
    bx.text((X(-FLOOR) + EX) / 2, 2.375, f"report usable if stored after −{FLOOR} h and before the landmark",
            ha="center", va="center", fontsize=6.9, color=INK)
    bx.text(X(-FLOOR), 3.45, "Eligible: in the ICU and not already in the adverse state (filtered state).  "
                          "Outcome: entry into the adverse state, or death.", fontsize=6.9, color=INK2, va="top")

    # ---------------------------------------------------------------- C: model sequence
    cxa = fig.add_axes([0.01, 0.0, 0.98, 0.215])
    cxa.set_xlim(0, 20.4); cxa.set_ylim(0, 6); cxa.axis("off")
    fig.text(0.01, 0.222, "C", fontsize=11, fontweight="bold", color=INK, va="top")
    fig.text(0.045, 0.219, "Models, each adding one source of information", fontsize=9, color=INK, va="top")
    specs = [("Dynamic-state\nbaseline (M0-state)", "demographics, comorbidity,\nfiltered state"),
             ("Full physiological\nbaseline (M0-full)", "+ physiology, laboratory,\ntreatment"),
             ("Imaging-availability\nbaseline (M0+A)", "+ whether a report\nwas available"),
             ("Imaging-augmented\nmodel (M1-D)", "+ imaging\nphenotypes")]
    w, gap, x0 = 4.35, 0.8, 0.2
    for i, (name, add) in enumerate(specs):
        x = x0 + i * (w + gap)
        ec, lw = (BLUE, 1.4) if i >= 2 else (INK2, 0.8)
        box(cxa, x, 2.4, w, 1.3, name, ec=ec, lw=lw, fs=7.4)
        cxa.text(x + w / 2, 2.2, add, ha="center", va="top", fontsize=6.9, color=INK2, linespacing=1.3)
        if i:
            arrow(cxa, x - gap, 3.05, x, 3.05)
    xa, xd = x0 + 2 * (w + gap) + w / 2, x0 + 3 * (w + gap) + w / 2
    cxa.plot([xa, xa, xd, xd], [3.7, 4.2, 4.2, 3.7], color=BLUE, lw=1.2)
    cxa.text((xa + xd) / 2, 4.3, "Primary comparison: top-10% event capture\nin temporal validation",
             ha="center", va="bottom", fontsize=7.2, color=INK, linespacing=1.3)
    cxa.text(x0, 0.1, "Availability-adjusted imaging-information model (M1-I): imaging phenotypes among landmarks with a report,\n"
                      "weighted for who was imaged — an information-content analysis, not a deployment model.",
             fontsize=6.9, color=INK2, va="bottom", linespacing=1.3)
    save(fig, "fig1_study_design")


figure4()
figure1()
print("written figures/fig1_study_design and figures/fig4_redundancy (.pdf, .png)")

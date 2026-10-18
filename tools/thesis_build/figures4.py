"""Regenerate the Chapter 4 result figures from the single campaign.

Every figure here is drawn from the same database the dashboard reads, so a
figure in the thesis and the same view in the interface cannot disagree. Colour
is assigned per framework and never per rank, so a framework keeps its hue
whichever chart it appears in; the plain-NumPy control is drawn dashed
throughout so it never reads as a competitor.
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import campaign_data as CD

sys.path.insert(0, "/root/work/cpu/final/dashboard")
import dashboard_data as dd            # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "figs"
OUT.mkdir(exist_ok=True)

INK, SOFT, MUTE = "#16202f", "#3c4a60", "#67768d"
GRID, BORDER = "#e3e9f1", "#c3cedd"
COLOR = {"brian2": "#c2521c", "nest": "#2a6fd0", "snntorch": "#0e8a63",
         "spikingjelly": "#7a4fbf", "nengo": "#a8760b", "reference": "#b03a6a"}
DASH = {"numpy": (0, ()), "cython": (0, (5, 2)), "cpp_standalone": (0, (1, 2)),
        "threads1": (0, ()), "threads2": (0, (5, 2)),
        "scalar": (0, (4, 2)), "vectorised": (0, (1, 2))}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "text.color": INK,
    "axes.edgecolor": BORDER, "axes.labelcolor": SOFT,
    "xtick.color": MUTE, "ytick.color": MUTE,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.12,
})


def style(ax, *, xlabel="", ylabel="", grid_axis="x"):
    ax.set_xlabel(xlabel, fontsize=8.5)
    ax.set_ylabel(ylabel, fontsize=8.5)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def save(fig, name):
    fig.savefig(OUT / name, facecolor="white")
    plt.close(fig)
    print("  wrote", name)


INF = CD.inference()
SCAL = CD.scalability()
SIZES = CD.summary()["sizes"]


def fig_4_1():
    """Inference runtime at the reference size, with the measured range."""
    rows = list(reversed(INF))
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    y = range(len(rows))
    for i, c in zip(y, rows):
        col = COLOR[c["framework"]]
        lo, hi = min(c["runs"]) * 1000, max(c["runs"]) * 1000
        ax.barh(i, c["runtime_median_s"] * 1000, height=0.6, color=col,
                alpha=.9, zorder=3)
        ax.plot([lo, hi], [i, i], color=INK, linewidth=1.1, zorder=4)
        ax.plot([lo, hi], [i, i], "|", color=INK, markersize=4, zorder=4)
    ax.set_yticks(list(y))
    ax.set_yticklabels([c["id"] for c in rows], fontsize=7.6)
    ax.set_xscale("log")
    style(ax, xlabel="median runtime per run, milliseconds (log scale)")
    ax.set_title("the bar is the median of five runs; the line is the full "
                 "measured range", fontsize=7.4, color=MUTE, loc="left",
                 pad=6)
    save(fig, "fig-4-1.png")


def fig_4_2():
    """Runtime against network size, log-log."""
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for s in SCAL:
        xs = [n for n, _ in s["points"]]
        ys = [c["runtime_median_s"] for _, c in s["points"]]
        ax.plot(xs, ys, marker="o", markersize=4, linewidth=1.6,
                color=COLOR[s["framework"]],
                linestyle=DASH.get(s["backend"], (0, ())),
                label=s["id"], zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    style(ax, xlabel="network size, neurons (log scale)",
          ylabel="median runtime, seconds (log scale)", grid_axis="both")
    ax.legend(fontsize=6.6, frameon=False, ncol=2, loc="upper left")
    save(fig, "fig-4-2.png")


def fig_4_3():
    """Fitted scaling exponents with their confidence intervals."""
    rows = [s for s in SCAL if s["fit"]]
    rows.sort(key=lambda s: s["fit"]["k"])
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for i, s in enumerate(rows):
        f = s["fit"]
        col = COLOR[s["framework"]]
        ax.plot([f["ci"][0], f["ci"][1]], [i, i], color=col, linewidth=2,
                solid_capstyle="round", zorder=3)
        ax.plot(f["k"], i, "o", color=col, markersize=5,
                markeredgecolor="white", markeredgewidth=.9, zorder=4)
    ax.axvline(1.0, color=MUTE, linestyle=(0, (4, 3)), linewidth=1)
    ax.text(1.02, len(rows) - .4, "cost proportional to size", fontsize=7,
            color=MUTE)
    ax.axvline(0.0, color=BORDER, linewidth=1)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([s["id"] for s in rows], fontsize=7.6)
    style(ax, xlabel="fitted scaling exponent k, with 95% interval")
    save(fig, "fig-4-3.png")


def fig_4_4():
    """Speed rank at each network size."""
    series = {s["id"]: {n: c["runtime_median_s"] for n, c in s["points"]}
              for s in SCAL}
    fw = {s["id"]: s["framework"] for s in SCAL}
    ranks = {}
    for n in SIZES:
        order = sorted((v[n], k) for k, v in series.items() if n in v)
        for pos, (_t, k) in enumerate(order, 1):
            ranks.setdefault(k, {})[n] = pos
    ordered = sorted(ranks, key=lambda k: ranks[k].get(SIZES[-1], 99))
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for k in ordered:
        xs = [n for n in SIZES if n in ranks[k]]
        ys = [ranks[k][n] for n in xs]
        ax.plot(xs, ys, marker="o", markersize=4.5, linewidth=1.6,
                color=COLOR[fw[k]], label=k, zorder=3)
        # A series that stops short of the largest size would otherwise put
        # its label on top of one that reaches the end, so short series are
        # labelled at their own last point and nudged clear.
        short = xs[-1] != SIZES[-1]
        ax.annotate(k, (xs[-1], ys[-1]), textcoords="offset points",
                    xytext=(6, 7 if short else 0), fontsize=6.8,
                    color=COLOR[fw[k]], va="center")
    ax.set_xscale("log")
    ax.invert_yaxis()
    ax.set_yticks(range(1, len(ordered) + 1))
    style(ax, xlabel="network size, neurons (log scale)",
          ylabel="rank by runtime (1 = fastest)", grid_axis="y")
    ax.set_xlim(SIZES[0] * .8, SIZES[-1] * 3.2)
    ax.set_title("a line that crosses another is a recommendation that changes "
                 "with the size measured", fontsize=7.4, color=MUTE,
                 loc="left", pad=6)
    save(fig, "fig-4-4.png")


def fig_4_5():
    """Peak resident set size across the sweep."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for s in SCAL:
        xs = [n for n, _ in s["points"]]
        ys = [c["peak_rss_mb"] for _, c in s["points"]]
        ax.plot(xs, ys, marker="o", markersize=4, linewidth=1.6,
                color=COLOR[s["framework"]],
                linestyle=DASH.get(s["backend"], (0, ())), label=s["id"],
                zorder=3)
    ax.set_xscale("log")
    style(ax, xlabel="network size, neurons (log scale)",
          ylabel="peak resident set size, MB", grid_axis="both")
    ax.legend(fontsize=6.6, frameon=False, ncol=2, loc="upper left")
    save(fig, "fig-4-5.png")


def fig_4_6():
    """Energy proxy against the analytic operation count, one panel per
    framework."""
    by_fw = {}
    for s in SCAL:
        by_fw.setdefault(s["framework"], []).append(s)
    fws = [f for f in COLOR if f in by_fw]
    fig, axes = plt.subplots(1, len(fws), figsize=(7.2, 2.4), sharey=True)
    for ax, f in zip(axes, fws):
        for s in by_fw[f]:
            xs = [c["eflop"] for _, c in s["points"] if c["eflop"]]
            ys = [c["energy_median_j"] for _, c in s["points"] if c["eflop"]]
            ax.plot(xs, ys, marker="o", markersize=3.5, linewidth=1.3,
                    color=COLOR[f], linestyle=DASH.get(s["backend"], (0, ())),
                    zorder=3)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(CD.LABEL[f], fontsize=7.6, color=COLOR[f])
        style(ax, xlabel="", ylabel="", grid_axis="both")
        ax.tick_params(labelsize=6.2)
    axes[0].set_ylabel("energy proxy, J", fontsize=8)
    fig.supxlabel("analytic operation count (log scale)", fontsize=8,
                  color=SOFT, y=-0.04)
    save(fig, "fig-4-6.png")


def fig_4_7():
    """Rank agreement with the ordering at the largest network size."""
    sens = dd.get_sensitivity()
    rows = [r for r in sens["size_stability"]]
    fig, ax = plt.subplots(figsize=(6.0, 2.9))
    xs = [f"{r['n']:,}" for r in rows]
    ys = [r["tau"] for r in rows]
    cols = ["#0e8a63" if v >= .8 else "#a8760b" if v >= .5 else "#c2521c"
            for v in ys]
    ax.bar(xs, ys, color=cols, width=.55, zorder=3)
    for x, v in zip(xs, ys):
        ax.text(x, v + .03, f"{v:.3f}", ha="center", fontsize=7.4, color=INK)
    ax.axhline(1.0, color=MUTE, linestyle=(0, (4, 3)), linewidth=1)
    ax.set_ylim(0, 1.16)
    style(ax, xlabel="network size at which the ordering was measured",
          ylabel="Kendall's tau against N = 10,000", grid_axis="y")
    save(fig, "fig-4-7.png")


def fig_4_8():
    """Rank agreement between metric orderings and the runtime ordering."""
    sens = dd.get_sensitivity()
    rows = sens["metric_stability"]
    fig, ax = plt.subplots(figsize=(6.0, 2.9))
    xs = [r["metric"] for r in rows]
    ys = [r["tau"] for r in rows]
    cols = ["#0e8a63" if v >= .8 else "#a8760b" if v >= .5 else "#c2521c"
            for v in ys]
    ax.bar(xs, ys, color=cols, width=.55, zorder=3)
    for x, v in zip(xs, ys):
        ax.text(x, v + (.03 if v >= 0 else -.09), f"{v:.3f}", ha="center",
                fontsize=7.4, color=INK)
    ax.axhline(0, color=BORDER, linewidth=1)
    ax.set_ylim(min(-.35, min(ys) - .15), 1.16)
    ax.tick_params(axis="x", labelsize=7.4)
    style(ax, xlabel="metric the backends are ranked by",
          ylabel="Kendall's tau against the runtime ordering", grid_axis="y")
    save(fig, "fig-4-8.png")


if __name__ == "__main__":
    for f in (fig_4_1, fig_4_2, fig_4_3, fig_4_4, fig_4_5, fig_4_6, fig_4_7,
              fig_4_8):
        f()
    print("  chapter 4 figures regenerated")

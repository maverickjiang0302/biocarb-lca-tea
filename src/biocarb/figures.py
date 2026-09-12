"""All figures are generated from results/*.csv so that they can be regenerated without re-running the model."""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .params import ROOT
from . import inventory as I, lca as L

RES = ROOT / "results"; FIG = ROOT / "figures"
LABEL = {"IL_A": "Type IL\n(dry-mix)", "IL_B": "Type IL\n(ready-mix)", "FA_A": "IL+30% FA\n(dry-mix)", "FA_B": "IL+30% FA\n(ready-mix)",
         "BC_A": "BioCarb\n(dry-mix)", "BC_B": "BioCarb\n(ready-mix)", "LC3_A": "LC3-50\n(dry-mix)", "LC3_B": "LC3-50\n(ready-mix)"}
COL = {"IL": "#7f7f7f", "FA": "#d99a4a", "BC": "#3b8a4a", "LC3": "#4a72b8"}
SHORT = {"IL": "Type IL", "FA": "IL + 30%\nfly ash", "LC3": "LC3-50", "BC": "BioCarb"}
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
                     "font.size": 11, "axes.labelsize": 11, "axes.titlesize": 11, "xtick.labelsize": 10, "ytick.labelsize": 10,
                     "legend.fontsize": 9.5, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.8,
                     "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight"})


def _c(s): return COL[s.split("_")[0]]


def fig_gwp_stages():
    df = pd.read_csv(RES / "lca_gwp_by_stage.csv", index_col=0)
    order = ["IL_A", "FA_A", "LC3_A", "BC_A", "IL_B", "FA_B", "LC3_B", "BC_B"]
    df = df.loc[order]
    groups = {"Cement (IL or LC3)": ["IL cement", "LC3 cement"], "Sand, water, mixing": ["mortar mixing"],
              "Fly ash handling": ["fly ash supply"], "RCF prep. + TA + process energy": ["RCF preparation", "TA production (proxy)", "soaking & carbonation"],
              "CO2 supply (capture-plant electricity)": ["CO2 supply"], "Drying": ["dewatering & drying"], "Electricity co-product (plant w/o capture)": ["functional-unit electricity"],
              "CO2 vented (mineralized CO2 not credited)": ["CO2 mineralized / vented"]}
    pos = np.arange(len(order)); fig, ax = plt.subplots(figsize=(8.6, 4.6))
    bottom = np.zeros(len(order)); neg = np.zeros(len(order))
    cmap = plt.get_cmap("tab20c")
    for k, (lab, cols) in enumerate(groups.items()):
        v = df[[c for c in cols if c in df.columns]].sum(axis=1).to_numpy()
        vp = np.where(v > 0, v, 0); vn = np.where(v < 0, v, 0)
        ax.bar(pos, vp, bottom=bottom, color=cmap(k * 2), label=lab, width=0.7); bottom += vp
        ax.bar(pos, vn, bottom=neg, color=cmap(k * 2)); neg += vn
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(pos); ax.set_xticklabels([SHORT[s.split("_")[0]] for s in order], fontsize=10)
    ax.set_ylabel("kg CO$_2$e per kg mortar (+ co-product electricity)")
    ax.set_ylim(min(neg.min() * 1.3, -0.02), bottom.max() * 1.12)
    ax.axvline(3.5, color="grey", ls=":", lw=0.8); ax.text(1.5, bottom.max() * 1.06, "Scenario A: dry-mix plant", ha="center", fontsize=10)
    ax.text(6.5, bottom.max() * 1.06, "Scenario B: ready-mix plant", ha="center", fontsize=10)
    ax.legend(fontsize=9, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.22), frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "Fig3_gwp_contribution.png", bbox_inches="tight"); fig.savefig(FIG / "Fig3_gwp_contribution.pdf", bbox_inches="tight"); plt.close(fig)


def fig_heatmap():
    tot = pd.read_csv(RES / "lca_totals.csv", index_col=0)
    order = ["FA_A", "LC3_A", "BC_A", "FA_B", "LC3_B", "BC_B"]
    rel = tot.loc[order, L.SHORT].div(tot.loc["IL_A", L.SHORT], axis=1) * 100
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    im = ax.imshow(rel.to_numpy(), cmap="RdYlGn_r", vmin=50, vmax=150, aspect="auto")
    ax.set_xticks(range(len(L.SHORT))); ax.set_xticklabels(L.SHORT)
    ax.set_yticks(range(len(order))); ax.set_yticklabels([LABEL[s].replace("\n", " ") for s in order], fontsize=9.5)
    for i in range(len(order)):
        for j in range(len(L.SHORT)):
            v = rel.iloc[i, j]; ax.text(j, i, f"{v:.0f}" if v < 1000 else ">1000", ha="center", va="center", fontsize=9.5)
    cb = fig.colorbar(im, ax=ax, fraction=0.03); cb.set_label("% of Type IL mortar (same scenario)")
    ax.set_title("Impact relative to Type IL mortar = 100", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "Fig4_impact_heatmap.png"); fig.savefig(FIG / "Fig4_impact_heatmap.pdf"); plt.close(fig)


def fig_msp():
    con = pd.read_csv(RES / "tea_msp_contributions.csv")
    order = ["IL_A", "FA_A", "LC3_A", "BC_A", "IL_B", "FA_B", "LC3_B", "BC_B"]
    grp = {"Cement (IL or LC3)": ["Type IL cement", "LC3 cement"], "Fly ash": ["fly ash (by-product, cut-off)"], "Sand & water": ["sand", "tap water (mixing, make-up)", "tap water (process make-up)"],
           "Tannic acid": ["tannic acid make-up (purchased)"], "RCF & CO2 purchase": ["RCF purchase", "CO2 purchase", "diesel (mobile crusher)"],
           "Electricity": [c for c in con.item.unique() if c.startswith("electricity")], "Labor": ["labor"],
           "Maintenance & insurance": ["maintenance", "insurance"], "Capital recovery & tax": ["capital recovery + tax"]}
    piv = con.pivot_table(index="scenario", columns="item", values="cents_per_kg", aggfunc="sum").fillna(0).loc[order]
    fig, ax = plt.subplots(figsize=(8.6, 4.6)); pos = np.arange(len(order)); bottom = np.zeros(len(order)); cmap = plt.get_cmap("tab20")
    for k, (lab, cols) in enumerate(grp.items()):
        v = piv[[c for c in cols if c in piv.columns]].sum(axis=1).to_numpy()
        ax.bar(pos, v, bottom=bottom, color=cmap(k), label=lab, width=0.7); bottom += v
    for x, t in zip(pos, bottom): ax.text(x, t + 0.05, f"{t:.2f}", ha="center", fontsize=9.5)
    ax.set_xticks(pos); ax.set_xticklabels([SHORT[s.split("_")[0]] for s in order], fontsize=10); ax.set_ylabel("MSP, US cents per kg mortar (2024$)")
    ax.axvline(3.5, color="grey", ls=":", lw=0.8); ax.legend(fontsize=9, ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    ax.text(1.5, bottom.max() * 1.10, "Scenario A: dry-mix plant", ha="center", fontsize=10); ax.text(5.5, bottom.max() * 1.10, "Scenario B: ready-mix plant", ha="center", fontsize=10)
    ax.set_ylim(0, bottom.max() * 1.16)
    fig.tight_layout(); fig.savefig(FIG / "Fig5_msp_contribution.png"); fig.savefig(FIG / "Fig5_msp_contribution.pdf"); plt.close(fig)


def _lines(ax, base, metric, scale, lc3_prices=False):
    ax.axhline(base.loc[f"IL_{scale}", metric], color=COL["IL"], ls="--", lw=1, label="Type IL")
    ax.axhline(base.loc[f"FA_{scale}", metric], color=COL["FA"], ls="--", lw=1, label="IL + 30% fly ash")
    if lc3_prices:
        for f, ls, lab in ((0.8, ":", "LC3 @0.8x IL price"), (1.0, "-.", "LC3 @1.0x"), (1.15, "--", "LC3 @1.15x")):
            ax.axhline(base.loc[f"LC3_{scale}_p{f}", metric], color=COL["LC3"], ls=ls, lw=1, label=lab)
    else:
        ax.axhline(base.loc[f"LC3_{scale}", metric], color=COL["LC3"], ls="--", lw=1, label="LC3-50")


def fig_breakeven():
    """Six panels: BioCarb dry-mix (A), BioCarb ready-mix (B), Type IL, IL + 30 % fly ash.
    GWP: per kg mortar with the electricity co-product credited at the no-capture plant rate (GWP_credited in
    sweeps.csv). This is the system-expansion result minus the E kWh term that every system carries, so all
    BioCarb-minus-reference differences and crossings are identical to the equal-functional-unit form, while the
    IL and FA references stay flat when a BioCarb parameter (and hence E) is swept. Absolute values are therefore
    lower than in Fig. 3 / Table S13 by E x 0.942 kg CO2e (0.011 at the base case).
    MSP: % of the same-scale Type IL mortar; the FA line is drawn per scale (86.5 % at A, 87.7 % at B). The step
    in the dry-mix curve between 0.25 and 0.30 replacement is the second filter-press unit (filter area > 80 m2
    per unit, tea.size_biocarb_unit); it is explained in the caption, not annotated."""
    sw = pd.read_csv(RES / "sweeps.csv")
    gw = [("repl", "BioCarb replacement (kg RCF / kg binder)"), ("cao_field", "CaO content of field RCF (kg/kg)"), ("util", "CO$_2$ utilization in column")]
    ms = [("repl", "BioCarb replacement (kg RCF / kg binder)"), ("price_rcf", "RCF purchase price (USD / t)"), ("price_ta", "Tannic acid price (USD / kg)")]
    fig, axes = plt.subplots(2, 3, figsize=(11.5, 7.0))
    for ax, (par, xl) in zip(axes[0], gw):
        d = sw[sw.parameter == par].pivot_table(index="value", columns="scenario", values="GWP_credited")
        ax.plot(d.index, d["BC_A"], "-", color=COL["BC"], lw=1.2, alpha=0.6, label="BioCarb dry-mix (A)")
        ax.plot(d.index, d["BC_B"], "-", color=COL["BC"], lw=2.0, label="BioCarb ready-mix (B)")
        ax.plot(d.index, d["IL_B"], "--", color=COL["IL"], lw=1.2, label="Type IL")
        ax.plot(d.index, d["FA_B"], "--", color=COL["FA"], lw=1.2, label="IL + 30% fly ash")
        if par == "repl":
            ax.axvspan(0.30, d.index.max(), color="grey", alpha=0.12); ax.text(0.31, ax.get_ylim()[0] + 0.002, "strength\nnot verified", fontsize=10.5, va="bottom")
        ax.set_xlabel(xl, fontsize=10); ax.set_ylabel("GWP (kg CO$_2$e / kg mortar),\nco-product electricity credited", fontsize=10)
    axes[0, 0].legend(fontsize=9, frameon=False)
    for ax, (par, xl) in zip(axes[1], ms):
        d = sw[sw.parameter == par].pivot_table(index="value", columns="scenario", values="MSP")
        ax.plot(d.index, 100 * d["BC_A"] / d["IL_A"], "-", color=COL["BC"], lw=1.2, alpha=0.6, label="BioCarb dry-mix (A)")
        ax.plot(d.index, 100 * d["BC_B"] / d["IL_B"], "-", color=COL["BC"], lw=2.0, label="BioCarb ready-mix (B)")
        ax.axhline(100, ls="--", color=COL["IL"], lw=1.2, label="Type IL (= 100)")
        ax.plot(d.index, 100 * d["FA_A"] / d["IL_A"], "--", color=COL["FA"], lw=1.2, alpha=0.6, label="IL + 30% fly ash (A)")
        ax.plot(d.index, 100 * d["FA_B"] / d["IL_B"], "--", color=COL["FA"], lw=1.2, label="IL + 30% fly ash (B)")
        if par == "repl":
            ax.axvspan(0.30, d.index.max(), color="grey", alpha=0.12)
        ax.set_xlabel(xl, fontsize=10); ax.set_ylabel("MSP, % of same-scenario Type IL mortar", fontsize=10)
    axes[1, 1].legend(fontsize=9, frameon=False, loc="center left", bbox_to_anchor=(0.0, 0.63))   # free band between the IL (100 %) and dry-mix lines
    fig.tight_layout(); fig.savefig(FIG / "Fig6_breakeven.png"); fig.savefig(FIG / "Fig6_breakeven.pdf"); plt.close(fig)


PARAM_LABEL = {"repl": "Replacement level", "cao_field": "CaO content of RCF", "ce0_field": "Pre-existing carbonate", "CE": "Carbonation efficiency",
               "ta_retained": "TA loss with product", "util": "CO$_2$ utilization", "grind_e": "Grinding energy", "crush_alloc": "Crusher allocation",
               "dry_MJ_per_kg_water": "Dryer energy", "price_ta": "Tannic acid price", "price_il": "Type IL price", "price_rcf": "RCF price",
               "price_co2": "CO$_2$ price", "price_fa": "Fly ash price", "price_lc3_factor": "LC3 price factor", "price_elec": "Electricity price",
               "labor_rate": "Labor rate", "labor_fte_bc_A": "BioCarb crew (A)", "labor_fte_bc_B": "BioCarb crew (B)",
               "plant_common_A_cost": "Common plant capital (A)", "plant_common_B_cost": "Common plant capital (B)"}


def _tornado(ax, tor, col, xlabel, n=10):
    t = tor.pivot_table(index="parameter", columns="bound", values=col)
    t["span"] = (t["high"] - t["low"]).abs(); t = t[t["span"] > 1e-12].sort_values("span").tail(n)   # drop parameters with no effect
    y = np.arange(len(t))
    ax.barh(y, t["low"], color="#9ecae1", label="low bound"); ax.barh(y, t["high"], color="#fd8d3c", label="high bound")
    ax.set_yticks(y); ax.set_yticklabels([PARAM_LABEL.get(p_, p_) for p_ in t.index], fontsize=10); ax.axvline(0, color="k", lw=0.6); ax.set_xlabel(xlabel, fontsize=10)


def fig_uncertainty():
    tor = pd.read_csv(RES / "tornado_BC_B.csv"); mc = pd.read_csv(RES / "montecarlo.csv")
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.6))
    _tornado(axes[0, 0], tor, "dGWP_vs_FA", "Change in GWP of BioCarb (B) relative to IL+30% FA\n(kg CO$_2$e / kg mortar, equal functional unit)")
    axes[0, 0].legend(fontsize=10.5, frameon=False); axes[0, 0].set_title("(a) GWP tornado", fontsize=10, loc="left")
    _tornado(axes[0, 1], tor, "dMSP_vs_IL", "Change in MSP margin of BioCarb (B) over Type IL (B), cents / kg\n(negative = BioCarb gains)")
    axes[0, 1].set_title("(b) MSP tornado (margin over Type IL, same scenario)", fontsize=10, loc="left")
    ax = axes[1, 0]; data = [mc[f"GWP_{s}"] for s in ("IL_B", "FA_B", "LC3_B", "BC_B")]
    ax.violinplot(data, showmedians=True); ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["IL", "IL+FA", "LC3", "BioCarb"], fontsize=10)
    ax.set_ylabel("GWP (kg CO$_2$e/kg mortar), ready-mix"); ax.set_title("(c) Monte Carlo GWP (n = %d)" % len(mc), fontsize=10, loc="left")
    ax = axes[1, 1]; data = [mc[f"MSP_{s}"] for s in ("IL_B", "FA_B", "LC3_B", "BC_B")]
    ax.violinplot(data, showmedians=True); ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["IL", "IL+FA", "LC3", "BioCarb"], fontsize=10)
    ax.set_ylabel("MSP (cents/kg mortar), ready-mix"); ax.set_title("(d) Monte Carlo MSP", fontsize=10, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "Fig7_uncertainty.png"); fig.savefig(FIG / "Fig7_uncertainty.pdf"); plt.close(fig)


def fig_mac():
    """Figure 8 (one panel): marginal abatement cost per t CO2e avoided. This study: base-case values (results/mac_by_baseline.csv)
    with 5th-95th percentile ranges over the Monte Carlo draws (results/montecarlo.csv); mortar-producer perspective at market
    prices. Benchmarks on the same footing: concrete-producer values derived from SDSN (2022) and, as the supply-side alternative,
    the premium a cement buyer would pay per t avoided if kiln CO2 capture and storage were passed through (rows flagged in the
    `fig8` column of data/abatement_cost_literature.csv). Cement-producer values at clinker production cost are not comparable and
    are listed in Table S19 only."""
    mb = pd.read_csv(RES / "mac_by_baseline.csv").set_index(["scenario", "baseline"])["MAC_usd_per_tCO2e"]
    mc = pd.read_csv(RES / "montecarlo.csv"); lit = pd.read_csv(ROOT / "data" / "abatement_cost_literature.csv")

    def mac_mc(x, ref):
        dG = mc[f"GWP_{ref}"] - mc[f"GWP_{x}"]; dC = (mc[f"MSP_{x}"] - mc[f"MSP_{ref}"]) / 100
        m = (dC / dG * 1000)[dG > 1e-6]
        return m.quantile(0.05), m.quantile(0.95)

    study = [("BioCarb ready-mix (B) vs Type IL", "BC_B", "IL_B"), ("BioCarb dry-mix (A) vs Type IL", "BC_A", "IL_A"),
             ("IL + 30% fly ash vs Type IL (fly ash $40-90/t)", "FA_B", "IL_B"), ("LC3-50 vs Type IL (0.8-1.15x cement price)", "LC3_B", "IL_B"),
             ("BioCarb ready-mix vs IL + 30% fly ash", "BC_B", "FA_B"), ("BioCarb ready-mix vs LC3-50", "BC_B", "LC3_B")]
    conc = lit[lit.fig8 == "point"]; band = lit[lit.fig8 == "band"]
    n_s, n_c = len(study), len(conc)
    y_s = np.arange(n_s)[::-1] + n_c + 1 + 1.4          # this study on top
    y_c = np.arange(n_c)[::-1] + 1.4                    # concrete-producer rows in the middle
    y_b = 0.0                                           # CCS pass-through band at the bottom
    fig, ax = plt.subplots(figsize=(9.8, 6.4)); xlim = (-220, 560)
    labels = []
    for yy, (lab, x, ref) in zip(y_s, study):
        lo, hi = mac_mc(x, ref); pt = mb[(x, ref)]; c = COL[x.split("_")[0]] if x.startswith("BC") else COL[x.split("_")[0]]
        lo_c, hi_c = max(lo, xlim[0] + 5), min(hi, xlim[1] - 5)
        ax.plot([lo_c, hi_c], [yy, yy], "-", color=c, lw=7, alpha=0.35, solid_capstyle="butt")
        if lo < xlim[0] + 5: ax.annotate("", (xlim[0] + 5, yy), (lo_c + 25, yy), arrowprops=dict(arrowstyle="->", color=c, lw=1.2))
        if hi > xlim[1] - 5: ax.annotate("", (xlim[1] - 5, yy), (hi_c - 25, yy), arrowprops=dict(arrowstyle="->", color=c, lw=1.2))
        ax.plot(pt, yy, "D", color=c, ms=7, mec="white", mew=0.8)
        ax.text(min(max(pt, xlim[0] + 60), xlim[1] - 60), yy + 0.32, f"{pt:+.0f}", ha="center", fontsize=9.5, color=c, fontweight="bold")
        labels.append((yy, lab))
    for yy, (_, r) in zip(y_c, conc.iterrows()):
        ax.plot(r.point_usd_per_t, yy, "o", color="#4a72b8", ms=7, mec="white", mew=0.8)
        ax.text(r.point_usd_per_t, yy + 0.32, f"{r.point_usd_per_t:+.0f}", ha="center", fontsize=9.5, color="#4a72b8")
        labels.append((yy, r.technology))
    for _, r in band.iterrows():
        ax.plot([r.low_usd_per_t, r.high_usd_per_t], [y_b, y_b], "-", color="#7f7f7f", lw=7, alpha=0.45, solid_capstyle="butt")
        ax.plot(r.point_usd_per_t, y_b, "o", color="#7f7f7f", ms=7, mec="white", mew=0.8)
        ax.text(r.high_usd_per_t + 12, y_b, f"{r.low_usd_per_t:.0f} to {r.high_usd_per_t:.0f}", va="center", fontsize=9.5, color="#555555")
        labels.append((y_b, r.technology))
    ax.axvline(0, color="k", lw=0.8)
    for ysep in (n_c + 1.4 + 0.5, 0.7): ax.axhline(ysep, color="k", lw=0.5, ls=":")
    bb = dict(boxstyle="square,pad=0.15", fc="white", ec="none", alpha=1.0)
    ax.text(xlim[0] + 8, y_s[0] + 0.85, "This study: mortar producer, market prices (diamond = base case; bar = 5th-95th percentile of the Monte Carlo)", fontsize=9.5, fontweight="bold", va="center", bbox=bb, zorder=6)
    ax.text(xlim[0] + 8, y_c[0] + 0.85, "Concrete producer, market prices (derived from SDSN 2022, Table S19)", fontsize=9.5, fontweight="bold", va="center", bbox=bb, zorder=6)
    ax.text(xlim[0] + 8, y_b + 0.85, "Cement buyer's premium if kiln CO$_2$ capture and storage were passed through (Table S19)", fontsize=9.5, fontweight="bold", va="center", bbox=bb, zorder=6)
    ax.set_yticks([yy for yy, _ in labels]); ax.set_yticklabels([lab for _, lab in labels], fontsize=10)
    ax.set_xlim(*xlim); ax.set_ylim(-0.8, y_s[0] + 1.3)
    ax.set_xlabel("Marginal abatement cost, USD (2024) per t CO$_2$e avoided   (negative = net saving)")
    ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
    fig.tight_layout(); fig.savefig(FIG / "Fig8_mac.png"); fig.savefig(FIG / "Fig8_mac.pdf"); plt.close(fig)


def fig_graphic_abstract():
    """TOC / graphic abstract (ACS: 8.25 cm x 4.45 cm): process in one line, base-case GWP and MSP of the four ready-mix mortars."""
    import matplotlib.patches as mpatches
    base = pd.read_csv(RES / "base_results.csv", index_col=0)
    fig = plt.figure(figsize=(8.25 / 2.54 * 1.6, 4.45 / 2.54 * 1.6))
    ax = fig.add_axes([0, 0.60, 1, 0.40]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    steps = [("Demolition\nconcrete fines", "#eeeeee"), ("+ tannic acid\n+ captured CO$_2$", "#e7f2e7"), ("BioCarb\ncarbonated RCF", "#cfe6cf"), ("30% of cement\nin mortar", "#f3e6e6")]
    x0, w, gap = 0.02, 0.21, 0.035
    for i, (t, fc) in enumerate(steps):
        x = x0 + i * (w + gap)
        ax.add_patch(mpatches.FancyBboxPatch((x, 0.30), w, 0.62, boxstyle="round,pad=0.01", fc=fc, ec="#444444", lw=0.8))
        ax.text(x + w / 2, 0.61, t, ha="center", va="center", fontsize=8.5)
        if i < len(steps) - 1: ax.annotate("", (x + w + gap - 0.004, 0.61), (x + w + 0.004, 0.61), arrowprops=dict(arrowstyle="->", lw=1.0))
    ax.text(0.5, 0.04, "Harmonized LCA + TEA of two deployment scenarios: dry-mix (dried powder) and ready-mix (slurry)", ha="center", va="bottom", fontsize=7.5, style="italic")
    order = ["IL_B", "FA_B", "LC3_B", "BC_B"]; names = ["Type IL", "IL + 30%\nfly ash", "LC3-50", "BioCarb\nslurry"]; cols = [COL[s_.split("_")[0]] for s_ in order]
    for k, (col, lab, fmt) in enumerate([("GWP", "kg CO$_2$e per kg mortar", "{:.3f}"), ("MSP", "MSP, US cents per kg mortar", "{:.2f}")]):
        axb = fig.add_axes([0.08 + k * 0.5, 0.13, 0.40, 0.33]); v = base.loc[order, col]
        axb.bar(range(4), v, color=cols, width=0.7)
        for i_, val in enumerate(v): axb.text(i_, val * 1.02, fmt.format(val), ha="center", va="bottom", fontsize=7)
        axb.set_xticks(range(4)); axb.set_xticklabels(names, fontsize=7); axb.set_yticks([]); axb.spines["left"].set_visible(False)
        axb.set_title(lab, fontsize=8, pad=3); axb.set_ylim(0, v.max() * 1.25)
    fig.savefig(FIG / "Fig0_graphic_abstract.png", dpi=600); fig.savefig(FIG / "Fig0_graphic_abstract.pdf"); plt.close(fig)

def fig_process_flow():
    """Figure 1: block-flow diagram of the BioCarb and reference mortars in the two deployment scenarios. Process names,
    equipment and technologies only (numbers are in the SI)."""
    import matplotlib.patches as mpatches
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.4))

    def box(ax, x, y, w, h, t, fc="#eef3f8", fs=9.5):
        ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008", fc=fc, ec="#333333", lw=0.8)); ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs)

    def arr(ax, x0, y0, x1, y1):
        ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="->", lw=0.9, color="#333333"))

    for ax, scale in zip(axes, "AB"):
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.add_patch(mpatches.Rectangle((0.0, 0.50), 1.0, 0.50, fc="#e7f2e7", ec="none")); ax.add_patch(mpatches.Rectangle((0.0, 0.0), 1.0, 0.48, fc="#fdf3e3", ec="none"))
        ax.text(0.008, 0.985, "BioCarb mortar", fontsize=10.5, fontweight="bold", va="top"); ax.text(0.008, 0.465, "Reference mortars: Type IL, IL + 30% fly ash, LC3-50", fontsize=10.5, fontweight="bold", va="top")
        ax.set_title("(a) Scenario A: dry-mix mortar plant, bagged premix mixed on site" if scale == "A" else "(b) Scenario B: ready-mix plant, slurry dosed into the plant mixer", fontsize=11, loc="left", fontweight="bold")
        yb, hb = 0.64, 0.19
        chain = [("Demolition\nconcrete", 0.02, 0.085), ("Mobile\ncrusher", 0.12, 0.085), ("Fine grinding\n(ball mill)", 0.22, 0.095), ("Soaking tank\n(tannic acid)", 0.33, 0.10),
                 ("Carbonation\ncolumn", 0.445, 0.10), ("Settling\ntank", 0.56, 0.08)]
        for t, x, w in chain: box(ax, x, yb, w, hb, t)
        for (t, x, w), (t2, x2, w2) in zip(chain[:-1], chain[1:]): arr(ax, x + w, yb + hb / 2, x2, yb + hb / 2)
        ax.plot([0.60, 0.60, 0.38, 0.38], [yb + hb, 0.925, 0.925, yb + hb + 0.02], color="#333333", lw=0.9); ax.annotate("", (0.38, yb + hb), (0.38, yb + hb + 0.03), arrowprops=dict(arrowstyle="->", lw=0.9))
        ax.text(0.49, 0.935, "filtrate (water + tannic acid) recycled", fontsize=9, ha="center")
        box(ax, 0.40, 0.515, 0.19, 0.09, "Coal power plant with CO$_2$ capture", "#f3e6e6", 9)
        arr(ax, 0.495, 0.605, 0.495, yb); ax.text(0.505, 0.622, "captured CO$_2$", fontsize=9, va="center")
        arr(ax, 0.59, 0.56, 0.985, 0.56); ax.text(0.79, 0.567, "electricity co-product", fontsize=9, ha="center")
        if scale == "A":
            box(ax, 0.655, yb, 0.10, hb, "Filter press\n+ spray dryer", "#e3e3f5"); arr(ax, 0.64, yb + hb / 2, 0.655, yb + hb / 2)
            box(ax, 0.77, yb, 0.215, hb, "Dry blending + bagging\nwith Type IL cement and sand;\non-site mixing", "#e3e3f5", 9); arr(ax, 0.755, yb + hb / 2, 0.77, yb + hb / 2)
        else:
            box(ax, 0.655, yb, 0.33, hb, "Plant mixer: carbonated-RCF slurry\n+ Type IL cement + sand;\nwet mortar delivered", "#e3e3f5", 9); arr(ax, 0.64, yb + hb / 2, 0.655, yb + hb / 2)
        yr, hr = 0.10, 0.25
        box(ax, 0.02, yr, 0.17, hr, "Clinker, limestone,\ngypsum\n(+ calcined clay for LC3)", "#f3f3f3", 9)
        box(ax, 0.22, yr, 0.16, hr, "Cement grinding:\nType IL / IL + fly ash /\nLC3-50", "#f3f3f3", 9); arr(ax, 0.19, yr + hr / 2, 0.22, yr + hr / 2)
        box(ax, 0.41, yr, 0.19, hr, "Dry blending + bagging\nwith sand;\non-site mixing" if scale == "A" else "Plant mixer:\nbinder + sand + water;\nwet mortar delivered", "#e3e3f5", 9); arr(ax, 0.38, yr + hr / 2, 0.41, yr + hr / 2)
        box(ax, 0.66, 0.16, 0.16, 0.12, "Same coal power plant\nwithout CO$_2$ capture", "#f3e6e6", 9)
        arr(ax, 0.82, 0.22, 0.985, 0.22); ax.text(0.90, 0.232, "electricity", fontsize=9, ha="center")
    fig.tight_layout(); fig.savefig(FIG / "Fig1_process_flow.png"); fig.savefig(FIG / "Fig1_process_flow.pdf"); plt.close(fig)

def fig_si():
    tor = pd.read_csv(RES / "tornado_BC_A.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
    _tornado(axes[0], tor, "dGWP_vs_FA", "Change in GWP of BioCarb (A) relative to IL+30% FA\n(kg CO$_2$e / kg mortar)"); axes[0].legend(fontsize=10.5, frameon=False)
    _tornado(axes[1], tor, "dMSP_vs_IL", "Change in MSP margin of BioCarb (A) over Type IL (A), cents / kg\n(negative = BioCarb gains)")
    fig.tight_layout(); fig.savefig(FIG / "FigS1_tornado_BC_A.png"); plt.close(fig)


def all_figures():
    FIG.mkdir(exist_ok=True)
    fig_process_flow(); fig_gwp_stages(); fig_heatmap(); fig_msp(); fig_breakeven(); fig_uncertainty(); fig_mac(); fig_si(); fig_graphic_abstract()

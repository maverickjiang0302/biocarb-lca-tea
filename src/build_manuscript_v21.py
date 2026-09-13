"""Build manuscript/manuscript_v21.md from the authors' edited v20 Word file (converted to markdown) and the model results.
All numbers that depend on the model are read from results/*.csv so that the text cannot drift from the figures."""
import pathlib, re, sys
import numpy as np, pandas as pd

REPO = pathlib.Path(sys.argv[1]); M = REPO / "manuscript"; R = REPO / "results"
src = (M / "manuscript_v20_edited.md").read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
lines = src.split("\n")

# ------------------------------------------------------------------ numbers from the model ------------------------
base = pd.read_csv(R / "base_results.csv", index_col=0); tea = pd.read_csv(R / "tea_summary.csv").set_index("scenario")
con = pd.read_csv(R / "tea_msp_contributions.csv"); mb = pd.read_csv(R / "mac_by_baseline.csv").set_index(["scenario", "baseline"])
mcs = pd.read_csv(R / "montecarlo_summary.csv").set_index(["scenario", "metric"]); probs = pd.read_csv(R / "montecarlo_probabilities.csv", index_col=0).iloc[:, 0]
mc = pd.read_csv(R / "montecarlo.csv"); tor = pd.read_csv(R / "tornado_BC_B.csv").set_index(["parameter", "bound"]); sw = pd.read_csv(R / "sweeps.csv")
litn = pd.read_csv(R / "literature_uptake_normalized.csv"); tp = pd.read_csv(REPO / "data/tea_parameters.csv").set_index("name")["value"]
MSP = base["MSP"]; GWP = base["GWP"]
f1 = lambda x: f"{x:.1f}".replace("-", "−"); f2 = lambda x: f"{x:.2f}".replace("-", "−"); f0 = lambda x: f"{x:.0f}".replace("-", "−"); pct = lambda a, b: f"{abs(a / b - 1) * 100:.0f}"

def cross(par, a, b, col, lo_first=True):
    """x where series a - b changes sign (linear interpolation) within the sweep of `par`."""
    d = sw[sw.parameter == par].pivot_table(index="value", columns="scenario", values=col)
    y = (d[a] - d[b]).to_numpy(); x = d.index.to_numpy()
    for i in range(len(x) - 1):
        if y[i] * y[i + 1] < 0:
            return x[i] + (x[i + 1] - x[i]) * (-y[i]) / (y[i + 1] - y[i])
    return np.nan

def sweep_val(par, scn, col, value):
    d = sw[(sw.parameter == par) & (sw.scenario == scn)].set_index("value")[col]
    return float(np.interp(value, d.index.to_numpy(), d.to_numpy()))

cement_share = {}
for s_ in base.index:
    c = con[(con.scenario == s_) & con.item.isin(["Type IL cement", "LC3 cement"])].cents_per_kg.sum()
    cement_share[s_] = 100 * c / MSP[s_]
labor_share = {s_: 100 * con[(con.scenario == s_) & (con.item == "labor")].cents_per_kg.sum() / MSP[s_] for s_ in base.index}
co2_cpkg = con[(con.scenario == "BC_B") & (con.item == "CO2 purchase")].cents_per_kg.sum()
dG_IL = GWP["IL_B"] - GWP["BC_B"]
co2_per_t = co2_cpkg / 100 / dG_IL * 1000
mac = {k: mb.loc[k, "MAC_usd_per_tCO2e"] for k in [("FA_B", "IL_B"), ("LC3_B", "IL_B"), ("BC_B", "IL_B"), ("BC_A", "IL_A"), ("BC_B", "FA_B"), ("BC_B", "LC3_B")]}
# fly-ash MAC at 90 USD/t fly ash (from the price_fa sweep)
fa90 = (sweep_val("price_fa", "FA_B", "MSP", 90) - sweep_val("price_fa", "IL_B", "MSP", 90)) / 100 / (sweep_val("price_fa", "IL_B", "GWP", 90) - sweep_val("price_fa", "FA_B", "GWP", 90)) * 1000
repl_msp_fa = cross("repl", "BC_B", "FA_B", "MSP"); repl_msp_lc3 = cross("repl", "BC_B", "LC3_B", "MSP")
repl_gwp_fa = cross("repl", "BC_B", "FA_B", "GWP"); repl_gwp_lc3 = cross("repl", "BC_B", "LC3_B", "GWP")
repl_gwp_fa_A = cross("repl", "BC_A", "FA_A", "GWP"); repl_gwp_lc3_A = cross("repl", "BC_A", "LC3_A", "GWP")
ta_parity = cross("price_ta", "BC_B", "FA_B", "MSP")
if np.isnan(ta_parity):   # no crossing inside the sweep: extrapolate the (linear) MSP difference to zero
    d = sw[sw.parameter == "price_ta"].pivot_table(index="value", columns="scenario", values="MSP"); y = (d["BC_B"] - d["FA_B"]).to_numpy(); x = d.index.to_numpy()
    slope = (y[-1] - y[0]) / (x[-1] - x[0]); ta_parity = x[0] - y[0] / slope
d_co2 = sweep_val("price_co2", "BC_B", "MSP", 120) - sweep_val("price_co2", "BC_B", "MSP", 60)
d_rcf = tor.loc[("price_rcf", "high"), "dMSP"]; d_lab_abs = tor.loc[("labor_rate", "high"), "dMSP"]; d_lab_m = tor.loc[("labor_rate", "high"), "dMSP_vs_IL"]
d_ta_loss = tor.loc[("ta_retained", "high"), "dMSP"]
t = lambda p, b, c="dMSP_vs_IL": tor.loc[(p, b), c]
ce = litn[litn.table1_order > 0]
ce_aq = ce[(ce.ref_key != "chen2016") & ~ce.ref_key.str.startswith("biocarb")]["apparent_CE_pct"]
ce_slag = float(ce.loc[ce.ref_key == "chen2016", "apparent_CE_pct"].iloc[0])
p05 = lambda s_, m: mcs.loc[(s_, m), "p05"]; p50 = lambda s_, m: mcs.loc[(s_, m), "p50"]; p95 = lambda s_, m: mcs.loc[(s_, m), "p95"]

N = dict(msp_bcb=f2(MSP["BC_B"]), msp_bca=f2(MSP["BC_A"]), msp_ila=f2(MSP["IL_A"]), msp_ilb=f2(MSP["IL_B"]), msp_fab=f2(MSP["FA_B"]), msp_lc3b=f2(MSP["LC3_B"]),
         bcb_vs_il=pct(MSP["BC_B"], MSP["IL_B"]), bcb_vs_fa=pct(MSP["BC_B"], MSP["FA_B"]), bcb_vs_lc3=pct(MSP["BC_B"], MSP["LC3_B"]),
         bca_vs_il=pct(MSP["BC_A"], MSP["IL_A"]), bca_vs_fa=pct(MSP["BC_A"], MSP["FA_A"]), bca_premix=f1(tea.loc["BC_A", "MSP_per_kg_product_cpkg"]),
         cem_lo=f0(min(cement_share.values())), cem_hi=f0(max(cement_share.values())), lab_lo=f0(min(labor_share.values())), lab_hi=f0(max(labor_share.values())),
         co2_cpkg=f2(co2_cpkg), co2_per_t=f0(co2_per_t), cap_bcb=f2(tea.loc["BC_B", "capital_and_tax_cpkg"] - tea.loc["IL_B", "capital_and_tax_cpkg"] + con[(con.scenario == "BC_B") & con.item.isin(["maintenance", "insurance"])].cents_per_kg.sum() - con[(con.scenario == "IL_B") & con.item.isin(["maintenance", "insurance"])].cents_per_kg.sum()),
         mac_fa=f0(-mac[("FA_B", "IL_B")]), mac_lc3=f0(-mac[("LC3_B", "IL_B")]), mac_bcb=f0(-mac[("BC_B", "IL_B")]), mac_bca=f0(mac[("BC_A", "IL_A")]),
         mac_bcb_fa=f0(mac[("BC_B", "FA_B")]), mac_bcb_lc3=f0(mac[("BC_B", "LC3_B")]), mac_fa90=f0(-fa90),
         dg_fa=f"{GWP['FA_B'] - GWP['BC_B']:.3f}", dg_lc3=f"{GWP['LC3_B'] - GWP['BC_B']:.3f}",
         repl_msp_fa=f0(100 * repl_msp_fa), repl_msp_lc3=f0(100 * repl_msp_lc3), repl_gwp_fa=f0(100 * repl_gwp_fa), repl_gwp_lc3=f0(100 * repl_gwp_lc3),
         repl_gwp_A_lo=f0(100 * min(repl_gwp_fa_A, repl_gwp_lc3_A)), repl_gwp_A_hi=f0(100 * max(repl_gwp_fa_A, repl_gwp_lc3_A)),
         ta_parity=f1(ta_parity), d_co2=f2(d_co2), d_rcf=f2(d_rcf), d_lab_abs=f2(d_lab_abs), d_lab_m=f2(d_lab_m), d_ta_loss=f2(d_ta_loss),
         p_gwp_fa=f0(100 * probs["P(GWP BC_B < FA_B)"]), p_gwp_lc3=f0(100 * probs["P(GWP BC_B < LC3_B)"]),
         p_msp_il=f0(100 * probs["P(MSP BC_B < IL_B)"]), p_msp_lc3=f0(100 * probs["P(MSP BC_B < LC3_B)"]), p_msp_fa=("<1" if probs["P(MSP BC_B < FA_B)"] < 0.005 else f"{100 * probs['P(MSP BC_B < FA_B)']:.0f}"),
         mc_msp_lo=f1(p05("BC_B", "MSP")), mc_msp_hi=f1(p95("BC_B", "MSP")), mc_msp_med=f1(p50("BC_B", "MSP")),
         g_bcb=f"{p05('BC_B','GWP'):.3f}--{p95('BC_B','GWP'):.3f}", g_fab=f"{p05('FA_B','GWP'):.3f}--{p95('FA_B','GWP'):.3f}", g_lc3b=f"{p05('LC3_B','GWP'):.3f}--{p95('LC3_B','GWP'):.3f}",
         t_repl=f2(abs(t("repl", "low"))), t_ta_lo=f2(t("price_ta", "low")), t_ta_hi=f2(t("price_ta", "high")), t_taloss=f2(t("ta_retained", "high")), t_rcf=f2(t("price_rcf", "high")),
         t_crew_lo=f2(t("labor_fte_bc_B", "low")), t_crew_hi=f2(t("labor_fte_bc_B", "high")), t_il=f2(t("price_il", "high")), t_co2=f2(t("price_co2", "high")),
         ce_lo=f0(ce_aq.min()), ce_hi=f0(ce_aq.max()), ce_slag=f0(ce_slag))
for k, v in N.items(): print(f"{k:14s} {v}")
(M / "_v21_numbers.txt").write_text("\n".join(f"{k}: {v}" for k, v in N.items()), encoding="utf-8")

# ------------------------------------------------------------------ clean pandoc artefacts ------------------------
out = []
skip_table = False
for l in lines:
    if l.strip() in ("**\\**", "## ", "##"): continue
    if l.startswith(("|", "+-", "+=")):      # the superseded Table 1 grid (the manuscript has no other tables)
        continue
    l = re.sub(r"\{#[a-z0-9-]+\}", "", l).rstrip()
    l = re.sub(r"\{width=\"[^\"]+\" height=\"[^\"]+\"\}", "", l)
    out.append(l)
text = "\n".join(out)
imgs = ["Fig0_graphic_abstract.png", "Fig1_process_flow.png", "Fig2_lab_data.png", "Fig3_gwp_contribution.png", "Fig4_impact_heatmap.png",
        "Fig5_msp_contribution.png", "Fig6_breakeven.png", "Fig7_uncertainty.png", "Fig8_mac.png"]
for i, name in enumerate(imgs, start=1):
    text = text.replace(f"![](_user_media/media/image{i}.png)", f"![](../figures/{name})")
assert "_user_media" not in text
# Table 1 -> markers (build_si.py regenerates caption + table from data/literature_uptake.csv)
text = re.sub(r"\*\*Table 1\.\*\* Reported CO~2~ uptake.*?\n", "<!-- TABLE1_START -->\n<!-- TABLE1_END -->\n", text, count=1, flags=re.S)
text = re.sub(r"\n{3,}", "\n\n", text)
lines = text.split("\n")

def edit(prefix, old, new, count=1):
    idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(idx) == 1, (prefix[:40], idx)
    assert lines[idx[0]].count(old) == count, (prefix[:40], old[:60], lines[idx[0]].count(old))
    lines[idx[0]] = lines[idx[0]].replace(old, new)

def replace_para(prefix, new):
    idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(idx) == 1, (prefix[:40], idx)
    lines[idx[0]] = new

# ------------------------------------------------------------------ front matter -----------------------------------
header = ['---', 'title: "Biomolecule-regulated carbonation (BioCarb) as a drop-in supplementary cementitious material (SCM): harmonized life-cycle and techno-economic assessment"', '---', '']
lines = header + lines

# ------------------------------------------------------------------ abstract ---------------------------------------
edit("Carbonated recycled concrete fines (RCF) can store CO~2~ and has potential",
     "Carbonated recycled concrete fines (RCF) can store CO~2~ and has potential as a supplementary cementitious material (SCM) as established SCM fly ash shrinks in the U.S. and Europe. However, their system-level performance has not been compared with established clinker substitutes.",
     "Carbonated recycled concrete fines (RCF) can store CO~2~ and have potential as a supplementary cementitious material (SCM) as the supply of fly ash, the established SCM, shrinks in the U.S. and Europe. However, their system-level performance has not been compared with established clinker substitutes.")
edit("Carbonated recycled concrete fines (RCF) can store CO~2~ and have potential",
     "In the laboratory, BioCarb achieves 80 % of the theoretical carbonation efficiency using simulated RCF -- nearly 35% higher than previously reported RCF carbonation methods.",
     "In the laboratory, 80 % of the CaO of a simulated RCF was present as carbonate after 60 min (64 % newly fixed), an uptake of 0.365 kg CO~2~ kg^−1^, about 35 % above the highest value previously reported for RCF.")
edit("Carbonated recycled concrete fines (RCF) can store CO~2~ and have potential",
     "The slurry route outperforms Type IL mortar, 30% fly ash and LC3 in global warming potential, while only modestly increasing the minimum selling price compared to 30% fly ash and LC3. The dried route, in contrast, incurs a significant penalty in minimum selling price even compared to IL cement (6.28 vs. 5.18 ¢ kg^−1^) and underperforms 30% fly ash and LC3 in global warming potential.",
     f"The slurry route outperforms Type IL mortar, 30 % fly ash and LC3 in global warming potential (0.145 versus 0.210, 0.152 and 0.149 kg CO~2~e kg^−1^) at a minimum selling price of {N['msp_bcb']} ¢ kg^−1^, below Type IL ({N['msp_ilb']}) and modestly above 30 % fly ash ({N['msp_fab']}) and LC3 ({N['msp_lc3b']}). The dried route, in contrast, incurs a significant penalty in minimum selling price even relative to Type IL mortar ({N['msp_bca']} versus {N['msp_ila']} ¢ kg^−1^) and underperforms 30 % fly ash and LC3 in global warming potential.")

# ------------------------------------------------------------------ introduction (R1-7, R3-1) -------------------------
edit("Cement production accounts for roughly 8 %", "roughly 8 % of anthropogenic greenhouse-gas emissions,^1--3^", "roughly 8 % of anthropogenic CO~2~ emissions,^1--3^")
edit("We previously showed that tannic acid (TA) regulates",
     "We previously showed that tannic acid (TA) regulates CaCO~3~ nucleation during CO~2~ mineralization,^22^ and here we report",
     "We previously showed that tannic acid (TA) regulates CaCO~3~ nucleation during CO~2~ mineralization.^22^ TA has also been applied to recycled concrete fines and aggregates as a surface or activation treatment that improves hydration, pore structure and interfacial bonding;^55--58^ here it is used to regulate the carbonation reaction itself. We report")

# ------------------------------------------------------------------ reviewer-driven additions ---------------------------
# R1-9: cement as the driver of concrete emissions; carbonation and displacement in separate sentences
edit("Cement production accounts for roughly 8 %",
     "Clinker substitution with supplementary cementitious materials (SCMs) remains the largest near-term lever,^5,6^ but the two incumbent routes are constrained.",
     "Because clinker production causes most of the greenhouse-gas emissions of concrete and mortar, replacing part of the cement with supplementary cementitious materials (SCMs) remains the largest near-term lever,^5,6^ but the two incumbent routes are constrained.")
edit("Recycled concrete fines (RCF), the paste-rich fraction",
     "Their calcium content can be carbonated to stable carbonates while the product serves as a filler-plus-reactive SCM.^11--13^",
     "Their calcium content can be carbonated to stable carbonates.^11--13^ The carbonated product can then replace part of the cement as a filler-plus-reactive SCM, so that its climate benefit arises mainly from the cement it displaces and only secondarily from the CO~2~ it stores.")
# R1-2: age and preparation of the model feedstock
edit("Simulated RCF was prepared from hydrated",
     "Simulated RCF was prepared from hydrated ordinary Portland cement paste (CaO 57.8 wt %, Table S1) ground to \\<75 µm; field demolition fines differ (Section 2.3).",
     "Simulated RCF was prepared from hydrated ordinary Portland cement paste (oxide composition by XRF, CaO 57.8 wt %, Table S1) that had been cured under standard conditions for more than 28 days so that it contained mature hydrate phases, then crushed, dried and ground to \\<75 µm (Text S1); field demolition fines differ in paste content, carbonation history and inert fraction (Section 2.3).")
# R2-1: why a mass-based functional unit at a fixed mix design is defensible here
edit("The captured CO~2~ used by BioCarb is modelled",
     "A strength-normalized functional unit is discussed in Section 3.4.",
     "All mortars share one mix design (binder:sand:water 1:2.82:0.50), and the BioCarb mortar met or exceeded the control strength at 28 d at that mix design (Section 3.1), so a mass-based functional unit does not favour BioCarb; a strength-normalized functional unit is discussed in Section 3.4.")
# R1-3: which inputs are laboratory-derived and which are industrial-scale
edit("All inventories are generated per kg of mortar",
     "Key choices are summarized here.",
     "Laboratory data enter the model only through the carbonation chemistry (carbonation efficiency, pre-existing carbonate, tannic-acid dose, liquid-to-solid ratio and water retention; Text S1); all equipment energies, sizes and costs are industrial-scale values from vendor specifications, engineering correlations and published prices (Tables S3, S7, S8, S10 and S11), so laboratory inefficiencies are not carried into the plant model. Key choices are summarized here.")
# R1-6: explicit statement of limitations in the concluding section
edit("Three conclusions follow. First, on a harmonized basis",
     "Priorities for the next stage are field-RCF carbonation and strength testing,",
     "The assessment rests on laboratory data for a simulated RCF and on mortar-cube strength alone; durability, rheology, shrinkage and setting behaviour, and the performance of field RCF with lower and variable CaO content remain to be established. Priorities for the next stage are therefore field-RCF carbonation and strength testing,")

# ------------------------------------------------------------------ methods ----------------------------------------
edit("The captured CO~2~ used by BioCarb is modelled",
     "(0.942 kg CO~2~e kWh^−1^), and any CO~2~ not absorbed in the carbonation process using a typical industrial-scale column (SI Text S2). Transport is excluded, and results are reported per kg of mortar.",
     "(0.942 kg CO~2~e kWh^−1^), so that all systems deliver both products. The climate benefit of capturing the CO~2~ is thereby expressed by the lower emission rate of the capture plant; the CO~2~ mineralized in the mortar is not credited a second time, and any CO~2~ not absorbed in the industrial-scale column is charged as an emission (Text S2). Transport is excluded, and results are reported per kg of mortar.")
edit("Equipment is sized from the inventory",
     "RCF and captured CO~2~ at \\$0 t^−1^ in the base case (sensitivity 0--30 and 0--100 \\$ t^−1^).",
     "RCF at \\$0 t^−1^ as a by-product of aggregate recycling (sensitivity 0--30 \\$ t^−1^), and purified CO~2~ at a market price of \\$60 t^−1^, the mid-point of the \\$40--80 t^−1^ cost of capture and purification at coal- and gas-fired plants, below which a capture plant would not sell (sensitivity 40--120 \\$ t^−1^).^50^")

# ------------------------------------------------------------------ 3.1 ---------------------------------------------
edit("With TA, the carbonate fraction of CaO rose", "based on real-world RCF compositions reported in the literature (SI Table Sxxx).", "based on the CaO contents reported for real-world RCF (Table S5).")
edit("Simulated RCF was prepared from hydrated", "These data (Fig. 2, Table S2) are reported as measured;", "These data (Fig. 2) are reported as measured;")
edit("**Figure 2.**", " (n and standard deviations in Table S2).", ".")
edit("MSP is the plant-gate price", "7-yr MACRS, 21 % tax, 2024 USD; Text S4, Table S11).", "7-yr MACRS, 21 % tax, 2024 USD; NREL discounted-cash-flow convention,^54^ Text S4, Table S11).")
replace_para("Table 1 places these values among reported",
     f"Table 1 places these values among reported carbonation results for RCF and other alkaline wastes. Per kilogram of feedstock, reported uptakes range from 0.03 (biomass and lignite fly ash) to 0.27 (laboratory paste, NaOH-assisted), and the spread is governed by CaO content rather than by process performance: real demolition fines with 25--30 wt % CaO cannot exceed \\~0.2 kg kg^−1^ even at complete conversion. Normalizing each value to the theoretical uptake of its feedstock (apparent carbonation efficiency, Eq. S24, Table S18) puts the direct aqueous, dry and semi-dry processes at {N['ce_lo']}--{N['ce_hi']} % and the high-gravity slag process at \\~{N['ce_slag']} %; BioCarb's 80 % total carbonate (64 % newly fixed) in 60 min at ambient conditions is at the upper end for cement-derived fines. The CaO values behind Table S18 are taken from the cited papers where reported and otherwise from typical compositions for the feedstock class, so the apparent efficiencies are indicative.")

# ------------------------------------------------------------------ 3.2 ---------------------------------------------
replace_para("Replacing 30 % of the binder lowers the GWP in all three SCM systems.",
     "Replacing 30 % of the binder lowers the GWP from 0.210 kg CO~2~e kg^−1^ for Type IL mortar to 0.152 (fly ash), 0.149 (LC3) and 0.145 (BioCarb slurry) (Fig. 3, Table S13). BioCarb in the ready-mix scenario outperforms 30 % fly ash and LC3-50 because the carbonation chain adds only RCF grinding (0.0012 kg CO~2~e kg^−1^), tannic acid (0.0004) and process energy (0.0002), while its 0.0113 kWh of co-product electricity comes from the capture plant at 0.0031 rather than 0.0106 kg CO~2~e. In the dry-mix scenario BioCarb becomes the worst of the three: the electric spray dryer adds 0.0199 kg CO~2~e kg^−1^, lifting BioCarb to 0.165, 8 % above fly ash and 11 % above LC3.")
replace_para("**Figure 3.**", "**Figure 3.** Global warming potential per functional unit (1 kg of mortar plus 0.0113 kWh of electricity) by contribution.")
edit("Across the seven TRACI categories", "This trend is aligned with the GWP trends. However, LC3 is 4 % above Type IL cement mortar for ozone depletion because of calcined-clay production.",
     "BioCarb slurry and fly ash are within one percentage point of each other in every non-GWP category, the dried BioCarb route is the highest of the SCM systems for acidification and particulate matter (81 and 84 % of Type IL) because of dryer electricity, and LC3 is lowest for smog and water but 4 % above Type IL for ozone depletion because of calcined-clay production.")

# ------------------------------------------------------------------ 3.3 ---------------------------------------------
edit("Cement is the main cost driver", "accounts for 50--65 % of MSP in every system (Fig. 5, Table S14). At ready-mix scenario,",
     f"accounts for {N['cem_lo']}--{N['cem_hi']} % of MSP across the eight systems, labor for {N['lab_lo']}--{N['lab_hi']} % (Fig. 5, Table S14). In the ready-mix scenario,")
edit("Cement is the main cost driver",
     "0.09 ¢ extra labor and 0.21 ¢ additional capital recovery and maintenance for the carbonation unit (\\$0.46 M purchased equipment, Table S12), giving 5.11 ¢ kg^−1^: 10 % below Type IL, 3 % above fly ash, and 4 % above LC3 priced at 0.8× cement (4.92);",
     f"0.09 ¢ extra labor, {N['co2_cpkg']} ¢ purchased CO~2~ and {N['cap_bcb']} ¢ additional capital recovery and maintenance for the carbonation unit (\\$0.46 M purchased equipment, Table S12), giving {N['msp_bcb']} ¢ kg^−1^: {N['bcb_vs_il']} % below Type IL, {N['bcb_vs_fa']} % above fly ash, and {N['bcb_vs_lc3']} % above LC3 priced at 0.8× cement ({N['msp_lc3b']});")
edit("At dry-mix scale the filter presses", "MSP rises to 6.29 ¢ kg^−1^ of mortar (7.1 ¢ kg^−1^ of premix), 21 % above Type IL and 40 % above fly ash at the same scale.",
     f"MSP rises to {N['msp_bca']} ¢ kg^−1^ of mortar ({N['bca_premix']} ¢ kg^−1^ of premix), {N['bca_vs_il']} % above Type IL and {N['bca_vs_fa']} % above fly ash in the same scenario.")

# ------------------------------------------------------------------ 3.4 ---------------------------------------------
edit("*Replacement level* is the strongest lever",
     "BioCarb slurry undercuts fly ash on GWP above 27 % replacement and LC3 above 28 %, and reaches MSP parity with fly ash at 35 % and with cost-based LC3 at 37 %---levels above the 30 % verified in mortar cubes and shaded accordingly; the dried route needs 39--41 % replacement to match them on GWP,",
     f"BioCarb slurry undercuts fly ash on GWP above {N['repl_gwp_fa']} % replacement and LC3 above {N['repl_gwp_lc3']} %, and reaches MSP parity with fly ash at {N['repl_msp_fa']} % and with cost-based LC3 at {N['repl_msp_lc3']} %---levels above the 30 % verified in mortar cubes and shaded accordingly; the dried route needs {N['repl_gwp_A_lo']}--{N['repl_gwp_A_hi']} % replacement to match them on GWP,")
edit("*Feedstock calcium* has a modest effect",
     "parity with fly ash at 30 % replacement requires TA at ≤\\$2.0 kg^−1^ (the lower end of industrial tannin prices) or a TA recovery well above the two-thirds assumed here; complete loss of TA raises MSP by 0.46 ¢ kg^−1^. An *RCF price* of \\$30 t^−1^ adds 0.21 ¢ and a *CO~2~ price* of \\$100 t^−1^ adds 0.10 ¢; a *loaded labor rate* of \\$36 h^−1^ adds 0.11 ¢ to every mortar but only 0.03 ¢ to BioCarb's margin, because the crew is largely shared.",
     f"parity with fly ash at 30 % replacement would require TA at about \\${N['ta_parity']} kg^−1^, below the \\$2 kg^−1^ lower end of industrial tannin prices, or a TA recovery well above the two-thirds assumed here; complete loss of TA raises MSP by {N['d_ta_loss']} ¢ kg^−1^. An *RCF price* of \\$30 t^−1^ adds {N['d_rcf']} ¢ and doubling the *CO~2~ price* to \\$120 t^−1^ adds {N['d_co2']} ¢; a *loaded labor rate* of \\$36 h^−1^ adds {N['d_lab_abs']} ¢ to every mortar but only {N['d_lab_m']} ¢ to BioCarb's margin, because the crew is largely shared.")

edit("**Figure 6.**",
     "Top: GWP per kg of mortar of BioCarb at dry-mix (A, thin) and ready-mix (B, thick) scale against the Type IL and IL + 30 % fly-ash mortars, with the co-product electricity credited at the no-capture plant rate; the reference values are therefore constant, and all differences and crossings equal those at equal functional unit (absolute values are 0.011 kg CO~2~e kg^−1^ lower than in Fig. 3 at the base case). Bottom: MSP as a percentage of the same-scale Type IL mortar, with the fly-ash mortar drawn for each scale (86.5 % at A, 87.7 % at B); the step in the dry-mix curve between 25 and 30 % replacement is the second filter-press unit (filter area \\> 80 m^2^ per unit). Shaded: replacement beyond the 30 % verified in mortar cubes.",
     "Top: GWP per kg of mortar of BioCarb in the dry-mix (A, thin) and ready-mix (B, thick) scenarios against the Type IL and IL + 30 % fly-ash mortars of scenario B (identical in scenario A), with the co-product electricity credited at the no-capture plant rate; the reference values are therefore constant, and all differences and crossings equal those at equal functional unit (absolute values are 0.011 kg CO~2~e kg^−1^ lower than in Fig. 3 at the base case). Bottom: MSP as a percentage of the same-scenario Type IL mortar, with the same scenario-B references as the top row (Type IL = 100; fly-ash mortar 87.7 %, versus 86.5 % in scenario A); the step in the dry-mix curve between 25 and 30 % replacement is the second filter-press unit (filter area \\> 80 m^2^ per unit). Shaded: replacement beyond the 30 % verified in mortar cubes.")

# ------------------------------------------------------------------ 3.5 ---------------------------------------------
replace_para("Propagating all parameter ranges",
     f"Propagating all parameter ranges (Fig. 7, Table S15) leaves the ranking of GWP robust: BioCarb slurry is below fly ash in {N['p_gwp_fa']} % and below LC3 in {N['p_gwp_lc3']} % of draws (5th--95th percentiles {N['g_bcb']} versus {N['g_fab']} and {N['g_lc3b']}), whereas the dried route is never below fly ash. Cost is far less certain: the BioCarb-slurry MSP spans {N['mc_msp_lo']}--{N['mc_msp_hi']} ¢ kg^−1^ (median {N['mc_msp_med']}, higher than the base case because the TA-price, TA-loss and RCF-price ranges extend only upward from the base values), and it undercuts Type IL in {N['p_msp_il']} %, LC3 (over its price range) in {N['p_msp_lc3']} % and fly ash in {N['p_msp_fa']} % of draws. The GWP tornado (Fig. 7a) shows that only the replacement level and, far behind it, the feedstock's CaO and pre-existing carbonate materially change BioCarb's margin over fly ash; process-energy and carbonation-efficiency parameters are secondary. The MSP tornado (Fig. 7b), expressed as BioCarb's margin over the same-scenario Type IL mortar so that shared inputs cancel, ranks replacement level (±{N['t_repl']} ¢ kg^−1^), tannic-acid price ({N['t_ta_lo']} to +{N['t_ta_hi']}), TA loss (+{N['t_taloss']}), RCF price (+{N['t_rcf']}) and the BioCarb crew ({N['t_crew_lo']} to +{N['t_crew_hi']}) as the dominant drivers; the CO~2~ price adds at most {N['t_co2']} ¢, common-plant capital drops out entirely because the same plant serves every mortar, and a higher Type IL price widens BioCarb's advantage ({N['t_il']} ¢ kg^−1^ at \\$180 t^−1^) because BioCarb contains 30 % less cement.")
replace_para("Expressed as marginal abatement cost against Type IL mortar",
     f"Expressed as marginal abatement cost against Type IL mortar (Eq. S22; Fig. 8), fly ash and cost-based LC3 abate at −\\${N['mac_fa']} and −\\${N['mac_lc3']} t^−1^ CO~2~e (they save money), BioCarb slurry at −\\${N['mac_bcb']} t^−1^, and the dried route at +\\${N['mac_bca']} t^−1^. Measured against the next-best SCM mortars instead of Type IL, the sign changes: BioCarb slurry avoids only {N['dg_fa']} and {N['dg_lc3']} kg CO~2~e kg^−1^ more than the fly-ash and LC3 mortars and costs more, so each extra tonne avoided costs +\\${N['mac_bcb_fa']} and +\\${N['mac_bcb_lc3']} t^−1^; the dried route avoids nothing relative to either. Fig. 8 puts these numbers next to the few published values that were calculated the same way, that is, from the point of view of a company that buys cement and SCMs at market prices and mixes them into concrete or mortar. The only such study we found is the SDSN analysis of a US ready-mix plant:^49^ read from its cost and emission tables, replacing part of the cement with slag, fly ash, limestone or calcined clay saved that plant \\$11 to \\$39 per tonne of CO~2~ avoided. Fig. 8 also shows what a cement buyer would pay per tonne avoided if a cement plant installed CO~2~ capture and storage and passed the full cost on in its price, \\$50 to \\$240 t^−1^.^46--48^ Estimates made from the cement producer's side, which value clinker at its production cost rather than its selling price, are not comparable and are listed in Table S19 only.")
replace_para("Two qualifications govern the reading.",
     f"Three points follow. First, the savings from fly ash and LC3 depend entirely on how much cheaper they are than cement. Fly ash at \\$60 t^−1^ saves the mortar producer \\${N['mac_fa']} per tonne of CO~2~ avoided, fly ash at \\$90 t^−1^ only \\${N['mac_fa90']} (the bar in Fig. 8), and the SDSN plant saved even less because its SCMs cost almost as much as cement. BioCarb's saving does not rest on a by-product staying cheap: its feedstock is demolition concrete, which is available wherever buildings are torn down. Second, once a plant already uses fly ash or LC3, switching to BioCarb buys the last few grams of CO~2~ at a high price (\\${N['mac_bcb_fa']} and \\${N['mac_bcb_lc3']} t^−1^), more than buying cement made with carbon capture would cost. BioCarb's place is therefore to replace plain Type IL where fly ash has become scarce, not to compete with LC3. Third, almost all of the CO~2~ avoided comes from using less clinker, not from the CO~2~ stored in the material: the 0.010 kg of CO~2~ fixed per kg of mortar avoids 0.0075 kg CO~2~e at the power plant, one eighth of what the clinker saving avoids. Buying that CO~2~ at \\$60 t^−1^ costs {N['co2_cpkg']} ¢ per kg of mortar, or about \\${N['co2_per_t']} per tonne of CO~2~ avoided.")
replace_para("**Figure 8.**",
     "**Figure 8.** Marginal abatement cost per tonne of CO~2~e avoided (2024 USD; negative = net saving). Top: this study, from the mortar producer's perspective at market prices; diamonds are base-case values and bars the 5th--95th percentile range over the Monte Carlo draws (arrows: range extends beyond the axis). Middle: concrete-producer values derived from the SDSN batching-plant study (Table S19).^49^ Bottom: the premium a cement buyer would face per tonne avoided if kiln CO~2~ capture and storage were passed through (Table S19).^46--48^ Cement-producer costs at clinker production cost are not comparable and are listed in Table S19 only.")

# ------------------------------------------------------------------ data availability ------------------------------
edit("**Data Availability Statement.**", 'https://github.com/\\[org\\]/biocarb-lca-tea', "https://github.com/maverickjiang0302/biocarb-lca-tea")

# ------------------------------------------------------------------ references -------------------------------------
edit("(20) Cunningham, P. R.", "*197*, 107xxx.", "*197*, 107772.")
replace_para("(49) ", "(49) Sustainable Development Solutions Network; Saoradh Enterprise Partners. *Life Cycle Assessment (LCA) and Cost-Benefit Analysis for Low Carbon Concrete and Cement Mix Designs*; SDSN, 2022.")
replace_para("(50) ", "(50) International Energy Agency. *Putting CO~2~ to Use: Creating Value from Emissions*; IEA: Paris, 2019.")
i50 = [i for i, l in enumerate(lines) if l.startswith("(50) ")][0]
lines[i50:i50 + 1] = [lines[i50],
    "(51) Siriruang, C.; Toochinda, P.; Julnipitawong, P.; Tangtermsirikul, S. CO~2~ Capture Using Fly Ash from Coal Fired Power Plant and Applications of CO~2~-Captured Fly Ash as a Mineral Admixture for Concrete. *J. Environ. Manage.* **2016**, *170*, 70--78.",
    "(52) Pei, S.-L.; Pan, S.-Y.; Gao, X.; Fang, Y.-K.; Chiang, P.-C. Efficacy of Carbonated Petroleum Coke Fly Ash as Supplementary Cementitious Materials in Cement Mortars. *J. Clean. Prod.* **2018**, *180*, 689--697.",
    "(53) Chen, K.-W.; Pan, S.-Y.; Chen, C.-T.; Chen, Y.-H.; Chiang, P.-C. High-Gravity Carbonation of Basic Oxygen Furnace Slag for CO~2~ Fixation and Utilization in Blended Cement. *J. Clean. Prod.* **2016**, *124*, 350--360.",
    "(54) Davis, R.; Kinchin, C.; Markham, J.; Tan, E.; Laurens, L.; Sexton, D.; Knorr, D.; Schoen, P.; Lukas, J. *Process Design and Economics for the Conversion of Algal Biomass to Biofuels: Algal Biomass Fractionation to Lipid- and Carbohydrate-Derived Fuel Products*; NREL/TP-5100-62368; National Renewable Energy Laboratory: Golden, CO, 2014.",
    "(55) Wang, L.; Wang, J.; Wang, H.; Fang, Y.; Shen, W.; Chen, P.; Xu, Y. Eco-Friendly Treatment of Recycled Concrete Fines as Supplementary Cementitious Materials. *Constr. Build. Mater.* **2022**, *322*, 126491.",
    "(56) Proença, M. P.; Oliveira, D. R. B.; de Souza Risson, K. D. B.; Possan, E. CDW Powder Activated by Mechanical, Thermal and Tannic Acid Treatment: An Option for Circularity in Construction. *Waste Biomass Valoriz.* **2025**, *16*, 2367--2390.",
    "(57) Wang, H.; Wang, L.; Xu, Y.; Ge, Y.; Wang, X.; Li, D.; Cui, L. Bio-Inspired Functionalization of Recycled Concrete Powder for Better Performance of Alkali-Activated Slag/Recycled Concrete Powder. *Constr. Build. Mater.* **2024**, *449*, 138393.",
    "(58) Wang, L.; Xu, H.; Xu, J.; Shen, W.; Wang, H.; Ge, Y.; Cheng, W. Tannic Acid Treatment of Fine Recycled Concrete Aggregates (RCAs) for Better Impact Resistance Performance of Cementitious Materials. *Mech. Time-Depend. Mater.* **2025**, *29*, 101."]

text = "\n".join(lines)
text = text.replace(" Fig. 8 puts these numbers next to the few published values", "\n\nFig. 8 puts these numbers next to the few published values")   # separate paragraph, as in the authors' file
# SI Table S2 was deleted: renumber Table S3..S19 -> S2..S18 in every cross-reference (single pass; the source is always the v20 text)
assert "Table S2" not in text, [l for l in lines if "Table S2" in l]
def _renum_group(m):
    return re.sub(r"S(\d+)", lambda k: f"S{int(k.group(1)) - 1 if int(k.group(1)) >= 3 else int(k.group(1))}", m.group(0))
text = re.sub(r"Tables? S\d+(?:(?:, | and |–|-)S\d+)*", _renum_group, text)
assert "v19" not in text, [l for l in lines if "v19" in l]
(M / "manuscript_v21.md").write_text(text, encoding="utf-8")
print("wrote manuscript_v21.md;", len(lines), "lines")

"""Reproduce every number and figure in the manuscript and SI.

    python src/make_all.py [--mc N]

Requires the local impact-factor file (see docs/impact_factors_schema.md).
Outputs: results/*.csv, figures/*.png|pdf
"""
import argparse, json, sys, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import numpy as np, pandas as pd
from biocarb.params import load_process_params, load_tea_params, ROOT
from biocarb import inventory as I, lca as L, tea as T, analysis as A, figures as G

RES = ROOT / "results"; RES.mkdir(exist_ok=True)


def main(n_mc: int):
    t0 = time.time()
    p, ptab = load_process_params(); tp, _ = load_tea_params(); F = L.load_factors()

    # 1. inventory
    inv = I.build_all(p)
    inv.to_csv(RES / "inventory.csv", index=False)
    pd.DataFrame({"parameter": ["electricity_coproduct_kWh_per_kg_mortar", "co2_uptake_field_kg_per_kg_rcf", "co2_new_lab_from_CE_kg_per_kg_rcf","co2_total_carbonate_lab_from_CE_kg_per_kg_rcf",
                                "rcf_per_kg_mortar", "co2_supplied_per_kg_mortar"],
                  "value": [I.electricity_coproduct(p), I.co2_uptake(p), I.co2_uptake(p, p["cao_lab"], p["ce0_lab"]), I.co2_uptake(p, p["cao_lab"], 0.0),
                            p["binder"] * p["repl"] / (1 + I.co2_uptake(p) * p["binder"] * p["repl"]),
                            inv.loc[(inv.scenario == "BC_B") & (inv.flow.str.startswith("CO2 supplied")), "amount"].sum() * p["co2_per_kwh_capture"]]
                  }).to_csv(RES / "derived_quantities.csv", index=False)

    # 2. LCA
    tot = L.totals(inv, F); tot.to_csv(RES / "lca_totals.csv")
    L.by_stage(inv, F, "GWP").to_csv(RES / "lca_gwp_by_stage.csv")
    L.impacts(inv, F).to_csv(RES / "lca_flow_level.csv", index=False)
    L.validation(p, F).to_csv(RES / "lca_validation.csv", index=False)
    bench = F.loc["hand-mixed mortar RoW (validation only)", "GWP"] + I.electricity_coproduct(p) * F.loc[I.DS["nocapture"], "GWP"]
    json.dump({"ecoinvent_hand_mixed_mortar_plus_coproduct_GWP": bench}, open(RES / "benchmark.json", "w"), indent=1)

    # 3. TEA
    res, con, eq = T.run_tea(inv, p, tp)
    res.to_csv(RES / "tea_summary.csv", index=False); con.to_csv(RES / "tea_msp_contributions.csv", index=False); eq.to_csv(RES / "tea_equipment.csv", index=False)

    # 4. base evaluation + MAC + LC3 price variants (reference lines for break-even plots)
    base = A.evaluate(p, tp, F); base.to_csv(RES / "base_results.csv")
    A.mac(base).to_frame().to_csv(RES / "mac.csv")
    A.mac_by_baseline(base).to_csv(RES / "mac_by_baseline.csv", index=False)
    ref = base.copy()
    for f in (0.8, 1.0, 1.15):
        tt = dict(tp); tt["price_lc3_factor"] = f
        r = A.evaluate(p, tt, F, ["LC3_A", "LC3_B"])
        for s in r.index:
            ref.loc[f"{s}_p{f}"] = r.loc[s]
    ref.to_csv(RES / "breakeven_reference_lines.csv")

    # 5. sweeps
    sweeps = [("repl", np.linspace(0.10, 0.50, 9), "p"), ("cao_field", np.linspace(0.15, 0.45, 7), "p"),
              ("util", np.linspace(0.80, 1.00, 5), "p"), ("ce0_field", np.linspace(0.10, 0.40, 7), "p"), ("price_rcf", np.linspace(0, 30, 7), "tp"),
              ("price_ta", np.linspace(2, 16, 8), "tp"), ("labor_rate", np.linspace(22, 36, 8), "tp"),
              ("ta_retained", np.linspace(0.33, 1.0, 8), "p"), ("price_il", np.linspace(140, 180, 5), "tp"),
              ("price_fa", np.linspace(40, 90, 6), "tp"), ("price_lc3_factor", np.array([0.8, 0.9, 1.0, 1.15]), "tp"),
              ("price_co2", np.linspace(0, 120, 7), "tp")]
    sw = pd.concat([A.sweep(p, tp, F, n, v, w) for n, v, w in sweeps], ignore_index=True)   # all scenarios: references move with the co-product
    sw.to_csv(RES / "sweeps.csv", index=False)

    # 6. tornado + Monte Carlo
    A.tornado(p, tp, F, "BC_B").to_csv(RES / "tornado_BC_B.csv", index=False)
    A.tornado(p, tp, F, "BC_A").to_csv(RES / "tornado_BC_A.csv", index=False)
    mc = A.monte_carlo(p, tp, F, n=n_mc); mc.to_csv(RES / "montecarlo.csv", index=False)
    summ, probs = A.mc_summary(mc); summ.to_csv(RES / "montecarlo_summary.csv", index=False); probs.to_csv(RES / "montecarlo_probabilities.csv")

    # 6b. literature CO2-uptake normalisation to carbonation efficiency (Eq. S24: CE_app = u / (CaO x 44.01/56.08))
    lit = pd.read_csv(ROOT / "data" / "literature_uptake.csv", dtype={"cao_wt_pct": str, "theoretical_uptake_override": str})
    lit = A.normalize_literature_uptake(lit)
    lit.to_csv(RES / "literature_uptake_normalized.csv", index=False)

    # 7. figures
    G.all_figures()
    print(f"done in {time.time()-t0:.0f} s"); print(base.round(4)); print(probs.round(3))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--mc", type=int, default=1000)
    main(ap.parse_args().mc)

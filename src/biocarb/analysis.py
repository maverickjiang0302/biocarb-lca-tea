"""Sensitivity, break-even, Monte Carlo and marginal-abatement-cost analyses.

All routines call `evaluate(p, tp, F)`, which rebuilds the inventory for the given parameter
sets (so that the electricity co-product and mass normalisation stay consistent) and returns
GWP [kg CO2e/kg mortar] and MSP [cents/kg mortar] for every scenario.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import inventory as I, lca as L, tea as T
from .params import mc_table

RNG = np.random.default_rng(20260910)


def evaluate(p: dict, tp: dict, F: pd.DataFrame, scenarios=None, tea=True) -> pd.DataFrame:
    scn = scenarios or I.SCENARIOS
    E = I.electricity_coproduct(p)
    inv = pd.concat([I.build_scenario(s, p, E) for s in scn], ignore_index=True)
    tot = L.totals(inv, F).loc[scn]
    out = tot.copy()
    if tea:
        res, _, _ = T.run_tea(inv, p, tp, scn)
        out["MSP"] = res.set_index("scenario").loc[scn, "MSP_cpkg"]
    return out


def mac(df: pd.DataFrame, baseline_by_scale=True) -> pd.Series:
    """Marginal abatement cost, USD per t CO2e avoided vs the Type IL mortar of the same scale (Eq. S22)."""
    out = {}
    for s in df.index:
        base = "IL_" + I.SCALE[s]
        dG = df.loc[base, "GWP"] - df.loc[s, "GWP"]                 # kg CO2e / kg mortar
        dC = (df.loc[s, "MSP"] - df.loc[base, "MSP"]) / 100        # USD / kg mortar
        out[s] = np.nan if abs(dG) < 1e-9 else dC / dG * 1000       # USD / t CO2e
    return pd.Series(out, name="MAC_usd_per_tCO2e")


def mac_by_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Marginal abatement cost of every scenario against each reference mortar of the same scale (Type IL,
    IL + 30 % fly ash, LC3-50). NaN where the scenario does not abate relative to that reference (avoided
    CO2 <= 0), because the ratio is then meaningless. Fig. 8b uses the BC_B rows."""
    rows = []
    for s in df.index:
        sc = I.SCALE[s]
        for ref in ("IL", "FA", "LC3"):
            b = f"{ref}_{sc}"
            if b == s:
                continue
            dG = df.loc[b, "GWP"] - df.loc[s, "GWP"]                 # kg CO2e avoided per kg mortar
            dC = (df.loc[s, "MSP"] - df.loc[b, "MSP"]) / 100        # USD per kg mortar
            rows.append(dict(scenario=s, baseline=b, dGWP_kg_per_kg=dG, dMSP_usd_per_kg=dC,
                             MAC_usd_per_tCO2e=(dC / dG * 1000) if dG > 1e-9 else np.nan))
    return pd.DataFrame(rows)


def sweep(p, tp, F, name, values, which="p", scenarios=None) -> pd.DataFrame:
    """One-at-a-time sweep. GWP is the system-expansion total per functional unit (1 kg mortar + E kWh, Eq. S3).
    GWP_credited subtracts the E kWh that the functional unit requires from the plant WITHOUT capture, i.e. the
    same result expressed per kg of mortar with the electricity co-product credited (avoided burden). All
    scenario differences and crossings are identical in both forms; the credited form keeps the reference
    mortars constant when a BioCarb parameter (and therefore E) is varied, which is what Fig. 6 needs."""
    ef_nocap = F.loc[I.DS["nocapture"], "GWP"]
    rows = []
    for v in values:
        pp, tt = dict(p), dict(tp)
        (pp if which == "p" else tt)[name] = v
        E = I.electricity_coproduct(pp)
        r = evaluate(pp, tt, F, scenarios)
        for s in r.index:
            rows.append(dict(parameter=name, value=v, scenario=s, GWP=r.loc[s, "GWP"], MSP=r.loc[s, "MSP"],
                             E_kWh=E, GWP_credited=r.loc[s, "GWP"] - E * ef_nocap))
    return pd.DataFrame(rows)


def tornado(p, tp, F, target="BC_B") -> pd.DataFrame:
    """One-at-a-time bounds. GWP is reported as the difference to the fly-ash and LC3 references of the same
    scale, re-evaluated at the same electricity co-product (system expansion requires equal functional units).
    MSP is reported both as the absolute change of the target (dMSP) and as the change of its margin over the
    same-scale Type IL and fly-ash mortars (dMSP_vs_IL, dMSP_vs_FA); inputs shared by all systems (cement price,
    common-plant capital, common labor) largely cancel in the margin, which is the quantity Fig. 7b shows."""
    sc = I.SCALE[target]; refs = [f"FA_{sc}", f"LC3_{sc}", f"IL_{sc}"]
    base = evaluate(p, tp, F, [target] + refs)
    rows = []
    for _, r in mc_table().iterrows():
        which = "p" if r["file"] == "parameters.csv" else "tp"
        for bound in ("mc_low", "mc_high"):
            pp, tt = dict(p), dict(tp)
            (pp if which == "p" else tt)[r["name"]] = float(r[bound])
            res = evaluate(pp, tt, F, [target] + refs)
            rows.append(dict(parameter=r["name"], bound=bound.replace("mc_", ""), value=float(r[bound]),
                             GWP=res.loc[target, "GWP"], MSP=res.loc[target, "MSP"],
                             dGWP=res.loc[target, "GWP"] - base.loc[target, "GWP"],
                             dGWP_vs_FA=(res.loc[target, "GWP"] - res.loc[refs[0], "GWP"]) - (base.loc[target, "GWP"] - base.loc[refs[0], "GWP"]),
                             GWP_minus_FA=res.loc[target, "GWP"] - res.loc[refs[0], "GWP"],
                             GWP_minus_LC3=res.loc[target, "GWP"] - res.loc[refs[1], "GWP"],
                             dMSP=res.loc[target, "MSP"] - base.loc[target, "MSP"],
                             MSP_minus_IL=res.loc[target, "MSP"] - res.loc[refs[2], "MSP"],
                             MSP_minus_FA=res.loc[target, "MSP"] - res.loc[refs[0], "MSP"],
                             dMSP_vs_IL=(res.loc[target, "MSP"] - res.loc[refs[2], "MSP"]) - (base.loc[target, "MSP"] - base.loc[refs[2], "MSP"]),
                             dMSP_vs_FA=(res.loc[target, "MSP"] - res.loc[refs[0], "MSP"]) - (base.loc[target, "MSP"] - base.loc[refs[0], "MSP"])))
    return pd.DataFrame(rows)


def _sample(row, n):
    lo, hi = float(row["mc_low"]), float(row["mc_high"])
    if row["mc_dist"].startswith("triangular"):
        return RNG.triangular(lo, float(row["value"]), hi, n)
    return RNG.uniform(lo, hi, n)


def monte_carlo(p, tp, F, n=1000) -> pd.DataFrame:
    tbl = mc_table()
    tbl = tbl[~tbl["mc_dist"].str.endswith("_sa")]          # "_sa" = sensitivity-only (design choice, not uncertainty)
    samples = {r["name"]: (_sample(r, n), r["file"]) for _, r in tbl.iterrows()}
    rows = []
    for i in range(n):
        pp, tt = dict(p), dict(tp)
        for k, (arr, f) in samples.items():
            (pp if f == "parameters.csv" else tt)[k] = float(arr[i])
        r = evaluate(pp, tt, F)
        rec = {"iter": i}
        for s in r.index:
            rec[f"GWP_{s}"] = r.loc[s, "GWP"]; rec[f"MSP_{s}"] = r.loc[s, "MSP"]
        for k, (arr, _) in samples.items():
            rec[f"in_{k}"] = float(arr[i])
        rows.append(rec)
    return pd.DataFrame(rows)


def mc_summary(mc: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for s in I.SCENARIOS:
        for m in ("GWP", "MSP"):
            x = mc[f"{m}_{s}"]
            rows.append(dict(scenario=s, metric=m, p05=x.quantile(.05), p50=x.quantile(.5), p95=x.quantile(.95), mean=x.mean()))
    probs = {
        "P(GWP BC_B < FA_B)": (mc.GWP_BC_B < mc.GWP_FA_B).mean(),
        "P(GWP BC_B < LC3_B)": (mc.GWP_BC_B < mc.GWP_LC3_B).mean(),
        "P(GWP BC_A < FA_A)": (mc.GWP_BC_A < mc.GWP_FA_A).mean(),
        "P(MSP BC_B < FA_B)": (mc.MSP_BC_B < mc.MSP_FA_B).mean(),
        "P(MSP BC_B < LC3_B)": (mc.MSP_BC_B < mc.MSP_LC3_B).mean(),
        "P(MSP BC_B < IL_B)": (mc.MSP_BC_B < mc.MSP_IL_B).mean(),
        "P(MSP BC_A < FA_A)": (mc.MSP_BC_A < mc.MSP_FA_A).mean(),
    }
    return pd.DataFrame(rows), pd.Series(probs, name="probability")

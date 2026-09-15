"""Techno-economic analysis.

Minimum selling price (MSP) is the plant-gate price at which the net present value of the equity
cash flows over the plant life equals zero at the target IRR (NREL discounted-cash-flow convention).

Basis. MSP_cpkg is expressed per kg of mortar AS MIXED (w/b 0.50), the same basis as the LCA
functional unit, so that both scales and all binders can be compared on one denominator. The
product actually sold differs by scale: at the dry-mix plant (A) it is a bagged dry premix
(0.884 kg per kg of mortar; the customer adds 0.116 kg water and mixes on site), at the ready-mix
plant (B) it is wet mortar. MSP_per_kg_product_cpkg gives the price per kg of product as sold
(= MSP_cpkg / 0.884 at scale A). Plant-gate boundary: delivery, site mixing labor and, at scale A,
mixing water and mixer electricity are excluded because they are identical across binders at a
given scale (see SI Text S4).

Capital cost (Eq. S9-S12)
  purchased equipment  C_p  = vendor quote scaled: C_base * (S/S_base)^n * CEPCI_2024/CEPCI_quote
                            or Towler & Sinnott correlation: (a + b S^n) * CEPCI_2024/CEPCI_2010
  ISBL                 = install_factor * sum(C_p)
  OSBL                 = osbl_frac * ISBL
  TDC                  = ISBL + OSBL (+ common plant, already installed cost)
  FCI                  = TDC * (1 + indirect_frac)
  TCI                  = FCI * (1 + working_capital_frac)

Operating cost (Eq. S13)
  variable: sum over inventory flows (amount per kg mortar x price) x annual production
  fixed:    labor (FTE x hours x rate) + maintenance (3 % ISBL) + insurance & tax (0.7 % FCI)

Sizing of the BioCarb unit (per plant, Eq. S14-S20)
  RCF rate       m_rcf  = rcf_per_kg x annual mortar / op_hours                    [t/h]
  slurry volume  V_tank = m_rcf * (1 + L/S) * t_res / (rho_slurry * fill)           [m3], t_res = 1 h each for soaking and carbonation tanks; settling 2 h
  agitators      0.2 kW/m3 (min 5 kW), one per tank
  gas flow       Q_gas  = CO2 supplied [kg/h] * 0.5535 m3/kg                        [m3/h]
  column         D from u_g = 0.05 m/s; H = 3 m packed + 1 m; shell 8 mm CS
  filter press   V = wet cake [kg/h] x 1 h cycle / 2000 kg/m3 = cake volume per cycle [m3]; split into units of <= 1.4 m3 (Towler capacity range)
  spray dryer    water evaporated [kg/h]
Scale A (dry-mix plant) includes filter press and dryer; scale B (ready-mix, slurry) does not.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from .params import load_equipment
from . import inventory as I

RHO_CAKE = 2000.0      # wet filter-cake bulk density, kg/m3 (dense mineral cake at 30 % moisture)
FILTER_CYCLE_H = 1.0   # filter-press cycle time, h
RHO_STEEL = 7850.0


def scenario_meta(scn: str, tp: dict) -> dict:
    scale = I.SCALE[scn]
    prod = tp["plantA_tpy"] / (1 - 0.115789) if scale == "A" else tp["plantB_tpy"]   # t wet-mortar-equivalent / yr
    return dict(scale=scale, prod_t=prod, common_cost=tp["plant_common_A_cost"] if scale == "A" else tp["plant_common_B_cost"],
                fte_common=tp["labor_fte_common_A"] if scale == "A" else tp["labor_fte_common_B"],
                fte_bc=tp["labor_fte_bc_A"] if scale == "A" else tp["labor_fte_bc_B"])


def _towler(a, b, n, S, tp):
    return (a + b * S ** n) * tp["cepci_2024"] / tp["cepci_2010"]


def _vendor(base_cost, base_size, base_year, exp, S, tp):
    idx = tp["cepci_2024"] / (tp["cepci_2020"] if int(base_year) == 2020 else tp["cepci_2010"])
    return base_cost * (S / base_size) ** exp * idx


def size_biocarb_unit(scn: str, inv_s: pd.DataFrame, p: dict, tp: dict) -> pd.DataFrame:
    """Return purchased-equipment table for the BioCarb add-on at the given scale."""
    meta = scenario_meta(scn, tp)
    kg_per_h = meta["prod_t"] * 1000 / tp["op_hours"]
    g = lambda flow: float(inv_s.loc[inv_s.flow.str.startswith(flow), "amount"].sum())
    rcf = p["binder"] * p["repl"] / (1 + I.co2_uptake(p) * p["binder"] * p["repl"])        # kg RCF per kg mortar (normalised)
    m_rcf = rcf * kg_per_h                                                                # kg/h
    co2_kgh = g("CO2 supplied") * p["co2_per_kwh_capture"] * kg_per_h
    q_gas = co2_kgh * I.V_CO2                                                             # m3/h
    slurry_kgh = m_rcf * (1 + p["ls"])
    v_tank = slurry_kgh * 1.0 / 1100.0 / 0.8                                              # 1 h residence, 1100 kg/m3, 80 % fill
    v_settle = slurry_kgh * 2.0 / 1100.0 / 0.8
    D = math.sqrt(q_gas / 3600 / 0.05 / (math.pi / 4))
    D = max(D, 0.3)
    H = 4.0
    shell = math.pi * D * H * 0.008 * RHO_STEEL * 1.2
    packing = math.pi / 4 * D ** 2 * 3.0
    eq = load_equipment()
    rows = []
    for _, r in eq.iterrows():
        if not any(s.startswith("BC_" + I.SCALE[scn]) for s in r["scenario_scope"].split(";")):
            continue
        item = r["item"]; n_units = 1
        if item.startswith("fine ball mill"):
            S, unit = m_rcf / 1000, "t/h"
        elif item.startswith("soaking"):
            S, unit, n_units = max(v_tank, 10.0), "m3 each (x2)", 2
        elif item.startswith("agitators"):
            S, unit, n_units = max(0.2 * v_tank, 5.0), "kW each (x2)", 2
        elif item.startswith("settling"):
            S, unit = max(v_settle, 10.0), "m3"
        elif item.startswith("CO2 packed column"):
            S, unit = max(shell, 160.0), "kg shell"
        elif item.startswith("column packing"):
            S, unit = max(packing, 0.1), "m3"
        elif item.startswith("blower"):
            S, unit = max(q_gas, 200.0), "m3/h"
        elif item.startswith("slurry pump"):
            S, unit = max(slurry_kgh / 1100 * 1000 / 3600, 0.2), "L/s"
        elif item.startswith("plate-and-frame"):
            m_cake = m_rcf * (1 + I.co2_uptake(p)) / (1 - p["cake_moisture"])   # wet cake, kg/h
            V = m_cake * FILTER_CYCLE_H / RHO_CAKE                               # cake volume per press cycle, m3 (Towler capacity basis)
            n_units = max(1, math.ceil(V / r["S_max"])); S, unit = max(V / n_units, r["S_min"]), f"m3 each (x{n_units})"
        elif item.startswith("spray dryer"):
            m_carb = m_rcf * (1 + I.co2_uptake(p))
            S, unit = m_carb * p["cake_moisture"] / (1 - p["cake_moisture"]), "kg water/h"
        elif item.startswith("belt conveyor"):
            S, unit = 20.0, "m"
        else:
            continue
        if r["method"] == "towler":
            cost = _towler(r["a"], r["b"], r["n"], S, tp)
            note = f"Towler (a={r['a']},b={r['b']},n={r['n']})"
            if pd.notna(r["S_min"]) and pd.notna(r["S_max"]):
                note += f"; valid {r['S_min']}-{r['S_max']}"
                if not (r["S_min"] <= S <= r["S_max"]):
                    note += " | OUTSIDE RANGE (floor/ceiling applied)"
        else:
            cost = _vendor(r["base_cost_usd"], r["base_size"], r["base_year"], r["scale_exp"], S, tp)
            note = f"vendor {r['base_cost_usd']:.0f} USD@{r['base_size']} ({int(r['base_year'])}), exp {r['scale_exp']}, size ratio {S/r['base_size']:.2f}"
        rows.append(dict(scenario=scn, item=item, size=S, size_unit=unit, n_units=n_units,
                         purchased_cost_2024=cost * n_units, basis=note))
    return pd.DataFrame(rows)


def capital(scn: str, inv_s: pd.DataFrame, p: dict, tp: dict) -> dict:
    meta = scenario_meta(scn, tp)
    eqp = size_biocarb_unit(scn, inv_s, p, tp) if scn.startswith("BC") else pd.DataFrame(columns=["purchased_cost_2024"])
    purchased = float(eqp["purchased_cost_2024"].sum()) if len(eqp) else 0.0
    isbl = tp["install_factor"] * purchased
    osbl = tp["osbl_frac"] * isbl
    tdc = isbl + osbl + meta["common_cost"]
    fci = tdc * (1 + tp["indirect_frac"])
    tci = fci * (1 + tp["working_capital_frac"])
    return dict(equipment=eqp, purchased=purchased, isbl=isbl, osbl=osbl, common=meta["common_cost"], tdc=tdc, fci=fci, tci=tci)


PRICE_KEY = {  # inventory flow prefix -> (tea price name, unit conversion to per kg or per kWh)
    "clinker": None, "limestone": None, "gypsum": None, "calcined clay": None,  # cements priced as products below
    "sand": ("price_sand", 1e-3), "tap water": ("price_water", 1e-3), "electricity": ("price_elec", 1.0),
    "diesel": ("price_diesel", 1.0), "tannic acid make-up": ("price_ta", 1.0), "fly ash": ("price_fa", 1e-3),
    "demolition concrete": None, "CO2 supplied": None,
}


def variable_cost_per_kg(scn: str, inv_s: pd.DataFrame, p: dict, tp: dict) -> pd.DataFrame:
    """USD per kg mortar by cost item (Eq. S13)."""
    items = []
    # binders priced as delivered cements / SCMs
    il_kg = inv_s.loc[(inv_s.stage == "IL cement") & (inv_s.flow == "clinker"), "amount"].sum() / p["il_clinker"]
    if il_kg > 0:
        items.append(("Type IL cement", il_kg * tp["price_il"] * 1e-3))
    lc3_kg = inv_s.loc[(inv_s.stage == "LC3 cement") & (inv_s.flow == "clinker"), "amount"].sum() / p["lc3_clinker"]
    if lc3_kg > 0:
        items.append(("LC3 cement", lc3_kg * tp["price_il"] * tp["price_lc3_factor"] * 1e-3))
    scale = I.SCALE[scn]
    for _, r in inv_s.iterrows():
        if r["stage"] in ("IL cement", "LC3 cement", "product", "functional-unit electricity", "TA production (proxy)"):
            continue
        if scale == "A" and r["stage"] == "mortar mixing" and r["flow"].startswith(("tap water (mixing", "electricity (mixer")):
            continue   # dry-mix plant sells premix; mixing water and site mixing are the customer's (plant-gate boundary)
        for pre, spec in PRICE_KEY.items():
            if r["flow"].startswith(pre):
                if spec:
                    name, conv = spec
                    items.append((r["flow"], r["amount"] * tp[name] * conv))
                break
    if scn.startswith("BC"):
        rcf = inv_s.loc[inv_s.flow.str.startswith("demolition concrete"), "amount"].sum() * p["rcf_yield"]
        items.append(("RCF purchase", rcf * tp["price_rcf"] * 1e-3))
        co2 = inv_s.loc[inv_s.flow.str.startswith("CO2 supplied"), "amount"].sum() * p["co2_per_kwh_capture"]
        items.append(("CO2 purchase", co2 * tp["price_co2"] * 1e-3))
    df = pd.DataFrame(items, columns=["item", "usd_per_kg"])
    return df.groupby("item", as_index=False).sum()


def fixed_cost(scn: str, cap: dict, tp: dict) -> dict:
    meta = scenario_meta(scn, tp)
    fte = meta["fte_common"] + (meta["fte_bc"] if scn.startswith("BC") else 0.0)
    labor = fte * tp["fte_hours"] * tp["labor_rate"]
    maint = tp["maintenance_frac"] * (cap["isbl"] + meta["common_cost"])
    ins = tp["insurance_frac"] * cap["fci"]
    return dict(labor=labor, maintenance=maint, insurance=ins, total=labor + maint + ins, fte=fte)


def macrs7():
    return np.array([0.1429, 0.2449, 0.1749, 0.1249, 0.0893, 0.0892, 0.0893, 0.0446])


def dcf_msp(prod_kg: float, var_per_kg: float, fixed: float, cap: dict, tp: dict) -> float:
    """Solve MSP such that equity NPV = 0 (Eq. S21)."""
    life = int(tp["plant_life"]); n = int(tp["loan_years"])
    loan = (1 - tp["equity"]) * cap["tci"]
    pay = loan * tp["loan_rate"] / (1 - (1 + tp["loan_rate"]) ** -n)
    dep = np.zeros(life); d = macrs7(); dep[:len(d)] = d * cap["fci"]
    bal = loan; interest = np.zeros(life)
    for y in range(n):
        interest[y] = bal * tp["loan_rate"]; bal -= pay - interest[y]
    prodf = np.ones(life); prodf[0] = 0.9                                      # 10 % start-up loss in year 1
    varf = np.ones(life); varf[0] = 0.9 * 1.0 + 0.1 * tp["startup_frac_var"]

    def npv(msp):
        cf = [-tp["equity"] * cap["tci"]]
        for y in range(life):
            rev = msp * prod_kg * prodf[y]
            var = var_per_kg * prod_kg * varf[y]
            taxable = rev - var - fixed - dep[y] - interest[y]
            tax = max(0.0, tp["tax_rate"] * taxable)
            cf.append(rev - var - fixed - (pay if y < n else 0.0) - tax)
        cf[-1] += tp["working_capital_frac"] * cap["fci"]                      # working capital recovered
        return sum(c / (1 + tp["irr"]) ** t for t, c in enumerate(cf))
    return brentq(npv, 0.0, 5.0)


def run_tea(inv: pd.DataFrame, p: dict, tp: dict, scenarios=None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    out, contrib, eqs = [], [], []
    for scn in (scenarios or I.SCENARIOS):
        inv_s = inv[inv.scenario == scn]
        meta = scenario_meta(scn, tp)
        prod_kg = meta["prod_t"] * 1000
        cap = capital(scn, inv_s, p, tp)
        var = variable_cost_per_kg(scn, inv_s, p, tp)
        fx = fixed_cost(scn, cap, tp)
        vpk = float(var.usd_per_kg.sum())
        msp = dcf_msp(prod_kg, vpk, fx["total"], cap, tp)
        capex_ann = msp * prod_kg - vpk * prod_kg - fx["total"]                # capital recovery + tax implied by MSP
        water = 0.115789                                                        # kg mixing water per kg mortar (mix design)
        premix_per_kg_mortar = 1.0 - water if meta["scale"] == "A" else 1.0    # kg product sold per kg mortar as mixed
        out.append(dict(scenario=scn, scale=meta["scale"], production_t_per_yr=meta["prod_t"],
                        product_as_sold="dry premix (bagged)" if meta["scale"] == "A" else "wet mortar (ready-mixed)",
                        product_t_per_yr=meta["prod_t"] * premix_per_kg_mortar,
                        MSP_per_kg_product_cpkg=msp * 100 / premix_per_kg_mortar,
                        purchased_equipment_usd=cap["purchased"],
                        common_plant_usd=cap["common"], FCI_usd=cap["fci"], TCI_usd=cap["tci"], FTE=fx["fte"],
                        variable_cost_cpkg=vpk * 100, fixed_cost_cpkg=fx["total"] / prod_kg * 100,
                        capital_and_tax_cpkg=capex_ann / prod_kg * 100, MSP_cpkg=msp * 100))
        for _, r in var.iterrows():
            contrib.append(dict(scenario=scn, item=r["item"], cents_per_kg=r["usd_per_kg"] * 100))
        for k in ("labor", "maintenance", "insurance"):
            contrib.append(dict(scenario=scn, item=k, cents_per_kg=fx[k] / prod_kg * 100))
        contrib.append(dict(scenario=scn, item="capital recovery + tax", cents_per_kg=capex_ann / prod_kg * 100))
        if len(cap["equipment"]):
            eqs.append(cap["equipment"])
    return pd.DataFrame(out), pd.DataFrame(contrib), (pd.concat(eqs, ignore_index=True) if eqs else pd.DataFrame())

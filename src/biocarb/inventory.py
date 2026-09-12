"""Life-cycle inventory generator.

Every flow is expressed per 1 kg of finished mortar (wet, as mixed) and is derived from the
parameters in data/parameters.csv. The equations are numbered to match the SI:

  S1  CO2 uptake (new)    u   = CaO * (44.01/56.08) * (CE - ce0)            [kg CO2 / kg RCF]
      CE = total carbonate fraction of CaO measured by TGA after carbonation; ce0 = fraction already
      present as carbonate before carbonation (Fig. 1a, t = 0). Only newly fixed CO2 is credited.
  S2  CO2 supplied        s   = u / util                                     [kg CO2 / kg RCF]
      CO2 vented          v   = s - u
  S3  Electricity co-product accompanying CO2 supply (NETL SubPC with capture)
                          E   = s * rcf / r_cap ,  r_cap = 0.910 kg CO2/kWh  [kWh / kg mortar]
      The functional unit is therefore "1 kg mortar + E kWh electricity"; non-BioCarb
      scenarios receive E kWh from the same coal plant WITHOUT capture (NETL CO2U system
      expansion), so that all systems deliver both products. Because the capture plant's
      inventory already reflects the CO2 it does not emit, mineralized CO2 is NOT credited
      again (no -1); vented CO2 (util < 1) is charged at +1.
  S4  TA make-up          m_TA = d_TA * f_ret * rcf                          [kg TA / kg mortar]
  S5  Process make-up water   w_p = L/S * f_ret * rcf                        [kg / kg mortar]
  S6  Column blower       W = dP * V / eta,  V = 0.5535 m3 per kg CO2 (25 C, 1 atm)
  S7  Drying              Q = m_water * q_dry / 3.6                          [kWh / kg mortar]
      m_water = m_carb * x / (1 - x), x = cake moisture
  S8  Mass normalisation  all BioCarb flows / (1 + u * rcf) so that the product is exactly 1 kg

Scenarios
  IL_A, IL_B   Type IL mortar (baseline), scale A (dry-mix plant + on-site mixing) / B (ready-mix)
  FA_A, FA_B   Type IL + 30 % fly ash
  BC_A         BioCarb: carbonated RCF dewatered, dried and bagged with IL and sand at a dry-mix plant
  BC_B         BioCarb: carbonated RCF slurry used directly at a ready-mix plant
  LC3_A, LC3_B LC3-50 cement mortar
"""
from __future__ import annotations
import pandas as pd

R_CO2 = 44.01 / 56.08
V_CO2 = 0.5535          # m3 per kg CO2 at 25 C, 1 atm

# Dataset keys used in the inventory. Mapping to database UUIDs is in data/impact_factor_map.csv.
DS = dict(
    clinker="clinker RoW", limestone="limestone RoW", gypsum="gypsum RoW", clay="calcined clay RoW",
    grid="US grid", sand="sand RoW", water="tap water RoW", diesel="diesel US",
    methanol="methanol GLO", bark="bark chips RoW",
    capture="SubPC capture (per kWh; delivers 0.910 kg CO2)",
    nocapture="SubPC no capture (per kWh)",
    flue="SubPC no capture, flue gas (per kWh)",
    direct_pos="direct emission CO2 (+1)", direct_neg="CO2 mineralized (information; not credited)",
    none="no burden (cut-off)", flow="reported flow, no factor",
)

SCENARIOS = ["IL_A", "IL_B", "FA_A", "FA_B", "BC_A", "BC_B", "LC3_A", "LC3_B"]
SCALE = {s: s.split("_")[1] for s in SCENARIOS}


def co2_uptake(p: dict, cao: float | None = None, ce0: float | None = None) -> float:
    """Eq. S1: newly fixed CO2 per kg RCF (total carbonate minus pre-existing carbonate)."""
    c0 = p.get("ce0_field", 0.0) if ce0 is None else ce0
    return (p["cao_field"] if cao is None else cao) * R_CO2 * max(p["CE"] - c0, 0.0)


def electricity_coproduct(p: dict) -> float:
    """Eq. S3: kWh of capture-plant electricity accompanying the CO2 supplied per kg mortar
    (after mass normalisation, Eq. S8). Same for BC_A and BC_B."""
    rcf = p["binder"] * p["repl"]
    u = co2_uptake(p)
    s = u / p["util"]
    return s * rcf / p["co2_per_kwh_capture"] / (1 + u * rcf)   # per kg of normalised product


class Inv:
    def __init__(self, scenario: str):
        self.s = scenario
        self.rows: list[dict] = []

    def add(self, stage, flow, amount, unit, ds, eq, note=""):
        self.rows.append(dict(scenario=self.s, stage=stage, flow=flow, amount=amount, unit=unit,
                              dataset=ds, equation=eq, note=note))

    def scale(self, f: float):
        for r in self.rows:
            r["amount"] *= f

    def df(self):
        return pd.DataFrame(self.rows)


def _cement(inv: Inv, p: dict, kind: str, kg: float):
    if kind == "IL":
        comp = {"clinker": p["il_clinker"], "limestone": p["il_limestone"], "gypsum": p["il_gypsum"]}
        e = p["il_grind_e"]
    else:
        comp = {"clinker": p["lc3_clinker"], "calcined clay": p["lc3_clay"],
                "limestone": p["lc3_limestone"], "gypsum": p["lc3_gypsum"]}
        e = p["lc3_grind_e"]
    key = {"clinker": DS["clinker"], "limestone": DS["limestone"], "gypsum": DS["gypsum"],
           "calcined clay": DS["clay"]}
    for k, f in comp.items():
        inv.add(f"{kind} cement", k, kg * f, "kg", key[k], f"{kg:.5f} kg cement x {f}")
    inv.add(f"{kind} cement", "electricity (finish grinding)", kg * e, "kWh", DS["grid"], f"{kg:.5f} x {e} kWh/kg")


def _mortar(inv: Inv, p: dict, sand: float, water: float, scale: str):
    inv.add("mortar mixing", "sand", sand, "kg", DS["sand"], "mix design")
    inv.add("mortar mixing", "tap water (mixing, make-up)", water, "kg", DS["water"],
            "mix design; slurry water credited in BC_B")
    inv.add("mortar mixing", "electricity (mixer)", p["mix_e"], "kWh", DS["grid"],
            "0.56 kW x 10 min / 183.8 kg" if scale == "A" else "same specific energy assumed for plant mixer")


def _coproduct_grid(inv: Inv, E: float):
    inv.add("functional-unit electricity", "electricity (SubPC plant without capture, to match BioCarb co-product)", E, "kWh", DS["nocapture"],
            "Eq. S3: equal electricity output for all systems (NETL CO2U system expansion)")


def build_scenario(scenario: str, p: dict, E_cop: float | None = None) -> pd.DataFrame:
    scale = SCALE[scenario]
    inv = Inv(scenario)
    if E_cop is None:
        E_cop = electricity_coproduct(p)

    if scenario.startswith("IL"):
        _cement(inv, p, "IL", p["binder"]); _mortar(inv, p, p["sand"], p["water"], scale); _coproduct_grid(inv, E_cop)

    elif scenario.startswith("FA"):
        fa = p["binder"] * p.get("repl_fa", p["repl"])
        _cement(inv, p, "IL", p["binder"] - fa)
        inv.add("fly ash supply", "fly ash (by-product, cut-off)", fa, "kg", DS["none"], "repl_fa x binder")
        inv.add("fly ash supply", "electricity (handling/classification)", fa * p["fa_handling_e"], "kWh", DS["grid"], "fa x 0.005 kWh/kg")
        _mortar(inv, p, p["sand"], p["water"], scale); _coproduct_grid(inv, E_cop)

    elif scenario.startswith("LC3"):
        _cement(inv, p, "LC3", p["binder"]); _mortar(inv, p, p["sand"], p["water"], scale); _coproduct_grid(inv, E_cop)

    elif scenario.startswith("BC"):
        rcf = p["binder"] * p["repl"]
        u = co2_uptake(p)                     # S1
        s = u / p["util"]                     # S2
        v = s - u
        conc = rcf / p["rcf_yield"]
        inv.add("RCF preparation", "demolition concrete (cut-off)", conc, "kg", DS["none"], "rcf / yield")
        inv.add("RCF preparation", "diesel (mobile crusher)", conc * p["crush_diesel"] * p["crush_alloc"], "kg", DS["diesel"],
                f"concrete x {p['crush_diesel']} x allocation {p['crush_alloc']}")
        inv.add("RCF preparation", "electricity (fine grinding)", rcf * p["grind_e"], "kWh", DS["grid"], f"rcf x {p['grind_e']}")
        w_ret = rcf * p["ls"] * p["water_retained_frac"]                       # S5
        inv.add("soaking & carbonation", "tap water (process make-up)", w_ret, "kg", DS["water"],
                f"rcf x L/S {p['ls']} x retained {p['water_retained_frac']:.3f}; 2/3 recycled uncharged")
        m_ta = rcf * p["ta_dose"] * p["ta_retained"]                            # S4
        inv.add("soaking & carbonation", "tannic acid make-up (purchased)", m_ta, "kg", DS["flow"],
                f"rcf x {p['ta_dose']} x {p['ta_retained']:.3f} (Eq. S4)", "impacts via TA proxy inventory below")
        sol = m_ta / p["ta_solution_fraction"]                                  # kg TA solution equivalent
        inv.add("TA production (proxy)", "methanol (net make-up)", sol * p["ta_methanol_makeup"], "kg", DS["methanol"], "sol x 0.07")
        inv.add("TA production (proxy)", "bark chips", sol * p["ta_bark"], "kg", DS["bark"], "sol x 0.67")
        inv.add("TA production (proxy)", "tap water", sol * p["ta_water"], "kg", DS["water"], "sol x 2.33")
        inv.add("TA production (proxy)", "electricity", sol * p["ta_elec"], "kWh", DS["grid"], "sol x 0.26")
        inv.add("TA production (proxy)", "methanol to water (flow only)", sol * p["ta_methanol_emission"], "kg", DS["flow"], "sol x 0.04")
        inv.add("soaking & carbonation", "electricity (agitation)", rcf * p["stir_e"], "kWh", DS["grid"], "rcf x 0.00496")
        ds_co2 = DS["flue"] if scenario.endswith("flue") else DS["capture"]
        inv.add("CO2 supply", "CO2 supplied, expressed as kWh of source plant", rcf * s / p["co2_per_kwh_capture"], "kWh", ds_co2,
                f"rcf x {s:.4f} kg CO2 / {p['co2_per_kwh_capture']} kg CO2/kWh (Eq. S2-S3)",
                f"= {rcf*s:.5f} kg CO2 per kg mortar (pre-normalisation)")
        inv.add("soaking & carbonation", "electricity (column blower)", rcf * s * p["blower_dp"] * V_CO2 / p["blower_eta"] / 3.6e6,
                "kWh", DS["grid"], "Eq. S6")
        if v > 0:
            inv.add("CO2 mineralized / vented", "CO2 vented", rcf * v, "kg", DS["direct_pos"], "(1-util) x supplied")
        inv.add("CO2 mineralized / vented", "CO2 mineralized (permanent; information only)", -rcf * u, "kg", DS["direct_neg"],
                "Eq. S1; avoided emission already reflected in the capture-plant inventory, so not credited again")
        m_carb = rcf * (1 + u)
        if scale == "A":
            m_w = m_carb * p["cake_moisture"] / (1 - p["cake_moisture"])       # S7
            inv.add("dewatering & drying", "electricity (spray dryer)", m_w * p["dry_MJ_per_kg_water"] / 3.6, "kWh", DS["grid"],
                    f"{m_w:.4f} kg water x {p['dry_MJ_per_kg_water']} MJ/kg / 3.6")
            water_mix = p["water"]
        else:
            water_mix = max(p["water"] - w_ret, 0.0)
        _cement(inv, p, "IL", p["binder"] - rcf)
        _mortar(inv, p, p["sand"], water_mix, scale)
        inv.add("product", "carbonated RCF in mortar (information)", m_carb, "kg", DS["flow"], "rcf x (1+u)")
        inv.scale(1.0 / (1 + u * rcf))                                          # S8
    return inv.df()


def build_all(p: dict) -> pd.DataFrame:
    E = electricity_coproduct(p)
    return pd.concat([build_scenario(s, p, E) for s in SCENARIOS], ignore_index=True)

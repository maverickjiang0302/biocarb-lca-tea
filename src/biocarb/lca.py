"""LCA calculation: impact = sum over flows of amount x unit impact score of the linked dataset.

Unit impact scores (TRACI 2.1 via the NETL openLCA implementation, ecoinvent 3.7 cut-off
background) are read from a LOCAL file that is NOT distributed with this repository because it
contains licensed ecoinvent-derived data. Set the environment variable BIOCARB_IMPACT_FACTORS to
its path, or place `entries_with_impacts.csv` in the repository root. The file must have the
columns listed in data/impact_factor_map.csv (name, UUID) plus one column per impact category as
exported by openLCA (see docs/impact_factors_schema.md). Aggregated results per scenario ARE
distributed (results/).
"""
from __future__ import annotations
import os
import pathlib
import pandas as pd
from .params import ROOT, DATA
from . import inventory as I

CATS = {  # column-name fragment in the export -> short label, unit
    "Global Warming": ("GWP", "kg CO2e"),
    "Acidification": ("AP", "kg SO2e"),
    "Water Consumption": ("WC", "kg water"),
    "Particulate": ("PM", "kg PM2.5e"),
    "Ozone Depletion": ("ODP", "kg CFC-11e"),
    "Smog": ("SFP", "kg O3e"),
    "Eutrophication": ("EP", "kg Ne"),
}
SHORT = [v[0] for v in CATS.values()]


def factors_path() -> pathlib.Path:
    env = os.environ.get("BIOCARB_IMPACT_FACTORS")
    for cand in ([pathlib.Path(env)] if env else []) + [ROOT / "entries_with_impacts.csv"]:
        if cand.exists():
            return cand
    raise FileNotFoundError("Impact-factor file not found; see docs/impact_factors_schema.md")


def load_factors() -> pd.DataFrame:
    """Return DataFrame indexed by dataset_key with one column per short category."""
    raw = pd.read_csv(factors_path()).dropna(subset=["UUID"])
    cols = {}
    for frag, (short, _) in CATS.items():
        m = [c for c in raw.columns if frag in c]
        if not m:
            raise KeyError(f"No column for {frag}")
        cols[short] = m[0]
    raw = raw.set_index("UUID")
    mp = pd.read_csv(DATA / "impact_factor_map.csv")
    F = pd.DataFrame(index=mp["dataset_key"], columns=SHORT, dtype=float)
    for _, r in mp.iterrows():
        if r["uuid"] in raw.index:
            for short, col in cols.items():
                F.loc[r["dataset_key"], short] = float(raw.loc[r["uuid"], col])
    # direct flows
    F.loc[I.DS["direct_pos"]] = 0.0; F.loc[I.DS["direct_pos"], "GWP"] = 1.0
    F.loc[I.DS["direct_neg"]] = 0.0                                          # not credited (see inventory.py)
    F.loc[I.DS["none"]] = 0.0
    F.loc[I.DS["flow"]] = 0.0
    return F


def impacts(inv: pd.DataFrame, F: pd.DataFrame) -> pd.DataFrame:
    """Per-flow impacts (all categories)."""
    missing = set(inv["dataset"]) - set(F.index)
    if missing:
        raise KeyError(f"datasets without factors: {missing}")
    fac = F.loc[inv["dataset"].values, SHORT].to_numpy()
    out = inv.copy()
    for j, c in enumerate(SHORT):
        out[c] = out["amount"].to_numpy() * fac[:, j]
    return out


def totals(inv: pd.DataFrame, F: pd.DataFrame) -> pd.DataFrame:
    return impacts(inv, F).groupby("scenario")[SHORT].sum().reindex(I.SCENARIOS)


def by_stage(inv: pd.DataFrame, F: pd.DataFrame, cat: str = "GWP") -> pd.DataFrame:
    return impacts(inv, F).groupby(["scenario", "stage"])[cat].sum().unstack("stage").reindex(I.SCENARIOS).fillna(0.0)


def validation(p: dict, F: pd.DataFrame) -> pd.DataFrame:
    """Compare component-built cements with independent datasets/EPDs (GWP)."""
    il = (p["il_clinker"] * F.loc[I.DS["clinker"], "GWP"] + p["il_limestone"] * F.loc[I.DS["limestone"], "GWP"]
          + p["il_gypsum"] * F.loc[I.DS["gypsum"], "GWP"] + p["il_grind_e"] * F.loc[I.DS["grid"], "GWP"])
    opc = (0.92 * F.loc[I.DS["clinker"], "GWP"] + 0.05 * F.loc[I.DS["gypsum"], "GWP"] + 0.03 * F.loc[I.DS["limestone"], "GWP"]
           + p["lc3_grind_e"] * F.loc[I.DS["grid"], "GWP"])
    rows = [
        ("Type IL, component-built", il, 0.846, "PCA 2021 industry-average PLC EPD"),
        ("Portland, component-built", opc, 0.922, "PCA 2021 industry-average portland cement EPD"),
        ("Portland, component-built", opc, F.loc["cement Portland US (validation only)", "GWP"], "ecoinvent market for cement, Portland | US"),
    ]
    return pd.DataFrame(rows, columns=["item", "model_kgCO2e_per_kg", "reference_kgCO2e_per_kg", "reference_source"]).assign(
        deviation_pct=lambda d: 100 * (d.model_kgCO2e_per_kg / d.reference_kgCO2e_per_kg - 1))

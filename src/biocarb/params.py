"""Parameter handling: every model input lives in data/parameters.csv (LCA/process) and
data/tea_parameters.csv (TEA). Values are loaded into plain dicts so that sensitivity and
Monte Carlo routines can override any entry by name."""
from __future__ import annotations
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _load(path: pathlib.Path) -> tuple[dict, pd.DataFrame]:
    df = pd.read_csv(path)
    vals = {}
    for _, r in df.iterrows():
        v = r["value"]
        try:
            v = float(v)
        except (TypeError, ValueError):
            pass
        vals[r["name"]] = v
    return vals, df


def load_process_params() -> tuple[dict, pd.DataFrame]:
    return _load(DATA / "parameters.csv")


def load_tea_params() -> tuple[dict, pd.DataFrame]:
    return _load(DATA / "tea_parameters.csv")


def load_equipment() -> pd.DataFrame:
    return pd.read_csv(DATA / "equipment.csv")


def mc_table() -> pd.DataFrame:
    """Rows of both parameter files that carry a Monte Carlo distribution."""
    _, a = load_process_params()
    _, b = load_tea_params()
    a = a.assign(file="parameters.csv")
    b = b.assign(file="tea_parameters.csv")
    t = pd.concat([a, b], ignore_index=True)
    return t[t["mc_dist"].notna()][["name", "value", "mc_dist", "mc_low", "mc_high", "file"]]

"""Regression and sanity tests.  Run:  BIOCARB_IMPACT_FACTORS=/path/to/entries_with_impacts.csv pytest -q"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd, pytest
from biocarb.params import load_process_params, load_tea_params, ROOT
from biocarb import inventory as I, lca as L, tea as T, analysis as A


@pytest.fixture(scope="module")
def setup():
    p, _ = load_process_params(); tp, _ = load_tea_params()
    try:
        F = L.load_factors()
    except FileNotFoundError:
        pytest.skip("impact-factor file not available")
    return p, tp, F


def test_mass_balance(setup):
    p, tp, F = setup
    inv = I.build_all(p)
    for s in ["IL_A", "FA_A", "LC3_A"]:
        d = inv[(inv.scenario == s)]
        mass = d[(d.unit == "kg") & d.stage.isin(["mortar mixing"])].amount.sum()
        binder = d[d.stage.str.contains("cement")].loc[lambda x: x.unit == "kg", "amount"].sum() + d[d.flow.str.startswith("fly ash")].amount.sum()
        assert abs(mass + binder - 1.0) < 1e-6
    d = inv[inv.scenario == "BC_B"]
    prod = d[d.flow.str.startswith("carbonated RCF")].amount.sum() + d[(d.stage == "IL cement") & (d.unit == "kg")].amount.sum() \
        + d[d.stage == "mortar mixing"].loc[lambda x: x.unit == "kg", "amount"].sum() + d[d.flow.str.startswith("tap water (process")].amount.sum()
    assert abs(prod - 1.0) < 1e-6


def test_uptake_equation(setup):
    p, tp, F = setup
    assert abs(I.co2_uptake(p) - 0.30 * 44.01 / 56.08 * (0.80 - 0.165)) < 1e-9
    assert abs(I.co2_uptake(p, p["cao_lab"], 0.0) - 0.3631) < 1e-3     # total carbonate = reported 0.365
    assert abs(I.co2_uptake(p, p["cao_lab"], p["ce0_lab"]) - 0.2882) < 1e-3  # newly fixed CO2


def test_il_validation(setup):
    p, tp, F = setup
    v = L.validation(p, F)
    assert abs(v.loc[0, "deviation_pct"]) < 5.0


def test_regression_against_shipped_results(setup):
    p, tp, F = setup
    base = A.evaluate(p, tp, F)
    ref = pd.read_csv(ROOT / "results" / "base_results.csv", index_col=0)
    assert np.allclose(base["GWP"].values, ref.loc[base.index, "GWP"].values, rtol=1e-6)
    assert np.allclose(base["MSP"].values, ref.loc[base.index, "MSP"].values, rtol=1e-6)


def test_msp_solver_monotone(setup):
    p, tp, F = setup
    r1 = A.evaluate(p, tp, F, ["BC_B"]); tt = dict(tp); tt["price_ta"] = 16
    r2 = A.evaluate(p, tt, F, ["BC_B"])
    assert r2.loc["BC_B", "MSP"] > r1.loc["BC_B", "MSP"]

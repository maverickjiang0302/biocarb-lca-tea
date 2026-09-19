# BioCarb harmonized LCA–TEA

Model, inventory and results for:

> *Biomolecule-regulated carbonation (BioCarb) as a drop-in supplementary cementitious material (SCM): harmonized life-cycle and techno-economic assessment* (Chen, Huang, Chen, Wang, Wang and Jiang; revised manuscript for *Environmental Science & Technology*).

Every number and table in the manuscript and Supporting Information is produced by `python src/make_all.py` from the CSV inputs in `data/`, and every result table is in `results/`. The figures and the documents were drawn and rendered from those result tables with separate scripts that are not part of this archive; nothing in them adds a number to the analysis.

## Layout
```
data/
  parameters.csv          process/LCA parameters: value, unit, description, source, Monte Carlo range
  tea_parameters.csv      economic parameters (2024 USD)
  equipment.csv           equipment sizing/costing basis (vendor quotes and cost correlations)
  impact_factor_map.csv   dataset keys -> database process names and UUIDs (no impact values)
  lab_data.csv            laboratory data as reported (Fig. 2)
  literature_uptake.csv   literature CO2-uptake data and feedstock CaO (Table 1 / S18)
  abatement_cost_literature.csv  benchmark abatement costs (Fig. 8b / S19)
src/
  biocarb/params.py       parameter loading
  biocarb/inventory.py    inventory generator (Eq. S1–S8)
  biocarb/lca.py          LCA engine, validation (Eq. S8)
  biocarb/tea.py          equipment sizing, capital & operating cost, DCF/MSP (Eq. S9–S21)
  biocarb/analysis.py     sensitivity sweeps, tornado, Monte Carlo, marginal abatement cost (Eq. S22)
  make_all.py             pipeline entry point
  tests/                  pytest sanity + regression tests
results/                  all model outputs (CSV): inventory, LCA totals and stages, TEA summary and
                          contributions, base results, break-even reference lines, sweeps, tornado,
                          Monte Carlo draws and summary, abatement costs, normalized literature uptake
docs/                     impact-factor schema, change log
```

## Reproduce
```bash
pip install -r requirements.txt
export BIOCARB_IMPACT_FACTORS=/path/to/entries_with_impacts.csv   # see docs/impact_factors_schema.md
python src/make_all.py --mc 1000
pytest -q src/tests
```
Runtime is under a minute (Monte Carlo n = 1000, fixed seed; results are reproducible to the last digit).

## What is and is not included
* Included: all inventories per kg mortar, all parameters with sources, equipment sizing basis, TEA cash-flow model, aggregated LCA/TEA results per scenario, Monte Carlo samples, sweeps, tornado and abatement-cost tables.
* Not included: process-level unit impact scores derived from ecoinvent (licensed), and the per-flow impact table `results/lca_flow_level.csv` from which they could be recovered. The map of dataset keys to UUIDs is provided so that licence holders can regenerate the factor file in openLCA; all aggregated results per scenario are included.
* Also not included: the figure and document scripts and the figure files. They are produced from `results/*.csv` and add no number.

## Scenarios
| key | system | scale |
|---|---|---|
| IL_A / IL_B | ASTM C595 Type IL mortar (baseline) | A: dry-mix plant + on-site mixing (100 kt/yr dry mortar); B: ready-mix plant (60 kt/yr) |
| FA_A / FA_B | Type IL + 30 % Class F fly ash | A / B |
| BC_A | BioCarb: carbonated RCF dewatered, dried and bagged with IL and sand | A |
| BC_B | BioCarb: carbonated RCF slurry dosed directly into mortar | B |
| LC3_A / LC3_B | LC3-50 mortar | A / B |

Functional unit: 1 kg of mortar (as mixed, w/b 0.50) **plus** 0.0113 kWh of electricity (the co-product of the captured CO2 used by BioCarb; Eq. S3). Reference systems supply that electricity from the same coal plant without capture (NETL CO2U system expansion); mineralized CO2 is not credited separately. Cradle-to-gate; transport excluded.

## Citation
See `CITATION.cff`. Zenodo: concept DOI https://doi.org/10.5281/zenodo.22767758 (always resolves to the latest version). Version 1.3.0 (model, results and figures): https://doi.org/10.5281/zenodo.22767759. Version 1.4.0 (this release; model and data only, same results): https://doi.org/10.5281/zenodo.22851009.

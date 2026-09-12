# Impact-factor file (not distributed)

The model multiplies each inventory flow by the cradle-to-gate unit impact score of the linked background
process. Those scores were exported from openLCA 2.x with the NETL implementation of TRACI 2.1 using the
ecoinvent 3.7 cut-off database and the NETL CO2U unit-process library. ecoinvent's licence does not permit
redistribution of these process-level results, so the file is excluded from the repository (`.gitignore`).

## How to regenerate
1. In openLCA, create a product system for each process listed in `data/impact_factor_map.csv`
   (UUIDs are given; names may differ slightly between database versions).
2. Calculate with the impact method "TRACI 2.1 (NETL)" and export the results per unit of reference flow.
3. Assemble a CSV with the columns below and point the model to it:
   `export BIOCARB_IMPACT_FACTORS=/path/to/entries_with_impacts.csv` (or place it in the repo root).

## Required columns
| column | content |
|---|---|
| name | process name as in openLCA |
| UUID | process UUID (must match `data/impact_factor_map.csv`) |
| reference_flow, reference_unit | e.g. `Electricity`, `kWh` |
| Global Warming Potential [100 yr] - TRACI 2.1 (NETL) [kg CO2e] | score per unit |
| Acidification Potential - TRACI 2.1 (NETL) [kg SO2e] | |
| Water Consumption (NETL) [kg water] | |
| Particulate Matter Formation Potential - TRACI 2.1 (NETL) [kg PM2.5e] | |
| Ozone Depletion Potential - TRACI 2.1 (NETL) [kg CFC-11e] | |
| Photochemical Smog Formation Potential- TRACI 2.1 (NETL) [kg O3e] | |
| Eutrophication Potential - TRACI 2.1 (NETL) [kg Ne] | |

Column matching is by the fragment before the dash (e.g. "Global Warming"), see `src/biocarb/lca.py::CATS`.

## Provenance note (September 2026)
The three NETL SubPC rows were regenerated from openLCA product-system exports (results per 3600 MJ of electricity, divided by 1000 to obtain per-kWh scores). With these values the v19 inventory reproduces the published v19 results exactly (0.238 and 0.163 kg CO~2~e per kg mortar).

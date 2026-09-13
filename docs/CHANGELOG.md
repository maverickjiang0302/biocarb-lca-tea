# Changes from manuscript v19 to v20 (model version 1.0.0)

Inventory / LCA
- Baseline cement changed from ecoinvent "cement, Portland | US" to ASTM C595 Type IL built from clinker, limestone, gypsum and grinding electricity (validated against the PCA 2021 EPD, −2.5 %). All cements (IL, LC3) are built from the same components; the fly-ash mortar uses IL + 30 % fly ash (cut-off) instead of the ecoinvent "portland fly ash cement 21–35 % | RoW" dataset.
- CO2 uptake for the LCA/TEA is field-adjusted and net of pre-existing carbonate: 0.30 kg CaO/kg RCF × 44.01/56.08 × (CE 0.80 − CE0 0.165) = 0.149 kg CO2/kg RCF (v19: 0.20, gross). Laboratory data (0.365 kg/kg, CaO 57.8 %) reported unchanged as raw data.
- Tannic acid make-up corrected from 4.57e-7 to 4.5e-4 kg per kg mortar (factor ≈1000; v19 unit error). TA now purchased; impacts via the extraction inventory as proxy.
- CO2 supply modelled as NETL SubPC-with-capture electricity at 0.910 kg CO2/kWh; the accompanying electricity (0.0113 kWh per kg mortar) is added to the functional unit and supplied to all non-BioCarb systems from the same plant without capture (v19: 0.017 kWh). Mineralized CO2 is not credited separately (NETL CO2U convention; a -1 credit would double count the avoided plant emission).
- CO2 utilization 100 % in base case (v19 implicit 100 %); 80–100 % in sensitivity with vented CO2 counted.
- Recycled process water no longer charged as tap water; slurry water credited against mixing water at ready-mix scale.
- Column blower electricity added (Eq. S6). Stages re-labelled; CO2 mineralization shown separately.

TEA
- Two deployment scales replacing the 2.6 kt/yr hand-mixer site: 100 kt/yr dry-mix plant (A) and 60 kt/yr ready-mix plant (B).
- Equipment: vendor quotes scaled within one order of magnitude, Towler & Sinnott (2013) correlations otherwise; on-site TA extraction plant removed.
- Labor scaled by unit operations; 2024 cost year (CEPCI 800); plant life 20 yr; prices updated (USGS, EIA, BLS).
- LC3 priced at 0.8/1.0/1.15 × Type IL; RCF, CO2 and TA prices as sensitivity variables.

Analysis
- Monte Carlo (n = 1000) on all parameters with ranges; tornado; break-even sweeps; marginal abatement cost.
- Global Gt/yr potential removed from the main text (see SI note).


v1.1.0 (2026-09-11)
- Flue-gas CO2 scenario removed. Table 1 (systems) replaced by Fig. 1 process-flow diagram; literature uptake comparison restored as Table 1 with apparent-CE normalization (Eq. S24). LC3 price basis and ODP literature added. Fig. 6 reduced to four lines per panel; GWP tornado added to Fig. 7; literature abatement-cost benchmarks added to Fig. 8b (Table S19). Site-mixing/plant-gate boundary made explicit; MSP per kg of product as sold reported.


v1.1.1 (2026-09-11)
- Fig. 6: GWP sweeps drawn with the electricity co-product credited at the no-capture rate (sweeps.csv gains E_kWh and GWP_credited), so the Type IL and fly-ash references are flat; fly-ash MSP line drawn per scale.
- Fig. 7b and Fig. S1: MSP tornado reported as the margin over the same-scale Type IL mortar (tornado CSVs gain dMSP_vs_IL, dMSP_vs_FA, MSP_minus_IL, MSP_minus_FA); parameters with no effect dropped from tornados.
- Fig. 8b rebuilt with cement-sector abatement-cost benchmarks (data/abatement_cost_literature.csv, converted to 2024 USD) and this study's fly-ash and LC3 values; new results/mac_by_baseline.csv (MAC against IL, FA and LC3 baselines).
- SI Table S17 header reads base values from results; Table S19 and a MAC-by-baseline table regenerated; build_si.py writes the manuscript in UTF-8 explicitly.
- Manuscript: Methods 2.5, Sections 3.4-3.5, captions of Figs 6-8 and references 47-50 updated; CO2-price sensitivity corrected from 0.13 to 0.10 cents/kg.


v1.2.0 (2026-09-12) - manuscript v21
- TEA: purified CO2 purchased at a market price of 60 USD/t (Monte Carlo 40-120; IEA 2019 capture-and-purification cost range) instead of a zero transfer price. BioCarb MSP +0.06 c/kg (ready-mix 5.17, dry-mix 6.34 c/kg); MAC vs Type IL -77 (ready-mix) and +258 USD/t (dry-mix).
- Fig. 8 rebuilt as one panel: this study (base case + Monte Carlo 5th-95th percentile) against concrete-producer values derived from SDSN (2022) and the pass-through premium of kiln CCS; former panel (a) removed (values remain in Table S14 and results/mac_by_baseline.csv). data/abatement_cost_literature.csv gains perspective/fig8 columns.
- Fig. 1 simplified to process names, equipment and technologies; Fig. 3 net-total markers removed; Figs 3 and 5 use short binder labels; tornado parameters labelled in words; all figures larger fonts (Arial, 11 pt base, 300 dpi); graphic abstract added (figures/Fig0_graphic_abstract.png); Fig. 2 file renamed Fig2_lab_data.png.
- Wording: deployment 'scenarios' A/B instead of 'scales'; all references to the superseded v19 draft removed (build_si.house_style). Table 1 regenerated in the authors' layout with numbered references (data/literature_uptake.csv: technology, condition, ..., ref_no columns); new references 51-53 (Siriruang 2016, Pei 2018, Chen 2016), 49 SDSN 2022, 50 IEA 2019.
- Manuscript v21 built by src/build_manuscript_v21.py from the authors' edited v20 Word file (manuscript/manuscript_v20_edited.md) and results/*.csv; Word export with a Times New Roman reference document (manuscript/reference_tnr.docx). Extra sweeps: price_fa, price_lc3_factor, price_co2.


v1.2.1 (2026-09-13) - SI revision
- Flue-gas CO2 dataset and code vestige removed (data/impact_factor_map.csv, inventory.py); scenario wording throughout the SI.
- SI: Text S6, Table S2 (laboratory data) and Figure S1 deleted; Tables S3-S19 renumbered S2-S18; parameter table gains a 'process' column; TEA equations cite the NREL DCF convention (Davis et al. 2014, new ref. 54).
- Provenance columns in data/parameters.csv, tea_parameters.csv and equipment.csv now name the actual sources (laboratory data of this work, vendor specifications, Scrivener et al. 2018, Davis et al. 2014) instead of the superseded draft.
- Manuscript cross-references to SI tables updated by src/build_manuscript_v21.py.

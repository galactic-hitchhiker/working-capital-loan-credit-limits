# Item 1.03 versus combined Item 1.03 + qualified Item 2.04

Sources: run_001 and run_002 inventory/disclosure_events.csv, panel/panel.csv, models/stage_membership.csv, models/selection.json, models/metrics.csv.

Filing counts below are for candidate (screen-eligible) issuers in run_002, before 2026-09-07. Item 2.04 counts include only QUALIFIED_DEFAULT. Both is the overlap: subtract it when combining filing counts. Panel events are distinct first-event filings with at least one positive monthly panel row, before stage-boundary purging. These are disclosure events, not independently verified defaults.

Year is filing/event year. Stage describes decision dates in that year, not an exact allocation of events: the 60-day horizon can cross a year boundary. Historical events can exclude later observations; 2026 only provides follow-up, with no 2026 decision rows.

| Year | Item 1.03 filings | Qualified Item 2.04 filings | Both | Original panel events | Combined panel events | Use of decision-year observations |
|---|---:|---:|---:|---:|---:|---|
| 2004 | 15 | 0 | 0 | 0 | 0 | Historical exclusions only |
| 2005 | 34 | 0 | 0 | 0 | 0 | Historical exclusions only |
| 2006 | 27 | 0 | 0 | 0 | 0 | Historical exclusions only |
| 2007 | 17 | 0 | 0 | 0 | 0 | Historical exclusions only |
| 2008 | 24 | 0 | 0 | 0 | 0 | Historical exclusions only |
| 2009 | 61 | 0 | 0 | 0 | 0 | Historical exclusions only |
| 2010 | 41 | 26 | 3 | 0 | 0 | Historical exclusions only |
| 2011 | 37 | 23 | 7 | 4 | 5 | Training |
| 2012 | 78 | 34 | 7 | 19 | 20 | Training |
| 2013 | 84 | 31 | 9 | 25 | 22 | Training |
| 2014 | 84 | 28 | 11 | 30 | 31 | Training |
| 2015 | 86 | 41 | 21 | 27 | 21 | Training |
| 2016 | 168 | 73 | 43 | 31 | 31 | Training |
| 2017 | 109 | 45 | 26 | 24 | 22 | Temporal tuning / refit |
| 2018 | 87 | 37 | 22 | 27 | 29 | Temporal tuning / refit |
| 2019 | 109 | 57 | 29 | 37 | 42 | Calibration |
| 2020 | 169 | 57 | 38 | 63 | 61 | Selection / robustness |
| 2021 | 60 | 18 | 4 | 7 | 13 | Selection / robustness |
| 2022 | 36 | 25 | 7 | 18 | 23 | Selection / robustness |
| 2023 | 146 | 67 | 38 | 60 | 61 | Held-out evaluation |
| 2024 | 139 | 58 | 30 | 64 | 65 | Held-out evaluation |
| 2025 | 82 | 42 | 13 | 33 | 33 | Held-out evaluation |
| 2026 | 40 | 23 | 7 | 3 | 1 | Follow-up only (partial year) |

## Selected model metrics

The target and evaluation population change between runs, so this is a descriptive comparison, not a controlled estimate of the effect of adding Item 2.04.

| Metric | run_001 | run_002 |
|---|---:|---:|
| model | random_forest | xgboost |
| selection_ap_lift | 30.72051867958184 | 17.282413119386344 |
| selection_brier_skill | 0.011964776043051462 | 0.009250046146486057 |
| test_ap_lift | 12.991080102225956 | 10.675101814460437 |
| test_brier_skill | 0.011414000036433336 | -0.008685535540996936 |
| retained_distinct_events | 460 | 464 |
| selection: rows | 124931 | 116899 |
| selection: positives | 152 | 161 |
| selection: roc_auc | 0.8594091458962603 | 0.8860344111871687 |
| selection: average_precision | 0.03737678269842105 | 0.02380232946578843 |
| selection: brier | 0.0012006519723786607 | 0.0013626636020225415 |
| selection: precision | 0.06956521739130435 | 0.06666666666666667 |
| selection: recall | 0.15789473684210525 | 0.10559006211180125 |
| selection: f1 | 0.096579476861167 | 0.08173076923076923 |
| test: rows | 136177 | 127543 |
| test: positives | 288 | 292 |
| test: roc_auc | 0.9088733880839018 | 0.9017218343037485 |
| test: average_precision | 0.027474764970891383 | 0.024439833858561015 |
| test: brier | 0.0020871531795469936 | 0.00230518091795932 |
| test: precision | 0.03969957081545064 | 0.04285714285714286 |
| test: recall | 0.1284722222222222 | 0.13356164383561644 |
| test: f1 | 0.060655737704918035 | 0.064891846921797 |

## Distinct events represented in each stage

Events are deduplicated within each stage. An event can appear in multiple stages through different decision dates; do not sum these counts as unique events.

| Stage | Original | Combined |
|---|---:|---:|
| training | 133 | 126 |
| tuning | 47 | 47 |
| calibration | 35 | 39 |
| selection | 85 | 92 |
| test | 160 | 160 |

## Why the extra filings did not produce a clear improvement

- Full inventory: 1,915 Item 1.03 filings and 770 qualified Item 2.04 filings. Among screen-eligible issuers: 1,733 and 685, respectively, with 315 filings in both groups. These counts precede first-event selection and financial-data filtering.
- The combined panel contains 350 of the original first-event filings plus 130 Item-2.04-only first-event filings. It no longer contains 122 of the original first-event filings. These can be displaced by an earlier qualifying disclosure or excluded by unresolved evidence; this comparison does not attribute each loss to a cause.
- Distinct positive events before stage purging: 472 to 480. After purging: 460 to 464. Positive company-month labels: 875 to 888 before purging.
- Labeled company-months decrease from 588,111 to 548,118. The combined audit records 39,062 rows excluded after an unresolved Item 2.04 and another 362 whose horizon includes unresolved evidence. These exclusions are not identical to the net row-count change because other label/exclusion outcomes also change.
- The combined inventory reports 864 Item 2.04 filings with no matching review and 856 MANUAL_REVIEW filings. The discovery audit starts on 2010-01-01, whereas the inventory includes earlier histories. Zero qualified counts before 2010 reflect absent review coverage and do not establish that no qualifying events occurred then. The missing-review count is not attributed entirely to that cutoff without a filing-level coverage reconciliation.
- selection.json describes selection-period performance (2020–2022), not final held-out performance. Both the target and evaluated population change. More event labels alone do not establish better predictive performance.

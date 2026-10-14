# Recovering financial features from complete statements

Company Facts is a useful first source, but it does not preserve the complete
statement presentation and calculation structure. Missing `Liabilities` need not
mean missing financial reporting. Some balance sheets list current liabilities,
long-term debt, and other obligations without one liabilities subtotal. Issuers can
also use custom concepts or apply a standard concept to a differently scoped row.

The [SEC Financial Statement and Notes Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-notes-data-sets)
provide another public source. They include standard and custom concepts, original
statement labels, numeric values, dimensional information, and calculation
relationships. They can be downloaded by archive instead of requesting each filing
individually. The smaller [Financial Statement Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets)
contain face-statement values and labels, but the notes datasets additionally supply
the calculation relationships used here.

## Implemented extraction

`mcf.data.statement_facts` reads the SUB, PRE, TAG, NUM and CAL tables directly from
downloaded ZIPs. It writes auditable issuer supplements for assets, total liabilities,
current assets, current liabilities, noncurrent liabilities, and cash equivalents.
Annual flows are not inferred from the bulk dataset's rounded durations.

Acceptance rules:

1. Use domestic periodic filings, consolidated USD instant facts, and nonparenthetical
   primary balance-sheet rows. Reject dimensional and co-registrant values.
2. Pin each exact period end to an agreeing Assets or LiabilitiesAndStockholdersEquity
   value in Company Facts from the **same accession**. Bulk dates are rounded and
   must not be treated as exact fiscal dates. Contexts with different date proximity
   values remain separate. Reject ambiguous date anchors or conflicting values.
3. Accept recognized standard totals; map custom totals only when both taxonomy and
   face-statement labels exactly identify the requested total.
4. Reconstruct a missing standard subtotal only when every calculation child has an
   explicit value. Keep separate calculation groups separate and preserve arc signs.
5. Recover liabilities from the reported liabilities-and-equity equation only when
   all nonzero branches are recognized liability or equity components and the full
   equation reconciles within the reported numeric precision. Temporary equity and
   noncontrolling interests are classified separately. Unknown nonzero branches
   prevent recovery. A non-amount CommitmentsAndContingencies disclosure can be
   omitted only when the remaining amounts reconcile to the reported parent.
6. Preserve source amounts, tags, taxonomy versions, filing date, accession, archive
   hash, precision, and calculation basis. Filing-day values become available on the
   next day. Native observations block same/later supplementary vintages, including
   when the native observations conflict. A supported supplementary total can replace
   a previously computed current-plus-noncurrent estimate.

The downloaded archives use signed `-1`/`1` calculation weights despite the older
documentation's boolean description of the `negative` column. The importer detects
the observed encoding domain and rejects ambiguous/unsupported domains. It does not
choose a sign interpretation based on a desired feature value. Literal quotation
marks in the SEC TSV files are not treated as CSV quote delimiters.

There is also a local Company Facts improvement: total LiabilitiesAndStockholdersEquity
can supply missing Assets through the balance-sheet identity. It never supersedes
an Assets observation for that period that was already known when the fallback was
filed. It can introduce a newer reporting period, affecting related ratios or
financial eligibility; this is not limited to filling empty cells.

## Pilot evidence

The pilot uses **2017 Q4 and 2025 Q3**, covering different parts of the study period.
The importer produced 87,371 dated source facts for 5,925 issuers. Most duplicate
already available Company Facts values and are suppressed by the native-priority
rule. There are 2,558 liabilities reconstructions from reconciled balance-sheet
equations; 1,582 lack a usable original liabilities value at the filing-period
comparison date. These are source-fact counts, not additional monthly rows.

Of the reconstructions compared with an existing same-filing total, 852 agree and
37 differ. Of those differences, 36 concern the previous current-plus-noncurrent
formula; one concerns a direct native total, which remains protected by the
native-priority rule. These comparisons identify scope disagreements, not an
independent estimate of extraction accuracy. Two source checks illustrate why
statement structure adds information:

- Accession `0000012400-17-000011` labels `LiabilitiesNoncurrent` as “Total deferred
  credits and other liabilities” and lists long-term debt separately. For 2017-09-30,
  current plus that reported noncurrent amount gives 386,484,000. The full statement
  equation includes another 339,860,000 of debt, giving liabilities of 726,344,000.
- Accession `0000059527-17-000037` labels `LiabilitiesNoncurrent` as “Total Liabilities”.
  Adding current liabilities again gives 2,005,031,000. The full equation gives
  liabilities of 1,465,175,000 and reconciles to assets of 2,411,103,000 and equity
  of 945,928,000.

The assets-only rebuild adds 2,621 labeled observations and removes 11, a **net
increase of 2,610**. Its 566,217 rows cover 8,788 companies, compared with 563,607
rows and 8,770 companies in run 005. Removal or revision can occur when a newly
recoverable reporting period supersedes an older balance sheet. Shared labels were
checked and do not change. The 1,052 positive rows and 573 distinct positive events
are unchanged in that rebuild.

The final panel at `results/run_005_statement_coverage/panel` also contains 566,217
rows and 8,788 companies. On the identical expanded sample, adding the two statement
archives yields:

| Feature | Missing cells recovered |
| --- | ---: |
| Liabilities / assets | 1,610 |
| 12-month change in liabilities / assets | 527 |
| Operating cash flow / average liabilities | 961 |
| Current ratio | 7 |
| Working capital / assets | 7 |
| **Total** | **3,112** |

No previously observed cells become missing in the statement-source comparison.
It revises 532 previously calculated feature cells: 51 liabilities/assets, 148
leverage changes, and 333 cash-flow/average-liabilities ratios. This reflects the
statement-based accounting totals and their use across monthly dates and beginning/
ending balance sheets. Complete rows increase from 363,700 to 364,096 on that sample.

Compared directly with run 005, both improvements together fill 5,362 cells on the
563,596 shared rows and make 81 cells missing as newer balance periods become
available. There are 2,621 added rows and 11 removed rows. Complete rows across the
full final panel increase from 363,033 to 364,096. The broader sample introduces
additional partially observed rows, so absolute missing-cell totals across the two
different panels should not be interpreted as a fill-only comparison.

Both merge comparisons verify unchanged labels on shared observations and check
feature availability against every new/shared decision date. Machine-readable
results are `comparison_to_run_005.json` and `statement_source_only.json` beside the
final panel directory. Validation ran 155 tests, with one local-data-dependent skip.

## Reproduce

Download archives from the SEC page, using your identifying `SEC_USER_AGENT`. Then:

```sh
.venv/bin/python -m mcf.data.statement_facts \
  --archives results/sec/financial_statements/2017q4_notes.zip \
             results/sec/financial_statements/2025q3_notes.zip \
  --dataset ../dataset \
  --inventory results/run_005_recurrent_disclosures_retrained/inventory/issuer_inventory.csv \
  --output-dir results/statement_recovery_2017_2025

.venv/bin/python -m mcf.data.empirical panel \
  --dataset ../dataset \
  --inventory results/run_005_recurrent_disclosures_retrained/inventory \
  --config results/run_005_recurrent_disclosures_retrained/panel/design.json \
  --statement-facts results/statement_recovery_2017_2025/companies \
  --output-dir results/run_005_statement_coverage/panel
```

Choose new output directories when rerunning. The end-to-end
`mcf.workflows.payment_default_proxy` requires `--statement-facts` for training.
For broader historical coverage, supply additional SEC notes ZIPs to the same
importer. Both the input archives and per-issuer supplements are hashed, and the
panel records the supplement hashes alongside the Company Facts hashes.

Outputs include the importer `audit.json`, `validation.json` with source examples,
and the rebuilt panel with full feature provenance. `mcf.data.coverage.compare_expanded_panels`
compares shared, added, removed and revised observations without pretending that
an expanded panel is a fill-only change.

This is a two-quarter source pilot, not complete statement enrichment of 2011–2025.
It leaves the annual-flow eligibility requirement in place. Models must be rerun
before making any claim about predictive improvement, and the already-examined
evaluation period remains retrospective. Some remaining cases still require the
original filing/XBRL package, especially dimensional contexts, ambiguous custom
concepts, incomplete calculation networks, and unclassified capital components.

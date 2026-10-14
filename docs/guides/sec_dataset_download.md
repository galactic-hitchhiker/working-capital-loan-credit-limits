# Download a complete SEC dataset

`scripts/download_sec_dataset.py` is standalone: Python 3.10+ and its standard
library are sufficient. It does not call OpenAI or train models.

From the repository root:

```sh
export SEC_USER_AGENT="Your Name your-email@example.com"
python3 scripts/download_sec_dataset.py \
  --output-dir ../dataset_full \
  --start-year 2009 \
  --end-year 2026
```

Use your identifying name/organization and contact email. Start with 2009 to
provide available financial history before 2010 decisions. The year filter applies
only to statement archives: Company Facts and submissions are complete current
bulk snapshots, including their available historical records. Downloading them
does not change the study configuration's decision dates or outcome cutoff.

Sources:

- [SEC API bulk archives](https://www.sec.gov/search-filings/edgar-application-programming-interfaces):
  Company Facts and submissions JSON, including supplementary submission-history files.
- [Financial Statement and Notes Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-notes-data-sets):
  statement presentation, numbers, concepts, calculation relationships and notes.
  The script discovers current links, using quarterly archives when both a quarter
  and constituent monthly files are listed. It downloads only published archives;
  selecting the current year does not imply full-year availability.
- [Financial Statement Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets):
  the separate, smaller quarterly face-financial archives. These are included
  by default alongside the Notes archives.

The layout is:

```text
dataset_full/
  companyfacts.zip
  companyfacts/CIK##########.json
  submissions.zip
  submissions/CIK##########.json
  submissions/CIK##########-submissions-###.json
  financial_statements/
    archives/2010q1_notes_1.zip
    2010q1_notes_1/sub.tsv
    2010q1_notes_1/num.tsv
    face/archives/2010q1.zip
    face/2010q1/sub.tsv
    ...
  statement_archive_index.html
  face_statement_archive_index.html
  download_manifest.json
```

Some SEC archives have versioned names, for example `2010q1_notes_1.zip`.
The downloader preserves these names. Use `*notes*.zip` when passing all
archives to the statement importer so those periods are included.

All ZIP contents are unpacked, with each statement period kept separate. The
original ZIPs are retained because `mcf.data.statement_facts` reads the Notes
archives directly. Face-financial archives remain separate and are not used by
that importer.
The full dataset requires substantial disk space, especially unpacked notes.
Free space is checked against each ZIP's declared unpacked size before extraction.

Useful options:

```sh
# Preview URLs and destinations; fetches only the SEC index.
python3 scripts/download_sec_dataset.py --output-dir ../dataset_full --dry-run

# Fetch both statement series, leaving Company Facts/submissions untouched.
python3 scripts/download_sec_dataset.py --output-dir ../dataset_full \
  --datasets statements face_statements --start-year 2010 --end-year 2026

# Fetch only the smaller quarterly face-financial series.
python3 scripts/download_sec_dataset.py --output-dir ../dataset_full \
  --datasets face_statements --start-year 2010 --end-year 2026

# Keep only ZIPs initially; rerun without this flag to unpack later.
python3 scripts/download_sec_dataset.py --output-dir ../dataset_full --download-only
```

Rerun the same command after an interruption. Partial downloads resume when the
server provides a usable ETag or Last-Modified validator; otherwise they restart.
An updated nightly snapshot restarts instead of being appended to an older one.
Completed archives are reused, not automatically refreshed. For a new source
snapshot, use a new output directory. Do not run two copies against the same output
directory concurrently.

Downloads run sequentially with request spacing and bounded retries for transient
errors. ZIP CRC checks precede completion. Extraction rejects path traversal and
symlinks, stages files before publishing the directory, and does not merge into an
existing unmanaged dataset. A manifest records source URLs, archive SHA-256 hashes,
sizes, extraction destinations and check timestamps. It is a local integrity record,
not an SEC-provided checksum. Extraction markers allow completed unpacking to be
skipped; manually altered or incomplete output should be rebuilt in a fresh directory.

## Feed the feature importer

After building an inventory for the downloaded snapshot, pass its
`issuer_inventory.csv` to the importer. For a comparison restricted to the existing
run 005 candidate universe, use:

```sh
.venv/bin/python -m mcf.data.statement_facts \
  --archives ../dataset_full/financial_statements/archives/*notes*.zip \
  --dataset ../dataset_full \
  --inventory results/run_005_recurrent_disclosures_retrained/inventory/issuer_inventory.csv \
  --output-dir results/statement_recovery_full
```

The importer writes `audit.json` immediately and updates it after each archive.
Its `status` is `in_progress` until all selected archives finish. Company files
appear as soon as a processed archive yields facts. If interrupted, rerun the
same command with the same archive list, dataset and inventory; completed
archives are verified and skipped. A different input list needs a fresh output
directory. A header-only early CAL table produces an audit count and no
calculation-based recoveries; it is not an import failure.

Then use `--dataset ../dataset_full` and
`--statement-facts results/statement_recovery_full/companies` when rebuilding a
panel or running the full workflow. The statement importer has previously been
validated on a two-quarter pilot; inspect the full historical import's audit before
making coverage claims. New submissions may also require refreshed disclosure
reviews. Existing review files do not automatically cover newly downloaded filings.

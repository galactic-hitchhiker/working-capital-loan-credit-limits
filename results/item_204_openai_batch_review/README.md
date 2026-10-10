# Item 2.04 classification run

OpenAI Batch review of 2,968 SEC Item 2.04 filings. `audit.json` records the model, inputs, processing status, and final label counts: 1,281 `NON_DEFAULT`, 961 `QUALIFIED_DEFAULT`, and 726 `MANUAL_REVIEW`.

`classifications.jsonl` is the tracked reusable export. It includes the classification and review evidence for each filing. The CSV export, review log, per-filing review files, and batch records remain local and are excluded from Git. The export retains original absolute paths as historical provenance.

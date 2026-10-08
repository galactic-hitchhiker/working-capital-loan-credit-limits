# Item 1.03/2.04 enrichment

For the current bankruptcy/payment-failure target, Item 1.03 qualifies
automatically. Discover Item 2.04 and review with `--payment-failure-only`. See the
[combined-target guide](../../../docs/bankruptcy_payment_failure_workflow.md).
The narrower payment-only design still requires reviews of both items.
The legacy package name is retained; defaults below still review Item 2.04 alone.

OpenAI Batch is the only AI integration. From the repository root, with
`OPENAI_API_KEY` set, classify all filings in the source inventory with:

```bash
.venv/bin/python -m mcf.enrichment.item204.reviewers.openai_batch
```

Defaults: `gpt-6-luna`, all Item 2.04 filings, and full visible filing text.
Input is `results/item_204_pipeline/source/filings.jsonl`, HTML is in
`results/item_204_pipeline/source/html`, and output goes to
`results/item_204_openai_batch_review/`.

The first run submits jobs. Rerun the same command later to collect results.
Existing completed reviews and pending requests are reused.

To discover and download SEC filings before AI classification:

```bash
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.enrichment.item204.workflow \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_pipeline
```

See [the workflow guide](../../../docs/item_204_workflow.md) for every parameter,
output locations, and label definitions.

Existing `rules/classifications.jsonl` and `rules/html` remain usable as source
metadata/cache until discovery runs. Their old labels are ignored; all filings
are reviewed. There is no rule-based event classification stage.

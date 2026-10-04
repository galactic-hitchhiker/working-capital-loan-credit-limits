# Item 2.04 enrichment

Run from the repository root:

```bash
.venv/bin/python -m mcf.enrichment.item204.reviewers.ollama --limit 20
```

Default local model: `qwen3.5:9b`. Ollama must be running.

See [the workflow](../../../docs/item_204_workflow.md) for discovery, OpenAI review, outputs, and conservative label rules.

# Item 2.04 enrichment

Run from the repository root:

```bash
SEC_USER_AGENT='Your Name your.email@example.com' \
.venv/bin/python -m mcf.enrichment.item204.workflow \
  --submissions ../dataset/submissions \
  --output-dir results/item_204_pipeline
```

This runs deterministic classification first and sends only unresolved cases to
the LLM. The default local model is `gemma3:12b`. Install it with
`ollama pull gemma3:12b`, then ensure Ollama is running. Use `--model MODEL_NAME`
to override it with another installed model.

See [the workflow](../../../docs/item_204_workflow.md) for discovery, OpenAI review, outputs, and conservative label rules.

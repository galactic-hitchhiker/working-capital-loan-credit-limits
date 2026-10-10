# Saved runs

Each `run_*` directory has a short README describing its target and setup. Runs 001–003 use first-disclosure targets; runs 004–006 use recurrent bankruptcy or payment-failure disclosure episodes. The coverage directories record panel feature investigations, and run 006 contains paired models with and without financial statement enrichment.

The run directories contain model metrics, predictions, fitted models, and comparisons. Generated `inventory/`, `panel/`, and `models*/predictions.csv` files are kept locally and excluded from Git. Run 006's extracted statement facts live with the source dataset at `../dataset_full/statement_facts/`. The Item 2.04 classification run is in [`item_204_openai_batch_review/`](item_204_openai_batch_review/README.md).

These are historical outputs. Some audit and manifest files record their original absolute paths, which may no longer resolve after the directory names were updated.

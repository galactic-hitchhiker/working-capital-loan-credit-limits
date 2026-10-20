# Master's Thesis Deliverables

The Word files in this directory were formatted from the supplied RAF thesis and report examples. The PDFs are LibreOffice verification renders of the same files.

- `Djordje_Velickovic_Master_Thesis.docx` — formatted 48-page thesis with the RAF reference cover, a page-accurate table of contents, list of figures, list of tables, 27 formatted data tables, 3 figures and 16 numbered editable equations.
- `Djordje_Velickovic_Master_Thesis_Report.docx` — three-page draft report on the completed thesis, following the supplied memorandum and report structure.

Before official submission, replace the following administrative placeholders:

- Thesis: student ID number.
- Report: session number, session date, student ID, report date, the two unconfirmed commission members, and all commission roles.

The report is a draft for review and signature by the formally appointed commission. It does not assert that the administrative details or final acceptance have already been approved.

## Export the Thesis to Word

From the repository root, run:

```bash
.venv/bin/python scripts/build_thesis_documents.py --word-only
```

The command rebuilds `Djordje_Velickovic_Master_Thesis.docx` from the Markdown sources using Times New Roman 12 pt. It creates no deliverable PDF or committee report; any temporary pagination renders remain under `build/`.

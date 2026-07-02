# Install Verification And Workflows

## Verify The Install

Run the synthetic fixture through the core validator:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py validate data/examples/synthetic_case
```

Check that the case-builder app can plan a dry run:

```bash
PYTHONPATH=src python -m case_builder.cli plan data/cases/install_smoke \
  --title "Install Smoke Test" \
  --subject "Synthetic public-source smoke test for setup verification"
```

If the package entry point is installed, the same app is available as:

```bash
trcr-case-builder plan data/cases/install_smoke \
  --title "Install Smoke Test" \
  --subject "Synthetic public-source smoke test for setup verification"
```

The dry-run planner records intended operations in JSON output. Add `--execute`
only when you want the app to create or modify the case workspace.

## Create The First Case

Initialize a local case workspace:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py init-case data/cases/<case_slug> \
  --title "<Case Title>"
```

Register a source manually when it should be tracked before extraction:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py add-source data/cases/<case_slug> \
  --title "<Source Title>" \
  --url "<URL or local path>" \
  --source-type news_article \
  --reliability-grade B \
  --notes "Initial source registration"
```

Or capture a public URL directly:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py ingest-url data/cases/<case_slug> \
  "<URL>" \
  --source-type news_article \
  --reliability-grade B
```

Draft an extraction packet for review:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py draft-extraction data/cases/<case_slug> <SOURCE_ID>
```

After the packet is filled and reviewed, import and validate it:

```bash
python .agents/skills/truecrime-cult-research/scripts/tcr.py import-extraction data/cases/<case_slug> \
  data/cases/<case_slug>/staging/extractions/<SOURCE_ID>_extraction.json

python .agents/skills/truecrime-cult-research/scripts/tcr.py validate data/cases/<case_slug>
python .agents/skills/truecrime-cult-research/scripts/tcr.py report data/cases/<case_slug>
```

## Run The Case-Builder App

The case-builder app wraps the same ledger operations in a resumable workflow.
The ledger under `records/*.jsonl` remains the source of truth.

Dry run:

```bash
trcr-case-builder plan data/cases/<case_slug> \
  --title "<Case Title>" \
  --subject "<case subject, source question, names, dates, and places>"
```

Execute deterministic commands:

```bash
trcr-case-builder plan data/cases/<case_slug> \
  --title "<Case Title>" \
  --subject "<case subject, source question, names, dates, and places>" \
  --execute
```

Run with LangGraph checkpoints:

```bash
trcr-case-builder plan data/cases/<case_slug> \
  --title "<Case Title>" \
  --subject "<case subject, source question, names, dates, and places>" \
  --runner langgraph \
  --checkpoint \
  --execute
```

Resume after human packet review:

```bash
trcr-case-builder resume data/cases/<case_slug> \
  --thread <thread_id> \
  --approve-packet <SOURCE_ID>_extraction.json \
  --execute
```

Resume after public-export review:

```bash
trcr-case-builder resume data/cases/<case_slug> \
  --thread <thread_id> \
  --approve-export \
  --execute
```

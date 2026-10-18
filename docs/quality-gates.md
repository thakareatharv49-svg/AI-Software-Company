# Product QA evidence and release gates

The factory must treat a successful model response or a single smoke command as insufficient evidence that a product is ready to deliver.

## Evidence collected

The execution pipeline records a bounded per-command QA ledger for each run:

- The configured QA command and its result.
- The generated Python test suite when present and not already covered by the configured command.
- Conventional JavaScript/TypeScript test suites supported by Node's built-in test runner when present.
- Exit status and duration for each command, so reviewers can distinguish what actually ran from checks that were not run.

The ledger is attached to the pipeline result and included in the durable mission QA evidence. Command arguments and subprocess output are redacted before persistence, and evidence is capped to avoid unbounded mission history. Older pipeline results without a ledger remain readable and are marked as having no per-command ledger; they are not represented as having detailed evidence.

## Delivery requirements

- The product's own behavioral tests must pass; a custom build or smoke command cannot replace them.
- If Python or supported Node test files are present, their suites are executed independently when needed.
- Any failed QA command blocks delivery before security review/publication.
- Artifact validation and security review remain separate gates; passing tests alone does not authorize release.
- Evidence is diagnostic provenance from the executed pipeline, not a claim that unrun build, startup, or integration checks passed.

## Regression tests

Run the focused evidence tests with:

```powershell
python -m pytest tests/unit/company/test_factory_qa_evidence.py -q
```

Run the pipeline and product QA regression tests with:

```powershell
python -m pytest tests/unit/company tests/integration/test_deterministic_product_qa.py -q
```
